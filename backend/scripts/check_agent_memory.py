from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.diagnostics import MEMORY_TABLES, check_memory_tables
from app.core.database import SessionLocal


def main() -> int:
    session = SessionLocal()
    try:
        results = check_memory_tables(session)
        for table in MEMORY_TABLES:
            print(f"{table} {'OK' if results.get(table) else 'MISSING'}")
        return 0 if all(results.values()) else 1
    finally:
        session.close()


if __name__ == "__main__":
    raise SystemExit(main())
