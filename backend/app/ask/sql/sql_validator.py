import re
from dataclasses import dataclass


FORBIDDEN_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|create|truncate|grant|revoke|copy|call|do|merge|vacuum|analyze)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True, slots=True)
class ValidationResult:
    ok: bool
    error: str | None = None


class SqlValidator:
    def __init__(self, approved_relations: set[str]):
        self.approved_relations = {relation.lower() for relation in approved_relations}

    def validate(self, sql: str) -> ValidationResult:
        normalized = sql.strip()
        if not normalized:
            return ValidationResult(False, "SQL vacio.")
        if normalized.count(";") > 0:
            return ValidationResult(False, "No se permiten punto y coma ni multiples sentencias.")
        if not re.match(r"^(select|with)\b", normalized, re.IGNORECASE):
            return ValidationResult(False, "Solo se permiten consultas SELECT/WITH.")
        if FORBIDDEN_SQL.search(normalized):
            return ValidationResult(False, "La consulta contiene una operacion no permitida.")
        if re.search(r"--|/\*", normalized):
            return ValidationResult(False, "No se permiten comentarios SQL.")
        if re.search(r"\b(pg_catalog|information_schema)\b", normalized, re.IGNORECASE):
            return ValidationResult(False, "No se permite acceder a catalogos del sistema.")

        referenced = self._referenced_relations(normalized)
        disallowed = sorted(relation for relation in referenced if relation.lower() not in self.approved_relations)
        if disallowed:
            return ValidationResult(False, f"Relaciones no aprobadas: {', '.join(disallowed)}.")
        return ValidationResult(True)

    def _referenced_relations(self, sql: str) -> set[str]:
        matches = re.findall(r"\b(?:from|join)\s+([a-zA-Z_][\w]*\.[a-zA-Z_][\w]*)", sql, flags=re.IGNORECASE)
        return set(matches)
