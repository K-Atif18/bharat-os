"""The deterministic engine.

The tests that matter most here are the ones asserting that missing data yields
``cannot_verify`` rather than ``unmet``. Everything else the product claims about
trustworthiness rests on that distinction holding.
"""

from __future__ import annotations

from datetime import date

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bharat_os.engine import (
    ApplicantProfile,
    HardCriterion,
    assess_hard_criteria,
    evaluate_rule,
)
from bharat_os.models.enums import EvaluationState
from bharat_os.rules import RuleSyntaxError

MET = EvaluationState.MET
UNMET = EvaluationState.UNMET
UNKNOWN = EvaluationState.CANNOT_VERIFY

FULL = ApplicantProfile(
    state="Maharashtra",
    district="Pune",
    sector="edtech",
    stage="early",
    employee_count=8,
    annual_turnover_inr=1_200_000,
    social_category="general",
    is_woman_led=False,
    incorporation_date=date(2025, 1, 1),
    registrations=frozenset({"dpiit", "gst"}),
    as_of=date(2026, 7, 1),
)


class TestComparisonOperators:
    @pytest.mark.parametrize(
        ("op", "value", "expected"),
        [
            ("eq", 1_200_000, MET),
            ("eq", 999, UNMET),
            ("ne", 999, MET),
            ("ne", 1_200_000, UNMET),
            ("lt", 2_000_000, MET),
            ("lt", 1_000_000, UNMET),
            ("lte", 1_200_000, MET),
            ("lte", 1_199_999, UNMET),
            ("gt", 1_000_000, MET),
            ("gt", 2_000_000, UNMET),
            ("gte", 1_200_000, MET),
            ("gte", 1_200_001, UNMET),
        ],
    )
    def test_numeric_comparisons(self, op: str, value: int, expected: EvaluationState) -> None:
        rule = {"op": op, "field": "annual_turnover_inr", "value": value}
        assert evaluate_rule(rule, FULL).state is expected

    def test_boundary_is_inclusive_for_lte(self) -> None:
        """Scheme ceilings are inclusive; an off-by-one here wrongly excludes people."""
        profile = ApplicantProfile(annual_turnover_inr=1_000_000_000)
        rule = {"op": "lte", "field": "annual_turnover_inr", "value": 1_000_000_000}
        assert evaluate_rule(rule, profile).state is MET

    def test_incomparable_types_are_unverifiable_not_unmet(self) -> None:
        """Bad data is our fault, so it must not be reported as the applicant failing."""
        profile = ApplicantProfile(state="Maharashtra")
        rule = {"op": "lt", "field": "state", "value": 5}
        result = evaluate_rule(rule, profile)
        assert result.state is UNKNOWN
        assert "cannot be compared" in result.reason


class TestMembershipOperators:
    @pytest.mark.parametrize(
        ("op", "field", "value", "expected"),
        [
            ("in", "stage", ["idea", "early"], MET),
            ("in", "stage", ["growth", "mature"], UNMET),
            ("not_in", "stage", ["growth"], MET),
            ("not_in", "stage", ["early"], UNMET),
            ("contains", "registrations", "dpiit", MET),
            ("contains", "registrations", "udyam", UNMET),
            ("not_contains", "registrations", "udyam", MET),
            ("not_contains", "registrations", "dpiit", UNMET),
        ],
    )
    def test_membership(
        self, op: str, field: str, value: object, expected: EvaluationState
    ) -> None:
        assert evaluate_rule({"op": op, "field": field, "value": value}, FULL).state is expected

    def test_declared_empty_registrations_is_knowledge_not_absence(self) -> None:
        """ "I hold no registrations" is an answer; a blank form is not."""
        declared = ApplicantProfile(registrations=frozenset(), registrations_declared=True)
        rule = {"op": "contains", "field": "registrations", "value": "dpiit"}
        assert evaluate_rule(rule, declared).state is UNMET

    def test_undeclared_registrations_are_unverifiable(self) -> None:
        undeclared = ApplicantProfile(registrations=frozenset(), registrations_declared=False)
        rule = {"op": "contains", "field": "registrations", "value": "dpiit"}
        assert evaluate_rule(rule, undeclared).state is UNKNOWN


