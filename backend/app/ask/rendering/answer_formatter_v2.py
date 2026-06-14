from __future__ import annotations

from typing import Any


class AnswerFormatterV2:
    def electoral_viability(self, row: dict[str, Any]) -> str:
        party = row.get("party") or "El partido"
        label = row.get("viability_label") or "competitiva"
        return "\n\n".join(
            [
                f"Con los datos históricos y territoriales disponibles, {party} presenta actualmente una posición {label} para disputar la victoria municipal.",
                "Indicadores principales\n\n"
                f"• Voto municipal más reciente: {self._decimal(row.get('latest_municipal_vote_pct'))}%\n"
                f"• Posición municipal reciente: {row.get('latest_municipal_position')}\n"
                f"• Secciones donde fue primera fuerza: {row.get('sections_won')} de {row.get('sections_total')}\n"
                f"• Margen frente al principal rival: {self._signed(row.get('margin_vs_main_opponent'))} puntos\n"
                f"• Fortaleza histórica media: {self._decimal(row.get('average_historical_vote_pct'))}%\n"
                f"• Tendencia: {row.get('trend_direction')}\n"
                f"• Zonas competitivas: {row.get('competitive_sections')}",
                "Qué significa\n\n"
                "No puedo calcular una probabilidad electoral real porque SocTrace todavía no dispone de una capa de sondeos conectada "
                "ni de un modelo probabilístico validado. Lo que sí puedo hacer es estimar la viabilidad electoral con datos históricos y territoriales.",
                "Cómo se ha calculado\n\n"
                "Para ello considero:\n\n"
                "• Resultados municipales históricos.\n"
                "• Fortaleza territorial por secciones.\n"
                "• Diferencia frente al principal rival.\n"
                "• Participación, abstención y competitividad electoral.",
                "Lectura estratégica\n\n"
                f"Los datos disponibles sugieren que {party} tiene una base territorial relevante para competir, pero la lectura debe entenderse "
                "como estimación orientativa: no es una probabilidad estadística real. La oportunidad política está en convertir secciones competitivas "
                "y bolsas de abstención en ventaja territorial.",
                "Cautela metodológica\n\n• No es una probabilidad estadística real.\n• No sustituye sondeos ni un modelo electoral validado.",
                "Preguntas relacionadas\n\n• ¿En qué secciones tendría más margen de crecimiento?\n• ¿Dónde hay más abstención movilizable?",
            ]
        )

    def electoral_viability_comparison(self, rows: list[dict[str, Any]]) -> str:
        top = rows[0] if rows else {}
        bullets = "\n".join(
            f"• {row.get('party')}: viabilidad {row.get('viability_label')} apoyada en {self._decimal(row.get('latest_municipal_vote_pct'))}% de voto municipal reciente"
            for row in rows[:5]
        )
        return "\n\n".join(
            [
                f"Ahora mismo, el partido mejor situado en esta lectura es {top.get('party')}.",
                f"Indicadores principales\n\n{bullets}",
                "Qué significa\n\nNo puedo comparar probabilidades reales de victoria porque SocTrace no tiene sondeos actuales ni un modelo probabilístico validado. Sí puedo comparar viabilidad orientativa con datos históricos y territoriales.",
                "Cómo se ha calculado\n\nCruzo voto municipal reciente, posición competitiva, fortaleza territorial, margen, tendencia y secciones ganadas.",
                "Lectura estratégica\n\nLa comparación debe leerse como posición competitiva territorial, no como predicción electoral. Sirve para priorizar análisis de campaña, no para sustituir un sondeo.",
                "Cautela metodológica\n\n• No es una predicción de resultado.\n• No incorpora sondeos actuales.",
                "Preguntas relacionadas\n\n• ¿Dónde hay más abstención movilizable?\n• ¿En qué secciones tendría más margen de crecimiento el PP?",
            ]
        )

    def electoral_growth_opportunity(self, party: str, rows: list[dict[str, Any]]) -> str:
        bullets = "\n".join(
            f"• {row.get('section_name')}: margen a primera fuerza {self._decimal(row.get('margin_to_first_place'))} puntos, abstención {self._decimal(row.get('abstention_pct'))}%. {row.get('opportunity_explanation')}"
            for row in rows[:6]
        )
        top = rows[0] if rows else {}
        return "\n\n".join(
            [
                f"Las secciones con mayor potencial aparecen encabezadas por {top.get('section_name')}.",
                f"Indicadores principales\n\n{bullets}",
                "Qué significa\n\nEl crecimiento se interpreta como margen de mejora electoral del partido, no como crecimiento de población.",
                "Cómo se ha calculado\n\nHe priorizado secciones donde el partido combina margen competitivo, abstención, volatilidad histórica y capacidad de recuperar techo electoral.",
                "Lectura estratégica\n\n"
                f"Para {party}, estas zonas son las más interesantes para una estrategia de refuerzo: no todas son necesariamente bastiones, "
                "pero sí lugares donde una mejora relativamente focalizada puede tener más rendimiento territorial.",
                "Cautela metodológica\n\n• Es una priorización estratégica orientativa.\n• No predice transferencia real de votos.",
                "Preguntas relacionadas\n\n• ¿Dónde hay más abstención movilizable?\n• ¿Cuántos votos adicionales podría captar el partido en esas secciones?",
            ]
        )

    def _decimal(self, value: Any, decimals: int = 1) -> str:
        try:
            return f"{float(value):.{decimals}f}".replace(".", ",")
        except (TypeError, ValueError):
            return "s/d"

    def _signed(self, value: Any, decimals: int = 1) -> str:
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return "s/d"
        sign = "+" if numeric > 0 else ""
        return f"{sign}{numeric:.{decimals}f}".replace(".", ",")
