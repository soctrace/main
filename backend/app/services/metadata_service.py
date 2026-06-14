from fastapi import Depends

from app.schemas.metadata import VariableMetadata, VariablesMetadataResponse


class MetadataService:
    def get_variables(self) -> VariablesMetadataResponse:
        return VariablesMetadataResponse(
            items=[
                VariableMetadata(
                    key="population_density",
                    label="Population Density",
                    type="number",
                    available=True,
                    description="Residents per square kilometre",
                ),
                VariableMetadata(
                    key="population_total",
                    label="Population Total",
                    type="number",
                    available=True,
                    description="Total resident population",
                ),
                VariableMetadata(
                    key="pct_65_plus",
                    label="Age Structure (% 65+)",
                    type="percentage",
                    available=True,
                    description="Population share aged 65 or above",
                ),
                VariableMetadata(
                    key="pct_foreign_born",
                    label="Foreign-born (%)",
                    type="percentage",
                    available=False,
                    description="Reserved for a future data source integration",
                ),
                VariableMetadata(
                    key="turnout",
                    label="Turnout 2023",
                    type="percentage",
                    available=True,
                    description="Votes cast divided by electoral census",
                ),
                VariableMetadata(
                    key="winning_party",
                    label="Winning Party",
                    type="category",
                    available=True,
                    description="Party with the most votes in the section",
                ),
            ]
        )


def get_metadata_service() -> MetadataService:
    return MetadataService()

