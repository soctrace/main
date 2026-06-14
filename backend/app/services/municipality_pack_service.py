import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class MunicipalityPack:
    metadata: dict
    documents: dict[str, str]


class MunicipalityPackService:
    def __init__(self, packs_root: Path | None = None):
        self.packs_root = packs_root or Path(__file__).resolve().parents[3] / "municipality_packs"

    def load_municipality_context(self, slug: str) -> MunicipalityPack:
        pack_path = self.packs_root / slug
        metadata = json.loads((pack_path / "municipality_metadata.json").read_text(encoding="utf-8"))
        documents = {
            document: (pack_path / document).read_text(encoding="utf-8")
            for document in metadata["documents"]
        }
        return MunicipalityPack(metadata=metadata, documents=documents)
