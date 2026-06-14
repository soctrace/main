from datetime import datetime, timezone
from typing import Any

from app.ask.conversation.conversation_state import (
    ActiveElection,
    AgeRange,
    AnalyticalContext,
    ConversationSection,
    ConversationState,
)


class ConversationStore:
    def __init__(self) -> None:
        self._states: dict[str, ConversationState] = {}

    def get(self, conversation_id: str | None) -> ConversationState | None:
        if not conversation_id:
            return None
        return self._states.get(conversation_id)

    def get_or_create(self, conversation_id: str, municipality: str | None = None) -> ConversationState:
        state = self._states.get(conversation_id)
        if state is None:
            state = ConversationState(conversationId=conversation_id, municipality=municipality)
            self._states[conversation_id] = state
        elif municipality:
            state.municipality = municipality
            state.touch()
        return state

    def clear(self) -> None:
        self._states.clear()

    def update_from_tool(
        self,
        conversation_id: str | None,
        tool_name: str,
        arguments: dict[str, Any],
        result: dict[str, Any],
    ) -> ConversationState | None:
        if not conversation_id or not result.get("ok"):
            return None

        output = result.get("result")
        state = self.get_or_create(conversation_id, arguments.get("municipality"))
        state.lastTool = tool_name
        state.lastResult = output

        if arguments.get("municipality"):
            state.municipality = str(arguments["municipality"])
        if arguments.get("year"):
            state.activeYear = int(arguments["year"])
        if arguments.get("party"):
            state.lastParty = str(arguments["party"]).upper()
        if arguments.get("electionType") or arguments.get("year"):
            election_type = arguments.get("electionType") or (state.activeElection.type if state.activeElection else "municipales")
            election_year = arguments.get("year") or (state.activeElection.year if state.activeElection else 2023)
            state.activeElection = ActiveElection(
                type=str(election_type),
                year=int(election_year),
            )
        if arguments.get("minAge") is not None:
            state.lastAgeRange = AgeRange(
                minAge=int(arguments["minAge"]),
                maxAge=int(arguments["maxAge"]) if arguments.get("maxAge") is not None else None,
            )

        rows = output.get("rows") if isinstance(output, dict) else None
        sections = output.get("sections") if isinstance(output, dict) else None
        top_sections = output.get("topSections") if isinstance(output, dict) else None
        section_rows = rows or sections or top_sections or []
        extracted_sections = self._extract_sections(section_rows)
        if extracted_sections:
            state.lastSections = extracted_sections

        state.analyticalContext = AnalyticalContext(
            resultType=tool_name,
            metrics=self._extract_metrics(output),
        )
        state.updatedAt = datetime.now(timezone.utc).isoformat()
        return state

    def _extract_sections(self, rows: Any) -> list[ConversationSection]:
        if not isinstance(rows, list):
            return []
        sections: list[ConversationSection] = []
        for row in rows:
            if not isinstance(row, dict):
                continue
            section_id = row.get("sectionId") or row.get("section_id")
            section_name = row.get("sectionName") or row.get("section_name") or row.get("section")
            if section_id and section_name:
                sections.append(ConversationSection(sectionId=str(section_id), sectionName=str(section_name)))
        return sections

    def _extract_metrics(self, output: Any) -> dict[str, Any]:
        if not isinstance(output, dict):
            return {}
        if isinstance(output.get("totals"), dict):
            return dict(output["totals"])
        return {}


conversation_store = ConversationStore()
