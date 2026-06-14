from dataclasses import dataclass
import json

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(slots=True)
class ForecastRepository:
    session: Session

    def get_municipality_outlook(self, municipality_id: str) -> dict | None:
        row = self.session.execute(
            text(
                """
                SELECT *
                FROM marts.electoral_forecasting_municipality_2027
                WHERE municipality_id = :municipality_id
                """
            ),
            {"municipality_id": municipality_id},
        ).mappings().first()
        return dict(row) if row else None

    def get_section_outlook(self, section_id: str) -> dict | None:
        row = self.session.execute(
            text(
                """
                SELECT *
                FROM marts.electoral_forecasting_ui_2027
                WHERE seccion_id = :section_id
                """
            ),
            {"section_id": section_id},
        ).mappings().first()
        return dict(row) if row else None

    def get_scenarios(self, municipality_id: str) -> list[dict]:
        rows = self.session.execute(
            text(
                """
                SELECT *
                FROM marts.electoral_scenarios_2027
                WHERE municipality_id = :municipality_id
                ORDER BY CASE scenario_id
                    WHEN 'structural' THEN 1
                    WHEN 'candidate_reset' THEN 2
                    WHEN 'localist_fragmentation' THEN 3
                    WHEN 'oraculum_ready' THEN 4
                    ELSE 5
                END
                """
            ),
            {"municipality_id": municipality_id},
        ).mappings().all()
        return [dict(row) for row in rows]

    def get_scenario(self, municipality_id: str, scenario_id: str) -> dict | None:
        row = self.session.execute(
            text(
                """
                SELECT *
                FROM marts.electoral_scenarios_2027
                WHERE municipality_id = :municipality_id
                  AND scenario_id = :scenario_id
                """
            ),
            {"municipality_id": municipality_id, "scenario_id": scenario_id},
        ).mappings().first()
        return dict(row) if row else None

    def audit(
        self,
        *,
        question: str,
        municipality_id: str,
        section_id: str | None,
        confidence_level: str,
        variables_used: list[str],
        metadata: dict,
    ) -> None:
        self.session.execute(
            text(
                """
                INSERT INTO core.agent_audit_log (
                    question,
                    municipality_id,
                    section_id,
                    datasets_used,
                    variables_used,
                    models_used,
                    confidence_level,
                    response_category,
                    metadata
                ) VALUES (
                    :question,
                    :municipality_id,
                    :section_id,
                    CAST(:datasets_used AS jsonb),
                    CAST(:variables_used AS jsonb),
                    CAST(:models_used AS jsonb),
                    :confidence_level,
                    'forecast_data',
                    CAST(:metadata AS jsonb)
                )
                """
            ),
            {
                "question": question,
                "municipality_id": municipality_id,
                "section_id": section_id,
                "datasets_used": json.dumps(
                    [
                        "marts.electoral_forecasting_features_2027",
                        "marts.electoral_forecast_counterweights_2027",
                        "marts.electoral_forecasting_municipality_2027"
                        if section_id is None
                        else "marts.electoral_forecasting_ui_2027",
                        *(
                            ["marts.electoral_scenarios_2027"]
                            if "scenario" in question.lower()
                            else []
                        ),
                    ]
                ),
                "variables_used": json.dumps(variables_used),
                "models_used": json.dumps(["electoral_structural_baseline_2027_v1"]),
                "confidence_level": confidence_level,
                "metadata": json.dumps(metadata),
            },
        )
        self.session.commit()
