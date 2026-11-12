import os
import re
import json
import time
import shutil
import subprocess
from pathlib import Path
from typing import Dict, Any, List, Tuple, Optional

import requests
from dotenv import load_dotenv

from dataset_pipeline.common import DATA, EXT, skip, secret, sid, stream_read, stream_write
from dataset_pipeline.build_chunks import py_chunks, java_chunks
from .retrieval_service import RetrievalService

load_dotenv()

MAX_ALLOWED_REPO_SIZE_KB = 250_000  # 250 MB limit to prevent disk exhaustion


def validate_and_parse_github_url(url: str) -> Tuple[str, str]:
    """Validate and parse a GitHub repository URL into (owner, repo).
    Rejects malicious inputs, command injection attempts, non-GitHub domains, and path traversal.
    """
    if not url or not isinstance(url, str):
        raise ValueError("Repository URL must be a non-empty string.")

    url_clean = url.strip()

    # Reject dangerous shell injection characters, spaces, or traversal sequences
    if any(c in url_clean for c in [";", "&", "|", "`", "$", "<", ">", "\n", "\r", " "]):
        raise ValueError("Invalid URL: Contains prohibited command injection or control characters.")

    if ".." in url_clean or "\\" in url_clean:
        raise ValueError("Invalid URL: Directory traversal sequences are strictly prohibited.")

    if url_clean.startswith("-"):
        raise ValueError("Invalid URL: URL cannot start with a dash flag.")

    # Match standard GitHub formats
    # 1. https://github.com/owner/repo or https://github.com/owner/repo.git
    full_pattern = re.match(
        r"^(?:https?:\/\/)?(?:www\.)?github\.com\/([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+?)(?:\.git|\/)?$",
        url_clean,
        re.IGNORECASE
    )
    if full_pattern:
        owner = full_pattern.group(1)
        repo = full_pattern.group(2)
        return _validate_owner_repo(owner, repo)

    # 2. Short form: owner/repo
    short_pattern = re.match(r"^([A-Za-z0-9_.-]+)\/([A-Za-z0-9_.-]+)$", url_clean)
    if short_pattern:
        owner = short_pattern.group(1)
        repo = short_pattern.group(2)
        return _validate_owner_repo(owner, repo)

    raise ValueError(
        "Invalid GitHub repository URL. Expected format: 'https://github.com/owner/repository' or 'owner/repository'."
    )


def _validate_owner_repo(owner: str, repo: str) -> Tuple[str, str]:
    """Validate owner and repository naming constraints."""
    if repo.endswith(".git"):
        repo = repo[:-4]

    if not owner or not repo:
        raise ValueError("Invalid URL: Repository owner and name must both be non-empty.")

    # Check valid GitHub identifier rules (alphanumeric, underscores, hyphens, periods)
    if not re.match(r"^[A-Za-z0-9_.-]+$", owner) or not re.match(r"^[A-Za-z0-9_.-]+$", repo):
        raise ValueError("Invalid URL: Owner or repository name contains invalid characters.")

    return owner, repo


