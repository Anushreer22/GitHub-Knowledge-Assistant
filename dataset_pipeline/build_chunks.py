import ast
import json
from pathlib import Path
from typing import Dict, Any, List, Set, Optional

from .common import DATA, EXT, skip, secret, sid, stream_read, stream_write


def py_chunks(text: str) -> List[tuple]:
    """Extract Python function, method, and class chunks with scope hierarchy and exact lines using AST."""
    lines = text.splitlines()
    try:
        tree = ast.parse(text)
    except Exception:
        return [
            ("fallback_block", f"lines_{i+1}", "\n".join(lines[i:i+80])[:12000], i+1, min(i+80, len(lines)), [], [], [], "line_fallback")
            for i in range(0, len(lines), 70) if "\n".join(lines[i:i+80]).strip()
        ]

    file_imports = set()
    for n in tree.body:
        if isinstance(n, ast.Import):
            for a in n.names:
                file_imports.add(a.name)
        elif isinstance(n, ast.ImportFrom):
            mod = n.module or ""
            for a in n.names:
                file_imports.add(f"{mod}.{a.name}" if mod else a.name)

    out = []

    def visit(nodes, scope_stack: List[str], parent_class: Optional[str] = None):
        for n in nodes:
            if isinstance(n, ast.ClassDef):
                start = min([d.lineno for d in n.decorator_list] + [n.lineno])
                end = getattr(n, "end_lineno", n.lineno)
                scope = ".".join(scope_stack + [n.name])
                code = "\n".join(lines[start - 1 : end])
                if len(code) <= 12000:
                    imps = sorted(file_imports | {a.name for x in ast.walk(n) if isinstance(x, ast.Import) for a in x.names})
                    defined = [n.name] + [b.id for b in n.bases if isinstance(b, ast.Name)]
                    used = sorted({x.id for x in ast.walk(n) if isinstance(x, ast.Name) and x.id != n.name})
                    out.append(("class_definition", scope, code, start, end, imps, defined, used, "python_ast"))
                visit(n.body, scope_stack + [n.name], parent_class=scope)
            elif isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                start = min([d.lineno for d in n.decorator_list] + [n.lineno])
                end = getattr(n, "end_lineno", n.lineno)
                scope = ".".join(scope_stack + [n.name])
                typ = "async_method_definition" if isinstance(n, ast.AsyncFunctionDef) and parent_class else (
                    "async_function_definition" if isinstance(n, ast.AsyncFunctionDef) else (
                        "method_definition" if parent_class else "function_definition"
                    )
                )
                code = "\n".join(lines[start - 1 : end])
                if len(code) <= 12000:
                    imps = sorted(file_imports | {a.name for x in ast.walk(n) if isinstance(x, ast.Import) for a in x.names})
                    params = [a.arg for a in n.args.args]
                    defined = [n.name] + params
                    used = sorted({x.id for x in ast.walk(n) if isinstance(x, ast.Name) and x.id not in defined})
                    out.append((typ, scope, code, start, end, imps, defined, used, "python_ast"))
                visit(n.body, scope_stack + [n.name], parent_class=parent_class)

    visit(tree.body, [])
    out.sort(key=lambda x: x[3])

    if not out and text.strip():
        out = [("module", "module", text[:12000], 1, min(len(lines), 500), sorted(file_imports), [], [], "python_ast_module")]
    return out


def java_chunks(text: str) -> List[tuple]:
    """Extract Java class, method, constructor, and interface declarations using tree-sitter-java."""
    lines = text.splitlines()
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_java

        parser = Parser(Language(tree_sitter_java.language()))
        raw = text.encode("utf-8", errors="replace")
        tree = parser.parse(raw)
        root = tree.root_node

        file_imports = []
        for child in root.children:
            if child.type == "import_declaration":
                for c in child.children:
                    if c.type in ("scoped_identifier", "identifier"):
                        file_imports.append(c.text.decode("utf-8"))

        out = []

        def visit(node, scope_stack: List[str]):
            ntype = node.type
            if ntype in ("class_declaration", "interface_declaration", "enum_declaration", "record_declaration"):
                ident = next((c.text.decode("utf-8") for c in node.children if c.type == "identifier"), "Anonymous")
                scope = ".".join(scope_stack + [ident])
                start = node.start_point.row + 1
                end = node.end_point.row + 1
                code = raw[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                if len(code) <= 12000:
                    out.append((ntype, scope, code, start, end, file_imports, [ident], [], "tree_sitter_java"))
                body = next((c for c in node.children if c.type in ("class_body", "interface_body", "enum_body_declarations")), None)
                if body:
                    for ch in body.children:
                        visit(ch, scope_stack + [ident])
            elif ntype in ("method_declaration", "constructor_declaration"):
                ident = next((c.text.decode("utf-8") for c in node.children if c.type == "identifier"), "")
                params_node = next((c for c in node.children if c.type == "formal_parameters"), None)
                param_types = []
                if params_node:
                    for p in params_node.children:
                        if p.type == "formal_parameter":
                            t_node = next((ch for ch in p.children if ch.type in ("type_identifier", "generic_type", "scoped_type_identifier", "integral_type", "floating_point_type", "boolean_type", "void_type") or ch.type.endswith("_type")), None)
                            if t_node:
                                param_types.append(t_node.text.decode("utf-8"))
                sig = f"({', '.join(param_types)})"
                scope = ".".join(scope_stack)
                name = f"{scope}.{ident}{sig}" if scope else f"{ident}{sig}"
                start = node.start_point.row + 1
                end = node.end_point.row + 1
                code = raw[node.start_byte:node.end_byte].decode("utf-8", errors="replace")
                if len(code) <= 12000:
                    out.append((ntype, name, code, start, end, file_imports, [ident] + param_types, [], "tree_sitter_java"))
            else:
                for ch in node.children:
                    visit(ch, scope_stack)

        visit(root, [])
        if out:
            out.sort(key=lambda x: x[3])
            return out
    except Exception:
        pass

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
