import re
from typing import Any

from app.ask.planner.execution_plan import ExecutionPlan, PlanStep
from app.services.local_analyst_service import extract_party, normalize


PLANNER_PROMPT = """
You are the soctrace planning engine.

Your job is not to answer.
Your job is to understand the question, resolve references, build a tool execution plan,
decide which tools must run, and return a structured plan.

Use conversation state when the user references previous results.
Do not ignore previous analytical outputs.
Never answer directly.
""".strip()


class SocTracePlanner:
    def build_plan(
        self,
        question: str,
        resolved_references: dict[str, Any],
        active_municipality: str | None,
    ) -> ExecutionPlan | None:
        text = normalize(question)
        sections = resolved_references.get("resolvedSections") or []
        if not sections:
            return None

        section_ids = [str(section["sectionId"]) for section in sections if section.get("sectionId")]
        if not section_ids:
            return None

        active_election = resolved_references.get("activeElection") or {}
        year = self._extract_year(question) or active_election.get("year") or 2023
        election_type = self._extract_election_type(question) or active_election.get("type") or "municipales"
        municipality = active_municipality or resolved_references.get("municipality") or "29070"

        if re.search(r"gan[oó]|fuerza m[aá]s votada|vencedor|winner|gano", text):
            party = extract_party(question) or resolved_references.get("lastParty") or "PP"
            return ExecutionPlan(
                intent="count_winner_party_in_previous_sections",
                resolvedReferences=resolved_references,
                steps=[
                    PlanStep(action="recover_context", description="Recover previous section set from conversation state."),
                    PlanStep(
                        action="call_tool",
                        toolName="winner_party_by_section_set",
                        toolInput={
                            "sectionIds": section_ids,
                            "electionType": election_type,
                            "year": year,
                        },
                        description="Get winning party by section.",
                    ),
                    PlanStep(action="calculate", description=f"Count sections where {party} is the winning party."),
                    PlanStep(action="synthesize", description="Explain the count and list matching sections."),
                ],
            )

        if re.search(r"renta|ingreso|income", text):
            return ExecutionPlan(
                intent="average_income_previous_sections",
                resolvedReferences=resolved_references,
                steps=[
                    PlanStep(action="recover_context", description="Recover previous section set from conversation state."),
                    PlanStep(
                        action="call_tool",
                        toolName="socioeconomic_section_profile",
                        toolInput={"municipality": municipality, "sectionIds": section_ids},
                        description="Get socioeconomic profile for previous section set.",
                    ),
                    PlanStep(action="calculate", description="Calculate average income for the selected sections."),
                    PlanStep(action="synthesize", description="Explain income average and compare with municipal average."),
                ],
            )

        if re.search(r"edad media|edad promedio|que edad|qué edad", text):
            return ExecutionPlan(
                intent="average_age_previous_sections",
                resolvedReferences=resolved_references,
                steps=[
                    PlanStep(action="recover_context", description="Recover previous section set from conversation state."),
                    PlanStep(
                        action="call_tool",
                        toolName="socioeconomic_section_profile",
                        toolInput={"municipality": municipality, "sectionIds": section_ids},
                        description="Get demographic profile for previous section set.",
                    ),
                    PlanStep(action="calculate", description="Calculate average age for the selected sections."),
                    PlanStep(action="synthesize", description="Explain average age and compare with municipal average."),
                ],
            )

        if re.search(r"comp[aá]ralas|comparalas|conjunto de mijas|resto de mijas|media municipal", text):
            return ExecutionPlan(
                intent="compare_previous_sections_with_mijas",
                resolvedReferences=resolved_references,
                steps=[
                    PlanStep(action="recover_context", description="Recover previous section set from conversation state."),
                    PlanStep(
                        action="call_tool",
                        toolName="socioeconomic_section_profile",
                        toolInput={"municipality": municipality, "sectionIds": section_ids},
                        description="Get socioeconomic and demographic profile with municipal averages.",
                    ),
                    PlanStep(action="calculate", description="Compare selected sections with Mijas averages."),
                    PlanStep(action="synthesize", description="Explain differences with the municipal baseline."),
                ],
            )

        return None

    def _extract_year(self, question: str) -> int | None:
        match = re.search(r"\b(20\d{2})\b", question)
        return int(match.group(1)) if match else None

    def _extract_election_type(self, question: str) -> str | None:
        text = normalize(question)
        if "andaluz" in text:
            return "andaluzas"
        if "congreso" in text or "generales" in text:
            return "congreso"
        if "europe" in text:
            return "europeas"
        if "municip" in text:
            return "municipales"
        return None
