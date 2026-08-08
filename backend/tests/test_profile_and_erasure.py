"""Profile handling, encryption at rest, log safety and the right to erasure."""

from __future__ import annotations

import logging

from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from bharat_os.models.application import Application, Outcome
from bharat_os.models.audit import AIJudgement
from bharat_os.models.auth import ConsentGrant, UserSession
from bharat_os.models.enums import CriterionType, SoftVerdict
from bharat_os.models.scheme import EligibilityCriterion
from bharat_os.models.user import Profile, UserAccount
from helpers import PASSWORD, TURNOVER, VALID_PROFILE, register


class TestProfileLifecycle:
    def test_create_and_read(self, client: TestClient) -> None:
        register(client)
        created = client.put("/profile", json=VALID_PROFILE)
        assert created.status_code == 200
        body = created.json()
        assert body["entity_name"] == VALID_PROFILE["entity_name"]
        assert body["annual_turnover_inr"] == TURNOVER
        assert body["registrations"] == ["dpiit"]
        assert client.get("/profile").json()["id"] == body["id"]

    def test_upsert_is_idempotent(self, client: TestClient, session: Session) -> None:
        """A client retrying after a dropped connection must not create a duplicate."""
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        client.put("/profile", json={**VALID_PROFILE, "employee_count": 12})
        assert len(list(session.scalars(select(Profile)).all())) == 1
        assert client.get("/profile").json()["employee_count"] == 12

    def test_missing_profile_returns_404_with_guidance(self, client: TestClient) -> None:
        register(client)
        response = client.get("/profile")
        assert response.status_code == 404
        assert "PUT /profile" in response.json()["detail"]

    def test_future_incorporation_date_is_rejected(self, client: TestClient) -> None:
        register(client)
        response = client.put(
            "/profile", json={**VALID_PROFILE, "incorporation_date": "2099-01-01"}
        )
        assert response.status_code == 422

    def test_negative_employee_count_is_rejected(self, client: TestClient) -> None:
        register(client)
        response = client.put("/profile", json={**VALID_PROFILE, "employee_count": -1})
        assert response.status_code == 422

    def test_sensitive_fields_are_optional(self, client: TestClient) -> None:
        """The product must work for a user who declines to share turnover."""
        register(client)
        minimal = {
            k: v
            for k, v in VALID_PROFILE.items()
            if k not in {"annual_turnover_inr", "social_category"}
        }
        response = client.put("/profile", json=minimal)
        assert response.status_code == 200
        assert response.json()["annual_turnover_inr"] is None

    def test_deleting_the_profile_keeps_the_account(self, client: TestClient) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        assert client.delete("/profile").status_code == 204
        assert client.get("/me").status_code == 200
        assert client.get("/me").json()["has_profile"] is False


class TestEncryptionAtRest:
    def test_sensitive_columns_hold_ciphertext(self, client: TestClient, engine) -> None:
        """A database dump must not expose turnover or social category."""
        register(client)
        client.put("/profile", json=VALID_PROFILE)

        with engine.connect() as connection:
            raw = connection.execute(
                text("SELECT annual_turnover_inr, social_category FROM profile")
            ).one()

        combined = f"{raw[0]}{raw[1]}"
        assert str(TURNOVER) not in combined
        assert "general" not in combined
        # Fernet tokens are versioned and start with a known prefix.
        assert raw[0].startswith("gAAAAA")
        assert raw[1].startswith("gAAAAA")

    def test_non_sensitive_columns_stay_queryable(self, client: TestClient, engine) -> None:
        """Encrypt what is sensitive, not everything: state must remain filterable."""
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        with engine.connect() as connection:
            state = connection.execute(text("SELECT state FROM profile")).scalar_one()
        assert state == "Maharashtra"

    def test_repr_omits_sensitive_fields(self, client: TestClient, session: Session) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        rendered = repr(session.scalars(select(Profile)).one())
        assert str(TURNOVER) not in rendered
        assert "general" not in rendered


class TestSensitiveDataStaysOutOfLogs:
    def test_profile_write_logs_no_sensitive_values(self, client: TestClient, caplog) -> None:
        """Logs outlive requests and are widely readable; PII must never reach them."""
        register(client)
        with caplog.at_level(logging.DEBUG):
            client.put("/profile", json=VALID_PROFILE)

        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert str(TURNOVER) not in logged
        assert "general" not in logged
        assert PASSWORD not in logged

    def test_registration_logs_no_password(self, client: TestClient, caplog) -> None:
        with caplog.at_level(logging.DEBUG):
            register(client)
        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert PASSWORD not in logged


