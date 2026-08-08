"""Assessing a whole scheme's hard criteria.

Takes the criteria belonging to one scheme version and produces a
:class:`HardRuleAssessment`. Still no AI, no network, no database — the caller
hands in plain data.
"""

from __future__ import annotations

from dataclasses import dataclass

from bharat_os.engine.evaluator import evaluate_rule
from bharat_os.engine.profile import ApplicantProfile
from bharat_os.engine.results import CriterionResult, HardRuleAssessment
from bharat_os.models.enums import EvaluationState


@dataclass(frozen=True)
class HardCriterion:
    """A hard criterion, reduced to what the engine needs."""

    key: str
    description: str
    rule: dict


def assess_hard_criteria(
    criteria: list[HardCriterion],
    profile: ApplicantProfile,
) -> HardRuleAssessment:
    """Evaluate every hard criterion, grouping the outcomes.

    A scheme with no hard criteria yields an empty assessment rather than a
    vacuous pass. Saying "you meet all zero requirements" as though it were
    reassurance would be actively misleading.
    """
    met: list[str] = []
    unmet: list[str] = []
    unverifiable: list[str] = []
    results: dict[str, CriterionResult] = {}

    for criterion in criteria:
        result = evaluate_rule(criterion.rule, profile)
        results[criterion.key] = result
        match result.state:
            case EvaluationState.MET:
                met.append(criterion.key)
            case EvaluationState.UNMET:
                unmet.append(criterion.key)
            case EvaluationState.CANNOT_VERIFY:
                unverifiable.append(criterion.key)

    return HardRuleAssessment(
        met=tuple(met),
        unmet=tuple(unmet),
        unverifiable=tuple(unverifiable),
        results=results,
    )
