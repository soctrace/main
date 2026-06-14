class LLMProviderError(Exception):
    """Base error for LLM provider layer failures."""


class ProviderNotConfiguredError(LLMProviderError):
    """Raised when a configured provider is unknown or incomplete."""


class ProviderNotImplementedError(LLMProviderError):
    """Raised for provider adapters reserved for a later phase."""


class LLMPlanningError(LLMProviderError):
    """Raised when a provider cannot produce a valid tool plan."""


class LLMSynthesisError(LLMProviderError):
    """Raised when a provider cannot synthesize a natural answer."""