class TestErasure:
    def _seed_application_with_outcome(self, session: Session, user_id) -> None:
        """An application and outcome, as a user who has actually used the product would have."""
        from datetime import UTC, datetime

        from bharat_os.models.scheme import Scheme, SchemeVersion

        version = SchemeVersion(
            scheme=Scheme(slug="erasure-test-scheme"),
            version=1,
            name="Test Scheme",
            summary="For erasure tests.",
            scheme_type="grant",
            status="active",
            administering_ministry="Ministry of Testing",
            target_segments=["msme"],
            sectors=[],
            states=[],
            benefit_description="Up to Rs 10 lakh.",
            application_difficulty="medium",
            effective_from=datetime.now(UTC),
            criteria=[
                EligibilityCriterion(
                    criterion_type=CriterionType.SOFT,
                    description="Must demonstrate innovation.",
                    source_url="https://example.gov.in/criteria",
                    last_verified_at=datetime.now(UTC),
                    verified_by_human=True,
                    display_order=1,
                )
            ],
        )
        application = Application(
            user_id=user_id,
            scheme_version=version,
            status="rejected",
        )
        application.outcome = Outcome(
            outcome_type="rejected",
            rejection_reason="Audited financials were not in the prescribed format.",
            applicant_state="Maharashtra",
            applicant_sector="edtech",
            applicant_turnover_band="10L-1Cr",
        )
        session.add(application)
        session.commit()

    def _seed_ai_judgement(self, session: Session, user_id) -> None:
        criterion_id = session.scalars(select(EligibilityCriterion.id)).one()
        session.add(
            AIJudgement(
                cache_key="erasure-user-scoped-cache-key",
                criterion_id=criterion_id,
                user_id=user_id,
                verdict=SoftVerdict.LIKELY_MET,
                confidence=0.8,
                reasoning="The profile appears to demonstrate innovation.",
                evidence_that_would_strengthen=["Product brief"],
                requires_human_review=False,
                provider="mock",
                model="mock-deterministic-v1",
                prompt_version="v1",
                prompt=f"Applicant annual turnover: Rs {TURNOVER}",
                raw_response='{"verdict":"likely_met"}',
            )
        )
        session.commit()

    def test_erasure_removes_all_personal_data(self, client: TestClient, session: Session) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        user_id = session.scalars(select(UserAccount.id)).one()
        self._seed_application_with_outcome(session, user_id)
        self._seed_ai_judgement(session, user_id)

        response = client.delete("/me")
        assert response.status_code == 200
        report = response.json()
        assert report["account_deleted"] is True
        assert report["profile_deleted"] is True
        assert report["ai_judgements_deleted"] == 1
        assert report["applications_unlinked"] == 1
        assert report["outcomes_retained_anonymised"] == 1

        session.expire_all()
        assert list(session.scalars(select(UserAccount)).all()) == []
        assert list(session.scalars(select(Profile)).all()) == []
        assert list(session.scalars(select(AIJudgement)).all()) == []
        assert list(session.scalars(select(UserSession)).all()) == []
        assert list(session.scalars(select(ConsentGrant)).all()) == []

    def test_erasure_retains_deidentified_outcome_data(
        self, client: TestClient, session: Session
    ) -> None:
        """Outcome data is the asset that compounds; it must survive without a person attached."""
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        user_id = session.scalars(select(UserAccount.id)).one()
        self._seed_application_with_outcome(session, user_id)

        client.delete("/me")
        session.expire_all()

        outcome = session.scalars(select(Outcome)).one()
        assert outcome.rejection_reason is not None
        assert outcome.applicant_state == "Maharashtra"
        assert outcome.applicant_turnover_band == "10L-1Cr"

        application = session.scalars(select(Application)).one()
        assert application.user_id is None

    def test_no_exact_turnover_survives_erasure(
        self, client: TestClient, session: Session, engine
    ) -> None:
        """Bands are retained; the exact figure is personal data and must be gone."""
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        user_id = session.scalars(select(UserAccount.id)).one()
        self._seed_application_with_outcome(session, user_id)
        self._seed_ai_judgement(session, user_id)
        client.delete("/me")

        with engine.connect() as connection:
            dump = "".join(
                str(row)
                for table in ("outcome", "application", "ai_judgement")
                for row in connection.execute(text(f"SELECT * FROM {table}")).all()
            )
        assert str(TURNOVER) not in dump

    def test_session_is_unusable_after_erasure(self, client: TestClient) -> None:
        register(client)
        client.delete("/me")
        assert client.get("/me").status_code == 401

    def test_erased_email_can_register_again(self, client: TestClient) -> None:
        """Erasure must be complete enough that the address is genuinely free."""
        register(client)
        client.delete("/me")
        client.cookies.clear()
        assert register(client).status_code == 201

    def test_erasure_reports_what_it_did(self, client: TestClient) -> None:
        """A vague confirmation is how erasure quietly fails; report the counts."""
        register(client, consents=["scheme_matching", "notifications"])
        response = client.delete("/me")
        report = response.json()
        assert report["consents_deleted"] == 2
        assert report["sessions_revoked"] >= 1
        assert "de-identified" in report["note"]
