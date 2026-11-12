import ast
import json
from pathlib import Path
from typing import Dict, Any, List, Set

from .common import DATA, EXT, skip, secret, sid, stream_read, stream_write


def py_chunks(text: str) -> List[tuple]:
    """Extract Python function and class chunks using AST."""
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return [
            ("fallback_block", f"lines_{i+1}", "\n".join(lines[i:i+80])[:12000], i+1, min(i+80, len(lines)), [], [], [], "line_fallback")
            for i in range(0, len(lines), 70) if "\n".join(lines[i:i+80]).strip()
        ]

    nodes = [n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))]
    nodes.sort(key=lambda n: n.lineno)
    out = []
    for n in nodes:
        start = n.lineno
        end = getattr(n, "end_lineno", n.lineno)
        code = "\n".join(lines[start-1:end])
        if len(code) > 12000:
            continue
        imports = sorted({a.name for x in ast.walk(n) if isinstance(x, ast.Import) for a in x.names} |
                         {x.module or "" for x in ast.walk(n) if isinstance(x, ast.ImportFrom)})
        used = sorted({x.id for x in ast.walk(n) if isinstance(x, ast.Name)})
        out.append((type(n).__name__, n.name, code, start, end, imports, [n.name], used, "python_ast"))

    if not out and text.strip():
        out = [("module", "module", text[:12000], 1, min(len(lines), 500), [], [], [], "python_ast_module")]
    return out


def java_chunks(text: str) -> List[tuple]:
    """Extract Java declarations using tree-sitter-java with regex/line fallback."""
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_java
        parser = Parser(Language(tree_sitter_java.language()))
        raw = text.encode("utf-8", errors="replace")
        root = parser.parse(raw).root_node
        wanted = {"class_declaration", "interface_declaration", "enum_declaration", "method_declaration", "constructor_declaration"}
        out = []
        stack = [root]
        while stack:
            n = stack.pop()
            if n.type in wanted:
                code = raw[n.start_byte:n.end_byte].decode("utf-8", errors="replace")
                if len(code) <= 12000:
                    name = next((raw[c.start_byte:c.end_byte].decode("utf-8", errors="replace") for c in n.children if c.type == "identifier"), "anonymous")
                    out.append((n.type, name, code, n.start_point.row + 1, n.end_point.row + 1, [], [name], [], "tree_sitter_java"))
            stack.extend(reversed(n.children))
        if out:
            return out
    except Exception:
        pass

    lines = text.splitlines()
    return [
        ("fallback_block", f"lines_{i+1}_{min(i+80, len(lines))}", "\n".join(lines[i:i+80])[:12000], i+1, min(i+80, len(lines)), [], [], [], "line_fallback")
        for i in range(0, len(lines), 70) if "\n".join(lines[i:i+80]).strip()
    ]


def main():
    chunks_path = DATA / "processed" / "code_chunks.jsonl"
    processed_repos: Set[str] = set()

    # Discover repositories already chunked to enable incremental updates
    if chunks_path.exists():
        print("Checking existing processed chunks...")
        for c in stream_read(chunks_path):
            processed_repos.add(c["repo_id"])
        print(f"Already processed repositories ({len(processed_repos)}): {processed_repos}")

    repos = list(stream_read(DATA / "metadata" / "repositories.jsonl"))
    new_chunks_count = 0

    # Append mode if file exists and has content, else write
    mode = "a" if chunks_path.exists() and chunks_path.stat().st_size > 0 else "w"

    with chunks_path.open(mode, encoding="utf-8") as out_f:
        for repo in repos:
            repo_id = repo["repo_id"]
            if repo_id in processed_repos:
                print(f"[SKIP EXISTING] {repo_id} already has extracted chunks.")
                continue

            base = DATA / "raw" / repo_id
            if not base.exists():
                print(f"[WARN] Repository directory not found: {base}")
                continue

            print(f"[PROCESSING] Extracting chunks from {repo_id}...")
            repo_chunk_count = 0

            for f in base.rglob("*"):
                if not f.is_file() or skip(f):
                    continue
                try:
                    text = f.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    continue

                if secret(text):
                    print(f"  [SKIP SECRET-LIKE FILE] {f.name}")
                    continue

                rel = f.relative_to(base).as_posix()
                lang = EXT.get(f.suffix.lower(), "unknown")

                try:
                    chunks = py_chunks(text) if lang == "python" else java_chunks(text)
                except Exception:
                    ls = text.splitlines()
                    chunks = [("fallback_block", f"lines_{i+1}", "\n".join(ls[i:i+80])[:12000], i+1, min(i+80, len(ls)), [], [], [], "line_fallback") for i in range(0, len(ls), 70)]

                for typ, name, code, start, end, imports, defined, used, status in chunks:
                    chunk_record = {
                        "schema_version": "1.0",
                        "repo_id": repo["repo_id"],
                        "repo_full_name": repo["full_name"],
                        "commit_sha": repo.get("commit_sha"),
                        "file_path": rel,
                        "language": lang,
                        "chunk_id": sid(repo["repo_id"], repo.get("commit_sha"), rel, start, end, name),
                        "chunk_type": typ,
                        "chunk_name": name,
                        "code_text": code,
                        "start_line": start,
                        "end_line": end,
                        "imports": imports,
                        "symbols_defined": defined,
                        "symbols_used": used,
                        "parser_status": status,
                        "license_spdx_id": repo.get("license_spdx_id"),
                        "licence_review_status": "needs_human_review",
                        "split": None
                    }
                    out_f.write(json.dumps(chunk_record, ensure_ascii=False) + "\n")
                    repo_chunk_count += 1
                    new_chunks_count += 1

            print(f"  -> Generated {repo_chunk_count} chunks for {repo_id}.")

    print(f"\nChunk extraction complete. Added {new_chunks_count} new chunks to {chunks_path}")


if __name__ == "__main__":
    main()
