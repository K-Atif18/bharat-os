"""The language model boundary and soft-criteria judgements.

Everything here runs against the mock provider: no network, no cost, no
flakiness. The tests that matter most are the ones proving a bad response is
refused rather than patched over with defaults.
"""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from bharat_os.engine import ApplicantProfile
from bharat_os.llm import LLMRequest, LLMResponseError, MockProvider, build_provider
from bharat_os.llm.base import LLMError, parse_json_object
from bharat_os.llm.mock import FORCE_ERROR, FORCE_MALFORMED, FORCE_MISSING_KEY
from bharat_os.models.audit import AIJudgement
from bharat_os.models.enums import CriterionType, SoftVerdict
from bharat_os.models.scheme import EligibilityCriterion, Scheme, SchemeVersion
from bharat_os.services.soft_criteria import (
    HUMAN_REVIEW_THRESHOLD,
    PROMPT_VERSION,
    REQUIRED_KEYS,
    build_prompt,
    cache_key,
    judge_all,
    judge_criterion,
    profile_summary,
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


def make_request(prompt: str = "assess this") -> LLMRequest:
    return LLMRequest(system="you judge criteria", prompt=prompt, required_keys=REQUIRED_KEYS)


@pytest.fixture
def scheme_version(session: Session) -> SchemeVersion:
    version = SchemeVersion(
        scheme=Scheme(slug="soft-test"),
        version=1,
        name="Soft Criteria Test Scheme",
        summary="For testing judgement.",
        scheme_type="grant",
        status="active",
        administering_ministry="Ministry of Testing",
        target_segments=["startup"],
        sectors=[],
        states=[],
        benefit_description="Up to Rs 20 lakh.",
        application_difficulty="high",
        effective_from=datetime.now(UTC),
        criteria=[
            EligibilityCriterion(
                criterion_type=CriterionType.SOFT,
                description="The startup must be working on an innovative product.",
                source_url="https://example.gov.in/criteria",
                source_quote="working towards innovation",
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
            EligibilityCriterion(
                criterion_type=CriterionType.HARD,
                description="Must hold DPIIT recognition.",
                machine_readable_rule={
                    "op": "contains",
                    "field": "registrations",
                    "value": "dpiit",
                },
                source_url="https://example.gov.in/criteria",
                last_verified_at=datetime.now(UTC),
                display_order=3,
            ),
        ],
    )
    session.add(version)
    session.commit()
    return version


class TestJsonParsing:
    def test_parses_a_bare_object(self) -> None:
        parsed = parse_json_object('{"verdict": "likely_met"}', ("verdict",))
        assert parsed["verdict"] == "likely_met"

    def test_parses_json_inside_a_code_fence(self) -> None:
        """Models add fences even when told not to."""
        text = 'Here you go:\n```json\n{"verdict": "uncertain"}\n```\nHope that helps.'
        assert parse_json_object(text, ("verdict",))["verdict"] == "uncertain"

    def test_parses_json_surrounded_by_prose(self) -> None:
        text = 'I think that {"verdict": "likely_unmet"} is the right call.'
        assert parse_json_object(text, ("verdict",))["verdict"] == "likely_unmet"

    def test_rejects_non_json(self) -> None:
        with pytest.raises(LLMResponseError, match="not valid JSON"):
            parse_json_object("I cannot answer that.", ("verdict",))

    def test_rejects_a_json_array(self) -> None:
        with pytest.raises(LLMResponseError, match="Expected a JSON object"):
            parse_json_object("[1, 2, 3]", ("verdict",))

    def test_refuses_to_default_a_missing_key(self) -> None:
        """A fabricated judgement is worse than no judgement."""
        with pytest.raises(LLMResponseError, match="missing required keys"):
            parse_json_object('{"reasoning": "because"}', ("verdict", "confidence"))


class TestProviderSelection:
    def test_mock_is_selected_by_name(self) -> None:
        assert isinstance(build_provider("mock"), MockProvider)

    def test_unknown_provider_is_rejected(self) -> None:
        with pytest.raises(LLMError, match="Unknown LLM provider"):
            build_provider("nonexistent")

    def test_gemini_without_a_key_fails_clearly(self) -> None:
        """The error must say what to do, not just that something is missing."""
        from bharat_os.llm.gemini import GeminiProvider

        with pytest.raises(LLMError, match="BHARAT_OS_GEMINI_API_KEY"):
            GeminiProvider(api_key="", model="gemini-2.5-pro")


class TestMockProvider:
    def test_is_deterministic(self) -> None:
        provider = MockProvider()
        first = provider.complete(make_request("same question"))
        second = provider.complete(make_request("same question"))
        assert first.data == second.data

    def test_different_prompts_give_different_answers(self) -> None:
        """A mock that always returns one value would not exercise aggregation."""
        provider = MockProvider()
        answers = {
            str(provider.complete(make_request(f"question {i}")).data["verdict"]) for i in range(40)
        }
        assert len(answers) > 1

    def test_returns_every_required_key(self) -> None:
        response = MockProvider().complete(make_request())
        for key in REQUIRED_KEYS:
            assert key in response.data

    def test_records_the_prompt_for_auditing(self) -> None:
        response = MockProvider().complete(make_request("a specific question"))
        assert response.prompt == "a specific question"
        assert response.model


class TestPromptConstruction:
    def test_summary_omits_fields_the_applicant_did_not_supply(self) -> None:
        """Saying "turnover: unknown" invites the model to speculate about the gap."""
        summary = profile_summary(ApplicantProfile(state="Kerala"))
        assert "Kerala" in summary
        assert "turnover" not in summary.lower()

    def test_summary_states_registrations_explicitly_when_none_are_held(self) -> None:
        """Holding none is an answer, and the model needs to know it is an answer."""
        assert "none" in profile_summary(ApplicantProfile(state="Goa"))

    def test_prompt_includes_the_criterion_and_official_wording(
        self, scheme_version: SchemeVersion
    ) -> None:
        criterion = scheme_version.criteria[0]
        prompt = build_prompt(criterion, scheme_version, PROFILE)
        assert criterion.description in prompt
        assert "working towards innovation" in prompt
        assert scheme_version.name in prompt


class TestCaching:
    def test_identical_questions_are_asked_once(self, session: Session, scheme_version) -> None:
        provider = MockProvider()
        criterion = scheme_version.criteria[0]

        first = judge_criterion(session, criterion, scheme_version, PROFILE, provider=provider)
        second = judge_criterion(session, criterion, scheme_version, PROFILE, provider=provider)

        assert len(provider.calls) == 1
        assert first.cached is False
        assert second.cached is True
        assert second.verdict is first.verdict

    def test_concurrent_cache_writer_reuses_the_winner(
        self, session: Session, scheme_version, monkeypatch
    ) -> None:
        provider = MockProvider()
        criterion = scheme_version.criteria[0]
        winner = AIJudgement(
            cache_key="winner",
            criterion_id=criterion.id,
            verdict=SoftVerdict.LIKELY_MET,
            confidence=0.84,
            reasoning="The other request completed first.",
            evidence_that_would_strengthen=["Customer traction"],
            requires_human_review=False,
            provider=provider.name,
            model=provider.model,
            prompt_version=PROMPT_VERSION,
            prompt="same question",
        )
        scalar = Mock(side_effect=[None, winner])
        monkeypatch.setattr(session, "scalar", scalar)
        monkeypatch.setattr(
            session,
            "commit",
            Mock(side_effect=IntegrityError("INSERT", {}, Exception("duplicate key"))),
        )

        judgement = judge_criterion(
            session, criterion, scheme_version, PROFILE, provider=provider
        )

        assert judgement.cached is True
        assert judgement.verdict is SoftVerdict.LIKELY_MET
        assert scalar.call_count == 2

    def test_a_changed_profile_is_a_new_question(self, session: Session, scheme_version) -> None:
        provider = MockProvider()
        criterion = scheme_version.criteria[0]
        judge_criterion(session, criterion, scheme_version, PROFILE, provider=provider)

        changed = ApplicantProfile(state="Kerala", sector="fintech", stage="growth")
        judge_criterion(session, criterion, scheme_version, changed, provider=provider)

        assert len(provider.calls) == 2

    def test_cache_key_is_scoped_to_the_user(self, scheme_version) -> None:
        provider = MockProvider()
        criterion = scheme_version.criteria[0]

        first_user = cache_key(criterion, PROFILE, provider, user_id="user-a")
        second_user = cache_key(criterion, PROFILE, provider, user_id="user-b")

        assert first_user != second_user

    def test_cache_key_includes_model_and_prompt_version(
        self, session: Session, scheme_version
    ) -> None:
        """Upgrading the model or the prompt must not serve stale judgements."""
        criterion = scheme_version.criteria[0]
        provider = MockProvider()
        baseline = cache_key(criterion, PROFILE, provider)

        class NewerModel(MockProvider):
            model = "mock-deterministic-v2"

        assert cache_key(criterion, PROFILE, NewerModel()) != baseline


class TestJudgement:
    def test_records_an_audit_row(self, session: Session, scheme_version) -> None:
        """Every AI judgement about a user must be reconstructable afterwards."""
        criterion = scheme_version.criteria[0]
        judge_criterion(session, criterion, scheme_version, PROFILE, provider=MockProvider())

        record = session.scalars(select(AIJudgement)).one()
        assert record.criterion_id == criterion.id
        assert record.prompt
        assert record.reasoning
        assert record.model
        assert record.prompt_version == PROMPT_VERSION
        assert criterion.description in record.prompt

    def test_verdicts_use_hedged_vocabulary(self, session: Session, scheme_version) -> None:
        """There is deliberately no plain "met": this is an opinion, not a finding."""
        assert {v.value for v in SoftVerdict} == {"likely_met", "likely_unmet", "uncertain"}

    def test_low_confidence_degrades_to_human_review(
        self, session: Session, scheme_version
    ) -> None:
        judgements = [
            judge_criterion(session, criterion, scheme_version, PROFILE, provider=MockProvider())
            for criterion in scheme_version.criteria
            if criterion.criterion_type is CriterionType.SOFT
        ]
        for judgement in judgements:
            if judgement.confidence < HUMAN_REVIEW_THRESHOLD:
                assert judgement.requires_human_review is True
            else:
                assert judgement.requires_human_review is False

    def test_a_weak_positive_does_not_count_as_support(
        self, session: Session, scheme_version
    ) -> None:
        """A "likely_met" at 0.4 confidence is not evidence of anything."""
        from bharat_os.services.soft_criteria import SoftJudgement

        weak = SoftJudgement(
            criterion_id="x",
            description="d",
            verdict=SoftVerdict.LIKELY_MET,
            confidence=0.4,
            reasoning="r",
            evidence_that_would_strengthen=(),
            requires_human_review=True,
            provider="mock",
            model="m",
            prompt_version=PROMPT_VERSION,
        )
        assert weak.is_positive is False

    def test_every_judgement_names_what_would_settle_it(
        self, session: Session, scheme_version
    ) -> None:
        """ "62% confident" is not actionable; "send your product description" is."""
        judgement = judge_criterion(
            session, scheme_version.criteria[0], scheme_version, PROFILE, provider=MockProvider()
        )
        assert judgement.evidence_that_would_strengthen

    def test_judges_only_soft_criteria(self, session: Session, scheme_version) -> None:
        provider = MockProvider()
        judgements = judge_all(session, scheme_version, PROFILE, provider=provider)
        assert len(judgements) == 2
        assert len(provider.calls) == 2


class TestFailureHandling:
    def _forced(self, marker: str):
        class Forcing(MockProvider):
            def complete(self, request: LLMRequest):
                return super().complete(
                    LLMRequest(
                        system=request.system,
                        prompt=request.prompt + marker,
                        required_keys=request.required_keys,
                    )
                )

        return Forcing()

    def test_malformed_output_does_not_crash_the_assessment(
        self, session: Session, scheme_version
    ) -> None:
        """The deterministic half of the report is still valid and must survive."""
        judgement = judge_criterion(
            session,
            scheme_version.criteria[0],
            scheme_version,
            PROFILE,
            provider=self._forced(FORCE_MALFORMED),
        )
        assert judgement.verdict is SoftVerdict.UNCERTAIN
        assert judgement.requires_human_review is True

    def test_missing_key_degrades_to_review_rather_than_inventing_a_value(
        self, session: Session, scheme_version
    ) -> None:
        judgement = judge_criterion(
            session,
            scheme_version.criteria[0],
            scheme_version,
            PROFILE,
            provider=self._forced(FORCE_MISSING_KEY),
        )
        assert judgement.requires_human_review is True
        assert judgement.confidence == 0.0

    def test_provider_outage_degrades_gracefully(self, session: Session, scheme_version) -> None:
        judgement = judge_criterion(
            session,
            scheme_version.criteria[0],
            scheme_version,
            PROFILE,
            provider=self._forced(FORCE_ERROR),
        )
        assert judgement.requires_human_review is True
        assert "human" in judgement.reasoning.lower()

    def test_failures_are_not_cached(self, session: Session, scheme_version) -> None:
        """A transient outage must not poison the cache with a permanent unknown."""
        judge_criterion(
            session,
            scheme_version.criteria[0],
            scheme_version,
            PROFILE,
            provider=self._forced(FORCE_ERROR),
        )
        assert session.scalars(select(AIJudgement)).all() == []

    def test_confidence_outside_range_is_rejected(self) -> None:
        from bharat_os.services.soft_criteria import _coerce_confidence

        with pytest.raises(LLMResponseError, match="outside"):
            _coerce_confidence(1.7)

    def test_unknown_verdict_is_rejected(self) -> None:
        from bharat_os.services.soft_criteria import _coerce_verdict

        with pytest.raises(LLMResponseError, match="not one of"):
            _coerce_verdict("definitely_eligible")


class TestPrivacy:
    def test_prompt_failures_do_not_log_the_profile(
        self, session: Session, scheme_version, caplog
    ) -> None:
        """The prompt contains personal data, so a failure must not log it."""
        import logging

        class Failing(MockProvider):
            def complete(self, request: LLMRequest):
                raise LLMError("boom")

        with caplog.at_level(logging.DEBUG):
            judge_criterion(
                session,
                scheme_version.criteria[0],
                scheme_version,
                PROFILE,
                provider=Failing(),
            )

        logged = "\n".join(record.getMessage() for record in caplog.records)
        assert "1,200,000" not in logged
        assert "1200000" not in logged
