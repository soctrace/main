from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterator


logger = logging.getLogger(__name__)


@contextmanager
def telemetry_span(event: str, **fields: object) -> Iterator[dict[str, object]]:
    started = time.monotonic()
    payload: dict[str, object] = dict(fields)
    try:
        yield payload
    finally:
        payload["latency_ms"] = round((time.monotonic() - started) * 1000)
        logger.info(event, extra=payload)