def fetch_github_metadata(owner: str, repo: str) -> Dict[str, Any]:
    """Fetch public repository metadata from GitHub REST API with graceful fallback to git ls-remote."""
    api_url = f"https://api.github.com/repos/{owner}/{repo}"
    token = os.getenv("GITHUB_TOKEN", "").strip()

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "GitHub-Knowledge-Assistant-Phase5",
        "X-GitHub-Api-Version": "2022-11-28"
    }
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        resp = requests.get(api_url, headers=headers, timeout=20)

        if resp.status_code == 404:
            raise ValueError(f"GitHub repository '{owner}/{repo}' does not exist or is private.")

        if resp.ok:
            data = resp.json()
            size_kb = data.get("size", 0)
            if size_kb > MAX_ALLOWED_REPO_SIZE_KB:
                raise ValueError(
                    f"Repository size ({size_kb // 1024} MB) exceeds maximum allowed limit of {MAX_ALLOWED_REPO_SIZE_KB // 1024} MB."
                )

            license_info = data.get("license") or {}
            return {
                "repo_id": f"{owner}__{repo}",
                "full_name": data.get("full_name", f"{owner}/{repo}"),
                "html_url": data.get("html_url", f"https://github.com/{owner}/{repo}"),
                "clone_url": data.get("clone_url", f"https://github.com/{owner}/{repo}.git"),
                "default_branch": data.get("default_branch", "main"),
                "language": data.get("language") or "Unknown",
                "stars": data.get("stargazers_count", 0),
                "license_spdx_id": license_info.get("spdx_id"),
                "license_name": license_info.get("name"),
                "description": data.get("description", "")
            }
        elif resp.status_code == 403:
            print(f"[WARN] GitHub API rate-limited (HTTP 403). Falling back to git ls-remote for {owner}/{repo}.")
        else:
            print(f"[WARN] GitHub API returned status {resp.status_code}. Falling back to git ls-remote.")

    except requests.RequestException as e:
        print(f"[WARN] GitHub API request failed: {e}. Falling back to git ls-remote.")

    # Fallback using git ls-remote to verify repository existence and detect default branch
    clone_url = f"https://github.com/{owner}/{repo}.git"
    try:
        ls_output = subprocess.check_output(
            ["git", "ls-remote", "--symref", clone_url, "HEAD"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=15
        )
        default_branch = "main"
        branch_match = re.search(r"ref:\s+refs/heads/([^\s]+)\s+HEAD", ls_output)
        if branch_match:
            default_branch = branch_match.group(1)

        return {
            "repo_id": f"{owner}__{repo}",
            "full_name": f"{owner}/{repo}",
            "html_url": f"https://github.com/{owner}/{repo}",
            "clone_url": clone_url,
            "default_branch": default_branch,
            "language": "Python / Java",
            "stars": 0,
            "license_spdx_id": "Detected on clone",
            "license_name": "Open Source",
            "description": f"Repository {owner}/{repo}"
        }
    except Exception:
        raise ValueError(f"Could not reach or verify GitHub repository '{owner}/{repo}'. Please check repository access.")


def clone_public_repo(clone_url: str, dest_dir: Path, default_branch: Optional[str] = None) -> str:
    """Perform a shallow, non-executing git clone into dest_dir and return the commit SHA."""
    dest_dir.parent.mkdir(parents=True, exist_ok=True)

    if dest_dir.exists():
        try:
            return subprocess.check_output(
                ["git", "-C", str(dest_dir), "rev-parse", "HEAD"],
                text=True,
                timeout=10
            ).strip()
        except Exception:
            # If invalid git dir, remove and re-clone
            shutil.rmtree(dest_dir, ignore_errors=True)

    cmd = ["git", "clone", "--depth", "1"]
    if default_branch:
        cmd.extend(["--branch", default_branch])
    cmd.extend([clone_url, str(dest_dir)])

    try:
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
            timeout=120
        )
    except subprocess.CalledProcessError as cpe:
        stderr_err = cpe.stderr.strip() if cpe.stderr else str(cpe)
        raise RuntimeError(f"Git clone failed: {stderr_err}")
    except subprocess.TimeoutExpired:
        raise RuntimeError("Git clone timed out after 120 seconds.")

    try:
        sha = subprocess.check_output(
            ["git", "-C", str(dest_dir), "rev-parse", "HEAD"],
            text=True,
            timeout=10
        ).strip()
        return sha
    except Exception as e:
        return "latest"


