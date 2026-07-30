from app.services.analyst.schemas import SyntheticVariableRef


TURNOUT_OPPORTUNITY_SCORE = SyntheticVariableRef(
    name="turnout_opportunity_score",
    version="v0",
    status="experimental",
    formula="0.45 * abstention_index + 0.35 * persuadable_margin_index + 0.20 * population_weight_index",
    source_variables=[
        "abstention_rate_pct",
        "winning_party_pct",
        "target_party_vote_pct",
        "population_total",
    ],
)


CAMPAIGN_ROI_SCORE = SyntheticVariableRef(
    name="campaign_roi_score",
    version="v0",
    status="experimental",
    formula="opportunity_score adjusted by section size and electoral competitiveness",
    source_variables=[
        "opportunity_score",
        "population_total",
        "winning_margin_pct",
    ],
)
