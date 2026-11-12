import re
from typing import List, Dict, Any, Optional, Tuple, Set


COMMON_QUERY_WORDS = {
    "where", "is", "the", "how", "does", "what", "which", "file", "in", "to",
    "of", "and", "or", "a", "an", "by", "for", "with", "from", "implemented",
    "defined", "code", "method", "function", "class", "operate", "work", "do",
    "call", "calls", "used", "located", "test", "tests", "testing", "show",
    "explain", "find", "get", "give", "me"
}


def extract_query_symbols(query: str) -> Dict[str, Any]:
    """Extract code identifiers, target symbol types, and requested repository/file hints from query."""
    result: Dict[str, Any] = {
        "explicit_symbols": [],
        "target_type": None,     # "function", "class", "file", "test", or None
        "file_hint": None,
        "is_test_query": False,
        "clean_tokens": []
    }

    q_lower = query.lower()

    # 1. Backticked code symbols: e.g. `check_auth`
    backticked = re.findall(r"`([A-Za-z0-9_]+)`", query)
    for sym in backticked:
        if sym.lower() not in COMMON_QUERY_WORDS:
            result["explicit_symbols"].append(sym)

    # 2. Function / Method / Class target patterns
    func_pattern = re.search(r"(?:function|method|def)\s+([A-Za-z0-9_]+)", query, re.IGNORECASE)
    if func_pattern:
        sym = func_pattern.group(1)
        if sym.lower() not in COMMON_QUERY_WORDS and sym not in result["explicit_symbols"]:
            result["explicit_symbols"].append(sym)
        result["target_type"] = "function"

    class_pattern = re.search(r"(?:class|interface|struct)\s+([A-Za-z0-9_]+)", query, re.IGNORECASE)
    if class_pattern:
        sym = class_pattern.group(1)
        if sym.lower() not in COMMON_QUERY_WORDS and sym not in result["explicit_symbols"]:
            result["explicit_symbols"].append(sym)
        result["target_type"] = "class"

    # 3. "where is [the] <symbol>" pattern
    where_pattern = re.search(r"where\s+is\s+(?:the\s+)?([A-Za-z0-9_]+)", query, re.IGNORECASE)
    if where_pattern:
        sym = where_pattern.group(1)
        if sym.lower() not in COMMON_QUERY_WORDS and sym not in result["explicit_symbols"]:
            result["explicit_symbols"].append(sym)

    # 4. Detect file hints (e.g. format.py, UserService.java)
    file_pattern = re.search(r"\b([A-Za-z0-9_\-]+\.(?:py|java|js|ts|json|md))\b", query, re.IGNORECASE)
    if file_pattern:
        result["file_hint"] = file_pattern.group(1).lower()

    # 5. Is user asking for a test specifically?
    if re.search(r"\b(?:test|tests|unit\s*test)\s+for\b|\bwhere\s+is\s+(?:the\s+)?test\b", query, re.IGNORECASE):
        result["is_test_query"] = True

    # 6. Extract identifiers (snake_case, camelCase) from text
    raw_identifiers = re.findall(r"\b[A-Za-z_][A-Za-z0-9_]*\b", query)
    for ident in raw_identifiers:
        # Check if identifier has underscores or internal uppercase (camelCase)
        is_snake = "_" in ident and len(ident) > 2
        is_camel = bool(re.search(r"[a-z][A-Z]", ident))
        if (is_snake or is_camel) and ident.lower() not in COMMON_QUERY_WORDS:
            if ident not in result["explicit_symbols"]:
                result["explicit_symbols"].append(ident)

    result["clean_tokens"] = [
        t.lower() for t in raw_identifiers if len(t) >= 2 and t.lower() not in COMMON_QUERY_WORDS
    ]

    return result


