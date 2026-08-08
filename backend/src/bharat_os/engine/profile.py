"""The applicant profile as the engine sees it.

Deliberately a plain frozen dataclass with no ORM, framework or network imports.
The engine is the part of this system whose correctness matters most, so it is
kept independently testable and free of anything that could make its behaviour
depend on a database session or a request context.

The central distinction in this module is between a field that is *absent* and a
field that is *empty*. ``annual_turnover_inr=None`` means the applicant has not
told us their turnover, so any rule about turnover is unverifiable.
``registrations=frozenset()`` means the applicant has told us they hold no
registrations, which is knowledge, and a rule requiring DPIIT recognition is
therefore genuinely unmet. Collapsing those two cases is how an eligibility
engine starts either lying or uselessly hedging.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from typing import Any, Final

#: Sentinel for a field the applicant has not supplied.
#:
#: Distinct from ``None``, which some fields use as a meaningful value.
MISSING: Final = object()


@dataclass(frozen=True)
class ApplicantProfile:
    """A startup or MSME, as far as eligibility rules are concerned.

    Every field is optional because a partially complete profile is the normal
    case, not an error. The engine's job is to say precisely how far it can get
    with what it has.
    """

    state: str | None = None
    district: str | None = None
    sector: str | None = None
    stage: str | None = None
    employee_count: int | None = None
    annual_turnover_inr: int | None = None
    social_category: str | None = None
    is_woman_led: bool | None = None
    incorporation_date: date | None = None

    #: Built-up space the applicant has available, in square feet. Used by
    #: incubator/institution-facing schemes (e.g. AIC, ASPIRE) that require a
    #: minimum facility size — a fact, not a judgement call, so it belongs
    #: here rather than being pushed to a soft criterion.
    available_space_sqft: int | None = None

    #: Whether the applicant entity has been profitable in each of the last
    #: three financial years. ``None`` means not yet told, not "no".
    profitable_last_three_years: bool | None = None

    #: Registrations actually held. An empty set is a positive statement that
    #: none are held, not an absence of information.
    registrations: frozenset[str] = field(default_factory=frozenset)

    #: Whether the applicant has confirmed the registrations list is complete.
    #: Until they have, an empty set is treated as unknown rather than as "none",
    #: because a blank form field and a considered "I hold none" are different.
    registrations_declared: bool = True

    #: Today's date, injectable so age-dependent rules are testable.
    as_of: date | None = None

    @property
    def entity_age_years(self) -> float | None:
        """Age in years since incorporation, or ``None`` if not derivable.

        Fractional, because scheme thresholds like "not more than 2 years"
        exclude an entity incorporated 2 years and 1 month ago, and rounding
        would wrongly include it.
        """
        if self.incorporation_date is None:
            return None
        reference = self.as_of or date.today()
        return (reference - self.incorporation_date).days / 365.25

    def resolve(self, field_name: str) -> Any:
        """Return the value of an addressable field, or :data:`MISSING`.

        Raises :class:`KeyError` for a field name the profile does not define, so
        a typo in curated data surfaces as an error rather than as a permanently
        unverifiable criterion.
        """
        if field_name == "entity_age_years":
            value = self.entity_age_years
            return MISSING if value is None else value

        if field_name == "registrations":
            if not self.registrations and not self.registrations_declared:
                return MISSING
            return self.registrations

        if not hasattr(self, field_name):
            raise KeyError(f"{field_name!r} is not a profile field")

        value = getattr(self, field_name)
        return MISSING if value is None else value

    def known_fields(self) -> frozenset[str]:
        """Field names for which the profile has a usable value."""
        from bharat_os.rules import ADDRESSABLE_FIELDS

        return frozenset(name for name in ADDRESSABLE_FIELDS if self.resolve(name) is not MISSING)
