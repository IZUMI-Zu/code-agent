"""
═══════════════════════════════════════════════════════════════
Tool Event Bus
═══════════════════════════════════════════════════════════════
Provides a lightweight pub/sub style interface so different
components (agent runtime, TUI, future web clients) can share
structured tool execution events in real time.
"""

from __future__ import annotations

import json
import threading
import time
import uuid
from pathlib import Path
from queue import Empty, Queue
from typing import Dict, List, Optional

# Internal thread-safe queue shared by publishers/subscribers
_EVENT_QUEUE: Queue = Queue()
# Lock to guard file writes so parallel tool calls do not interleave
_LOG_WRITE_LOCK = threading.Lock()


def _event_log_path() -> Path:
    """Return the JSONL log file path for the current day."""
    log_dir = Path("logs") / "events"
    log_dir.mkdir(parents=True, exist_ok=True)
    timestamp = time.strftime("%Y-%m-%d")
    return log_dir / f"tool_events_{timestamp}.jsonl"


def _safe_json_dumps(payload: Dict) -> str:
    """Serialize to JSON while keeping output ASCII-only by default."""
    try:
        return json.dumps(payload, ensure_ascii=True)
    except Exception:
        fallback = {
            "event_type": payload.get("event_type", "unknown"),
            "error": "Failed to serialize event payload",
        }
        return json.dumps(fallback, ensure_ascii=True)


def publish_tool_event(event: Dict) -> None:
    """Publish a structured tool event to in-memory queue and log file."""
    event.setdefault("event_id", str(uuid.uuid4()))
    event.setdefault("timestamp", time.time())

    # Queue for in-process subscribers (e.g., TUI renderer)
    _EVENT_QUEUE.put(event)

    # Append to JSONL log for persistence / replay
    try:
        log_path = _event_log_path()
        serialized = _safe_json_dumps(event)
        with _LOG_WRITE_LOCK:
            with log_path.open("a", encoding="utf-8") as fh:
                fh.write(serialized + "\n")
    except Exception:
        # Swallow logging errors; runtime visibility should not crash
        pass


def drain_tool_events(max_items: Optional[int] = None) -> List[Dict]:
    """Return all queued tool events (up to max_items) without blocking."""
    events: List[Dict] = []
    fetched = 0
    while True:
        if max_items is not None and fetched >= max_items:
            break
        try:
            events.append(_EVENT_QUEUE.get_nowait())
            fetched += 1
        except Empty:
            break
    return events


__all__ = ["publish_tool_event", "drain_tool_events"]
