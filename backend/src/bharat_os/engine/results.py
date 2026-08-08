"""Engine result types.

Every result carries a human-readable reason. That is not decoration: a verdict a
user cannot interrogate is a verdict they cannot act on, and "you scored 43%" with
no explanation is exactly the opacity this product exists to remove.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bharat_os.models.enums import EvaluationState


@dataclass(frozen=True)
class CriterionResult:
    """The outcome of evaluating one criterion against one profile."""

    state: EvaluationState
    #: Plain-language explanation of why this verdict was reached.
    reason: str
    #: Profile fields that were needed but absent. Non-empty only when the state
    #: is ``cannot_verify``, and it is what drives "tell us X to firm this up".
    missing_fields: tuple[str, ...] = ()

    @property
    def is_met(self) -> bool:
        return self.state is EvaluationState.MET

    @property
    def is_unmet(self) -> bool:
        return self.state is EvaluationState.UNMET

    @property
    def is_unverifiable(self) -> bool:
        return self.state is EvaluationState.CANNOT_VERIFY


@dataclass(frozen=True)
class HardRuleAssessment:
    """The deterministic part of an eligibility assessment.

    Contains no probabilities. Every conclusion here is reproducible from the
    profile and the rules alone, which is what makes it auditable.
    """

    met: tuple[str, ...] = ()
    unmet: tuple[str, ...] = ()
    unverifiable: tuple[str, ...] = ()
    results: dict[str, CriterionResult] = field(default_factory=dict)

    @property
    def total(self) -> int:
        return len(self.met) + len(self.unmet) + len(self.unverifiable)

    @property
    def has_disqualifier(self) -> bool:
        """Whether any hard criterion is definitively unmet.

        A single unmet hard criterion means the applicant does not qualify, full
        stop. No amount of strength elsewhere compensates, and presenting a high
        overall score alongside a failed hard requirement would be misleading.
        """
        return bool(self.unmet)

    @property
    def all_missing_fields(self) -> tuple[str, ...]:
        """Every field that, if supplied, could resolve an unverifiable criterion."""
        seen: dict[str, None] = {}
        for key in self.unverifiable:
            for name in self.results[key].missing_fields:
                seen.setdefault(name, None)
        return tuple(seen)
