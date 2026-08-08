"""The deterministic rule evaluator.

This module decides hard eligibility criteria. It contains no AI, no randomness
and no network access: given the same profile and rule it always returns the same
verdict, with the same explanation.

Three-valued logic
------------------

Verdicts are ``met``, ``unmet`` or ``cannot_verify``, and the composite operators
implement Kleene three-valued logic rather than treating unknown as false:

* ``all`` — one ``unmet`` makes the whole thing ``unmet`` regardless of unknowns,
  because a definite failure cannot be rescued by resolving an unknown. Otherwise
  any unknown makes it ``cannot_verify``.
* ``any`` — one ``met`` makes the whole thing ``met`` regardless of unknowns,
  because a definite success needs no further support. Otherwise any unknown makes
  it ``cannot_verify``.
* ``not`` — inverts ``met`` and ``unmet``, and leaves ``cannot_verify`` alone,
  because the negation of "we don't know" is still "we don't know".

The alternative — treating missing data as failure — would tell applicants they
are ineligible for schemes they may well qualify for, purely because they left a
form field blank. That is the single most damaging thing this engine could do.
"""

from __future__ import annotations

from typing import Any

from bharat_os.engine.profile import MISSING, ApplicantProfile
from bharat_os.engine.results import CriterionResult
from bharat_os.models.enums import EvaluationState
from bharat_os.rules import RuleSyntaxError, validate_rule

#: Human-readable descriptions of each operator, used to build explanations.
_OPERATOR_PHRASES = {
    "eq": "must equal",
    "ne": "must not equal",
    "lt": "must be less than",
    "lte": "must be at most",
    "gt": "must be more than",
    "gte": "must be at least",
    "in": "must be one of",
    "not_in": "must not be one of",
    "contains": "must include",
    "not_contains": "must not include",
    "is_true": "must be true",
    "is_false": "must be false",
}

#: Field names as they should appear in explanations shown to users.
_FIELD_LABELS = {
    "annual_turnover_inr": "annual turnover",
    "employee_count": "employee count",
    "entity_age_years": "age since incorporation",
    "is_woman_led": "woman-led status",
    "social_category": "social category",
    "registrations": "registrations held",
    "state": "state",
    "district": "district",
    "sector": "sector",
    "stage": "stage",
}


def _label(field_name: str) -> str:
    return _FIELD_LABELS.get(field_name, field_name.replace("_", " "))


def _show(value: Any) -> str:
    """Render a value for a human-readable explanation.

    Comparisons use full precision; only the *display* is rounded. Showing an
    applicant "1.4099931553730323 years" is technically accurate and practically
    useless.
    """
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.1f}"
    if isinstance(value, frozenset | set):
        return ", ".join(sorted(str(item) for item in value)) or "none"
    if isinstance(value, list | tuple):
        return ", ".join(str(item) for item in value)
    if isinstance(value, int):
        return f"{value:,}"
    return str(value)


def _unverifiable(field_name: str) -> CriterionResult:
    return CriterionResult(
        state=EvaluationState.CANNOT_VERIFY,
        reason=(
            f"Cannot verify: your {_label(field_name)} is not in your profile. "
            f"Add it and this criterion can be decided."
        ),
        missing_fields=(field_name,),
    )


def _compare(op: str, actual: Any, expected: Any) -> bool | None:
    """Apply a comparison, returning ``None`` if the types are not comparable."""
    try:
        match op:
            case "eq":
                return actual == expected
            case "ne":
                return actual != expected
            case "lt":
                return actual < expected
            case "lte":
                return actual <= expected
            case "gt":
                return actual > expected
            case "gte":
                return actual >= expected
    except TypeError:
        # Comparing incompatible types, e.g. a text turnover against a number.
        # Treated as unverifiable rather than as a failure, because the fault is
        # in the data, not in the applicant.
        return None
    return None


