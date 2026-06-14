from __future__ import annotations


class ToolLayerError(Exception):
    """Base error for controlled tool-layer failures."""


class UnknownToolError(ToolLayerError):
    pass


class PendingToolError(ToolLayerError):
    pass


class InvalidToolArgumentsError(ToolLayerError):
    pass


class ToolExecutionError(ToolLayerError):
    pass


class ToolUnsupportedError(ToolLayerError):
    pass


class ToolEmptyResult(ToolLayerError):
    pass


# Backward-compatible aliases for older imports/tests.
UnsupportedToolError = ToolUnsupportedError
ToolInputError = InvalidToolArgumentsError
