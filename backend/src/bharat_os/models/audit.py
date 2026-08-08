"""The AI audit trail.

Every judgement a language model makes about a user's eligibility is recorded
here with the exact prompt, the model that answered, and the reasoning it gave.

This is not diagnostics. It is the difference between "the system says 78%" and
"here is the question we asked, the model that answered, what it said, and when" —
and it is what allows a user, a support agent, or a regulator to check whether a
judgement was reasonable rather than taking it on faith.

The row is keyed by a hash of the user, criterion and profile, which doubles as
the cache key: one account's identical question is answered once. Explicit
account erasure deletes these rows because the stored prompt contains
profile-derived personal data.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    JSON,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from bharat_os.models.base import Base, created_at_column, enum_column, uuid_pk
from bharat_os.models.enums import SoftVerdict


class AIJudgement(Base):
    """One language model judgement about one criterion for one profile."""

    __tablename__ = "ai_judgement"
    __table_args__ = (
        Index("ix_ai_judgement_cache_key", "cache_key", unique=True),
        Index("ix_ai_judgement_user_id", "user_id"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()

    #: Hash of (criterion identity, profile-relevant facts, prompt version).
    #: Serves as both the cache key and the identity of the question asked.
    cache_key: Mapped[str] = mapped_column(String(64), nullable=False)

    criterion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("eligibility_criterion.id", ondelete="CASCADE"), nullable=False
    )
    #: Nullable and ``ON DELETE SET NULL`` as a database-level safety fallback.
    #: The erasure API deletes user-linked judgement rows before deleting the
    #: account because ``prompt`` can contain profile-derived personal data.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("user_account.id", ondelete="SET NULL"), nullable=True
    )

    verdict: Mapped[SoftVerdict] = mapped_column(
        enum_column(SoftVerdict, "soft_verdict"), nullable=False
    )
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reasoning: Mapped[str] = mapped_column(Text, nullable=False)
    #: Concrete things the applicant could supply to firm up the judgement.
    evidence_that_would_strengthen: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    #: Set when confidence fell below the threshold, meaning the judgement is
    #: reported as needing human review rather than presented as an answer.
    requires_human_review: Mapped[bool] = mapped_column(nullable=False, default=False)

    # --- Provenance of the judgement itself ---
    provider: Mapped[str] = mapped_column(String(40), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    #: Version of the prompt template, so a change in wording is distinguishable
    #: from a change in model behaviour.
    prompt_version: Mapped[str] = mapped_column(String(20), nullable=False)
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    raw_response: Mapped[str | None] = mapped_column(Text, nullable=True)
    prompt_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    completion_tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[datetime] = created_at_column()

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"<AIJudgement {self.verdict} {self.confidence:.2f} by {self.model}>"
