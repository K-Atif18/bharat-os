"""Authentication, consent gating, and the boundary around user data."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.dependencies import SESSION_COOKIE
from bharat_os.models.auth import UserSession
from bharat_os.models.document import UserDocument
from bharat_os.security import MIN_PASSWORD_LENGTH, hash_session_token
from helpers import EMAIL, PASSWORD, VALID_PROFILE, register


class TestRegistration:
    def test_creates_account_and_starts_a_session(self, client: TestClient) -> None:
        response = register(client)
        assert response.status_code == 201
        body = response.json()
        assert body["email"] == EMAIL
        assert body["has_profile"] is False
        assert SESSION_COOKIE in response.cookies

    def test_session_cookie_is_httponly(self, client: TestClient) -> None:
        """A cookie readable by JavaScript is stealable by any injected script."""
        response = register(client)
        header = response.headers["set-cookie"].lower()
        assert "httponly" in header
        assert "samesite=lax" in header

    def test_password_is_never_stored_in_plaintext(
        self, client: TestClient, session: Session
    ) -> None:
        from bharat_os.models.user import UserAccount

        register(client)
        stored = session.scalar(select(UserAccount.password_hash))
        assert stored is not None
        assert PASSWORD not in stored
        assert stored.startswith("$argon2")

    def test_session_token_is_not_stored(self, client: TestClient, session: Session) -> None:
        """Only a digest is persisted, so a database leak yields no usable sessions."""
        response = register(client)
        token = response.cookies[SESSION_COOKIE]
        rows = list(session.scalars(select(UserSession)).all())
        assert len(rows) == 1
        assert rows[0].token_hash != token
        assert rows[0].token_hash == hash_session_token(token)

    def test_short_password_is_rejected(self, client: TestClient) -> None:
        response = client.post(
            "/auth/register",
            json={"email": EMAIL, "password": "short", "consents": ["scheme_matching"]},
        )
        assert response.status_code == 422

    def test_matching_consent_is_required(self, client: TestClient) -> None:
        response = register(client, consents=["notifications"])
        assert response.status_code == 422
        assert "scheme_matching" in response.text

    def test_duplicate_email_is_rejected(self, client: TestClient) -> None:
        register(client)
        assert register(client).status_code == 409

    def test_email_is_normalised_to_lowercase(self, client: TestClient) -> None:
        register(client, email="Founder@Example.COM")
        response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert response.status_code == 200


class TestLogin:
    def test_valid_credentials_succeed(self, client: TestClient) -> None:
        register(client)
        client.cookies.clear()
        response = client.post("/auth/login", json={"email": EMAIL, "password": PASSWORD})
        assert response.status_code == 200
        assert SESSION_COOKIE in response.cookies

    def test_wrong_password_is_rejected(self, client: TestClient) -> None:
        register(client)
        response = client.post("/auth/login", json={"email": EMAIL, "password": "wrong" * 4})
        assert response.status_code == 401

    def test_unknown_email_gives_the_same_error_as_a_wrong_password(
        self, client: TestClient
    ) -> None:
        """Distinguishable errors turn a login form into an account enumerator."""
        register(client)
        wrong_password = client.post("/auth/login", json={"email": EMAIL, "password": "wrong" * 4})
        unknown_email = client.post(
            "/auth/login", json={"email": "nobody@example.com", "password": PASSWORD}
        )
        assert wrong_password.status_code == unknown_email.status_code == 401
        assert wrong_password.json() == unknown_email.json()


class TestSessionLifecycle:
    def test_logout_revokes_the_session(self, client: TestClient) -> None:
        register(client)
        assert client.get("/me").status_code == 200
        assert client.post("/auth/logout").status_code == 204
        assert client.get("/me").status_code == 401

    def test_revoked_session_cannot_be_replayed(self, client: TestClient) -> None:
        response = register(client)
        token = response.cookies[SESSION_COOKIE]
        client.post("/auth/logout")
        client.cookies.set(SESSION_COOKIE, token)
        assert client.get("/me").status_code == 401

    def test_expired_session_is_rejected(self, client: TestClient, session: Session) -> None:
        from datetime import UTC, datetime, timedelta

        register(client)
        row = session.scalars(select(UserSession)).one()
        row.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        session.commit()
        assert client.get("/me").status_code == 401

    def test_garbage_token_is_rejected(self, client: TestClient) -> None:
        client.cookies.set(SESSION_COOKIE, "not-a-real-token")
        assert client.get("/me").status_code == 401


class TestUnauthenticatedAccessIsRejected:
    """No endpoint touching user data may be reachable without a session.

    Parametrised over every such route so adding one without protecting it fails
    here rather than in production.
    """

    PROTECTED_ROUTES = [
        ("GET", "/me"),
        ("GET", "/me/consents"),
        ("POST", "/me/consents"),
        ("DELETE", "/me"),
        ("POST", "/auth/logout"),
        ("GET", "/profile"),
        ("PUT", "/profile"),
        ("DELETE", "/profile"),
        ("GET", "/matches"),
        ("GET", "/matches/{slug}"),
        ("GET", "/matches/{slug}/deep-dive"),
        ("GET", "/documents"),
        ("POST", "/documents"),
        ("DELETE", "/documents/{document_id}"),
        ("GET", "/matches/{slug}/documents"),
        ("GET", "/deadlines"),
        ("GET", "/deadlines/calendar.ics"),
        ("POST", "/matches/{slug}/draft"),
        ("GET", "/matches/{slug}/draft"),
        ("GET", "/applications"),
        ("POST", "/matches/{slug}/applications"),
        ("PATCH", "/applications/{application_id}"),
        ("POST", "/applications/{application_id}/outcome"),
        ("GET", "/review-queue"),
        ("POST", "/review-queue/{revision_id}/approve"),
        ("POST", "/review-queue/{revision_id}/reject"),
        ("POST", "/review-queue/{revision_id}/annotate"),
    ]

    @pytest.mark.parametrize(("method", "path"), PROTECTED_ROUTES)
    def test_requires_authentication(self, client: TestClient, method: str, path: str) -> None:
        client.cookies.clear()
        response = client.request(method, path, json={})
        assert response.status_code == 401, f"{method} {path} was reachable unauthenticated"

    def test_every_user_data_route_is_in_the_protected_list(self, client: TestClient) -> None:
        """Catches a new user-data route being added without a test guarding it."""
        from bharat_os.main import create_app

        # /matches/draftable lists which scheme slugs support drafting — no user
        # data, just static capability info. /schemes/*/outcome-stats is an
        # aggregate over de-identified outcomes, containing nothing that
        # identifies a contributor by design (see services.outcomes).
        # /freshness reports how recently each scheme's criteria were verified
        # against their official source — a property of the scheme catalogue,
        # not of any user, so it is public for the same reason /schemes is.
        public_prefixes = (
            "/health",
            "/schemes",
            "/freshness",
            "/auth/register",
            "/auth/login",
            "/matches/draftable",
        )
        documented = {(m, p) for m, p in self.PROTECTED_ROUTES}

        unguarded = []
        for route in create_app().routes:
            path = getattr(route, "path", "")
            methods = getattr(route, "methods", set()) - {"HEAD", "OPTIONS"}
            if not path or path.startswith(("/docs", "/redoc", "/openapi")):
                continue
            if path.startswith(public_prefixes):
                continue
            for method in methods:
                if (method, path) not in documented:
                    unguarded.append(f"{method} {path}")

        assert not unguarded, (
            f"routes not covered by the authentication test: {unguarded}. "
            "Add them to PROTECTED_ROUTES, or to public_prefixes if genuinely public."
        )

    def test_outcome_stats_requires_authentication_despite_the_schemes_prefix(
        self, client: TestClient
    ) -> None:
        """/schemes/*/outcome-stats matches the public /schemes prefix by path,
        but it is authenticated in the router. The prefix audit above cannot see
        that distinction, so it is asserted directly here."""
        client.cookies.clear()
        response = client.get("/schemes/sisfs/outcome-stats")
        assert response.status_code == 401


class TestConsentGating:
    def test_profile_access_requires_matching_consent(self, client: TestClient) -> None:
        register(client)
        client.post("/me/consents", json={"purpose": "scheme_matching", "granted": False})
        response = client.get("/profile")
        assert response.status_code == 403
        assert "scheme_matching" in response.text

    def test_withdrawing_matching_consent_deletes_the_profile(self, client: TestClient) -> None:
        """Consent that can be withdrawn without effect is not consent."""
        register(client)
        assert client.put("/profile", json=VALID_PROFILE).status_code == 200
        client.post("/me/consents", json={"purpose": "scheme_matching", "granted": False})
        assert client.get("/me").json()["has_profile"] is False

    def test_consent_can_be_regranted(self, client: TestClient) -> None:
        register(client)
        client.post("/me/consents", json={"purpose": "scheme_matching", "granted": False})
        client.post("/me/consents", json={"purpose": "scheme_matching", "granted": True})
        assert client.get("/profile").status_code == 404  # authorised again, no profile yet

    def test_optional_consents_are_not_required(self, client: TestClient) -> None:
        register(client)
        consents = {c["purpose"]: c["is_active"] for c in client.get("/me/consents").json()}
        assert consents == {"scheme_matching": True}
        assert client.put("/profile", json=VALID_PROFILE).status_code == 200

    def test_consent_records_the_policy_version(self, client: TestClient) -> None:
        from bharat_os.schemas.auth import CURRENT_POLICY_VERSION

        register(client)
        granted = client.get("/me/consents").json()[0]
        assert granted["policy_version"] == CURRENT_POLICY_VERSION
        assert granted["granted_at"] is not None
        assert granted["withdrawn_at"] is None


    def test_document_vault_requires_specific_consent(self, client: TestClient) -> None:
        register(client)
        response = client.post(
            "/documents",
            json={"document_type": "dpiit_certificate", "label": "DPIIT certificate"},
        )
        assert response.status_code == 403
        assert "document_storage" in response.text

    def test_withdrawing_document_consent_deletes_vault_records(
        self, client: TestClient, session: Session
    ) -> None:
        register(client, consents=["scheme_matching", "document_storage"])
        created = client.post(
            "/documents",
            json={"document_type": "dpiit_certificate", "label": "DPIIT certificate"},
        )
        assert created.status_code == 201

        client.post(
            "/me/consents",
            json={"purpose": "document_storage", "granted": False},
        )

        session.expire_all()
        assert list(session.scalars(select(UserDocument)).all()) == []
        assert client.get("/documents").status_code == 403

    def test_withdrawing_optional_consents_deletes_purpose_bound_records(
        self, client: TestClient, session: Session
    ) -> None:
        from datetime import UTC, datetime

        from bharat_os.models.application import Application, Outcome
        from bharat_os.models.notification import DeadlineNotification
        from bharat_os.models.scheme import Scheme, SchemeVersion
        from bharat_os.models.user import UserAccount

        register(
            client,
            consents=["scheme_matching", "outcome_analytics", "notifications"],
        )
        user_id = session.scalars(select(UserAccount.id)).one()
        version = SchemeVersion(
            scheme=Scheme(slug="consent-cleanup"),
            version=1,
            name="Consent Cleanup Scheme",
            summary="Used to verify purpose-bound deletion.",
            scheme_type="grant",
            status="active",
            administering_ministry="Ministry of Testing",
            target_segments=["startup"],
            sectors=[],
            states=[],
            benefit_description="Test benefit.",
            application_difficulty="low",
            effective_from=datetime.now(UTC),
        )
        session.add(version)
        session.flush()
        application = Application(user_id=user_id, scheme_version=version, status="rejected")
        application.outcome = Outcome(outcome_type="rejected")
        notification = DeadlineNotification(
            user_id=user_id,
            scheme_version_id=version.id,
            offset_days=7,
        )
        session.add_all([application, notification])
        session.commit()

        client.post(
            "/me/consents",
            json={"purpose": "outcome_analytics", "granted": False},
        )
        client.post(
            "/me/consents",
            json={"purpose": "notifications", "granted": False},
        )

        session.expire_all()
        assert list(session.scalars(select(Outcome)).all()) == []
        assert list(session.scalars(select(DeadlineNotification)).all()) == []
        assert session.scalars(select(Application)).one().user_id == user_id

    def test_outcome_capture_requires_analytics_consent(self, client: TestClient) -> None:
        register(client)
        response = client.post(
            "/applications/00000000-0000-0000-0000-000000000001/outcome",
            json={"outcome_type": "rejected"},
        )
        assert response.status_code == 403
        assert "outcome_analytics" in response.text


class TestPasswordPolicy:
    def test_minimum_length_is_enforced_at_the_boundary(self) -> None:
        from bharat_os.security import WeakPasswordError, hash_password

        with pytest.raises(WeakPasswordError):
            hash_password("x" * (MIN_PASSWORD_LENGTH - 1))
        assert hash_password("x" * MIN_PASSWORD_LENGTH)

    def test_verify_returns_false_for_a_missing_hash(self) -> None:
        from bharat_os.security import verify_password

        assert verify_password(PASSWORD, None) is False
