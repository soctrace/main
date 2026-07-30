from dataclasses import dataclass, field


@dataclass(slots=True)
class AnalystConversationMemory:
    conversation_id: str | None = None
    recent_messages: list[dict] = field(default_factory=list)

    def context(self) -> dict:
        return {
            "conversation_id": self.conversation_id,
            "recent_messages": self.recent_messages[-6:],
            "memory_status": "phase_3_placeholder",
        }
