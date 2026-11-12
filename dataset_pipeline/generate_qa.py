import ast
import re
import argparse
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple, Iterator

from .common import DATA, stream_read, stream_write, sid

KNOWN_PATTERNS = [
    "Factory", "Builder", "Singleton", "Observer", "Strategy",
    "Adapter", "Decorator", "Facade", "Proxy", "Command",
    "State", "Visitor", "Template", "Prototype", "Bridge", "Composite"
]

JAVA_METHOD_SIG = re.compile(
    r"(?:public|protected|private|static|final|abstract|synchronized|\s)*\s+"
    r"([\w<>?\[\],\s]+)\s+(\w+)\s*\(([^)]*)\)(?:\s*throws\s+([^{;]+))?"
)
JAVA_THROWS_SIG = re.compile(r"throws\s+([A-Za-z0-9_,\s]+)")
JAVA_CATCH_SIG = re.compile(r"catch\s*\(\s*([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)\s*\)")
JAVA_CLASS_SIG = re.compile(
    r"(?:public|protected|private|abstract|final|\s)*\s+"
    r"(class|interface|enum)\s+(\w+)(?:<[^>]+>)?(?:\s+extends\s+([^{]+))?(?:\s+implements\s+([^{]+))?"
)


def extract_python_details(code_text: str, chunk_name: str) -> Dict[str, Any]:
    """Extract AST information from a Python code chunk."""
    details: Dict[str, Any] = {
        "params": [],
        "returns": None,
        "docstring": None,
        "raises": [],
        "catches": [],
        "classes": [],
        "methods": []
    }
    # Indentation adjustment if snippet starts indented
    cleaned = code_text.strip()
    first_line = cleaned.splitlines()[0] if cleaned else ""
    leading_spaces = len(first_line) - len(first_line.lstrip())
    if leading_spaces > 0:
        cleaned = "\n".join(
            line[leading_spaces:] if len(line) >= leading_spaces else line.lstrip()
            for line in cleaned.splitlines()
        )

    try:
        tree = ast.parse(cleaned)
    except Exception:
        # Fallback regex for python signature
        m = re.search(r"def\s+(\w+)\s*\(([^)]*)\)(?:\s*->\s*([^:]+))?:", code_text)
        if m:
            details["params"] = [p.strip().split(":")[0].strip() for p in m.group(2).split(",") if p.strip()]
            details["returns"] = m.group(3).strip() if m.group(3) else None
        return details

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == chunk_name or not details["params"]:
                details["params"] = [a.arg for a in node.args.args if a.arg != "self"]
                details["docstring"] = ast.get_docstring(node)
                if node.returns:
                    try:
                        details["returns"] = ast.unparse(node.returns)
                    except Exception:
                        details["returns"] = str(getattr(node.returns, "id", "object"))
        elif isinstance(node, ast.ClassDef):
            details["classes"].append(node.name)
            if not details["docstring"]:
                details["docstring"] = ast.get_docstring(node)
        elif isinstance(node, ast.Raise):
            if isinstance(node.exc, ast.Call) and hasattr(node.exc.func, "id"):
                details["raises"].append(node.exc.func.id)
            elif isinstance(node.exc, ast.Name):
                details["raises"].append(node.exc.id)
        elif isinstance(node, ast.ExceptHandler):
            if isinstance(node.type, ast.Name):
                details["catches"].append(node.type.id)

    return details


def extract_java_details(code_text: str, chunk_name: str) -> Dict[str, Any]:
    """Extract signature and structure from Java code chunks."""
    details: Dict[str, Any] = {
        "params": [],
        "returns": None,
        "throws": [],
        "catches": [],
        "extends": None,
        "implements": None,
        "kind": "class"
    }
    # Match method signature
    for line in code_text.splitlines()[:5]:
        m = JAVA_METHOD_SIG.search(line)
        if m:
            ret, name, raw_params, throws_clause = m.groups()
            details["returns"] = ret.strip()
            if raw_params and raw_params.strip():
                details["params"] = [p.strip() for p in raw_params.split(",") if p.strip()]
            if throws_clause:
                details["throws"] = [t.strip() for t in throws_clause.split(",") if t.strip()]
            break

    # Check for catches
    for match in JAVA_CATCH_SIG.finditer(code_text):
        details["catches"].append(match.group(1).strip())

    # Check for class signature
    cm = JAVA_CLASS_SIG.search(code_text[:300])
    if cm:
        details["kind"] = cm.group(1)
        details["extends"] = cm.group(3).strip() if cm.group(3) else None
        details["implements"] = cm.group(4).strip() if cm.group(4) else None

    return details


