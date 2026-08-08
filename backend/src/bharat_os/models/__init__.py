"""ORM models.

Every model must be imported here. Alembic autogenerate only sees tables that
are attached to ``Base.metadata`` at import time, so a model missing from this
list silently disappears from migrations.
"""

from bharat_os.models.application import Application, Outcome
from bharat_os.models.audit import AIJudgement
from bharat_os.models.auth import ConsentGrant, UserSession
from bharat_os.models.base import Base
from bharat_os.models.crawl import CrawlSource, PendingRevision
from bharat_os.models.document import UserDocument
from bharat_os.models.draft import ApplicationDraft
from bharat_os.models.notification import DeadlineNotification
from bharat_os.models.scheme import (
    ApplicationWindow,
    Authority,
    Benefit,
    DocumentRequirement,
    EligibilityCriterion,
    Scheme,
    SchemeVersion,
)
from bharat_os.models.user import Profile, UserAccount

__all__ = [
    "AIJudgement",
    "Application",
    "ApplicationDraft",
    "ApplicationWindow",
    "Authority",
    "Base",
    "Benefit",
    "ConsentGrant",
    "CrawlSource",
    "DeadlineNotification",
    "DocumentRequirement",
    "EligibilityCriterion",
    "Outcome",
    "PendingRevision",
    "Profile",
    "Scheme",
    "SchemeVersion",
    "UserAccount",
    "UserDocument",
    "UserSession",
]
