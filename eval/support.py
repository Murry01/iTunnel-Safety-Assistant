"""Shared research artifact helpers. No API calls at import time."""
import hashlib
import json
import platform
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    temp.replace(path)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def environment():
    packages = {}
    for name in ("openai", "lancedb", "neo4j", "pandas", "ragas", "datasets",
                 "langchain-community", "instructor"):
        try:
            packages[name] = version(name)
        except PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "packages": packages}


def failure(exc):
    """Keep classification and Retry-After, without logging keys or account IDs."""
    status = getattr(exc, "status_code", None)
    code = getattr(exc, "code", None)
    name = type(exc).__name__
    retryable = (status in (408, 409, 429) or (status is not None and status >= 500)
                 or name in ("APIConnectionError", "APITimeoutError", "TimeoutError"))
    if code in ("insufficient_quota", "billing_hard_limit_reached"):
        retryable = False
    headers = getattr(getattr(exc, "response", None), "headers", {})
    delay = 0.0
    try:
        if headers.get("retry-after-ms"):
            delay = float(headers["retry-after-ms"]) / 1000
        elif headers.get("retry-after"):
            value = headers["retry-after"]
            try:
                delay = float(value)
            except ValueError:
                delay = (parsedate_to_datetime(value) - datetime.now(timezone.utc)).total_seconds()
    except (ValueError, TypeError, OverflowError):
        pass
    return {"type": name, "http_status": status, "code": code,
            "retryable": retryable, "retry_after_seconds": max(delay, 0.0)}


def completed(record):
    if "status" in record:
        return record["status"] == "completed"
    answer = record.get("answer", "")
    return bool(answer.strip()) and not answer.startswith("[AGENT ERROR]")


def load_records(path):
    path = Path(path)
    if path.suffix != ".jsonl":
        return read_json(path)
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def latest_records(records):
    latest = {}
    for record in records:
        latest[(record["id"], record["lang"])] = record
    return list(latest.values())
