"""Application draft generation."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bharat_os.engine import ApplicantProfile
from bharat_os.llm.mock import MockProvider
from bharat_os.models.enums import DraftFieldSource
from bharat_os.services.drafting import NoFieldMapError, generate_draft, supported_schemes
from helpers import VALID_PROFILE, register

PROFILE = ApplicantProfile(
    state="Maharashtra",
    sector="edtech",
    stage="early",
    employee_count=8,
    annual_turnover_inr=1_200_000,
    registrations=frozenset({"dpiit"}),
)


class TestFieldMapCoverage:
    def test_flagship_schemes_are_supported(self) -> None:
        assert set(supported_schemes()) >= {"sisfs", "pmegp", "cgtmse"}

    def test_unsupported_scheme_raises_a_named_error(self, session: Session) -> None:
        from bharat_os.models.scheme import Scheme, SchemeVersion

        version = SchemeVersion(
            scheme=Scheme(slug="no-map"),
            version=1,
            name="No Map Scheme",
            summary="s",
            scheme_type="grant",
            administering_ministry="m",
            target_segments=["msme"],
            benefit_description="b",
            application_difficulty="low",
            effective_from=datetime.now(UTC),
        )
        with pytest.raises(NoFieldMapError, match="No draft field map"):
            generate_draft(session, version, PROFILE, scheme_slug="no-map", provider=MockProvider())


class TestFieldGeneration:
    """Regression coverage for entity_name, which is deliberately not part of
    ApplicantProfile (identity data, not an eligibility fact) but is needed by
    every flagship field map."""

    def test_entity_name_is_threaded_through_separately(self, session: Session) -> None:
        from bharat_os.models.scheme import Scheme, SchemeVersion

        version = SchemeVersion(
            scheme=Scheme(slug="sisfs"),
            version=1,
            name="SISFS",
            summary="s",
            scheme_type="grant",
            administering_ministry="m",
            target_segments=["startup"],
            benefit_description="b",
            application_difficulty="high",
            effective_from=datetime.now(UTC),
        )
        fields = generate_draft(
            session,
            version,
            PROFILE,
            scheme_slug="sisfs",
            entity_name="Priya EdTech Private Limited",
            provider=MockProvider(),
        )
        name_field = next(f for f in fields if f.key == "startup_name")
        assert name_field.value == "Priya EdTech Private Limited"

    def test_narrative_fields_are_actually_populated(self, session: Session) -> None:
        """The gap that let a real bug through: the mock only ever answered the
        judgement shape, so a narrative field's KeyError was silently swallowed
        and every narrative field rendered as None without a test catching it."""
        from bharat_os.models.scheme import Scheme, SchemeVersion

        version = SchemeVersion(
            scheme=Scheme(slug="sisfs"),
            version=1,
            name="SISFS",
            summary="s",
            scheme_type="grant",
            administering_ministry="m",
            target_segments=["startup"],
            benefit_description="b",
            application_difficulty="high",
            effective_from=datetime.now(UTC),
        )
        fields = generate_draft(
            session,
            version,
            PROFILE,
            scheme_slug="sisfs",
            entity_name="Priya EdTech Private Limited",
            provider=MockProvider(),
        )
        narrative_fields = [f for f in fields if f.source is DraftFieldSource.GENERATED_NARRATIVE]
        assert narrative_fields, "sisfs field map should define at least one narrative field"
        for field in narrative_fields:
            assert field.value, f"{field.key} narrative was not populated"
            assert field.instruction

    def test_missing_entity_name_does_not_crash_drafting(self, session: Session) -> None:
        """ApplicantProfile.resolve raises KeyError for unknown fields — entity_name
        must never reach that path, even when the caller supplies none."""
        from bharat_os.models.scheme import Scheme, SchemeVersion

        version = SchemeVersion(
            scheme=Scheme(slug="sisfs"),
            version=1,
            name="SISFS",
            summary="s",
            scheme_type="grant",
            administering_ministry="m",
            target_segments=["startup"],
            benefit_description="b",
            application_difficulty="high",
            effective_from=datetime.now(UTC),
        )
        fields = generate_draft(
            session, version, PROFILE, scheme_slug="sisfs", provider=MockProvider()
        )
        name_field = next(f for f in fields if f.key == "startup_name")
        assert name_field.value is None

    def test_every_draft_has_at_least_one_human_required_field(self, session: Session) -> None:
        from bharat_os.models.scheme import Scheme, SchemeVersion

        for slug in supported_schemes():
            version = SchemeVersion(
                scheme=Scheme(slug=slug),
                version=1,
                name=slug,
                summary="s",
                scheme_type="grant",
                administering_ministry="m",
                target_segments=["startup"],
                benefit_description="b",
                application_difficulty="high",
                effective_from=datetime.now(UTC),
            )
            fields = generate_draft(
                session, version, PROFILE, scheme_slug=slug, provider=MockProvider()
            )
            assert any(f.source is DraftFieldSource.HUMAN_REQUIRED for f in fields)
            for human_field in (f for f in fields if f.source is DraftFieldSource.HUMAN_REQUIRED):
                assert human_field.value is None
                assert human_field.reason


class TestDraftEndpoint:
    def test_create_draft_over_http(self, client: TestClient, seeded_corpus) -> None:
        """The exact path that broke live: profile with entity_name via the API."""
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        response = client.post("/matches/sisfs/draft")
        assert response.status_code == 201
        body = response.json()
        assert body["version"] == 1
        assert body["human_required_count"] >= 1

        name_field = next(f for f in body["fields"] if f["key"] == "startup_name")
        assert name_field["value"] == VALID_PROFILE["entity_name"]

        narrative_field = next(f for f in body["fields"] if f["source"] == "generated_narrative")
        assert narrative_field["value"], "narrative field was not populated over HTTP"

    def test_regenerating_creates_a_new_version(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        first = client.post("/matches/sisfs/draft").json()
        second = client.post("/matches/sisfs/draft").json()
        assert second["version"] == first["version"] + 1

    def test_get_current_draft_returns_the_latest(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        client.post("/matches/sisfs/draft")
        client.post("/matches/sisfs/draft")
        current = client.get("/matches/sisfs/draft").json()
        assert current["version"] == 2

    def test_no_draft_yet_returns_404_with_guidance(
        self, client: TestClient, seeded_corpus
    ) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        response = client.get("/matches/sisfs/draft")
        assert response.status_code == 404
        assert "POST" in response.json()["detail"]

    def test_unsupported_scheme_returns_404(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        response = client.post("/matches/udyam-registration/draft")
        assert response.status_code == 404

    def test_review_notice_is_present(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        body = client.post("/matches/sisfs/draft").json()
        assert "not a submission" in body["review_notice"]

    def test_draftable_list_is_public(self, client: TestClient) -> None:
        client.cookies.clear()
        response = client.get("/matches/draftable")
        assert response.status_code == 200
        assert "sisfs" in response.json()["slugs"]
