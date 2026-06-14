import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator


Sector = Literal[
    "Investigación",
    "Educación",
    "Administración Pública",
    "Partido Político",
    "Empresa privada",
    "Otros",
]


class DemoRequest(BaseModel):
    organization: str = Field(min_length=2, max_length=160)
    firstName: str = Field(min_length=2, max_length=100)
    lastName: str = Field(min_length=2, max_length=140)
    email: str = Field(min_length=5, max_length=254)
    phone: str | None = Field(default=None, max_length=40)
    sector: Sector
    reasons: str = Field(min_length=10, max_length=2400)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        cleaned = value.strip()
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", cleaned):
            raise ValueError("Email inválido.")
        return cleaned

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, value: str | None) -> str | None:
        if value is None or not value.strip():
            return None
        cleaned = value.strip()
        if not re.match(r"^[0-9+()\s.-]{7,40}$", cleaned):
            raise ValueError("Teléfono inválido.")
        return cleaned

    @field_validator("reasons")
    @classmethod
    def validate_reasons_word_count(cls, value: str) -> str:
        cleaned = value.strip()
        if len(re.findall(r"\S+", cleaned)) > 200:
            raise ValueError("Los motivos no deben superar aproximadamente 200 palabras.")
        return cleaned


class DemoRequestResponse(BaseModel):
    ok: bool
    message: str