class TestBooleanOperators:
    def test_is_true_and_is_false(self) -> None:
        woman_led = ApplicantProfile(is_woman_led=True)
        assert evaluate_rule({"op": "is_true", "field": "is_woman_led"}, woman_led).state is MET
        assert evaluate_rule({"op": "is_false", "field": "is_woman_led"}, woman_led).state is UNMET

    def test_unset_boolean_is_unverifiable_not_false(self) -> None:
        """A blank checkbox is not a "no". Treating it as one silently excludes people."""
        blank = ApplicantProfile(is_woman_led=None)
        result = evaluate_rule({"op": "is_true", "field": "is_woman_led"}, blank)
        assert result.state is UNKNOWN
        assert result.missing_fields == ("is_woman_led",)


class TestDerivedFields:
    def test_entity_age_is_derived_from_incorporation_date(self) -> None:
        profile = ApplicantProfile(incorporation_date=date(2025, 1, 1), as_of=date(2026, 7, 1))
        rule = {"op": "lte", "field": "entity_age_years", "value": 2}
        assert evaluate_rule(rule, profile).state is MET

    def test_entity_age_is_fractional_so_thresholds_are_exact(self) -> None:
        """ "Not more than 2 years" must exclude an entity 2 years and 1 month old."""
        profile = ApplicantProfile(incorporation_date=date(2024, 1, 1), as_of=date(2026, 2, 1))
        rule = {"op": "lte", "field": "entity_age_years", "value": 2}
        assert evaluate_rule(rule, profile).state is UNMET

    def test_missing_incorporation_date_makes_age_unverifiable(self) -> None:
        rule = {"op": "lte", "field": "entity_age_years", "value": 2}
        result = evaluate_rule(rule, ApplicantProfile())
        assert result.state is UNKNOWN
        assert result.missing_fields == ("entity_age_years",)


class TestInstitutionFacingFields:
    """Facility-space and profitability facts, added for incubator/institution-
    targeted schemes (AIC, ASPIRE) where the applicant is an implementing
    institution rather than a startup or MSME. These are facts, not judgement
    calls, so they belong in the engine rather than as soft/LLM criteria.
    """

    def test_available_space_meets_threshold(self) -> None:
        profile = ApplicantProfile(available_space_sqft=10_000)
        rule = {"op": "gte", "field": "available_space_sqft", "value": 10_000}
        assert evaluate_rule(rule, profile).state is MET

    def test_available_space_below_threshold_is_unmet(self) -> None:
        profile = ApplicantProfile(available_space_sqft=4_000)
        rule = {"op": "gte", "field": "available_space_sqft", "value": 5_000}
        assert evaluate_rule(rule, profile).state is UNMET

    def test_missing_available_space_is_unverifiable(self) -> None:
        rule = {"op": "gte", "field": "available_space_sqft", "value": 5_000}
        result = evaluate_rule(rule, ApplicantProfile())
        assert result.state is UNKNOWN
        assert result.missing_fields == ("available_space_sqft",)

    def test_profitable_last_three_years_true(self) -> None:
        profile = ApplicantProfile(profitable_last_three_years=True)
        rule = {"op": "is_true", "field": "profitable_last_three_years"}
        assert evaluate_rule(rule, profile).state is MET

    def test_profitable_last_three_years_false_is_unmet(self) -> None:
        profile = ApplicantProfile(profitable_last_three_years=False)
        rule = {"op": "is_true", "field": "profitable_last_three_years"}
        assert evaluate_rule(rule, profile).state is UNMET

    def test_unset_profitability_is_unverifiable_not_false(self) -> None:
        """A profile that hasn't answered this yet must not be treated as unprofitable."""
        result = evaluate_rule(
            {"op": "is_true", "field": "profitable_last_three_years"}, ApplicantProfile()
        )
        assert result.state is UNKNOWN
        assert result.missing_fields == ("profitable_last_three_years",)


