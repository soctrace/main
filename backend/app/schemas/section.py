from pydantic import BaseModel


class SectionDisplayBlock(BaseModel):
    section_id: str
    label: str
    label_cliente: str | None = None
    section_name: str | None = None
    display_name: str | None = None
    municipality_id: str
    municipality: str
    district: str
    section_number: str | None = None
    neighborhood: str | None = None
    nombre_barrio: str | None = None
    zone: str | None = None
    year: int | None = None


class SectionGeographyBlock(BaseModel):
    area_km2: float | None = None
    population_density: float | None = None


class SectionDemographyBlock(BaseModel):
    population_total: int | None = None
    population_male: int | None = None
    population_female: int | None = None
    population_0_14: int | None = None
    population_15_29: int | None = None
    population_30_44: int | None = None
    population_45_64: int | None = None
    population_65_plus: int | None = None
    pct_0_14: float | None = None
    pct_15_29: float | None = None
    pct_30_44: float | None = None
    pct_45_64: float | None = None
    pct_65_plus: float | None = None
    pct_foreign_born: float | None = None
    dependency_ratio: float | None = None


class SectionElectoralBlock(BaseModel):
    election_id: int | None = None
    census: int | None = None
    turnout: float | None = None
    votes_cast: int | None = None
    valid_votes: int | None = None
    blank_votes: int | None = None
    null_votes: int | None = None
    blank_pct: float | None = None
    null_pct: float | None = None
    winning_party: str | None = None
    pct_pp: float | None = None
    pct_psoe: float | None = None
    pct_vox: float | None = None


class SectionIncomeBlock(BaseModel):
    renta_media_persona: float | None = None
    renta_media_hogar: float | None = None
    income_quintile: int | None = None
    income_level: str | None = None
    income_rank_municipal: int | None = None
    income_index: float | None = None
    income_salary: float | None = None
    income_pension: float | None = None
    income_unemployment: float | None = None
    income_social_benefits: float | None = None
    income_other: float | None = None
    pension_dependency_index: float | None = None
    employment_dependency_index: float | None = None
    welfare_dependency_index: float | None = None
    entrepreneurial_activity_signal: float | None = None
    passive_income_signal: float | None = None


class SectionDetailResponse(BaseModel):
    display: SectionDisplayBlock
    geography: SectionGeographyBlock
    demography: SectionDemographyBlock
    electoral: SectionElectoralBlock
    income: SectionIncomeBlock
