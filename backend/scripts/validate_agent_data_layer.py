from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sys
from typing import Iterable

from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal


REQUIRED_COLUMNS: dict[str, list[str]] = {
    "marts.agent_section_lookup": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_number",
        "section_name",
        "display_name",
    ],
    "marts.agent_population_age": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_name",
        "year",
        "gender",
        "age_cohort",
        "age_min",
        "age_max",
        "people",
    ],
    "marts.agent_section_profile": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_name",
        "year",
        "population_total",
        "population_density",
        "average_age",
        "population_under_18",
        "population_under_18_pct",
        "population_under_30",
        "population_under_30_pct",
        "population_over_65",
        "population_over_65_pct",
        "income_individual",
        "income_household",
        "participation_pct",
        "abstention_pct",
        "winner_party",
        "built_footprint",
        "parcel_density",
        "building_intensity",
        "estimated_real_estate_value_m2",
        "market_price_estimated_m2",
        "housing_pressure_label",
    ],
    "marts.agent_electoral_results": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_name",
        "election_id",
        "election_type",
        "election_year",
        "election_month",
        "election_label",
        "party",
        "canonical_party",
        "votes",
        "valid_votes",
        "vote_pct",
    ],
    "marts.agent_electoral_summary": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_name",
        "election_id",
        "election_type",
        "election_year",
        "election_label",
        "census",
        "valid_votes",
        "total_votes",
        "participation_pct",
        "abstention_pct",
        "winner_party",
        "winner_vote_pct",
        "second_party",
        "second_vote_pct",
        "margin_pct",
    ],
    "marts.agent_income_sources": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_name",
        "year",
        "income_individual",
        "income_household",
        "salary_share",
        "pension_share",
        "unemployment_share",
        "other_income_share",
    ],
    "marts.agent_housing_profile": [
        "municipio_id",
        "municipio_nombre",
        "section_id",
        "section_name",
        "year",
        "parcel_density",
        "built_footprint",
        "avg_plot_size",
        "building_intensity",
        "estimated_cadastral_value_m2",
        "market_price_estimated_m2",
        "market_to_cadastral_ratio",
        "housing_classification",
        "residential_pressure_index",
    ],
}


@dataclass(frozen=True)
class Check:
    ok: bool
    message: str
    warning: bool = False


def icon(check: Check) -> str:
    if check.ok and check.warning:
        return "⚠"
    return "✅" if check.ok else "❌"


def scalar(session, sql: str):
    return session.execute(text(sql)).scalar()


def rows(session, sql: str) -> list[dict]:
    return [dict(row) for row in session.execute(text(sql)).mappings().all()]


def check_view_exists(session, relation: str) -> Check:
    schema, name = relation.split(".")
    exists = bool(
        scalar(
            session,
            f"""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.views
                WHERE table_schema = '{schema}'
                  AND table_name = '{name}'
            )
            """,
        )
    )
    return Check(exists, f"{relation} exists" if exists else f"{relation} no existe")


def check_columns(session, relation: str, expected: Iterable[str]) -> Check:
    schema, name = relation.split(".")
    found = {
        row["column_name"]
        for row in rows(
            session,
            f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = '{schema}'
              AND table_name = '{name}'
            """,
        )
    }
    missing = [column for column in expected if column not in found]
    return Check(not missing, f"{relation} columns OK" if not missing else f"{relation} missing columns: {', '.join(missing)}")


def check_rows(session, relation: str) -> Check:
    count = int(scalar(session, f"SELECT COUNT(*) FROM {relation} WHERE municipio_id = '29070'") or 0)
    return Check(count > 0, f"{relation} returns {count} Mijas rows")


def check_not_all_null(session, relation: str, column: str) -> Check:
    count = int(scalar(session, f"SELECT COUNT(*) FROM {relation} WHERE municipio_id = '29070' AND {column} IS NOT NULL") or 0)
    return Check(count > 0, f"{relation}.{column} has {count} non-null Mijas rows")


def main() -> int:
    checks: list[Check] = []
    session = SessionLocal()
    try:
        for relation, columns in REQUIRED_COLUMNS.items():
            checks.append(check_view_exists(session, relation))
            checks.append(check_columns(session, relation, columns))
            checks.append(check_rows(session, relation))

        lookup_count = int(scalar(session, "SELECT COUNT(DISTINCT section_id) FROM marts.agent_section_lookup WHERE municipio_id = '29070'") or 0)
        checks.append(Check(lookup_count == 37, f"marts.agent_section_lookup has {lookup_count} Mijas sections", warning=lookup_count != 37))

        for column in ("population_total", "average_age", "population_over_65", "abstention_pct", "winner_party"):
            checks.append(check_not_all_null(session, "marts.agent_section_profile", column))

        for column in ("vote_pct", "canonical_party"):
            checks.append(check_not_all_null(session, "marts.agent_electoral_results", column))

        for column in ("income_individual", "pension_share"):
            checks.append(check_not_all_null(session, "marts.agent_income_sources", column))

        for column in ("market_price_estimated_m2", "residential_pressure_index"):
            checks.append(check_not_all_null(session, "marts.agent_housing_profile", column))

        population_years = rows(
            session,
            """
            SELECT year, COUNT(DISTINCT section_id) AS sections
            FROM marts.agent_section_profile
            WHERE municipio_id = '29070'
            GROUP BY year
            ORDER BY year
            """,
        )
        checks.append(Check(bool(population_years), f"population years: {population_years}"))

        electoral_processes = rows(
            session,
            """
            SELECT election_type, election_year, COUNT(DISTINCT election_id) AS elections
            FROM marts.agent_electoral_summary
            WHERE municipio_id = '29070'
            GROUP BY election_type, election_year
            ORDER BY election_type, election_year
            """,
        )
        checks.append(Check(bool(electoral_processes), f"electoral processes: {electoral_processes}"))

        income_years = rows(
            session,
            """
            SELECT year, COUNT(DISTINCT section_id) AS sections
            FROM marts.agent_income_sources
            WHERE municipio_id = '29070'
            GROUP BY year
            ORDER BY year
            """,
        )
        checks.append(Check(bool(income_years), f"income years: {income_years}", warning=bool(income_years)))

        housing_years = rows(
            session,
            """
            SELECT year, COUNT(DISTINCT section_id) AS sections
            FROM marts.agent_housing_profile
            WHERE municipio_id = '29070'
            GROUP BY year
            ORDER BY year
            """,
        )
        checks.append(Check(bool(housing_years), f"housing years: {housing_years}", warning=bool(housing_years)))
    finally:
        session.close()

    for check in checks:
        print(f"{icon(check)} {check.message}")

    return 0 if all(check.ok for check in checks) else 1


if __name__ == "__main__":
    raise SystemExit(main())
