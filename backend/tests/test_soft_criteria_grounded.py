"""Tests for the retrieval-grounded soft-criteria judgement path.

judge_criterion (the existing, default path) is unchanged and already fully
covered by test_llm.py. Everything here is about the new, additive
judge_criterion_with_context path only.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from bharat_os.engine import ApplicantProfile
from bharat_os.llm.mock import FORCE_ERROR, MockProvider
from bharat_os.models.audit import AIJudgement
from bharat_os.models.enums import CriterionType, SoftVerdict
from bharat_os.models.scheme import EligibilityCriterion, Scheme, SchemeVersion
from bharat_os.services.soft_criteria import (
    GROUNDED_PROMPT_VERSION,
    PROMPT_VERSION,
    build_grounding_context,
    judge_criterion,
    judge_criterion_with_context,
)

PROFILE = ApplicantProfile(
    state="Maharashtra",
    sector="edtech",
    stage="early",
    employee_count=8,
    annual_turnover_inr=1_200_000,
    registrations=frozenset({"dpiit"}),
    is_woman_led=True,
)


@pytest.fixture
def scheme_version(session: Session) -> SchemeVersion:
    version = SchemeVersion(
        scheme=Scheme(slug="grounded-test"),
        version=1,
        name="Grounded Judgement Test Scheme",
        summary=(
            "Supports innovative, technology-driven startups building a "
            "commercially viable product for underserved markets."
        ),
        scheme_type="grant",
        status="active",
        administering_ministry="Ministry of Testing",
        target_segments=["startup"],
        sectors=[],
        states=[],
        benefit_description=(
            "Grant of up to Rs 20 lakh, contingent on the product demonstrating "
            "a clear commercialisation path within 12 months."
        ),
        application_difficulty="high",
        effective_from=datetime.now(UTC),
        criteria=[
            EligibilityCriterion(
                criterion_type=CriterionType.SOFT,
                description="The startup must be working on an innovative product.",
                source_url="https://example.gov.in/criteria",
                last_verified_at=datetime.now(UTC),
                display_order=1,
            ),
            EligibilityCriterion(
                criterion_type=CriterionType.SOFT,
                description="The product must have a viable path to commercialisation.",
                source_url="https://example.gov.in/criteria",
                last_verified_at=datetime.now(UTC),
                display_order=2,
            ),
        ],
    )
    session.add(version)
    session.commit()
    return version


class TestBuildGroundingContext:
    def test_pulls_relevant_text_from_the_scheme_summary_and_benefit(
        self, scheme_version: SchemeVersion
    ) -> None:
        criterion = scheme_version.criteria[1]  # "commercialisation"
        context = build_grounding_context(criterion, scheme_version)
        assert "commercialis" in context.lower()

    def test_does_not_include_the_criterion_being_judged_as_its_own_grounding(
        self, scheme_version: SchemeVersion
    ) -> None:
        criterion = scheme_version.criteria[0]
        context = build_grounding_context(criterion, scheme_version)
        # The criterion's own exact description must not be trivially present
        # verbatim as if it were independent supporting context.
        assert criterion.description not in context

    def test_scheme_with_no_other_context_returns_empty_string(
        self, session: Session
    ) -> None:
        version = SchemeVersion(
            scheme=Scheme(slug="bare-scheme"),
            version=1,
            name="Bare Scheme",
            summary="",
            scheme_type="grant",
            status="active",
            administering_ministry="Ministry of Testing",
            target_segments=["startup"],
            sectors=[],
            states=[],
            benefit_description="",
            application_difficulty="medium",
            effective_from=datetime.now(UTC),
            criteria=[
                EligibilityCriterion(
                    criterion_type=CriterionType.SOFT,
                    description="Some criterion.",
                    source_url="https://example.gov.in/criteria",
                    last_verified_at=datetime.now(UTC),
                    display_order=1,
                )
            ],
        )
        session.add(version)
        session.commit()

        context = build_grounding_context(version.criteria[0], version)
        assert context == ""


class TestJudgeCriterionWithContext:
    def test_returns_a_hedged_verdict_like_the_default_path(
        self, session: Session, scheme_version: SchemeVersion
    ) -> None:
        criterion = scheme_version.criteria[0]
        provider = MockProvider()
        judgement = judge_criterion_with_context(
            session, criterion, scheme_version, PROFILE, provider=provider
        )
        assert judgement.verdict in {
            SoftVerdict.LIKELY_MET,
            SoftVerdict.LIKELY_UNMET,
            SoftVerdict.UNCERTAIN,
        }

    def test_records_the_grounded_prompt_version_not_the_default_one(
        self, session: Session, scheme_version: SchemeVersion
    ) -> None:
        criterion = scheme_version.criteria[0]
        provider = MockProvider()
        judgement = judge_criterion_with_context(
            session, criterion, scheme_version, PROFILE, provider=provider
        )
        assert judgement.prompt_version == GROUNDED_PROMPT_VERSION
        assert judgement.prompt_version != PROMPT_VERSION

    def test_grounded_and_default_judgements_are_cached_separately(
        self, session: Session, scheme_version: SchemeVersion
    ) -> None:
        """The two paths must never collide on cache_key - a grounded
        judgement must not be silently served in place of (or instead of)
        a default one, or vice versa."""
        criterion = scheme_version.criteria[0]
        provider = MockProvider()

        judge_criterion(session, criterion, scheme_version, PROFILE, provider=provider)
        judge_criterion_with_context(
            session, criterion, scheme_version, PROFILE, provider=provider
        )

        records = session.scalars(select(AIJudgement)).all()
        assert len(records) == 2
        prompt_versions = {r.prompt_version for r in records}
        assert prompt_versions == {PROMPT_VERSION, GROUNDED_PROMPT_VERSION}

    def test_the_grounded_prompt_includes_retrieved_context(
        self, session: Session, scheme_version: SchemeVersion
    ) -> None:
        criterion = scheme_version.criteria[1]
        provider = MockProvider()
        judge_criterion_with_context(
            session, criterion, scheme_version, PROFILE, provider=provider
        )
        assert len(provider.calls) == 1
        assert "additional context" in provider.calls[0].prompt.lower()

    def test_provider_failure_degrades_to_human_review_same_as_default_path(
        self, session: Session, scheme_version: SchemeVersion
    ) -> None:
        criterion_forced = EligibilityCriterion(
            criterion_type=CriterionType.SOFT,
            description=f"{FORCE_ERROR} unrelated criterion text",
            source_url="https://example.gov.in/criteria",
            last_verified_at=datetime.now(UTC),
            display_order=99,
            scheme_version_id=scheme_version.id,
        )
        session.add(criterion_forced)
        session.commit()

        provider = MockProvider()
        judgement = judge_criterion_with_context(
            session, criterion_forced, scheme_version, PROFILE, provider=provider
        )

        assert judgement.requires_human_review is True
        assert judgement.confidence == 0.0
        assert judgement.prompt_version == GROUNDED_PROMPT_VERSION

    def test_repeated_calls_reuse_the_cached_judgement(
        self, session: Session, scheme_version: SchemeVersion
    ) -> None:
        criterion = scheme_version.criteria[0]
        provider = MockProvider()

        first = judge_criterion_with_context(
            session, criterion, scheme_version, PROFILE, provider=provider
        )
        second = judge_criterion_with_context(
            session, criterion, scheme_version, PROFILE, provider=provider
        )

        assert first.cached is False
        assert second.cached is True
        assert len(provider.calls) == 1  # the model was only asked once
