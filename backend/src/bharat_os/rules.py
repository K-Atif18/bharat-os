"""The eligibility rule language.

Hard criteria are expressed as small JSON expressions so they can be stored as
data, reviewed by a domain expert who does not read Python, and evaluated
deterministically. This module defines the vocabulary; the evaluator lives in
:mod:`bharat_os.engine`, the deterministic evaluator.

Shape
-----

A rule is a JSON object with an ``op`` key. Leaf rules address a profile field::

    {"op": "lte", "field": "annual_turnover_inr", "value": 50000000}
    {"op": "contains", "field": "registrations", "value": "dpiit"}
    {"op": "is_true", "field": "is_woman_led"}

Composite rules nest other rules::

    {"op": "all", "rules": [{...}, {...}]}
    {"op": "any", "rules": [{...}, {...}]}
    {"op": "not", "rule": {...}}

Design notes
------------

There is no ``op`` for "unknown". When a rule addresses a profile field the user
has not supplied, evaluation yields ``cannot_verify`` rather than ``False``. That
distinction is the whole point: "we do not know whether you qualify" is not the
same statement as "you do not qualify", and collapsing the two is how an
eligibility engine starts lying to people.

The language is deliberately small. Anything requiring judgement — "innovative",
"commercially viable", "social impact" — is not expressible here and must be
modelled as a soft criterion instead.
"""

from __future__ import annotations

from typing import Final

#: Operators comparing a profile field against a literal.
COMPARISON_OPS: Final[frozenset[str]] = frozenset({"eq", "ne", "lt", "lte", "gt", "gte"})

#: Operators testing membership.
MEMBERSHIP_OPS: Final[frozenset[str]] = frozenset({"in", "not_in", "contains", "not_contains"})

#: Operators testing a boolean profile field, taking no ``value``.
BOOLEAN_OPS: Final[frozenset[str]] = frozenset({"is_true", "is_false"})

#: Operators combining other rules.
COMPOSITE_OPS: Final[frozenset[str]] = frozenset({"all", "any", "not"})

#: Every operator the language accepts.
ALL_OPS: Final[frozenset[str]] = COMPARISON_OPS | MEMBERSHIP_OPS | BOOLEAN_OPS | COMPOSITE_OPS

#: Profile attributes a rule may address.
#:
#: Restricting this set means a typo in curated data is caught at load time
#: rather than silently evaluating to ``cannot_verify`` forever.
ADDRESSABLE_FIELDS: Final[frozenset[str]] = frozenset(
    {
        "state",
        "district",
        "sector",
        "stage",
        "employee_count",
        "annual_turnover_inr",
        "social_category",
        "registrations",
        "is_woman_led",
        "entity_age_years",
    }
)


class RuleSyntaxError(ValueError):
    """Raised when a rule is not valid in this language."""


def validate_rule(rule: object, *, path: str = "rule") -> None:
    """Validate a rule's structure, raising :class:`RuleSyntaxError` if invalid.

    Called at load time so malformed curated data can never reach the engine.
    """
    if not isinstance(rule, dict):
        raise RuleSyntaxError(f"{path}: expected an object, got {type(rule).__name__}")

    op = rule.get("op")
    if not isinstance(op, str) or op not in ALL_OPS:
        raise RuleSyntaxError(f"{path}: unknown operator {op!r}; expected one of {sorted(ALL_OPS)}")

    if op in COMPOSITE_OPS:
        _validate_composite(rule, op, path)
        return

    field = rule.get("field")
    if not isinstance(field, str):
        raise RuleSyntaxError(f"{path}: '{op}' requires a 'field'")
    if field not in ADDRESSABLE_FIELDS:
        raise RuleSyntaxError(
            f"{path}: '{field}' is not an addressable profile field; "
            f"expected one of {sorted(ADDRESSABLE_FIELDS)}"
        )

    if op in BOOLEAN_OPS:
        if "value" in rule:
            raise RuleSyntaxError(f"{path}: '{op}' must not carry a 'value'")
        return

    if "value" not in rule:
        raise RuleSyntaxError(f"{path}: '{op}' requires a 'value'")

    if op in {"in", "not_in"} and not isinstance(rule["value"], list):
        raise RuleSyntaxError(f"{path}: '{op}' requires a list 'value'")

    unexpected = set(rule) - {"op", "field", "value"}
    if unexpected:
        raise RuleSyntaxError(f"{path}: unexpected keys {sorted(unexpected)}")


def _validate_composite(rule: dict, op: str, path: str) -> None:
    if op == "not":
        if "rule" not in rule:
            raise RuleSyntaxError(f"{path}: 'not' requires a nested 'rule'")
        unexpected = set(rule) - {"op", "rule"}
        if unexpected:
            raise RuleSyntaxError(f"{path}: unexpected keys {sorted(unexpected)}")
        validate_rule(rule["rule"], path=f"{path}.rule")
        return

    nested = rule.get("rules")
    if not isinstance(nested, list) or not nested:
        raise RuleSyntaxError(f"{path}: '{op}' requires a non-empty 'rules' list")
    unexpected = set(rule) - {"op", "rules"}
    if unexpected:
        raise RuleSyntaxError(f"{path}: unexpected keys {sorted(unexpected)}")
    for index, child in enumerate(nested):
        validate_rule(child, path=f"{path}.rules[{index}]")
