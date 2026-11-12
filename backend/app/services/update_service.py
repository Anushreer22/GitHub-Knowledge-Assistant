import os
import re
import json
import time
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Set, Tuple, Optional

from dataset_pipeline.common import (
    DATA,
    EXT,
    skip,
    secret,
    sid,
    stream_read,
    stream_write
)
from dataset_pipeline.build_chunks import py_chunks, java_chunks
from .retrieval_service import RetrievalService


HISTORY_PATH = DATA / "metadata" / "indexing_history.jsonl"


def get_indexing_history(repo_id: Optional[str] = None) -> List[Dict[str, Any]]:
    """Retrieve indexing history records, newest first, optionally filtered by repo_id."""
    if not HISTORY_PATH.exists():
        return []

    records = list(stream_read(HISTORY_PATH))
    if repo_id:
        records = [r for r in records if r.get("repo_id") == repo_id]

    records.reverse()
    return records


def record_history_entry(entry: Dict[str, Any]) -> None:
    """Append a structured indexing history record to persistent JSONL store."""
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def sync_repository(repo_id: str, max_chunks_per_file: int = 50) -> Dict[str, Any]:
    """Perform incremental repository update detection, selective AST chunk generation,
    outdated chunk pruning, and incremental index synchronization.
    """
    start_time = time.time()
    repos_meta_path = DATA / "metadata" / "repositories.jsonl"
    existing_repos = list(stream_read(repos_meta_path)) if repos_meta_path.exists() else []

    target_repo = next((r for r in existing_repos if r.get("repo_id") == repo_id), None)
    if not target_repo:
        raise ValueError(f"Repository '{repo_id}' is not indexed.")

    repo_dir = DATA / "raw" / repo_id
    if not repo_dir.exists():
        raise ValueError(f"Cloned repository directory for '{repo_id}' does not exist on disk.")

    prev_commit = target_repo.get("commit_sha", "unknown")
    default_branch = target_repo.get("default_branch", "main")

    # 1. Fetch latest remote state safely
    try:
        subprocess.run(
            ["git", "-C", str(repo_dir), "fetch", "--depth", "1", "origin", default_branch],
            check=True,
            capture_output=True,
            text=True,
            timeout=60
        )
        current_commit = subprocess.check_output(
            ["git", "-C", str(repo_dir), "rev-parse", "FETCH_HEAD"],
            text=True,
            timeout=10
        ).strip()
    except Exception as e:
        # If fetch fails (e.g. offline or no remote), check local HEAD
        try:
            current_commit = subprocess.check_output(
                ["git", "-C", str(repo_dir), "rev-parse", "HEAD"],
                text=True,
                timeout=10
            ).strip()
        except Exception:
            current_commit = prev_commit

    duration = round(time.time() - start_time, 2)

    # 2. Check if repository is already at latest commit
    if prev_commit != "unknown" and prev_commit == current_commit:
        entry = {
            "history_id": sid(repo_id, prev_commit, current_commit, time.time()),
            "repo_id": repo_id,
            "previous_commit": prev_commit,
            "current_commit": current_commit,
            "files_added": [],
            "files_modified": [],
            "files_deleted": [],
            "chunks_added": 0,
            "chunks_removed": 0,
            "duration_seconds": duration,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "up_to_date"
        }
        record_history_entry(entry)
        return {
            "status": "up_to_date",
            "repo_id": repo_id,
            "previous_commit": prev_commit,
            "current_commit": current_commit,
            "files_added": [],
            "files_modified": [],
            "files_deleted": [],
            "chunks_added": 0,
            "chunks_removed": 0,
            "duration_seconds": duration,
            "message": f"Repository '{repo_id}' is already up to date at commit {current_commit[:8]}."
        }

    # 3. Detect changed, added, and deleted files using git diff
    files_added: List[str] = []
    files_modified: List[str] = []
    files_deleted: List[str] = []

    try:
        diff_output = subprocess.check_output(
            ["git", "-C", str(repo_dir), "diff", "--name-status", prev_commit, current_commit],
            text=True,
            timeout=15
        )
        for line in diff_output.splitlines():
            parts = line.strip().split(maxsplit=1)
            if len(parts) == 2:
                status_char, fpath = parts[0][0], parts[1].replace("\\", "/")
                if status_char == "A":
                    files_added.append(fpath)
                elif status_char == "M":
                    files_modified.append(fpath)
                elif status_char == "D":
                    files_deleted.append(fpath)
    except Exception:
        # Fallback if diff against prev_commit is unavailable: treat as modified
        files_modified = [f.relative_to(repo_dir).as_posix() for f in repo_dir.rglob("*") if f.is_file() and not skip(f)]

    affected_files = set(files_added + files_modified + files_deleted)

    # 4. Advance working tree to current_commit
    try:
        subprocess.run(
            ["git", "-C", str(repo_dir), "checkout", "--detach", current_commit],
            check=True,
            capture_output=True,
            timeout=30
        )
    except Exception:
        pass

    # 5. Identify outdated chunks for affected files
    chunks_path = DATA / "processed" / "code_chunks.jsonl"
    existing_chunks = list(stream_read(chunks_path)) if chunks_path.exists() else []

    kept_chunks: List[Dict[str, Any]] = []
    outdated_chunk_ids: Set[str] = set()

    for c in existing_chunks:
        if c.get("repo_id") == repo_id and c.get("file_path") in affected_files:
            outdated_chunk_ids.add(c["chunk_id"])
        else:
            kept_chunks.append(c)

    # 6. Extract new AST chunks only for added and modified files
    new_chunks: List[Dict[str, Any]] = []
    for fpath in (files_added + files_modified):
        f = repo_dir / fpath
        if not f.exists() or not f.is_file() or skip(f):
            continue

        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if secret(text):
            continue

        lang = EXT.get(f.suffix.lower(), "unknown")
        try:
            chunks = py_chunks(text) if lang == "python" else java_chunks(text)
        except Exception:
            lines = text.splitlines()
            chunks = [
                ("fallback_block", f"lines_{i+1}", "\n".join(lines[i:i+80])[:12000], i+1, min(i+80, len(lines)), [], [], [], "line_fallback")
                for i in range(0, len(lines), 70)
            ]

        for typ, name, code, start, end, imports, defined, used, parser_status in chunks[:max_chunks_per_file]:
            chunk_record = {
                "schema_version": "1.0",
                "repo_id": repo_id,
                "repo_full_name": target_repo.get("full_name", repo_id),
                "commit_sha": current_commit,
                "file_path": fpath,
                "language": lang,
                "chunk_id": sid(repo_id, current_commit, fpath, start, end, name),
                "chunk_type": typ,
                "chunk_name": name,
                "code_text": code,
                "start_line": start,
                "end_line": end,
                "imports": imports,
                "symbols_defined": defined,
                "symbols_used": used,
                "parser_status": parser_status,
                "license_spdx_id": target_repo.get("license_spdx_id"),
                "licence_review_status": "needs_human_review",
                "split": "train"
            }
            new_chunks.append(chunk_record)

    # 7. Atomic dataset write for safe crash recovery
    tmp_chunks_path = chunks_path.with_suffix(".tmp")
    with tmp_chunks_path.open("w", encoding="utf-8") as out_f:
        for c in kept_chunks:
            out_f.write(json.dumps(c, ensure_ascii=False) + "\n")
        for c in new_chunks:
            out_f.write(json.dumps(c, ensure_ascii=False) + "\n")

    os.replace(tmp_chunks_path, chunks_path)

    # 8. Incrementally update BM25 index and Dense store
    retrieval_service = RetrievalService.get_instance()
    retrieval_service.remove_and_update_repository_chunks(outdated_chunk_ids, new_chunks)

    # 9. Update repositories.jsonl with new commit SHA
    target_repo["commit_sha"] = current_commit
    target_repo["last_synced"] = datetime.now(timezone.utc).isoformat()
    stream_write(repos_meta_path, existing_repos)

    duration = round(time.time() - start_time, 2)

    # 10. Record indexing history
    history_entry = {
        "history_id": sid(repo_id, prev_commit, current_commit, time.time()),
        "repo_id": repo_id,
        "previous_commit": prev_commit,
        "current_commit": current_commit,
        "files_added": files_added,
        "files_modified": files_modified,
        "files_deleted": files_deleted,
        "chunks_added": len(new_chunks),
        "chunks_removed": len(outdated_chunk_ids),
        "duration_seconds": duration,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": "success"
    }
    record_history_entry(history_entry)

    return {
        "status": "success",
        "repo_id": repo_id,
        "previous_commit": prev_commit,
        "current_commit": current_commit,
        "files_added": files_added,
        "files_modified": files_modified,
        "files_deleted": files_deleted,
        "chunks_added": len(new_chunks),
        "chunks_removed": len(outdated_chunk_ids),
        "duration_seconds": duration,
        "message": (
            f"Incrementally updated '{repo_id}' from {prev_commit[:8]} to {current_commit[:8]}: "
            f"+{len(files_added)} added, ~{len(files_modified)} modified, -{len(files_deleted)} deleted. "
            f"Added {len(new_chunks)} chunks, pruned {len(outdated_chunk_ids)} outdated chunks ({duration}s)."
        )
    }
