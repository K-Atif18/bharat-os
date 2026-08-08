"""Field maps for application drafting.

A field map defines, per scheme, which fields a draft has, where each one's value
comes from, and — for narrative fields — what to ask the model to write about.

This is data, not code, on purpose: adding drafting support for a new scheme
should not require a code change, and a domain reviewer without Python should be
able to read and correct a field map.

The invariant that matters most in this module: **no field map may define a
submission action**. A field map produces text for a human to copy, edit and
submit themselves. There is no code path from here to a government portal.
"""

from __future__ import annotations

from dataclasses import dataclass

from bharat_os.models.enums import DraftFieldSource


@dataclass(frozen=True)
class DraftField:
    """One field in an application draft."""

    key: str
    label: str
    source: DraftFieldSource
    #: For PROFILE fields: the profile attribute to copy.
    profile_field: str | None = None
    #: For GENERATED_NARRATIVE fields: what the model should write about.
    narrative_instruction: str | None = None
    #: For HUMAN_REQUIRED fields: why this cannot be filled automatically.
    human_required_reason: str | None = None
    max_words: int | None = None


#: Field maps for the three flagship schemes named in the plan.
FIELD_MAPS: dict[str, list[DraftField]] = {
    "sisfs": [
        DraftField(
            "startup_name", "Startup name", DraftFieldSource.PROFILE, profile_field="entity_name"
        ),
        DraftField("state", "State", DraftFieldSource.PROFILE, profile_field="state"),
        DraftField("sector", "Sector", DraftFieldSource.PROFILE, profile_field="sector"),
        DraftField(
            "stage_of_development",
            "Stage of development",
            DraftFieldSource.PROFILE,
            profile_field="stage",
        ),
        DraftField(
            "problem_statement",
            "What problem does the startup solve?",
            DraftFieldSource.GENERATED_NARRATIVE,
            narrative_instruction=(
                "Describe the problem this startup addresses, in plain language a "
                "non-technical reviewer can follow. Base this only on the sector and "
                "stage given; do not invent specifics the profile does not contain."
            ),
            max_words=120,
        ),
        DraftField(
            "innovation_and_scalability",
            "How is the product innovative and scalable?",
            DraftFieldSource.GENERATED_NARRATIVE,
            narrative_instruction=(
                "Explain, from the profile alone, why this business is plausibly "
                "innovative and has a scalable model. Flag where the profile does not "
                "give enough to say something specific, rather than inventing detail."
            ),
            max_words=150,
        ),
        DraftField(
            "use_of_funds",
            "How will the grant be used?",
            DraftFieldSource.HUMAN_REQUIRED,
            human_required_reason=(
                "Disbursal is milestone-based and the milestones are specific to your "
                "product roadmap, which is not something we can infer from a profile."
            ),
        ),
        DraftField(
            "pitch_deck_summary",
            "Pitch deck",
            DraftFieldSource.HUMAN_REQUIRED,
            human_required_reason="This is a document you attach, not text we can draft.",
        ),
    ],
    "pmegp": [
        DraftField(
            "applicant_name",
            "Applicant name",
            DraftFieldSource.PROFILE,
            profile_field="entity_name",
        ),
        DraftField("state", "State", DraftFieldSource.PROFILE, profile_field="state"),
        DraftField("sector", "Activity / sector", DraftFieldSource.PROFILE, profile_field="sector"),
        DraftField(
            "project_description",
            "Brief description of the proposed unit",
            DraftFieldSource.GENERATED_NARRATIVE,
            narrative_instruction=(
                "Write a short, plain description of a new micro-enterprise in the "
                "given sector and state, suitable as an opening paragraph of a "
                "project report. State only what follows from the profile."
            ),
            max_words=100,
        ),
        DraftField(
            "project_cost_breakdown",
            "Project cost breakdown",
            DraftFieldSource.HUMAN_REQUIRED,
            human_required_reason=(
                "Machinery, working capital and construction costs are specific to your "
                "actual plan and must come from your own quotations, not a profile."
            ),
        ),
        DraftField(
            "employment_generation",
            "Expected employment generated",
            DraftFieldSource.HUMAN_REQUIRED,
            human_required_reason="This depends on your specific staffing plan.",
        ),
    ],
    "cgtmse": [
        DraftField(
            "borrower_name", "Borrower name", DraftFieldSource.PROFILE, profile_field="entity_name"
        ),
        DraftField("state", "State", DraftFieldSource.PROFILE, profile_field="state"),
        DraftField(
            "business_summary",
            "Summary of the business",
            DraftFieldSource.GENERATED_NARRATIVE,
            narrative_instruction=(
                "Summarise the business for a lender's credit note, from the sector, "
                "stage and turnover given. Keep it factual and brief; do not speculate "
                "about financial performance the profile does not state."
            ),
            max_words=100,
        ),
        DraftField(
            "credit_facility_required",
            "Credit facility applied for",
            DraftFieldSource.HUMAN_REQUIRED,
            human_required_reason=(
                "The guarantee is sought by your lender once they have appraised a "
                "specific loan amount and purpose, which is not in your profile."
            ),
        ),
        DraftField(
            "collateral_offered",
            "Collateral position",
            DraftFieldSource.HUMAN_REQUIRED,
            human_required_reason="This is a matter for you and your lender to state accurately.",
        ),
    ],
}
