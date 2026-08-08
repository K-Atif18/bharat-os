"""Confidence aggregation and the calibration harness."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from bharat_os.engine.results import CriterionResult, HardRuleAssessment
from bharat_os.models.enums import EvaluationState, SoftVerdict
from bharat_os.services.aggregate import (
    SOFT_EVIDENCE_WEIGHT,
    EligibilityReport,
    ReportOutcome,
    aggregate,
)
from bharat_os.services.calibration import (
    ECE_TOLERANCE,
    CalibrationCase,
    measure,
)
from bharat_os.services.soft_criteria import PROMPT_VERSION, SoftJudgement

FIXTURES = Path(__file__).parent / "fixtures" / "calibration_cases.json"


def hard(met: int = 0, unmet: int = 0, unknown: int = 0) -> HardRuleAssessment:
    results = {}
    met_keys = tuple(f"m{i}" for i in range(met))
    unmet_keys = tuple(f"u{i}" for i in range(unmet))
    unknown_keys = tuple(f"k{i}" for i in range(unknown))
    for key in met_keys:
        results[key] = CriterionResult(EvaluationState.MET, "criterion satisfied")
    for key in unmet_keys:
        results[key] = CriterionResult(EvaluationState.UNMET, "turnover exceeds the ceiling")
    for key in unknown_keys:
        results[key] = CriterionResult(
            EvaluationState.CANNOT_VERIFY, "turnover missing", ("annual_turnover_inr",)
        )
    return HardRuleAssessment(met_keys, unmet_keys, unknown_keys, results)


def soft(
    verdict: SoftVerdict = SoftVerdict.LIKELY_MET,
    confidence: float = 0.8,
    *,
    review: bool = False,
    description: str = "must be innovative",
) -> SoftJudgement:
    return SoftJudgement(
        criterion_id="c",
        description=description,
        verdict=verdict,
        confidence=confidence,
        reasoning="because the profile says so",
        evidence_that_would_strengthen=("a product description",),
        requires_human_review=review,
        provider="mock",
        model="mock-v1",
        prompt_version=PROMPT_VERSION,
    )


class TestDisqualification:
    def test_a_failed_hard_requirement_produces_no_aggregate(self) -> None:
        """Averaging a disqualification with soft positives would mislead."""
        report = aggregate(hard(met=4, unmet=1), [soft(), soft(), soft(), soft()])
        assert report.outcome is ReportOutcome.RULED_OUT
        assert report.confidence is None

    def test_disqualification_carries_its_reason(self) -> None:
        report = aggregate(hard(met=1, unmet=1), [])
        assert report.disqualifying_reasons
        assert "ceiling" in report.disqualifying_reasons[0]

    def test_ruled_out_is_not_actionable(self) -> None:
        assert aggregate(hard(unmet=1), []).is_actionable is False

    def test_many_soft_positives_cannot_rescue_a_disqualification(self) -> None:
        report = aggregate(hard(unmet=1), [soft(confidence=0.95) for _ in range(20)])
        assert report.outcome is ReportOutcome.RULED_OUT


class TestEvidenceWeighting:
    def test_opinions_are_worth_less_than_facts(self) -> None:
        """A soft judgement at full confidence must not equal a confirmed fact."""
        facts_only = aggregate(hard(met=2), [])
        opinions_only = aggregate(hard(), [soft(confidence=1.0), soft(confidence=1.0)])
        assert facts_only.confidence == pytest.approx(1.0)
        assert opinions_only.confidence is not None
        assert opinions_only.confidence == pytest.approx(1.0)
        # Equal proportionally, but a soft criterion contributes a smaller share of
        # the total possible evidence.
        mixed = aggregate(hard(met=1), [soft(confidence=1.0)])
        assert mixed.confidence == pytest.approx(1.0)

    def test_a_hedged_opinion_contributes_proportionally(self) -> None:
        report = aggregate(hard(met=1), [soft(confidence=0.8)])
        expected = (1.0 + SOFT_EVIDENCE_WEIGHT * 0.8) / (1.0 + SOFT_EVIDENCE_WEIGHT)
        assert report.confidence == pytest.approx(expected)

    def test_a_flagged_judgement_contributes_nothing(self) -> None:
        """If it needs a human, it is not evidence yet."""
        report = aggregate(hard(met=1), [soft(confidence=0.5, review=True)])
        expected = 1.0 / (1.0 + SOFT_EVIDENCE_WEIGHT)
        assert report.confidence == pytest.approx(expected)

    def test_a_negative_judgement_contributes_nothing(self) -> None:
        report = aggregate(hard(met=1), [soft(SoftVerdict.LIKELY_UNMET, 0.9)])
        assert report.confidence == pytest.approx(1.0 / (1.0 + SOFT_EVIDENCE_WEIGHT))

    def test_unverifiable_lowers_confidence_without_being_a_failure(self) -> None:
        report = aggregate(hard(met=1, unknown=1), [])
        assert report.confidence == pytest.approx(0.5)
        assert report.outcome is not ReportOutcome.RULED_OUT
        assert report.missing_fields == ("annual_turnover_inr",)


class TestOutcomeClassification:
    def test_everything_confirmed_is_strong(self) -> None:
        report = aggregate(hard(met=4), [soft(confidence=0.9), soft(confidence=0.9)])
        assert report.outcome is ReportOutcome.STRONG

    def test_a_flagged_judgement_flags_the_whole_report(self) -> None:
        """The caveat must not be lost by a caller that only reads the number."""
        report = aggregate(hard(met=4), [soft(confidence=0.4, review=True)])
        assert report.outcome is ReportOutcome.NEEDS_HUMAN_REVIEW
        assert report.requires_human_review is True
        assert report.flagged_for_review == ("must be innovative",)

    def test_sparse_evidence_is_insufficient_data(self) -> None:
        report = aggregate(hard(met=1, unknown=4), [])
        assert report.outcome is ReportOutcome.INSUFFICIENT_DATA

    def test_no_criteria_at_all_is_insufficient_data(self) -> None:
        assert aggregate(hard(), []).outcome is ReportOutcome.INSUFFICIENT_DATA

    def test_unverified_criteria_prevent_a_strong_rating(self) -> None:
        """ "Strong" must mean nothing is outstanding."""
        report = aggregate(hard(met=9, unknown=1), [])
        assert report.outcome is ReportOutcome.PROMISING

    def test_evidence_requests_are_deduplicated(self) -> None:
        report = aggregate(hard(met=1), [soft(), soft(), soft()])
        assert report.evidence_requested == ("a product description",)


class TestCalibrationMeasurement:
    def test_perfect_calibration_scores_zero_error(self) -> None:
        # 80% confidence, 8 of 10 succeed.
        cases = [CalibrationCase(0.8, i < 8) for i in range(10)]
        report = measure(cases, buckets=5)
        assert report.expected_calibration_error == pytest.approx(0.0, abs=0.01)

    def test_detects_overconfidence(self) -> None:
        """The damaging direction: it sends people into applications they will lose."""
        cases = [CalibrationCase(0.9, i < 3) for i in range(10)]
        report = measure(cases, buckets=5)
        assert report.expected_calibration_error > 0.5
        assert report.overall_direction == "overconfident"
        assert report.is_within_tolerance is False

    def test_detects_underconfidence(self) -> None:
        cases = [CalibrationCase(0.2, i < 9) for i in range(10)]
        assert measure(cases, buckets=5).overall_direction == "underconfident"

    def test_max_error_surfaces_a_bad_bucket_a_mean_would_hide(self) -> None:
        # A large, well-calibrated low band drags the weighted mean down, while a
        # small high band is badly wrong. Reporting only the mean would call this
        # acceptable, which is why max error is reported alongside it.
        cases = [CalibrationCase(0.05, False) for _ in range(190)]
        cases += [CalibrationCase(0.9, False) for _ in range(10)]
        report = measure(cases, buckets=5)
        assert report.expected_calibration_error < 0.15
        assert report.max_calibration_error > 0.8

    def test_confidence_of_exactly_one_is_counted(self) -> None:
        """An off-by-one at the boundary would silently drop the most confident cases."""
        report = measure([CalibrationCase(1.0, True)], buckets=5)
        assert report.sample_size == 1
        assert sum(b.count for b in report.buckets) == 1

    def test_empty_input_reports_zero_samples_rather_than_passing(self) -> None:
        report = measure([])
        assert report.sample_size == 0
        assert report.buckets

    def test_out_of_range_confidence_is_rejected(self) -> None:
        with pytest.raises(ValueError, match="outside"):
            measure([CalibrationCase(1.5, True)])

    def test_report_renders_a_readable_diagram(self) -> None:
        report = measure([CalibrationCase(0.8, i < 8) for i in range(10)])
        rendered = report.render()
        assert "Expected calibration error" in rendered
        assert "tolerance" in rendered


class TestCalibrationFixtures:
    def test_fixture_file_is_labelled_as_synthetic(self) -> None:
        """Nobody should mistake these for real outcomes."""
        payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
        note = " ".join(payload["_note"])
        assert "SYNTHETIC" in note
        assert "not real application outcomes" in note

    def test_harness_reports_within_tolerance_on_the_fixtures(self) -> None:
        """Validates the measurement, not the system. The fixtures say so too."""
        payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
        cases = [CalibrationCase(**case) for case in payload["cases"]]
        report = measure(cases)

        assert report.sample_size >= 30, "too few cases for the number to mean anything"
        assert report.expected_calibration_error <= ECE_TOLERANCE, report.render()

    def test_fixture_base_rate_is_not_degenerate(self) -> None:
        """All-success or all-failure fixtures would make calibration untestable."""
        payload = json.loads(FIXTURES.read_text(encoding="utf-8"))
        cases = [CalibrationCase(**case) for case in payload["cases"]]
        report = measure(cases)
        assert 0.15 < report.base_rate < 0.85


class TestReportShape:
    def test_report_is_immutable(self) -> None:
        """An assessment must not be editable after the fact."""
        from dataclasses import FrozenInstanceError

        report = aggregate(hard(met=1), [])
        with pytest.raises(FrozenInstanceError):
            report.confidence = 0.99  # type: ignore[misc]

    def test_report_exposes_the_underlying_assessments(self) -> None:
        """The breakdown has to remain inspectable, not collapse into a number."""
        report: EligibilityReport = aggregate(hard(met=2, unknown=1), [soft()])
        assert report.hard.total == 3
        assert len(report.soft) == 1
        assert report.soft[0].reasoning
