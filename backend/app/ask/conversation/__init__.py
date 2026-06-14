from app.ask.conversation.conversation_state import ConversationState
from app.ask.conversation.conversation_store import ConversationStore, conversation_store
from app.ask.conversation.schemas import ConversationMemoryContext, ConversationRecord, TurnRecord

__all__ = [
    "ConversationMemoryContext",
    "ConversationRecord",
    "ConversationState",
    "ConversationStore",
    "PersistentConversationStore",
    "TurnRecord",
    "conversation_memory_to_state",
    "conversation_store",
]


def __getattr__(name: str):
    if name in {"PersistentConversationStore", "conversation_memory_to_state"}:
        from app.ask.conversation.persistent_store import PersistentConversationStore, conversation_memory_to_state

        return {
            "PersistentConversationStore": PersistentConversationStore,
            "conversation_memory_to_state": conversation_memory_to_state,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
