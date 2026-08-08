"""Controlled vocabularies shared by the ORM models and the API schemas.

All enums are persisted as ``VARCHAR`` with a ``CHECK`` constraint rather than a
native database enum type, so migrations behave identically on SQLite and
Postgres.
"""

from __future__ import annotations

from enum import StrEnum


class Segment(StrEnum):
    """Beneficiary segment a scheme targets.

    v1 curation covers ``STARTUP`` and ``MSME`` only. The remaining members
    exist so later curation needs no migration.
    """

    STARTUP = "startup"
    MSME = "msme"
    STUDENT = "student"
    FARMER = "farmer"
    NGO = "ngo"
    RESEARCHER = "researcher"
    WOMEN_ENTREPRENEUR = "women_entrepreneur"


class SchemeType(StrEnum):
    GRANT = "grant"
    LOAN = "loan"
    SUBSIDY = "subsidy"
    SCHOLARSHIP = "scholarship"
    TAX_BENEFIT = "tax_benefit"
    CREDIT_GUARANTEE = "credit_guarantee"
    CERTIFICATION = "certification"
    EQUITY = "equity"


class SchemeStatus(StrEnum):
    ACTIVE = "active"
    PAUSED = "paused"
    CLOSED = "closed"


class ApplicationDifficulty(StrEnum):
    """How hard the application is, used to discount the ranking score."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class CriterionType(StrEnum):
    """Whether a criterion is machine-decidable or requires judgement.

    ``HARD`` criteria are evaluated deterministically in code. ``SOFT`` criteria
    require language judgement and are evaluated by an LLM with an explicit
    confidence score, never presented as fact.
    """

    HARD = "hard"
    SOFT = "soft"


class EvaluationState(StrEnum):
    """Outcome of evaluating a single criterion.

    ``CANNOT_VERIFY`` is always preferred over guessing: it means the profile
    lacks the information needed to decide, which is materially different from
    the criterion being unmet.
    """

    MET = "met"
    UNMET = "unmet"
    CANNOT_VERIFY = "cannot_verify"


class AuthorityType(StrEnum):
    MINISTRY = "ministry"
    DEPARTMENT = "department"
    STATE_AGENCY = "state_agency"
    BANK = "bank"
    PSU = "psu"
    IMPLEMENTING_AGENCY = "implementing_agency"


class BenefitType(StrEnum):
    CASH = "cash"
    KIND = "kind"
    SERVICE = "service"
    RECOGNITION = "recognition"
    CREDIT_GUARANTEE = "credit_guarantee"
    INTEREST_SUBVENTION = "interest_subvention"


class Recurrence(StrEnum):
    ANNUAL = "annual"
    QUARTERLY = "quarterly"
    ROLLING = "rolling"
    ONE_TIME = "one_time"


class NotificationSource(StrEnum):
    """Where an application window was published."""

    GAZETTE = "gazette"
    PIB = "pib"
    PORTAL = "portal"
    CIRCULAR = "circular"


class EntityStage(StrEnum):
    IDEA = "idea"
    EARLY = "early"
    GROWTH = "growth"
    MATURE = "mature"


class RegistrationType(StrEnum):
    """Government registrations an applicant may hold.

    Many schemes gate eligibility on these, so they are first-class rather than
    free text.
    """

    DPIIT = "dpiit"
    UDYAM = "udyam"
    GST = "gst"
    FCRA = "fcra"
    MSME_UAM = "msme_uam"
    COMPANY_INCORPORATION = "company_incorporation"


class SocialCategory(StrEnum):
    GENERAL = "general"
    OBC = "obc"
    SC = "sc"
    ST = "st"
    EWS = "ews"


class ApplicationStatus(StrEnum):
    """Lifecycle of a user's application.

    Transitions past ``READY_FOR_REVIEW`` are always user-initiated. Nothing in
    the system advances an application to ``SUBMITTED`` on its own.
    """

    DRAFT = "draft"
    READY_FOR_REVIEW = "ready_for_review"
    SUBMITTED = "submitted"
    UNDER_REVIEW = "under_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    WITHDRAWN = "withdrawn"


class OutcomeType(StrEnum):
    APPROVED = "approved"
    PARTIALLY_APPROVED = "partially_approved"
    REJECTED = "rejected"
    LAPSED = "lapsed"


class SoftVerdict(StrEnum):
    """A language model's judgement on a criterion requiring interpretation.

    Deliberately hedged wording. A model reading a profile against "innovative
    technology-based startup" is forming an opinion, not making a finding, and the
    vocabulary should not let that opinion be mistaken for the latter. There is no
    plain ``met`` member for exactly that reason.
    """

    LIKELY_MET = "likely_met"
    LIKELY_UNMET = "likely_unmet"
    UNCERTAIN = "uncertain"


class ConsentPurpose(StrEnum):
    """Purposes a user consents to individually.

    The DPDP Act requires consent to be specific and purpose-limited, so consent
    is recorded per purpose rather than as a single blanket acceptance. Only
    ``SCHEME_MATCHING`` is required to use the product; the rest are genuinely
    optional and the product must remain usable without them.
    """

    #: Process profile data to match against schemes and assess eligibility.
    SCHEME_MATCHING = "scheme_matching"
    #: Store uploaded documents in the vault for reuse across applications.
    DOCUMENT_STORAGE = "document_storage"
    #: Retain de-identified application outcomes to improve recommendations.
    OUTCOME_ANALYTICS = "outcome_analytics"
    #: Send deadline reminders and status notifications.
    NOTIFICATIONS = "notifications"


class DraftFieldSource(StrEnum):
    """Where a draft's field value came from."""

    #: Copied directly from the applicant's profile.
    PROFILE = "profile"
    #: Written by the language model from the profile and scheme context.
    GENERATED_NARRATIVE = "generated_narrative"
    #: The applicant must supply this themselves; nothing pre-fills it.
    HUMAN_REQUIRED = "human_required"


class CrawlSourceType(StrEnum):
    STATIC_HTML = "static_html"
    JS_RENDERED = "js_rendered"
    PDF = "pdf"


class ReviewStatus(StrEnum):
    """State of a machine-detected change awaiting human judgement.

    Nothing produced by a crawler or extractor reaches the live scheme corpus
    without passing through ``APPROVED`` here. That is enforced by the loader
    only ever being called on hand-curated or approved data, never on raw
    crawl output.
    """

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class DocumentType(StrEnum):
    """Document kinds the vault understands.

    ``UNKNOWN`` is deliberate: an unrecognised document is flagged for human
    classification rather than guessed at.
    """

    DPIIT_CERTIFICATE = "dpiit_certificate"
    UDYAM_CERTIFICATE = "udyam_certificate"
    GST_CERTIFICATE = "gst_certificate"
    PAN_CARD = "pan_card"
    INCORPORATION_CERTIFICATE = "incorporation_certificate"
    AUDITED_FINANCIALS = "audited_financials"
    BANK_STATEMENT = "bank_statement"
    PITCH_DECK = "pitch_deck"
    PROJECT_REPORT = "project_report"
    CASTE_CERTIFICATE = "caste_certificate"
    INCOME_CERTIFICATE = "income_certificate"
    LAND_RECORD = "land_record"
    NOC = "noc"
    UNKNOWN = "unknown"
