import json
import re
import hashlib
from pathlib import Path
from typing import Iterator, Dict, Any, Iterable, List

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"

for d in ["raw", "metadata", "processed", "qa", "splits", "reports", "review"]:
    (DATA / d).mkdir(parents=True, exist_ok=True)

IGNORE = {
    ".git", ".venv", "venv", "node_modules", "vendor",
    "dist", "build", "target", "out", "__pycache__"
}

EXT = {".py": "python", ".java": "java"}
MAX_BYTES = 1_000_000

SECRET = [
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*[^,\s]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b")
]


def sid(*x: Any) -> str:
    """Generate a deterministic 20-character hash ID."""
    return hashlib.sha256("::".join(map(str, x)).encode("utf-8")).hexdigest()[:20]


def stream_read(path: Path) -> Iterator[Dict[str, Any]]:
    """Stream read JSONL records one by one to avoid loading entire datasets into memory."""
    if not path.exists():
        return
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line_str = line.strip()
            if line_str:
                yield json.loads(line_str)


def stream_write(path: Path, rows: Iterable[Dict[str, Any]]) -> int:
    """Stream write JSONL records line by line. Returns count of written records."""
    path.parent.mkdir(parents=True, exist_ok=True)
    count = 0
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
            count += 1
    return count


def write(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    """Write rows to a JSONL file (backwards-compatible)."""
    stream_write(path, rows)


def read(path: Path) -> List[Dict[str, Any]]:
    """Read all rows from a JSONL file into a list (backwards-compatible)."""
    return list(stream_read(path))


def count_lines(path: Path) -> int:
    """Count non-empty lines in a file without parsing JSON."""
    if not path.exists():
        return 0
    count = 0
    with path.open("r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.strip():
                count += 1
    return count


def secret(s: str) -> bool:
    """Check if code text matches secret patterns."""
    return any(p.search(s) for p in SECRET)


def skip(p: Path) -> bool:
    """Determine whether to skip a file during processing."""
    if any(x.lower() in IGNORE for x in p.parts):
        return True

    if p.suffix.lower() not in EXT:
        return True

    try:
        if p.stat().st_size > MAX_BYTES:
            return True
    except OSError:
        return True

    return False
