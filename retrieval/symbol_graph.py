import re
from pathlib import Path
from typing import Dict, Any, List, Set, Optional, Tuple
from collections import defaultdict

from dataset_pipeline.common import DATA, stream_read


class RelationshipType:
    DIRECTLY_VERIFIED = "directly_verified"        # Explicit AST definition/call in same repo
    STATICALLY_INFERRED = "statically_inferred"    # Resolved through static name usage
    UNVERIFIED_ASSUMPTION = "unverified_assumption"# External library or dynamic reference


class SymbolGraphIndex:
    """Lightweight static symbol relationship graph indexing call relationships,
    class inheritance, imported modules, and related test functions without executing code.
    """

    def __init__(self, chunks: Optional[List[Dict[str, Any]]] = None):
        # symbol_name -> list of chunk records defining it
        self.definitions: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # chunk_id -> chunk record
        self.chunk_by_id: Dict[str, Dict[str, Any]] = {}
        # symbol_name -> list of chunk records that call or reference it
        self.callers: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # class_name -> list of base class names
        self.inheritance: Dict[str, List[str]] = defaultdict(list)
        # base_class_name -> list of subclass names
        self.subclasses: Dict[str, List[str]] = defaultdict(list)
        # symbol_name -> list of test chunk records
        self.related_tests: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        # file_path -> set of imported modules
        self.file_imports: Dict[str, Set[str]] = defaultdict(set)

        if chunks:
            self.build_graph(chunks)

    def build_graph(self, chunks: List[Dict[str, Any]]) -> None:
        """Construct symbol graph from AST chunk records."""
        for c in chunks:
            cid = c.get("chunk_id", "")
            cname = c.get("chunk_name", "")
            ctype = c.get("chunk_type", "")
            fpath = c.get("file_path", "")
            repo = c.get("repo_id", "")
            defs = c.get("symbols_defined", [])
            uses = c.get("symbols_used", [])
            imports = c.get("imports", [])
            code = c.get("code_text", "")

            self.chunk_by_id[cid] = c

            # Track imports per file
            for imp in imports:
                self.file_imports[fpath].add(imp)

            # 1. Definitions index
            for sym in defs:
                if sym:
                    self.definitions[sym].append(c)

            if cname and cname not in defs:
                self.definitions[cname].append(c)

            # 2. Callers / Usages index
            for sym in uses:
                if sym and sym != cname:
                    self.callers[sym].append(c)

            # 3. Inheritance detection via static parsing
            if "class" in ctype.lower():
                bases = self._extract_bases(code, cname)
                for b in bases:
                    self.inheritance[cname].append(b)
                    self.subclasses[b].append(cname)

            # 4. Related Tests detection
            is_test_file = "test" in fpath.lower()
            is_test_chunk = cname.lower().startswith("test") or is_test_file

            if is_test_chunk:
                for target_sym in uses:
                    if target_sym != cname and len(target_sym) > 2:
                        self.related_tests[target_sym].append(c)

    def remove_chunks(self, chunk_ids: Set[str]) -> None:
        """Prune removed chunks from the symbol graph."""
        if not chunk_ids:
            return

        for cid in chunk_ids:
            self.chunk_by_id.pop(cid, None)

        for sym, clist in list(self.definitions.items()):
            self.definitions[sym] = [c for c in clist if c.get("chunk_id") not in chunk_ids]
            if not self.definitions[sym]:
                del self.definitions[sym]

        for sym, clist in list(self.callers.items()):
            self.callers[sym] = [c for c in clist if c.get("chunk_id") not in chunk_ids]
            if not self.callers[sym]:
                del self.callers[sym]

        for sym, clist in list(self.related_tests.items()):
            self.related_tests[sym] = [c for c in clist if c.get("chunk_id") not in chunk_ids]
            if not self.related_tests[sym]:
                del self.related_tests[sym]

    def _extract_bases(self, code_text: str, class_name: str) -> List[str]:
        """Extract base classes or implemented interfaces from class definition header."""
        bases = []
        # Python: class MyClass(Base1, Base2):
        py_match = re.search(r"class\s+" + re.escape(class_name) + r"\s*\(([^)]+)\)", code_text)
        if py_match:
            raw_bases = py_match.group(1).split(",")
            for b in raw_bases:
                clean_b = b.strip().split(".")[-1]
                if clean_b and clean_b not in ["object", "type"]:
                    bases.append(clean_b)

        # Java: class MyClass extends Base implements Interface1, Interface2
        java_match = re.search(
            r"(?:class|interface)\s+" + re.escape(class_name) + r"(?:\s+extends\s+([A-Za-z0-9_]+))?(?:\s+implements\s+([^{]+))?",
            code_text
        )
        if java_match:
            ext = java_match.group(1)
            if ext:
                bases.append(ext.strip())
            impl = java_match.group(2)
            if impl:
                for iface in impl.split(","):
                    clean_iface = iface.strip()
                    if clean_iface:
                        bases.append(clean_iface)

        return bases

    def get_symbol_relationships(self, symbol_name: str, repo_id: Optional[str] = None) -> Dict[str, Any]:
        """Query complete static relationships for a symbol."""
        clean_sym = symbol_name.strip()

        # Definitions
        def_chunks = self.definitions.get(clean_sym, [])
        if repo_id:
            def_chunks = [c for c in def_chunks if c.get("repo_id") == repo_id]

        # Callers / Usages
        caller_chunks = self.callers.get(clean_sym, [])
        if repo_id:
            caller_chunks = [c for c in caller_chunks if c.get("repo_id") == repo_id]

        # Deduplicate callers
        seen_caller_ids = set()
        unique_callers = []
        for c in caller_chunks:
            if c["chunk_id"] not in seen_caller_ids:
                seen_caller_ids.add(c["chunk_id"])
                unique_callers.append({
                    "chunk_id": c["chunk_id"],
                    "caller_name": c.get("chunk_name", ""),
                    "caller_type": c.get("chunk_type", ""),
                    "file_path": c.get("file_path", ""),
                    "lines": f"L{c.get('start_line', 1)}-L{c.get('end_line', 1)}",
                    "verification": (
                        RelationshipType.DIRECTLY_VERIFIED
                        if c.get("repo_id") == (def_chunks[0].get("repo_id") if def_chunks else "")
                        else RelationshipType.STATICALLY_INFERRED
                    )
                })

        # Callees (symbols called by this symbol's definition)
        callees = []
        if def_chunks:
            primary_def = def_chunks[0]
            for called_sym in primary_def.get("symbols_used", []):
                if called_sym != clean_sym:
                    has_local_def = called_sym in self.definitions
                    callees.append({
                        "symbol_name": called_sym,
                        "verification": (
                            RelationshipType.DIRECTLY_VERIFIED if has_local_def
                            else RelationshipType.UNVERIFIED_ASSUMPTION
                        )
                    })

        # Related Tests
        test_chunks = self.related_tests.get(clean_sym, [])
        if repo_id:
            test_chunks = [c for c in test_chunks if c.get("repo_id") == repo_id]

        formatted_tests = []
        seen_test_ids = set()
        for t in test_chunks:
            if t["chunk_id"] not in seen_test_ids:
                seen_test_ids.add(t["chunk_id"])
                formatted_tests.append({
                    "chunk_id": t["chunk_id"],
                    "test_name": t.get("chunk_name", ""),
                    "file_path": t.get("file_path", ""),
                    "lines": f"L{t.get('start_line', 1)}-L{t.get('end_line', 1)}",
                    "verification": RelationshipType.DIRECTLY_VERIFIED
                })

        # Class Hierarchy
        base_classes = self.inheritance.get(clean_sym, [])
        sub_classes = self.subclasses.get(clean_sym, [])

        # File dependencies
        file_deps = []
        if def_chunks:
            fpath = def_chunks[0].get("file_path", "")
            file_deps = sorted(list(self.file_imports.get(fpath, set())))

        return {
            "symbol_name": clean_sym,
            "is_defined": len(def_chunks) > 0,
            "definitions_count": len(def_chunks),
            "definitions": [
                {
                    "chunk_id": d["chunk_id"],
                    "repo_id": d.get("repo_id", ""),
                    "file_path": d.get("file_path", ""),
                    "chunk_name": d.get("chunk_name", ""),
                    "chunk_type": d.get("chunk_type", ""),
                    "start_line": d.get("start_line", 1),
                    "end_line": d.get("end_line", 1)
                }
                for d in def_chunks
            ],
            "callers": unique_callers[:20],
            "callees": callees[:20],
            "inheritance": {
                "base_classes": base_classes,
                "subclasses": sub_classes
            },
            "related_tests": formatted_tests[:10],
            "file_dependencies": file_deps[:15]
        }
