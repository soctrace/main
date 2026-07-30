from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class RuleThresholds:
    stronghold_pct: float = 40.0
    swing_margin_pct: float = 5.0
    high_abstention_pct: float = 38.0
    low_abstention_pct: float = 28.0
    young_under_30_pct: float = 30.0
    aging_over_65_pct: float = 24.0
    high_income_eur: float = 16000.0
    low_income_eur: float = 12000.0
    high_score: float = 70.0
    low_score: float = 35.0


class PoliticalClassificationEngine:
    def __init__(self, thresholds: RuleThresholds | None = None):
        self.thresholds = thresholds or RuleThresholds()

    def classify(self, profile: dict[str, Any]) -> list[str]:
        tags: list[str] = []
        winning_party = str(profile.get("winning_party") or "").upper()
        winning_pct = _float(profile.get("winning_party_pct"))
        second_pct = _float(profile.get("second_party_pct") or profile.get("runner_up_pct"))
        margin = _float(profile.get("victory_margin_pct"))
        if margin is None and winning_pct is not None and second_pct is not None:
            margin = winning_pct - second_pct
        abstention = _float(profile.get("abstention_rate_pct"))
        under_30 = _float(profile.get("under_30_pct"))
        over_65 = _float(profile.get("over_65_pct"))
        income = _float(profile.get("individual_income") or profile.get("renta_media_persona"))
        growth = _float(profile.get("population_growth_pct"))
        score = _float(profile.get("opportunity_score"))

        if winning_party in {"PP", "VOX"} and winning_pct is not None and winning_pct >= self.thresholds.stronghold_pct:
            tags.append("Conservative Stronghold")
        if winning_party in {"PSOE", "IU", "PODEMOS", "SUMAR"} and winning_pct is not None and winning_pct >= self.thresholds.stronghold_pct:
            tags.append("Progressive Stronghold")
        if margin is not None and margin <= self.thresholds.swing_margin_pct:
            tags.append("Swing Section")
        if abstention is not None and abstention >= self.thresholds.high_abstention_pct:
            tags.append("High Abstention Area")
        if growth is not None and growth >= 10:
            tags.append("Residential Growth Area")
        if over_65 is not None and over_65 >= self.thresholds.aging_over_65_pct:
            tags.append("Aging Population Area")
        if under_30 is not None and under_30 >= self.thresholds.young_under_30_pct:
            tags.append("Young Population Area")
        if income is not None and income >= self.thresholds.high_income_eur:
            tags.append("High Income Area")
        if income is not None and income <= self.thresholds.low_income_eur:
            tags.append("Low Income Area")
        if abstention is not None and abstention >= self.thresholds.high_abstention_pct and score is not None and score >= self.thresholds.high_score:
            tags.append("Mobilization Opportunity")
        if margin is not None and margin <= self.thresholds.swing_margin_pct and score is not None and score >= self.thresholds.low_score:
            tags.append("Persuasion Opportunity")
        if score is not None and score >= self.thresholds.high_score:
            tags.append("Door-to-Door Priority")
        if under_30 is not None and under_30 >= self.thresholds.young_under_30_pct:
            tags.append("Digital Campaign Priority")
        if score is not None and score < self.thresholds.low_score and abstention is not None and abstention <= self.thresholds.low_abstention_pct:
            tags.append("Low Electoral ROI Area")

        return tags


def _float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