def detect_design_pattern(file_path: str, chunk_name: str, code_text: str) -> Optional[str]:
    """Identify if the code chunk belongs to a recognized design pattern."""
    target = f"{file_path} {chunk_name}"
    for pattern in KNOWN_PATTERNS:
        if re.search(rf"\b{pattern}\b", target, re.IGNORECASE):
            return pattern
    return None


def generate_candidates_for_chunk(chunk: Dict[str, Any], max_per_chunk: int = 3) -> List[Dict[str, Any]]:
    """Generate deterministic, grounded QA candidates for a single code chunk."""
    candidates: List[Dict[str, Any]] = []
    repo_id = chunk["repo_id"]
    chunk_id = chunk["chunk_id"]
    file_path = chunk["file_path"]
    name = chunk.get("chunk_name", "unnamed")
    chunk_type = chunk.get("chunk_type", "").lower()
    lang = chunk.get("language", "python").lower()
    start = chunk.get("start_line", 1)
    end = chunk.get("end_line", 1)
    code = chunk.get("code_text", "")
    imports = chunk.get("imports", [])
    symbols_used = [s for s in chunk.get("symbols_used", []) if s not in {"self", "this", "str", "int", "None"}]

    def make_qa(question: str, answer: Optional[str], method: str, difficulty: str = "easy", answerable: bool = True) -> Dict[str, Any]:
        return {
            "schema_version": "1.0",
            "question_id": f"q_{sid(repo_id, chunk_id, method, question)}",
            "repo_id": repo_id,
            "question": question,
            "expected_answer": answer,
            "relevant_chunk_ids": [chunk_id],
            "relevant_files": [file_path],
            "difficulty": difficulty,
            "answerable": answerable,
            "generation_method": method,
            "review_status": "pending",
            "reviewer_notes": "",
            "source_chunk_id": chunk_id,
            "split": None
        }

    # 1. Class or Interface Definition
    if any(k in chunk_type for k in ["class", "interface", "enum"]):
        q = f"Where is the {name} {chunk_type.replace('_declaration', '')} defined?"
        a = f"The {name} {chunk_type.replace('_declaration', '')} is defined in {file_path} (lines {start}-{end})."
        candidates.append(make_qa(q, a, "class_identification", "easy"))

    # 2. Function or Method Implementation
    elif any(k in chunk_type for k in ["function", "method", "constructor"]):
        kind = "constructor" if "constructor" in chunk_type else ("method" if "method" in chunk_type else "function")
        q = f"Where is the {name} {kind} implemented?"
        a = f"The {name} {kind} is implemented in {file_path} at lines {start}-{end}."
        candidates.append(make_qa(q, a, "function_method_identification", "easy"))

    # 3. File Location Question
    q_loc = f"Which file contains the implementation of {name}?"
    a_loc = f"The symbol {name} is implemented in {file_path} (lines {start}-{end})."
    candidates.append(make_qa(q_loc, a_loc, "file_location", "easy"))

    # 4. Parameters and Return Values
    if lang == "python":
        py_info = extract_python_details(code, name)
        if py_info["params"]:
            params_str = ", ".join(py_info["params"][:6])
            ret_str = py_info["returns"] or "unspecified"
            q_param = f"What parameters does the {name} function accept and what does it return?"
            a_param = f"The {name} function accepts ({params_str}) and returns {ret_str} in {file_path}."
            candidates.append(make_qa(q_param, a_param, "parameters_and_return", "medium"))
    elif lang == "java":
        java_info = extract_java_details(code, name)
        if java_info["params"] or java_info["returns"]:
            params_str = ", ".join(java_info["params"][:6]) if java_info["params"] else "no parameters"
            ret_str = java_info["returns"] or "void"
            q_param = f"What parameters does the {name} method take and what is its return type?"
            a_param = f"The {name} method accepts ({params_str}) and returns {ret_str} in {file_path}."
            candidates.append(make_qa(q_param, a_param, "parameters_and_return", "medium"))

    # 5. Dependency and Imports
    if imports:
        imp_sample = ", ".join(imports[:5])
        q_imp = f"What dependencies or imports are used by {name} in {file_path}?"
        a_imp = f"The file/module {file_path} imports: {imp_sample}."
        candidates.append(make_qa(q_imp, a_imp, "dependency_and_imports", "medium"))

    # 6. Error Handling
    if lang == "python":
        py_info = extract_python_details(code, name)
        if py_info["raises"] or py_info["catches"]:
            errs = py_info["raises"] + py_info["catches"]
            q_err = f"How does {name} handle exceptions or errors?"
            a_err = f"The {name} function catches or raises: {', '.join(set(errs))} in {file_path}."
            candidates.append(make_qa(q_err, a_err, "error_handling", "hard"))
    elif lang == "java":
        java_info = extract_java_details(code, name)
        if java_info["throws"] or java_info["catches"]:
            errs = java_info["throws"] + java_info["catches"]
            q_err = f"How does the {name} method handle exceptions?"
            a_err = f"The {name} method declares or catches: {', '.join(set(errs))} in {file_path}."
            candidates.append(make_qa(q_err, a_err, "error_handling", "hard"))

    # 7. Design Pattern Question
    pattern = detect_design_pattern(file_path, name, code)
    if pattern:
        q_pat = f"What design pattern is represented or used by {name} in {file_path}?"
        a_pat = f"The {name} component implements or represents the {pattern} design pattern in {file_path}."
        candidates.append(make_qa(q_pat, a_pat, "design_pattern", "hard"))

    # 8. Cross-File Symbol Usage / Reference
    if symbols_used:
        sym_sample = ", ".join(symbols_used[:5])
        q_sym = f"Which symbols or functions are referenced inside {name}?"
        a_sym = f"The {name} implementation references: {sym_sample} in {file_path}."
        candidates.append(make_qa(q_sym, a_sym, "symbol_usage", "medium"))

    # 9. Code Flow
    if len(symbols_used) >= 2:
        q_flow = f"What is the operational flow of {name}?"
        a_flow = f"The {name} routine (lines {start}-{end}) coordinates operations involving {', '.join(symbols_used[:3])}."
        candidates.append(make_qa(q_flow, a_flow, "code_flow", "hard"))

    return candidates[:max_per_chunk]


