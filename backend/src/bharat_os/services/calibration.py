"""Measuring whether stated confidence means anything.

A confidence score is a claim about the world: "of the applications we rate 70%,
roughly 70% should succeed". If that claim is false the number is worse than
useless, because users calibrate their own effort against it. Miscalibrated
confidence is a documented failure mode for exactly this product category.

This module computes a reliability diagram and the **expected calibration error**:
the average gap between stated confidence and observed success rate, weighted by
how many cases fall in each bucket.

An important caveat, stated here rather than buried
-------------------------------------------------

Real calibration requires real outcomes, and there are none yet — the outcome table
is empty by design until applications complete. So the harness ships with synthetic
fixtures whose purpose is to prove *the measurement works*, not to prove the system
is calibrated.

The two claims are very different, and conflating them would be the same kind of
overreach this module exists to detect. Once real applications have completed and
their outcomes are recorded, the same code runs against them and the result
means something about the system rather than about the fixtures.
"""

from __future__ import annotations

from dataclasses import dataclass

#: Number of equal-width confidence buckets in the reliability diagram.
DEFAULT_BUCKETS = 5

#: Largest expected calibration error considered acceptable. Loose, because with
#: few samples the estimate is noisy; tighten it as real outcomes accumulate.
ECE_TOLERANCE = 0.15


@dataclass(frozen=True)
class CalibrationCase:
    """One prediction paired with what actually happened."""

    #: Confidence the system stated, in ``[0, 1]``.
    predicted_confidence: float
    #: Whether the application actually succeeded.
    succeeded: bool
    #: Optional label for reporting, e.g. a scheme slug.
    label: str = ""


@dataclass(frozen=True)
class Bucket:
    """One row of a reliability diagram."""

    lower: float
    upper: float
    count: int
    mean_predicted: float
    observed_rate: float

    @property
    def gap(self) -> float:
        """How far the stated confidence was from reality in this bucket."""
        return abs(self.mean_predicted - self.observed_rate)

    @property
    def direction(self) -> str:
        if self.count == 0:
            return "no data"
        if self.mean_predicted > self.observed_rate + 0.02:
            return "overconfident"
        if self.observed_rate > self.mean_predicted + 0.02:
            return "underconfident"
        return "well calibrated"


@dataclass(frozen=True)
class CalibrationReport:
    """The result of measuring calibration over a set of cases."""

    buckets: tuple[Bucket, ...]
    #: Expected calibration error: mean absolute gap, weighted by bucket size.
    expected_calibration_error: float
    #: Largest single-bucket gap, which a mean can hide.
    max_calibration_error: float
    sample_size: int
    #: Overall success rate, for context on whether the sample is degenerate.
    base_rate: float

    @property
    def is_within_tolerance(self) -> bool:
        return self.expected_calibration_error <= ECE_TOLERANCE

    @property
    def overall_direction(self) -> str:
        """Whether the system tends to overstate or understate its confidence.

        Overconfidence is the more damaging direction: it sends people into
        applications they will lose.
        """
        populated = [b for b in self.buckets if b.count > 0]
        if not populated:
            return "no data"
        signed = sum((b.mean_predicted - b.observed_rate) * b.count for b in populated)
        signed /= sum(b.count for b in populated)
        if signed > 0.05:
            return "overconfident"
        if signed < -0.05:
            return "underconfident"
        return "well calibrated"

    def render(self) -> str:
        """A plain-text reliability diagram, for humans reading CI output."""
        lines = [
            f"Calibration over {self.sample_size} cases "
            f"(base success rate {self.base_rate:.0%})",
            "",
            f"{'confidence band':<18}{'n':>5}{'stated':>10}{'actual':>10}"
            f"{'gap':>8}  assessment",
            "-" * 72,
        ]
        for bucket in self.buckets:
            band = f"{bucket.lower:.0%}-{bucket.upper:.0%}"
            if bucket.count == 0:
                lines.append(f"{band:<18}{0:>5}{'-':>10}{'-':>10}{'-':>8}  no data")
                continue
            lines.append(
                f"{band:<18}{bucket.count:>5}{bucket.mean_predicted:>10.0%}"
                f"{bucket.observed_rate:>10.0%}{bucket.gap:>8.0%}  {bucket.direction}"
            )
        lines += [
            "-" * 72,
            f"Expected calibration error : {self.expected_calibration_error:.1%}"
            f"  (tolerance {ECE_TOLERANCE:.0%})",
            f"Worst single bucket        : {self.max_calibration_error:.1%}",
            f"Overall tendency           : {self.overall_direction}",
        ]
        return "\n".join(lines)


def measure(
    cases: list[CalibrationCase],
    *,
    buckets: int = DEFAULT_BUCKETS,
) -> CalibrationReport:
    """Compute a calibration report over ``cases``.

    An empty input yields a report with zero error and zero samples rather than
    raising. That is not a pass: :attr:`CalibrationReport.sample_size` is what
    tells a caller whether the measurement means anything, and a caller asserting
    on tolerance alone should also assert on sample size.
    """
    if buckets < 1:
        raise ValueError("buckets must be at least 1")

    for case in cases:
        if not 0.0 <= case.predicted_confidence <= 1.0:
            raise ValueError(f"predicted_confidence {case.predicted_confidence} is outside [0, 1]")

    width = 1.0 / buckets
    rows: list[Bucket] = []
    weighted_error = 0.0
    worst = 0.0

    for index in range(buckets):
        lower = index * width
        upper = (index + 1) * width
        # The final bucket includes its upper bound, so a confidence of exactly
        # 1.0 is counted rather than silently dropped.
        in_bucket = [
            case
            for case in cases
            if (lower <= case.predicted_confidence < upper)
            or (index == buckets - 1 and case.predicted_confidence == 1.0)
        ]

        if not in_bucket:
            rows.append(Bucket(lower, upper, 0, 0.0, 0.0))
            continue

        mean_predicted = sum(c.predicted_confidence for c in in_bucket) / len(in_bucket)
        observed = sum(1 for c in in_bucket if c.succeeded) / len(in_bucket)
        bucket = Bucket(lower, upper, len(in_bucket), mean_predicted, observed)
        rows.append(bucket)

        weighted_error += bucket.gap * len(in_bucket)
        worst = max(worst, bucket.gap)

    total = len(cases)
    return CalibrationReport(
        buckets=tuple(rows),
        expected_calibration_error=(weighted_error / total) if total else 0.0,
        max_calibration_error=worst,
        sample_size=total,
        base_rate=(sum(1 for c in cases if c.succeeded) / total) if total else 0.0,
    )
