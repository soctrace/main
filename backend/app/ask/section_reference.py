from dataclasses import dataclass
import re
import unicodedata


_SECTION_NUMBER = r"(?:3[0-7]|[12]\d|[1-9])"
_EXPLICIT_SECTION = re.compile(
    rf"\b(?:seccion|section|sec)\s*(?:n(?:[º°o]|umero)?\.?\s*)?0?({_SECTION_NUMBER})\b"
)
_COMPACT_SECTION = re.compile(rf"\bs\s*0?({_SECTION_NUMBER})\b")
_MULTIPLE_SECTIONS = re.compile(
    rf"\bsecciones\s+((?:0?{_SECTION_NUMBER})(?:\s*(?:,|y|e)\s*0?{_SECTION_NUMBER})+)"
)
_FULL_SECTION_ID = re.compile(r"\b29\d{8}\b")
_BARE_SECTION = re.compile(rf"^\s*0?({_SECTION_NUMBER})\s*$")


def _normalize(text: str) -> str:
    return "".join(
        character
        for character in unicodedata.normalize("NFD", text.lower())
        if unicodedata.category(character) != "Mn"
    )


@dataclass(frozen=True, slots=True)
class SectionReferenceDetection:
    section_ids: tuple[str, ...]
    selected_section_id: str | None
    confidence: float

    @property
    def entities(self) -> tuple[dict[str, str], ...]:
        return tuple({"type": "section", "id": section_id} for section_id in self.section_ids)


def detect_section_references(user_query: str | None) -> SectionReferenceDetection:
    """Extract explicit census-section references without interpreting the query."""
    text = _normalize(user_query or "")
    detected: list[str] = []

    def add(value: str) -> None:
        normalized = value if len(value) == 10 else str(int(value))
        if normalized not in detected:
            detected.append(normalized)

    for match in _FULL_SECTION_ID.finditer(text):
        add(match.group(0))

    multiple = _MULTIPLE_SECTIONS.search(text)
    if multiple:
        for value in re.findall(r"\d{1,2}", multiple.group(1)):
            number = int(value)
            if 1 <= number <= 37:
                add(value)
    else:
        for pattern in (_EXPLICIT_SECTION, _COMPACT_SECTION):
            for match in pattern.finditer(text):
                add(match.group(1))

    if not detected:
        bare = _BARE_SECTION.fullmatch(text)
        if bare:
            add(bare.group(1))

    selected = detected[0] if len(detected) == 1 else None
    return SectionReferenceDetection(
        section_ids=tuple(detected),
        selected_section_id=selected,
        confidence=1.0 if detected else 0.0,
    )
