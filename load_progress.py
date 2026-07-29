"""Read/write load_to_db progress for terminal and web dashboards."""

from __future__ import annotations

import json
import re
import time
from datetime import UTC, datetime
from pathlib import Path

STATUS_PATH = Path("load_status.json")
DEFAULT_LOG_PATH = Path("load_to_db_ollama.log")


def _now_iso() -> str:
    return datetime.now(UTC).isoformat()


def write_status(
    *,
    phase: str,
    status: str = "running",
    provider: str = "",
    total_documents: int = 0,
    total_batches: int = 0,
    completed_batches: int = 0,
    batch_size: int = 0,
    started_at: str | None = None,
    last_error: str | None = None,
) -> None:
    documents_embedded = min(completed_batches * batch_size, total_documents)
    percent = (completed_batches / total_batches * 100) if total_batches else 0.0
    payload = {
        "phase": phase,
        "status": status,
        "provider": provider,
        "total_documents": total_documents,
        "total_batches": total_batches,
        "completed_batches": completed_batches,
        "batch_size": batch_size,
        "documents_embedded": documents_embedded,
        "percent": round(percent, 1),
        "started_at": started_at or _now_iso(),
        "updated_at": _now_iso(),
        "last_error": last_error,
    }
    if started_at:
        try:
            start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
            elapsed = (datetime.now(UTC) - start.astimezone(UTC)).total_seconds()
            payload["seconds_elapsed"] = int(elapsed)
            if completed_batches > 0:
                per_batch = elapsed / completed_batches
                remaining = total_batches - completed_batches
                payload["eta_seconds"] = int(per_batch * remaining)
        except ValueError:
            pass
    STATUS_PATH.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return payload


def read_status() -> dict | None:
    if not STATUS_PATH.exists():
        return None
    try:
        return json.loads(STATUS_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def parse_log_progress(log_path: Path = DEFAULT_LOG_PATH) -> dict | None:
    """Fallback for runs started before status JSON existed."""
    if not log_path.exists():
        return None
    text = log_path.read_text(encoding="utf-8", errors="replace")
    match = re.findall(
        r"Embedding batches:\s+(\d+)%\|.*?(\d+)/(\d+).*?\[.*?<([\d:]+),\s*([\d.]+)(s/it|it/s)\]",
        text,
    )
    if not match:
        return None
    pct, done, total, _elapsed, rate, rate_unit = match[-1]
    doc_match = re.search(r"Created (\d+) documents", text)
    provider_match = re.search(r"Embedding provider: (\w+)", text)
    return {
        "phase": "embedding",
        "status": "running",
        "provider": provider_match.group(1) if provider_match else "unknown",
        "total_documents": int(doc_match.group(1)) if doc_match else 0,
        "total_batches": int(total),
        "completed_batches": int(done),
        "percent": float(pct),
        "documents_embedded": int(done) * 100,
        "source": "log",
        "updated_at": _now_iso(),
        "rate": f"{rate}{rate_unit}",
    }


def get_progress() -> dict | None:
    status = read_status()
    if status and status.get("status") in {"running", "complete"}:
        age = time.time() - STATUS_PATH.stat().st_mtime
        if age < 120 or status.get("status") == "complete":
            return status
    return parse_log_progress() or status
