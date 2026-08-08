"""The eligibility engine.

A pure module: no framework, network or ORM imports anywhere in this package.
That constraint is enforced by a test, because it is the property that makes the
most correctness-critical part of the system independently testable.
"""

from bharat_os.engine.evaluator import evaluate_rule
from bharat_os.engine.hard_rules import HardCriterion, assess_hard_criteria
from bharat_os.engine.profile import MISSING, ApplicantProfile
from bharat_os.engine.results import CriterionResult, HardRuleAssessment

__all__ = [
    "MISSING",
    "ApplicantProfile",
    "CriterionResult",
    "HardCriterion",
    "HardRuleAssessment",
    "assess_hard_criteria",
    "evaluate_rule",
]