class TestThreeValuedLogic:
    """Composites use Kleene logic: unknown is not false."""

    KNOWN_TRUE = {"op": "eq", "field": "state", "value": "Maharashtra"}
    KNOWN_FALSE = {"op": "eq", "field": "state", "value": "Kerala"}
    UNKNOWABLE = {"op": "is_true", "field": "is_woman_led"}

    @pytest.fixture
    def profile(self) -> ApplicantProfile:
        return ApplicantProfile(state="Maharashtra", is_woman_led=None)

    def test_all_with_a_definite_failure_is_unmet_despite_unknowns(
        self, profile: ApplicantProfile
    ) -> None:
        """A definite failure cannot be rescued by resolving an unknown."""
        rule = {"op": "all", "rules": [self.KNOWN_FALSE, self.UNKNOWABLE]}
        assert evaluate_rule(rule, profile).state is UNMET

    def test_all_with_only_unknowns_remaining_is_unverifiable(
        self, profile: ApplicantProfile
    ) -> None:
        rule = {"op": "all", "rules": [self.KNOWN_TRUE, self.UNKNOWABLE]}
        assert evaluate_rule(rule, profile).state is UNKNOWN

    def test_all_true_is_met(self, profile: ApplicantProfile) -> None:
        rule = {"op": "all", "rules": [self.KNOWN_TRUE, self.KNOWN_TRUE]}
        assert evaluate_rule(rule, profile).state is MET

    def test_any_with_a_definite_success_is_met_despite_unknowns(
        self, profile: ApplicantProfile
    ) -> None:
        """A definite success needs no further support."""
        rule = {"op": "any", "rules": [self.KNOWN_TRUE, self.UNKNOWABLE]}
        assert evaluate_rule(rule, profile).state is MET

    def test_any_with_unknowns_and_no_success_is_unverifiable(
        self, profile: ApplicantProfile
    ) -> None:
        rule = {"op": "any", "rules": [self.KNOWN_FALSE, self.UNKNOWABLE]}
        assert evaluate_rule(rule, profile).state is UNKNOWN

    def test_any_all_false_is_unmet(self, profile: ApplicantProfile) -> None:
        rule = {"op": "any", "rules": [self.KNOWN_FALSE, self.KNOWN_FALSE]}
        assert evaluate_rule(rule, profile).state is UNMET

    def test_not_inverts_definite_verdicts(self, profile: ApplicantProfile) -> None:
        assert evaluate_rule({"op": "not", "rule": self.KNOWN_TRUE}, profile).state is UNMET
        assert evaluate_rule({"op": "not", "rule": self.KNOWN_FALSE}, profile).state is MET

    def test_not_leaves_unknown_unknown(self, profile: ApplicantProfile) -> None:
        """The negation of "we don't know" is still "we don't know"."""
        assert evaluate_rule({"op": "not", "rule": self.UNKNOWABLE}, profile).state is UNKNOWN

    def test_nested_composites(self, profile: ApplicantProfile) -> None:
        rule = {
            "op": "all",
            "rules": [
                self.KNOWN_TRUE,
                {"op": "any", "rules": [self.KNOWN_FALSE, self.KNOWN_TRUE]},
            ],
        }
        assert evaluate_rule(rule, profile).state is MET


class TestMalformedRules:
    @pytest.mark.parametrize(
        "rule",
        [
            {"op": "approximately", "field": "state", "value": "x"},
            {"op": "eq", "field": "not_a_field", "value": "x"},
            {"op": "eq", "field": "state"},
            {"op": "is_true", "field": "state", "value": True},
            {"op": "in", "field": "state", "value": "not-a-list"},
            {"op": "all", "rules": []},
            {"op": "not"},
            "not-an-object",
        ],
    )
    def test_invalid_rules_raise(self, rule: object) -> None:
        with pytest.raises(RuleSyntaxError):
            evaluate_rule(rule, FULL)  # type: ignore[arg-type]


class TestExplanations:
    def test_every_verdict_carries_a_reason(self) -> None:
        for rule in (
            {"op": "lte", "field": "annual_turnover_inr", "value": 1},
            {"op": "contains", "field": "registrations", "value": "dpiit"},
            {"op": "is_true", "field": "is_woman_led"},
        ):
            assert evaluate_rule(rule, ApplicantProfile(annual_turnover_inr=5)).reason

    def test_unverifiable_reason_names_the_missing_field_in_plain_language(self) -> None:
        result = evaluate_rule(
            {"op": "lte", "field": "annual_turnover_inr", "value": 1}, ApplicantProfile()
        )
        assert "annual turnover" in result.reason
        assert "annual_turnover_inr" not in result.reason