def classify_candidate_match(
    candidate: Dict[str, Any],
    query_symbols: Dict[str, Any],
    base_score: float = 0.0
) -> Tuple[str, float]:
    """Classify the retrieval match and compute a precision-adjusted score.
    Returns:
        (classification, adjusted_score)
        where classification in:
        - "exact_match": Exact definition of requested function/class in non-test source.
        - "strong_semantic_match": Highly relevant code or exact definition in requested context.
        - "related_context": Test function, caller/usage site, or related file component.
        - "insufficient_evidence": Weak or irrelevant match.
    """
    target_symbols = [s.lower() for s in query_symbols.get("explicit_symbols", [])]
    target_type = query_symbols.get("target_type")
    is_test_query = query_symbols.get("is_test_query", False)
    file_hint = query_symbols.get("file_hint")

    c_name = candidate.get("chunk_name", "").lower()
    c_type = candidate.get("chunk_type", "").lower()
    f_path = candidate.get("file_path", "").lower()
    defs = [d.lower() for d in candidate.get("symbols_defined", [])]
    uses = [u.lower() for u in candidate.get("symbols_used", [])]
    code_text = candidate.get("code_text", "").lower()

    is_test_file = "test" in f_path or "/tests/" in f_path
    is_test_chunk = c_name.startswith("test_") or c_name.startswith("test") or is_test_file

    # If explicit target symbols are requested, check if ANY target symbol exists in this chunk
    if target_symbols:
        has_any_target = (
            any(ts in c_name for ts in target_symbols)
            or any(ts in defs for ts in target_symbols)
            or any(ts in uses for ts in target_symbols)
            or any(ts in code_text for ts in target_symbols)
        )
        if not has_any_target:
            # Query explicitly asked for a symbol, but this candidate has zero mention of it
            return "insufficient_evidence", base_score

    # 1. Exact Match on target symbol
    has_exact_name = any(ts == c_name for ts in target_symbols)
    has_exact_def = any(ts in defs for ts in target_symbols)

    if has_exact_name or has_exact_def:
        if not is_test_chunk or is_test_query:
            # Exact implementation definition
            adjusted_score = base_score + 10.0
            return "exact_match", adjusted_score
        else:
            # It's a test chunk that defines or wraps the symbol
            adjusted_score = base_score + 2.0
            return "related_context", adjusted_score

    # 2. Check if it's a test function naming the target symbol (e.g. test_check_auth)
    is_test_for_target = any(
        c_name == f"test_{ts}" or c_name == f"test{ts}" or f"test_{ts}_" in c_name
        for ts in target_symbols
    )
    if is_test_for_target:
        if is_test_query:
            return "exact_match", base_score + 8.0
        else:
            # It is a related test, NOT the implementation
            return "related_context", base_score + 1.5

    # 3. Caller / Usage match
    has_symbol_usage = any(ts in uses for ts in target_symbols)
    if has_symbol_usage:
        return "related_context", base_score + 1.0

    # 4. File path hint match
    if file_hint and file_hint in f_path:
        return "strong_semantic_match", base_score + 3.0

    # 5. Type and token relevance
    if target_symbols and any(ts in c_name for ts in target_symbols):
        return "strong_semantic_match", base_score + 1.2

    # 6. Fallback based on score threshold
    if base_score >= 0.01:
        return "strong_semantic_match", base_score

    if base_score > 0.002:
        return "related_context", base_score

    return "insufficient_evidence", base_score


def rerank_and_classify_candidates(
    candidates: List[Dict[str, Any]],
    query: str,
    top_k: int = 10
) -> List[Dict[str, Any]]:
    """Deduplicate, rerank candidates using exact symbol matching, and tag each with its match classification."""
    if not candidates:
        return []

    q_info = extract_query_symbols(query)
    classified_results = []
    seen_cids: Set[str] = set()
    seen_spans: Set[Tuple[Any, ...]] = set()

    for c in candidates:
        cid = c.get("chunk_id")
        span_key = (
            c.get("repo_id"),
            c.get("file_path"),
            c.get("start_line"),
            c.get("end_line")
        )
        if cid and cid in seen_cids:
            continue
        if span_key in seen_spans:
            continue
        if cid:
            seen_cids.add(cid)
        seen_spans.add(span_key)

        base_score = float(c.get("score", 0.0))
        classification, adjusted_score = classify_candidate_match(c, q_info, base_score)

        item = dict(c)
        item["base_score"] = round(base_score, 4)
        item["score"] = round(adjusted_score, 4)
        item["match_classification"] = classification
        classified_results.append(item)

    # Sort primarily by adjusted score descending
    classified_results.sort(key=lambda x: x["score"], reverse=True)

    # Re-assign ranks
    for rank_idx, item in enumerate(classified_results, 1):
        item["rank"] = rank_idx

    return classified_results[:top_k]
