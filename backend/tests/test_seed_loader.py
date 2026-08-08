"""The seed loader must be idempotent and must never overwrite history."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.models.enums import CriterionType
from bharat_os.models.scheme import Scheme, SchemeVersion
from bharat_os.schemas.scheme import AuthorityIn, SchemeVersionIn
from bharat_os.seed.loader import (
    SCHEME_DIR,
    SeedDataError,
    content_hash,
    load_from_disk,
    load_schemes,
    read_authorities,
    read_schemes,
)

VERIFIED_AT = "2026-07-01T00:00:00Z"


def make_scheme(slug: str = "test-scheme", *, turnover_cap: int = 50000000) -> SchemeVersionIn:
    return SchemeVersionIn.model_validate(
        {
            "slug": slug,
            "name": "Test Scheme",
            "summary": "A scheme used only by tests.",
            "scheme_type": "grant",
            "administering_ministry": "Ministry of Testing",
            "target_segments": ["msme"],
            "benefit_description": "Up to Rs 10 lakh.",
            "application_difficulty": "medium",
            "effective_from": "2025-04-01T00:00:00Z",
            "criteria": [
                {
                    "criterion_type": "hard",
                    "description": f"Turnover must not exceed {turnover_cap}.",
                    "machine_readable_rule": {
                        "op": "lte",
                        "field": "annual_turnover_inr",
                        "value": turnover_cap,
                    },
                    "display_order": 1,
                    "source_url": "https://example.gov.in/scheme",
                    "last_verified_at": VERIFIED_AT,
                    "verified_by_human": True,
                }
            ],
        }
    )


def current_versions(session: Session, slug: str) -> list[SchemeVersion]:
    return list(
        session.scalars(
            select(SchemeVersion)
            .join(Scheme, SchemeVersion.scheme_id == Scheme.id)
            .where(Scheme.slug == slug)
            .order_by(SchemeVersion.version)
        ).all()
    )


class TestIdempotency:
    def test_first_load_creates_version_one(self, session: Session) -> None:
        report = load_schemes(session, [make_scheme()], [])
        assert report.schemes_created == 1
        versions = current_versions(session, "test-scheme")
        assert [v.version for v in versions] == [1]
        assert versions[0].is_current is True

    def test_reloading_identical_data_creates_no_new_version(self, session: Session) -> None:
        load_schemes(session, [make_scheme()], [])
        report = load_schemes(session, [make_scheme()], [])
        assert report.unchanged == 1
        assert report.versions_created == 0
        assert [v.version for v in current_versions(session, "test-scheme")] == [1]

    def test_reloading_many_times_is_stable(self, session: Session) -> None:
        for _ in range(5):
            load_schemes(session, [make_scheme()], [])
        assert len(current_versions(session, "test-scheme")) == 1

    def test_authorities_are_upserted_not_duplicated(self, session: Session) -> None:
        authority = AuthorityIn.model_validate(
            {"slug": "test-ministry", "name": "Ministry of Testing", "authority_type": "ministry"}
        )
        first = load_schemes(session, [], [authority])
        second = load_schemes(session, [], [authority])
        assert first.authorities_created == 1
        assert second.authorities_created == 0
        assert second.authorities_updated == 0

    def test_authority_correction_updates_in_place(self, session: Session) -> None:
        """Authorities are reference data: a corrected name is a fix, not a new fact."""
        load_schemes(
            session,
            [],
            [
                AuthorityIn.model_validate(
                    {"slug": "m", "name": "Ministry of Testng", "authority_type": "ministry"}
                )
            ],
        )
        report = load_schemes(
            session,
            [],
            [
                AuthorityIn.model_validate(
                    {"slug": "m", "name": "Ministry of Testing", "authority_type": "ministry"}
                )
            ],
        )
        assert report.authorities_updated == 1


class TestVersioningOnChange:
    def test_changed_content_creates_a_new_version(self, session: Session) -> None:
        load_schemes(session, [make_scheme(turnover_cap=50000000)], [])
        report = load_schemes(session, [make_scheme(turnover_cap=100000000)], [])

        assert report.versions_created == 1
        versions = current_versions(session, "test-scheme")
        assert [v.version for v in versions] == [1, 2]

    def test_superseded_version_is_retained_and_marked(self, session: Session) -> None:
        """History is never destroyed: an old assessment must stay explicable."""
        load_schemes(session, [make_scheme(turnover_cap=50000000)], [])
        load_schemes(session, [make_scheme(turnover_cap=100000000)], [])

        v1, v2 = current_versions(session, "test-scheme")
        assert v1.is_current is False
        assert v1.superseded_at is not None
        assert v2.is_current is True
        assert v2.superseded_at is None
        # The original threshold survives verbatim.
        assert v1.criteria[0].machine_readable_rule == {
            "op": "lte",
            "field": "annual_turnover_inr",
            "value": 50000000,
        }

    def test_exactly_one_current_version_per_scheme(self, session: Session) -> None:
        for cap in (10, 20, 30):
            load_schemes(session, [make_scheme(turnover_cap=cap)], [])
        versions = current_versions(session, "test-scheme")
        assert sum(1 for v in versions if v.is_current) == 1
        assert len(versions) == 3


class TestContentHash:
    def test_reverification_alone_does_not_change_the_hash(self) -> None:
        """Re-checking an unchanged criterion must not manufacture a revision."""
        first = make_scheme()
        second = make_scheme()
        second.criteria[0].last_verified_at = datetime.now(UTC) - timedelta(days=1)
        assert content_hash(first) == content_hash(second)

    def test_substantive_change_changes_the_hash(self) -> None:
        assert content_hash(make_scheme(turnover_cap=1)) != content_hash(
            make_scheme(turnover_cap=2)
        )

    def test_reverification_refreshes_provenance_without_a_new_version(
        self, session: Session
    ) -> None:
        load_schemes(session, [make_scheme()], [])
        refreshed = make_scheme()
        newer = datetime.now(UTC) - timedelta(days=1)
        refreshed.criteria[0].last_verified_at = newer

        load_schemes(session, [refreshed], [])

        versions = current_versions(session, "test-scheme")
        assert len(versions) == 1
        stored = versions[0].criteria[0].last_verified_at
        if stored.tzinfo is None:
            stored = stored.replace(tzinfo=UTC)
        assert stored.date() == newer.date()


class TestInvalidData:
    def test_unknown_authority_slug_is_rejected(self, session: Session) -> None:
        scheme = make_scheme()
        scheme.authority_slug = "no-such-authority"
        with pytest.raises(SeedDataError, match="unknown authority_slug"):
            load_schemes(session, [scheme], [])

    def test_duplicate_slugs_across_files_are_rejected(self, tmp_path: Path) -> None:
        for name in ("a.json", "b.json"):
            (tmp_path / name).write_text(
                json.dumps(make_scheme("clash").model_dump(mode="json")), encoding="utf-8"
            )
        with pytest.raises(SeedDataError, match="duplicate scheme slugs"):
            read_schemes(tmp_path)

    def test_malformed_json_names_the_offending_file(self, tmp_path: Path) -> None:
        (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
        with pytest.raises(SeedDataError, match="broken.json"):
            read_schemes(tmp_path)

    def test_invalid_rule_operator_is_rejected_at_load_time(self, tmp_path: Path) -> None:
        payload = make_scheme().model_dump(mode="json")
        payload["criteria"][0]["machine_readable_rule"] = {
            "op": "approximately",
            "field": "annual_turnover_inr",
            "value": 1,
        }
        (tmp_path / "bad-rule.json").write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(SeedDataError, match="unknown operator"):
            read_schemes(tmp_path)

    def test_rule_addressing_an_unknown_field_is_rejected(self, tmp_path: Path) -> None:
        """A typo in a field name must fail loudly, not evaluate to 'cannot verify' forever."""
        payload = make_scheme().model_dump(mode="json")
        payload["criteria"][0]["machine_readable_rule"] = {
            "op": "lte",
            "field": "anual_turnover",
            "value": 1,
        }
        (tmp_path / "typo.json").write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(SeedDataError, match="not an addressable profile field"):
            read_schemes(tmp_path)


class TestCuratedCorpus:
    """Invariants over the real curated data on disk."""

    def test_every_scheme_file_validates(self) -> None:
        schemes = read_schemes()
        assert schemes, "no curated schemes found on disk"

    def test_authorities_file_validates(self) -> None:
        assert read_authorities(), "no curated authorities found on disk"

    def test_corpus_holds_at_least_fifteen_schemes(self) -> None:
        assert len(read_schemes()) >= 15

    def test_every_scheme_targets_a_v1_segment(self) -> None:
        """v1 scope is startups and MSMEs. Breadth without depth serves nobody."""
        offenders = [
            scheme.slug
            for scheme in read_schemes()
            if not {"startup", "msme"} & set(scheme.target_segments)
        ]
        assert not offenders, f"schemes outside v1 scope: {offenders}"

    def test_every_scheme_has_at_least_one_hard_criterion(self) -> None:
        """A scheme decided entirely by LLM judgement has no deterministic floor."""
        offenders = [
            scheme.slug
            for scheme in read_schemes()
            if not any(c.criterion_type is CriterionType.HARD for c in scheme.criteria)
        ]
        assert not offenders, f"schemes with no hard criteria: {offenders}"

    def test_every_scheme_has_documents_and_a_window(self) -> None:
        missing_documents = [s.slug for s in read_schemes() if not s.document_requirements]
        missing_windows = [s.slug for s in read_schemes() if not s.windows]
        assert not missing_documents, f"schemes with no document requirements: {missing_documents}"
        assert not missing_windows, f"schemes with no application window: {missing_windows}"

    def test_every_referenced_authority_exists(self) -> None:
        known = {authority.slug for authority in read_authorities()}
        referenced = set()
        for scheme in read_schemes():
            if scheme.authority_slug:
                referenced.add(scheme.authority_slug)
            for document in scheme.document_requirements:
                if document.issuing_authority_slug:
                    referenced.add(document.issuing_authority_slug)
        assert not (referenced - known), f"undefined authorities: {sorted(referenced - known)}"

    def test_every_scheme_file_is_named_after_its_slug(self) -> None:
        """Keeps the corpus navigable as it grows past a screenful."""
        mismatched = [
            path.name
            for path in sorted(SCHEME_DIR.glob("*.json"))
            if json.loads(path.read_text(encoding="utf-8"))["slug"] != path.stem
        ]
        assert not mismatched, f"filename does not match slug: {mismatched}"

    def test_loading_the_real_corpus_is_idempotent(self, session: Session) -> None:
        first = load_from_disk(session)
        second = load_from_disk(session)
        assert first.schemes_created >= 15
        assert second.schemes_created == 0
        assert second.versions_created == 0
        assert second.unchanged == first.schemes_created