class TestSchemeAssessment:
    def _criteria(self) -> list[HardCriterion]:
        return [
            HardCriterion(
                "dpiit",
                "Must hold DPIIT recognition.",
                {"op": "contains", "field": "registrations", "value": "dpiit"},
            ),
            HardCriterion(
                "young",
                "Must be at most 2 years old.",
                {"op": "lte", "field": "entity_age_years", "value": 2},
            ),
            HardCriterion(
                "woman", "Must be woman-led.", {"op": "is_true", "field": "is_woman_led"}
            ),
        ]

    def test_groups_results_by_state(self) -> None:
        profile = ApplicantProfile(
            registrations=frozenset({"dpiit"}),
            incorporation_date=date(2019, 1, 1),
            as_of=date(2026, 7, 1),
            is_woman_led=None,
        )
        assessment = assess_hard_criteria(self._criteria(), profile)
        assert assessment.met == ("dpiit",)
        assert assessment.unmet == ("young",)
        assert assessment.unverifiable == ("woman",)
        assert assessment.total == 3

    def test_reports_a_disqualifier(self) -> None:
        """One unmet hard criterion means ineligible; no score should soften that."""
        profile = ApplicantProfile(registrations=frozenset(), registrations_declared=True)
        assessment = assess_hard_criteria(self._criteria()[:1], profile)
        assert assessment.has_disqualifier is True

    def test_collects_the_fields_that_would_resolve_unknowns(self) -> None:
        """This list is what turns "we can't tell" into an actionable next step."""
        assessment = assess_hard_criteria(
            self._criteria(),
            ApplicantProfile(registrations=frozenset(), registrations_declared=False),
        )
        assert set(assessment.all_missing_fields) == {
            "registrations",
            "entity_age_years",
            "is_woman_led",
        }

    def test_no_criteria_yields_an_empty_assessment_not_a_vacuous_pass(self) -> None:
        assessment = assess_hard_criteria([], FULL)
        assert assessment.total == 0
        assert assessment.has_disqualifier is False


class TestDeterminism:
    def test_repeated_evaluation_is_identical(self) -> None:
        rule = {"op": "lte", "field": "annual_turnover_inr", "value": 1_500_000}
        first = evaluate_rule(rule, FULL)
        for _ in range(50):
            assert evaluate_rule(rule, FULL) == first


class TestPurity:
    def test_engine_imports_no_framework_network_or_orm(self) -> None:
        """The engine's independence is the reason it can be trusted and tested.

        Enforced mechanically because it is exactly the kind of boundary that
        erodes the first time someone needs a database lookup "just here".
        """
        import ast
        from pathlib import Path

        import bharat_os.engine as engine_pkg

        forbidden = {
            "fastapi",
            "starlette",
            "sqlalchemy",
            "alembic",
            "httpx",
            "requests",
            "urllib",
            "socket",
            "psycopg",
            "bharat_os.db",
            "bharat_os.main",
        }

        offenders: list[str] = []
        for path in Path(engine_pkg.__file__).parent.glob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                names = []
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.module:
                    names = [node.module]
                for name in names:
                    root = name.split(".")[0]
                    if name in forbidden or root in forbidden:
                        offenders.append(f"{path.name} imports {name}")

        assert not offenders, f"engine purity violated: {offenders}"


class TestPropertyBased:
    """No input should produce a verdict without an explanation."""

    @given(
        turnover=st.one_of(st.none(), st.integers(min_value=0, max_value=10**12)),
        employees=st.one_of(st.none(), st.integers(min_value=0, max_value=10**6)),
        woman_led=st.one_of(st.none(), st.booleans()),
        registrations=st.frozensets(st.sampled_from(["dpiit", "udyam", "gst"]), max_size=3),
        threshold=st.integers(min_value=0, max_value=10**12),
        op=st.sampled_from(["eq", "ne", "lt", "lte", "gt", "gte"]),
    )
    def test_every_verdict_is_explained(
        self,
        turnover: int | None,
        employees: int | None,
        woman_led: bool | None,
        registrations: frozenset[str],
        threshold: int,
        op: str,
    ) -> None:
        profile = ApplicantProfile(
            annual_turnover_inr=turnover,
            employee_count=employees,
            is_woman_led=woman_led,
            registrations=registrations,
        )
        result = evaluate_rule(
            {"op": op, "field": "annual_turnover_inr", "value": threshold}, profile
        )
        assert result.state in {MET, UNMET, UNKNOWN}
        assert result.reason.strip()
        # Only unverifiable results may name missing fields, and they must name at
        # least one — otherwise the user is told "unknown" with no way forward.
        if result.state is UNKNOWN:
            assert result.missing_fields
        else:
            assert not result.missing_fields

    @given(
        turnover=st.integers(min_value=0, max_value=10**9),
        threshold=st.integers(min_value=0, max_value=10**9),
    )
    def test_a_known_field_never_yields_unverifiable(self, turnover: int, threshold: int) -> None:
        """If the data is present, the engine must reach a definite verdict."""
        profile = ApplicantProfile(annual_turnover_inr=turnover)
        result = evaluate_rule(
            {"op": "lte", "field": "annual_turnover_inr", "value": threshold}, profile
        )
        assert result.state is not UNKNOWN