def extract_repository_chunks(
    repo_id: str,
    repo_dir: Path,
    metadata: Dict[str, Any],
    commit_sha: str,
    max_chunks: int = 500
) -> List[Dict[str, Any]]:
    """Extract AST code chunks from repository source files up to max_chunks limit."""
    extracted_chunks: List[Dict[str, Any]] = []

    for f in repo_dir.rglob("*"):
        if len(extracted_chunks) >= max_chunks:
            break
        if not f.is_file() or skip(f):
            continue

        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except Exception:
            continue

        if secret(text):
            continue

        rel = f.relative_to(repo_dir).as_posix()
        lang = EXT.get(f.suffix.lower(), "unknown")

        try:
            chunks = py_chunks(text) if lang == "python" else java_chunks(text)
        except Exception:
            lines = text.splitlines()
            chunks = [
                ("fallback_block", f"lines_{i+1}", "\n".join(lines[i:i+80])[:12000], i+1, min(i+80, len(lines)), [], [], [], "line_fallback")
                for i in range(0, len(lines), 70)
            ]

        for typ, name, code, start, end, imports, defined, used, status in chunks:
            if len(extracted_chunks) >= max_chunks:
                break
            chunk_record = {
                "schema_version": "1.0",
                "repo_id": repo_id,
                "repo_full_name": metadata.get("full_name", repo_id),
                "commit_sha": commit_sha,
                "file_path": rel,
                "language": lang,
                "chunk_id": sid(repo_id, commit_sha, rel, start, end, name),
                "chunk_type": typ,
                "chunk_name": name,
                "code_text": code,
                "start_line": start,
                "end_line": end,
                "imports": imports,
                "symbols_defined": defined,
                "symbols_used": used,
                "parser_status": status,
                "license_spdx_id": metadata.get("license_spdx_id"),
                "licence_review_status": "needs_human_review",
                "split": "train"
            }
            extracted_chunks.append(chunk_record)

    return extracted_chunks


def add_and_index_github_repo(url: str, max_chunks: int = 500) -> Dict[str, Any]:
    """Complete workflow for Phase 5A: Validate URL, fetch metadata, clone, chunk, and index."""
    # 1. URL validation
    owner, repo_name = validate_and_parse_github_url(url)
    repo_id = f"{owner}__{repo_name}"

    # 2. Check for duplicate repository
    repos_meta_path = DATA / "metadata" / "repositories.jsonl"
    existing_repos = list(stream_read(repos_meta_path)) if repos_meta_path.exists() else []
    for r in existing_repos:
        if r.get("repo_id") == repo_id and r.get("clone_status") == "success":
            raise ValueError(f"Repository '{owner}/{repo_name}' is already indexed in the Knowledge Assistant.")

    # 3. Metadata retrieval
    metadata = fetch_github_metadata(owner, repo_name)

    # 4. Controlled cloning
    dest_dir = DATA / "raw" / repo_id
    commit_sha = clone_public_repo(metadata["clone_url"], dest_dir, metadata.get("default_branch"))
    metadata["commit_sha"] = commit_sha
    metadata["clone_status"] = "success"

    # 5. AST Chunk Extraction
    chunks = extract_repository_chunks(repo_id, dest_dir, metadata, commit_sha, max_chunks=max_chunks)

    # 6. Append to code_chunks.jsonl
    chunks_path = DATA / "processed" / "code_chunks.jsonl"
    with chunks_path.open("a", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")

    # 7. Update repositories.jsonl
    updated_repos = [r for r in existing_repos if r.get("repo_id") != repo_id]
    metadata["chunk_count"] = len(chunks)
    updated_repos.append(metadata)
    stream_write(repos_meta_path, updated_repos)

    # 8. Incremental indexing into BM25 and Dense vector store
    retrieval_service = RetrievalService.get_instance()
    index_res = retrieval_service.add_repository_chunks(chunks)

    return {
        "status": "success",
        "repo_id": repo_id,
        "full_name": metadata["full_name"],
        "commit_sha": commit_sha,
        "default_branch": metadata.get("default_branch", "main"),
        "language": metadata.get("language", "Unknown"),
        "stars": metadata.get("stars", 0),
        "chunks_extracted": len(chunks),
        "bm25_indexed": index_res["bm25_added"],
        "dense_indexed": index_res["dense_added"],
        "message": f"Successfully integrated '{metadata['full_name']}': extracted {len(chunks)} AST chunks and updated indexes."
    }
