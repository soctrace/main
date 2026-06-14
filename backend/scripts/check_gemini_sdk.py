from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.ask.diagnostics import check_gemini_sdk


def main() -> int:
    ok, error = check_gemini_sdk()
    if ok:
        print("Gemini SDK OK")
        return 0
    print(error or "Gemini SDK missing.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