def generate_qa_stream(
    chunks_path: Path,
    limit: Optional[int] = None,
    max_per_chunk: int = 2
) -> Iterator[Dict[str, Any]]:
    """Yield QA candidate records line-by-line."""
    count = 0
    for chunk in stream_read(chunks_path):
        candidates = generate_candidates_for_chunk(chunk, max_per_chunk=max_per_chunk)
        for c in candidates:
            yield c
            count += 1
            if limit and count >= limit:
                return


def main():
    parser = argparse.ArgumentParser(description="Generate grounded QA candidates from code chunks.")
    parser.add_argument("--input", type=str, default=str(DATA / "processed" / "code_chunks.jsonl"), help="Input chunks path")
    parser.add_argument("--output", type=str, default=str(DATA / "qa" / "qa_candidates.jsonl"), help="Output QA candidates path")
    parser.add_argument("--review-template", type=str, default=str(DATA / "qa" / "qa_review_template.jsonl"), help="Review template path")
    parser.add_argument("--limit", type=int, default=None, help="Optional limit on total generated questions")
    parser.add_argument("--max-per-chunk", type=int, default=2, help="Maximum QA candidates generated per chunk")
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output)
    review_template_path = Path(args.review_template)

    print(f"Generating QA pairs from {input_path}...")
    count = stream_write(output_path, generate_qa_stream(input_path, limit=args.limit, max_per_chunk=args.max_per_chunk))
    print(f"Generated {count} QA candidates saved to {output_path}")

    # Also keep review template in sync
    if review_template_path != output_path:
        stream_write(review_template_path, stream_read(output_path))
        print(f"Review template saved to {review_template_path}")


if __name__ == "__main__":
    main()