def _evaluate_leaf(rule: dict, profile: ApplicantProfile) -> CriterionResult:
    op: str = rule["op"]
    field_name: str = rule["field"]
    actual = profile.resolve(field_name)

    if actual is MISSING:
        return _unverifiable(field_name)

    if op in {"is_true", "is_false"}:
        expected_truth = op == "is_true"
        satisfied = bool(actual) is expected_truth
        return CriterionResult(
            state=EvaluationState.MET if satisfied else EvaluationState.UNMET,
            reason=(
                f"Your {_label(field_name)} is {_show(actual)}, and this criterion "
                f"requires it to be {str(expected_truth).lower()}."
            ),
        )

    expected = rule["value"]

    if op in {"in", "not_in"}:
        present = actual in expected
        satisfied = present if op == "in" else not present
        return CriterionResult(
            state=EvaluationState.MET if satisfied else EvaluationState.UNMET,
            reason=(
                f"Your {_label(field_name)} is {_show(actual)}. This criterion "
                f"{_OPERATOR_PHRASES[op]}: {_show(expected)}."
            ),
        )

    if op in {"contains", "not_contains"}:
        try:
            present = expected in actual
        except TypeError:
            return _unverifiable(field_name)
        satisfied = present if op == "contains" else not present
        return CriterionResult(
            state=EvaluationState.MET if satisfied else EvaluationState.UNMET,
            reason=(
                f"Your {_label(field_name)}: {_show(actual)}. This criterion "
                f"{_OPERATOR_PHRASES[op]} {_show(expected)}."
            ),
        )

    outcome = _compare(op, actual, expected)
    if outcome is None:
        return CriterionResult(
            state=EvaluationState.CANNOT_VERIFY,
            reason=(
                f"Cannot verify: your {_label(field_name)} ({_show(actual)}) cannot be "
                f"compared against the required value ({_show(expected)})."
            ),
            missing_fields=(field_name,),
        )

    return CriterionResult(
        state=EvaluationState.MET if outcome else EvaluationState.UNMET,
        reason=(
            f"Your {_label(field_name)} is {_show(actual)}. This criterion "
            f"{_OPERATOR_PHRASES[op]} {_show(expected)}."
        ),
    )


def _combine_all(children: list[CriterionResult]) -> CriterionResult:
    unmet = [c for c in children if c.is_unmet]
    if unmet:
        return CriterionResult(
            state=EvaluationState.UNMET,
            reason="All conditions must hold, and at least one does not: " + unmet[0].reason,
        )
    unverifiable = [c for c in children if c.is_unverifiable]
    if unverifiable:
        return CriterionResult(
            state=EvaluationState.CANNOT_VERIFY,
            reason="All conditions must hold, but some cannot be checked: "
            + unverifiable[0].reason,
            missing_fields=_merge_missing(unverifiable),
        )
    return CriterionResult(
        state=EvaluationState.MET,
        reason="Every condition holds: " + "; ".join(child.reason for child in children),
    )


def _combine_any(children: list[CriterionResult]) -> CriterionResult:
    met = [c for c in children if c.is_met]
    if met:
        return CriterionResult(
            state=EvaluationState.MET,
            reason="At least one alternative holds: " + met[0].reason,
        )
    unverifiable = [c for c in children if c.is_unverifiable]
    if unverifiable:
        return CriterionResult(
            state=EvaluationState.CANNOT_VERIFY,
            reason=(
                "No alternative could be confirmed, and some cannot be checked: "
                + unverifiable[0].reason
            ),
            missing_fields=_merge_missing(unverifiable),
        )
    return CriterionResult(
        state=EvaluationState.UNMET,
        reason="No alternative holds: " + "; ".join(child.reason for child in children),
    )


def _merge_missing(results: list[CriterionResult]) -> tuple[str, ...]:
    seen: dict[str, None] = {}
    for result in results:
        for name in result.missing_fields:
            seen.setdefault(name, None)
    return tuple(seen)


def evaluate_rule(rule: dict, profile: ApplicantProfile) -> CriterionResult:
    """Evaluate one rule against a profile.

    The rule is validated first, so malformed curated data raises rather than
    silently producing a verdict nobody can trust.
    """
    validate_rule(rule)
    return _evaluate(rule, profile)


def _evaluate(rule: dict, profile: ApplicantProfile) -> CriterionResult:
    op: str = rule["op"]

    if op == "all":
        return _combine_all([_evaluate(child, profile) for child in rule["rules"]])
    if op == "any":
        return _combine_any([_evaluate(child, profile) for child in rule["rules"]])
    if op == "not":
        inner = _evaluate(rule["rule"], profile)
        if inner.is_unverifiable:
            # The negation of "unknown" is still "unknown".
            return inner
        return CriterionResult(
            state=EvaluationState.UNMET if inner.is_met else EvaluationState.MET,
            reason=f"This must not hold, and {'it does' if inner.is_met else 'it does not'}: "
            + inner.reason,
        )

    return _evaluate_leaf(rule, profile)


__all__ = ["RuleSyntaxError", "evaluate_rule"]
