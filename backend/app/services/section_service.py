from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db_session
from app.repositories.section_repository import SectionRepository
from app.schemas.section import (
    SectionDemographyBlock,
    SectionDetailResponse,
    SectionDisplayBlock,
    SectionElectoralBlock,
    SectionGeographyBlock,
    SectionIncomeBlock,
)
from app.services.naming import district_label_from_code, municipality_name_from_id


class SectionService:
    def __init__(self, session: Session):
        self.repository = SectionRepository(session=session)

    def get_section_detail(
        self,
        section_id: str,
        year: int = 2023,
        election_id: int | None = None,
    ) -> SectionDetailResponse:
        row = self.repository.get_section_detail(
            section_id,
            year=year,
            election_id=election_id,
        )
        if not row:
            raise HTTPException(status_code=404, detail="Section not found")

        municipality_id = row["municipality_id"]
        return SectionDetailResponse(
            display=SectionDisplayBlock(
                section_id=row["seccion_id"],
                label=row["label_cliente"],
                label_cliente=row["label_cliente"],
                section_name=row["label_cliente"] or row["nombre_barrio"],
                display_name=row["label_cliente"] or row["nombre_barrio"] or row["seccion_numero_visible"],
                municipality_id=municipality_id,
                municipality=municipality_name_from_id(municipality_id),
                district=district_label_from_code(row["district_code"]),
                section_number=row["seccion_numero_visible"],
                neighborhood=row["nombre_barrio"],
                nombre_barrio=row["nombre_barrio"],
                zone=row["zona_macro"],
                year=row["anio"],
            ),
            geography=SectionGeographyBlock(
                area_km2=self._to_float(row["area_km2_geodesic"]),
                population_density=self._to_float(row["densidad"]),
            ),
            demography=SectionDemographyBlock(
                population_total=row["pob_total"],
                population_male=row["pob_h"],
                population_female=row["pob_m"],
                population_0_14=row["pob_0_14"],
                population_15_29=row["pob_15_29"],
                population_30_44=row["pob_30_44"],
                population_45_64=row["pob_45_64"],
                population_65_plus=row["pob_65p"],
                pct_0_14=self._to_float(row["pct_0_14"]),
                pct_15_29=self._to_float(row["pct_15_29"]),
                pct_30_44=self._to_float(row["pct_30_44"]),
                pct_45_64=self._to_float(row["pct_45_64"]),
                pct_65_plus=self._to_float(row["pct_65p"]),
                pct_foreign_born=None,
                dependency_ratio=self._to_float(row["dependency_ratio"]),
            ),
            electoral=SectionElectoralBlock(
                election_id=int(row["election_id"]) if row["election_id"] is not None else None,
                census=row["censo"],
                turnout=self._to_float(row["participacion"]),
                votes_cast=row["votos_emitidos"],
                valid_votes=row["votos_validos"],
                blank_votes=row["votos_blanco"],
                null_votes=row["votos_nulos"],
                blank_pct=self._to_float(row["blanco_pct"]),
                null_pct=self._to_float(row["nulos_pct"]),
                winning_party=row["sigla_ganadora"],
                pct_pp=self._to_float(row["pct_pp"]),
                pct_psoe=self._to_float(row["pct_psoe"]),
                pct_vox=self._to_float(row["pct_vox"]),
            ),
            income=SectionIncomeBlock(
                renta_media_persona=self._to_float(row["renta_media_persona"]),
                renta_media_hogar=self._to_float(row["renta_media_hogar"]),
                income_quintile=int(row["income_quintile"]) if row["income_quintile"] is not None else None,
                income_level=row["income_level"],
                income_rank_municipal=int(row["income_rank_municipal"]) if row["income_rank_municipal"] is not None else None,
                income_index=self._to_float(row["income_index"]),
                income_salary=self._to_float(row["income_salary"]),
                income_pension=self._to_float(row["income_pension"]),
                income_unemployment=self._to_float(row["income_unemployment"]),
                income_social_benefits=self._to_float(row["income_social_benefits"]),
                income_other=self._to_float(row["income_other"]),
                pension_dependency_index=self._to_float(row["pension_dependency_index"]),
                employment_dependency_index=self._to_float(row["employment_dependency_index"]),
                welfare_dependency_index=self._to_float(row["welfare_dependency_index"]),
                entrepreneurial_activity_signal=self._to_float(row["entrepreneurial_activity_signal"]),
                passive_income_signal=self._to_float(row["passive_income_signal"]),
            ),
        )

    @staticmethod
    def _to_float(value) -> float | None:
        return float(value) if value is not None else None


def get_section_service(
    session: Session = Depends(get_db_session),
) -> SectionService:
    return SectionService(session=session)
