"""Ranking and the matched feed."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from bharat_os.engine.results import CriterionResult, HardRuleAssessment
from bharat_os.models.enums import ApplicationDifficulty, EvaluationState
from bharat_os.services.ranking import (
    MatchOutcome,
    RankingInput,
    benefit_factor,
    classify,
    hard_rule_confidence,
    rank,
    score_one,
)
from helpers import VALID_PROFILE, register

LOW = ApplicationDifficulty.LOW
MEDIUM = ApplicationDifficulty.MEDIUM
HIGH = ApplicationDifficulty.HIGH


def assessment(met: int = 0, unmet: int = 0, unknown: int = 0) -> HardRuleAssessment:
    results = {}
    met_keys = tuple(f"m{i}" for i in range(met))
    unmet_keys = tuple(f"u{i}" for i in range(unmet))
    unknown_keys = tuple(f"k{i}" for i in range(unknown))
    for key in met_keys:
        results[key] = CriterionResult(EvaluationState.MET, "met")
    for key in unmet_keys:
        results[key] = CriterionResult(EvaluationState.UNMET, "unmet")
    for key in unknown_keys:
        results[key] = CriterionResult(
            EvaluationState.CANNOT_VERIFY, "unknown", ("annual_turnover_inr",)
        )
    return HardRuleAssessment(met_keys, unmet_keys, unknown_keys, results)


class TestClassification:
    def test_all_met_is_eligible(self) -> None:
        assert classify(assessment(met=3)) is MatchOutcome.ELIGIBLE

    def test_any_unmet_is_ruled_out(self) -> None:
        assert classify(assessment(met=5, unmet=1)) is MatchOutcome.RULED_OUT

    def test_unmet_outranks_unknown(self) -> None:
        """A definite failure is not softened by also having unknowns."""
        assert classify(assessment(met=1, unmet=1, unknown=5)) is MatchOutcome.RULED_OUT

    def test_unknowns_alone_need_more_data(self) -> None:
        assert classify(assessment(met=2, unknown=1)) is MatchOutcome.NEEDS_MORE_DATA

    def test_no_criteria_is_judgement_only(self) -> None:
        assert classify(assessment()) is MatchOutcome.JUDGEMENT_ONLY


class TestConfidence:
    def test_confidence_is_share_of_criteria_met(self) -> None:
        assert hard_rule_confidence(assessment(met=3, unknown=1)) == pytest.approx(0.75)

    def test_unknowns_reduce_confidence_without_being_failures(self) -> None:
        """The number reflects what has been established, not an optimistic guess."""
        assert hard_rule_confidence(assessment(met=1, unknown=3)) == pytest.approx(0.25)

    def test_no_criteria_gives_neutral_confidence(self) -> None:
        assert hard_rule_confidence(assessment()) == pytest.approx(0.5)

    def test_confidence_never_exceeds_one(self) -> None:
        assert hard_rule_confidence(assessment(met=10)) == pytest.approx(1.0)


class TestBenefitScaling:
    def test_larger_benefits_score_higher(self) -> None:
        assert benefit_factor(10_000_000) > benefit_factor(1_000_000)

    def test_scaling_is_sublinear(self) -> None:
        """A 100x larger benefit must not be 100x more influential."""
        small = benefit_factor(1_000_000)
        large = benefit_factor(100_000_000)
        assert large / small < 3

    def test_non_monetary_schemes_are_not_ranked_last(self) -> None:
        """DPIIT recognition pays nothing but unlocks much of the corpus."""
        assert benefit_factor(None) > 0
        assert benefit_factor(0) > 0

    def test_factor_is_bounded(self) -> None:
        assert benefit_factor(10**15) <= 1.0


class TestScoring:
    def test_difficulty_discounts_the_score(self) -> None:
        easy = score_one(RankingInput("easy", assessment(met=2), LOW, 1_000_000))
        hard = score_one(RankingInput("hard", assessment(met=2), HIGH, 1_000_000))
        assert easy.score > hard.score

    def test_ruled_out_schemes_score_zero(self) -> None:
        """Not a weak match: the applicant cannot have it."""
        result = score_one(RankingInput("no", assessment(met=9, unmet=1), LOW, 100_000_000))
        assert result.score == 0.0
        assert result.outcome is MatchOutcome.RULED_OUT

    def test_breakdown_components_are_exposed(self) -> None:
        result = score_one(RankingInput("s", assessment(met=2), MEDIUM, 5_000_000))
        assert result.confidence_factor > 0
        assert result.benefit_factor > 0
        assert result.difficulty_factor == pytest.approx(0.7)
        assert result.score == pytest.approx(
            result.confidence_factor * result.benefit_factor * result.difficulty_factor
        )

    def test_missing_fields_are_surfaced(self) -> None:
        result = score_one(RankingInput("s", assessment(met=1, unknown=1), LOW, 1))
        assert result.missing_fields == ("annual_turnover_inr",)


class TestRanking:
    def test_ruled_out_is_partitioned_not_appended(self) -> None:
        matches, ruled_out = rank(
            [
                RankingInput("good", assessment(met=2), LOW, 1_000_000),
                RankingInput("bad", assessment(met=1, unmet=1), LOW, 100_000_000),
            ]
        )
        assert [m.slug for m in matches] == ["good"]
        assert [m.slug for m in ruled_out] == ["bad"]

    def test_higher_score_comes_first(self) -> None:
        matches, _ = rank(
            [
                RankingInput("small-hard", assessment(met=1, unknown=1), HIGH, 100_000),
                RankingInput("big-easy", assessment(met=2), LOW, 20_000_000),
            ]
        )
        assert [m.slug for m in matches] == ["big-easy", "small-hard"]

    def test_ordering_is_stable_for_ties(self) -> None:
        """A feed that reshuffles between identical requests looks broken."""
        items = [
            RankingInput("beta", assessment(met=1), LOW, 1_000_000),
            RankingInput("alpha", assessment(met=1), LOW, 1_000_000),
        ]
        first, _ = rank(items)
        second, _ = rank(items)
        assert [m.slug for m in first] == ["alpha", "beta"] == [m.slug for m in second]

    def test_empty_input_yields_empty_output(self) -> None:
        assert rank([]) == ([], [])


class TestMatchesEndpoint:
    def test_requires_a_profile(self, client: TestClient) -> None:
        register(client)
        response = client.get("/matches")
        assert response.status_code == 409
        assert "PUT /profile" in response.json()["detail"]

    def test_returns_a_ranked_feed(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        body = client.get("/matches").json()

        assert body["schemes_assessed"] == 40
        assert body["matches"], "a DPIIT-recognised early-stage startup should match something"
        scores = [m["score"] for m in body["matches"]]
        assert scores == sorted(scores, reverse=True)

    def test_feed_includes_the_advisory_disclaimer(self, client: TestClient, seeded_corpus) -> None:
        """API consumers must not be able to drop the caveat by ignoring the UI."""
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        body = client.get("/matches").json()
        assert "not a determination of eligibility" in body["disclaimer"]

    def test_ruled_out_schemes_are_separated_with_reasons(
        self, client: TestClient, seeded_corpus
    ) -> None:
        register(client)
        # No Udyam registration, so Udyam-gated schemes must be ruled out.
        client.put("/profile", json={**VALID_PROFILE, "registrations": ["dpiit"]})
        body = client.get("/matches").json()

        ruled_out_slugs = {m["slug"] for m in body["ruled_out"]}
        assert "cgtmse" in ruled_out_slugs
        for entry in body["ruled_out"]:
            assert entry["criteria_unmet"] >= 1
            assert entry["score"] == 0.0

    def test_suggests_profile_additions_that_resolve_unknowns(
        self, client: TestClient, seeded_corpus
    ) -> None:
        register(client)
        minimal = {
            k: v
            for k, v in VALID_PROFILE.items()
            if k not in {"annual_turnover_inr", "social_category"}
        }
        client.put("/profile", json=minimal)
        body = client.get("/matches").json()
        assert "annual_turnover_inr" in body["suggested_profile_additions"]

    def test_confidence_filter_narrows_the_feed(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        everything = client.get("/matches").json()["matches"]
        strict = client.get("/matches?min_confidence=1.0").json()["matches"]
        assert len(strict) <= len(everything)
        assert all(m["confidence"] >= 1.0 for m in strict)

    def test_single_scheme_assessment(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        body = client.get("/matches/sisfs").json()
        assert body["slug"] == "sisfs"
        assert body["soft_criteria_count"] >= 1
        assert 0.0 <= body["confidence"] <= 1.0

    def test_unknown_scheme_returns_404(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        assert client.get("/matches/nope").status_code == 404

    def test_matches_require_consent(self, client: TestClient, seeded_corpus) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)
        client.post("/me/consents", json={"purpose": "scheme_matching", "granted": False})
        assert client.get("/matches").status_code == 403


class TestExpensiveRouteRateLimit:
    def test_deep_dive_has_a_per_session_budget(self, client: TestClient) -> None:
        register(client)
        client.put("/profile", json=VALID_PROFILE)

        # A caller-controlled forwarded address must not create a fresh budget.
        responses = [
            client.get(
                "/matches/missing/deep-dive",
                headers={"X-Forwarded-For": f"203.0.113.{index}"},
            )
            for index in range(11)
        ]

        assert all(response.status_code == 404 for response in responses[:10])
        assert responses[10].status_code == 429
        assert "wait" in responses[10].json()["detail"].lower()
