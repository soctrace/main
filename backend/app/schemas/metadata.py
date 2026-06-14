from pydantic import BaseModel


class VariableMetadata(BaseModel):
    key: str
    label: str
    type: str
    available: bool
    description: str
    supported_in_map: bool = True


class VariablesMetadataResponse(BaseModel):
    items: list[VariableMetadata]

