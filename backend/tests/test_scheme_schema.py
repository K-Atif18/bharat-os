"""The knowledge base refuses unsourced or undecidable claims.

These invariants are the difference between a system that can explain itself and
one that confidently repeats something nobody checked.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError
from sqlalchemy.exc import IntegrityError

from bharat_os.models.enums import CriterionType
from bharat_os.models.scheme import EligibilityCriterion, Scheme, SchemeVersion
from bharat_os.schemas.scheme import EligibilityCriterionIn

VERIFIED_AT = datetime.now(UTC) - timedelta(days=1)


def _valid_hard_criterion() -> dict:
    return {
        "criterion_type": "hard",
        "description": "Entity must hold a valid DPIIT recognition certificate.",
        "machine_readable_rule": {"op": "contains", "field": "registrations", "value": "dpiit"},
        "source_url": "https://www.startupindia.gov.in/content/sih/en/startupgov/startup-recognition-page.html",
        "last_verified_at": VERIFIED_AT.isoformat(),
        "verified_by_human": True,
    }


class TestProvenanceIsMandatory:
    def test_valid_criterion_is_accepted(self) -> None:
        criterion = EligibilityCriterionIn.model_validate(_valid_hard_criterion())
        assert criterion.criterion_type is CriterionType.HARD
        assert criterion.verified_by_human is True

    def test_missing_source_url_is_rejected(self) -> None:
        payload = _valid_hard_criterion()
        del payload["source_url"]
        with pytest.raises(ValidationError, match="source_url"):
            EligibilityCriterionIn.model_validate(payload)

    def test_missing_last_verified_at_is_rejected(self) -> None:
        payload = _valid_hard_criterion()
        del payload["last_verified_at"]
        with pytest.raises(ValidationError, match="last_verified_at"):
            EligibilityCriterionIn.model_validate(payload)

    def test_non_url_source_is_rejected(self) -> None:
        payload = _valid_hard_criterion()
        payload["source_url"] = "see the circular"
        with pytest.raises(ValidationError, match="source_url"):
            EligibilityCriterionIn.model_validate(payload)

    def test_future_verification_date_is_rejected(self) -> None:
        payload = _valid_hard_criterion()
        payload["last_verified_at"] = (datetime.now(UTC) + timedelta(days=2)).isoformat()
        with pytest.raises(ValidationError, match="cannot be in the future"):
            EligibilityCriterionIn.model_validate(payload)


class TestCriterionTypeMatchesRule:
    """A hard criterion needs a rule; a soft criterion must not have one.

    Allowing a hard criterion without a rule would mean an eligibility question
    the engine cannot decide but presents as if it had.
    """

    def test_hard_criterion_without_rule_is_rejected(self) -> None:
        payload = _valid_hard_criterion()
        payload["machine_readable_rule"] = None
        with pytest.raises(ValidationError, match="requires a machine_readable_rule"):
            EligibilityCriterionIn.model_validate(payload)

    def test_soft_criterion_with_rule_is_rejected(self) -> None:
        payload = _valid_hard_criterion()
        payload["criterion_type"] = "soft"
        with pytest.raises(ValidationError, match="must not carry a machine_readable_rule"):
            EligibilityCriterionIn.model_validate(payload)

    def test_soft_criterion_without_rule_is_accepted(self) -> None:
        payload = _valid_hard_criterion()
        payload["criterion_type"] = "soft"
        payload["machine_readable_rule"] = None
        payload["description"] = "The startup must be working on an innovative product."
        criterion = EligibilityCriterionIn.model_validate(payload)
        assert criterion.criterion_type is CriterionType.SOFT
        assert criterion.machine_readable_rule is None


class TestDatabaseEnforcesProvenance:
    """The same invariants hold at the database level, not only in Pydantic.

    Validation can be bypassed by a loader or a migration; a ``NOT NULL`` cannot.
    """

    def _scheme_version(self, session) -> SchemeVersion:
        scheme = Scheme(slug="test-scheme")
        version = SchemeVersion(
            scheme=scheme,
            version=1,
            name="Test Scheme",
            summary="A scheme used only by tests.",
            scheme_type="grant",
            status="active",
            administering_ministry="Ministry of Testing",
            target_segments=["startup"],
            sectors=[],
            states=[],
            benefit_description="Up to Rs 10 lakh.",
            application_difficulty="medium",
            effective_from=datetime.now(UTC),
        )
        session.add(version)
        session.flush()
        return version

    def test_criterion_without_source_url_violates_not_null(self, session) -> None:
        version = self._scheme_version(session)
        session.add(
            EligibilityCriterion(
                scheme_version_id=version.id,
                criterion_type=CriterionType.SOFT,
                description="Unsourced claim.",
                source_url=None,
                last_verified_at=VERIFIED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()

    def test_criterion_without_last_verified_violates_not_null(self, session) -> None:
        version = self._scheme_version(session)
        session.add(
            EligibilityCriterion(
                scheme_version_id=version.id,
                criterion_type=CriterionType.SOFT,
                description="Claim with no verification date.",
                source_url="https://example.gov.in/scheme",
                last_verified_at=None,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()

    def test_hard_criterion_without_rule_violates_check_constraint(self, session) -> None:
        version = self._scheme_version(session)
        session.add(
            EligibilityCriterion(
                scheme_version_id=version.id,
                criterion_type=CriterionType.HARD,
                description="Hard criterion with no rule.",
                machine_readable_rule=None,
                source_url="https://example.gov.in/scheme",
                last_verified_at=VERIFIED_AT,
            )
        )
        with pytest.raises(IntegrityError):
            session.flush()
