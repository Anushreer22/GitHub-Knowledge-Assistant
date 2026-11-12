import re
from typing import Dict, Any, List, Optional, Set

from .hybrid_retriever import HybridRetriever
from .context_expander import ContextExpander
from .evidence_builder import EvidenceBuilder

QUESTION_STOPWORDS = {
    "where", "is", "the", "how", "does", "what", "which", "file", "in", "to",
    "of", "and", "or", "a", "an", "by", "for", "with", "from", "implemented",
    "defined", "code", "method", "function", "class", "operate", "work", "do"
}

MULTI_FILE_TRIGGERS = [
    "flow", "architecture", "interaction", "callers", "called from", "how does",
    "dispatch", "register", "across files", "pipeline", "lifecycle", "worker",
    "handle", "step by step", "components", "workflow"
]


def extract_content_tokens(text: str) -> List[str]:
    """Extract substantive keywords from question query."""
    tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return [t for t in tokens if len(t) >= 3 and t not in QUESTION_STOPWORDS]


def is_multi_file_query(question: str) -> bool:
    """Identify if question requires multi-component architectural flow across multiple files."""
    q_lower = question.lower()
    return any(trig in q_lower for trig in MULTI_FILE_TRIGGERS)


class AnswerEngine:
    """Evidence-Grounded Question Answering Engine for GitHub Repositories.
    Generates factual explanations strictly supported by verified source code evidence,
    including cross-file flow synthesis and missing-evidence detection.
    """

    def __init__(
        self,
        retriever: HybridRetriever,
        expander: ContextExpander,
        symbol_graph: Optional[Any] = None,
        min_evidence_threshold: float = 0.005
    ):
        self.retriever = retriever
        self.expander = expander
        self.symbol_graph = symbol_graph
        self.min_evidence_threshold = min_evidence_threshold

    def answer_question(
        self,
        question: str,
        repo_id: Optional[str] = None,
        top_k: int = 5,
        mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """Retrieve code evidence, expand context, and generate a factual evidence-grounded answer."""
        is_multi = is_multi_file_query(question)
        search_k = max(top_k * 2, 10) if is_multi else top_k

        retrieved_chunks = self.retriever.search(
            query=question,
            top_k=search_k,
            mode=mode,
            repo_id=repo_id
        )

        content_keywords = extract_content_tokens(question)

        # 1. Check for insufficient evidence or empty retrieval
        insufficient = False
        if not retrieved_chunks:
            insufficient = True
        elif retrieved_chunks[0].get("match_classification") == "insufficient_evidence":
            insufficient = True
        elif retrieved_chunks[0].get("score", 0.0) < self.min_evidence_threshold:
            insufficient = True
        else:
            combined_top_text = " ".join(
                (c.get("file_path", "") + " " + c.get("chunk_name", "") + " " + c.get("code_text", "")).lower()
                for c in retrieved_chunks[:3]
            )
            top_tokens = set(re.findall(r"[A-Za-z0-9_]+", combined_top_text))

            def match_token(kw: str) -> bool:
                if kw in combined_top_text:
                    return True
                prefix = kw[:4] if len(kw) >= 4 else kw
                for tok in top_tokens:
                    if len(tok) >= 4 and (tok.startswith(prefix) or prefix in tok):
                        return True
                return False

            if content_keywords and not any(match_token(kw) for kw in content_keywords):
                insufficient = True
        if insufficient:
            return {
                "question": question,
                "answer": (
                    f"Insufficient evidence: The repository does not contain verifiable code matching '{question}'. "
                    "No corresponding functions, classes, or files were found with sufficient confidence in the indexed codebase."
                ),
                "is_answered": False,
                "confidence_indicator": "insufficient_evidence",
                "retrieval_method": mode,
                "evidence": [],
                "citations": []
            }

        # 2. Multi-file retrieval strategy: ensure diverse cross-file coverage
        if is_multi and len(retrieved_chunks) > 1:
            diverse_chunks = []
            seen_files: Set[str] = set()
            # First pass: one top chunk per distinct file
            for chunk in retrieved_chunks:
                fpath = chunk.get("file_path", "")
                if fpath not in seen_files:
                    seen_files.add(fpath)
                    diverse_chunks.append(chunk)
                if len(diverse_chunks) >= top_k:
                    break
            # Second pass: fill remaining slots if needed
            if len(diverse_chunks) < top_k:
                for chunk in retrieved_chunks:
                    if chunk not in diverse_chunks:
                        diverse_chunks.append(chunk)
                    if len(diverse_chunks) >= top_k:
                        break
            selected_chunks = diverse_chunks
        else:
            selected_chunks = retrieved_chunks[:top_k]

        # 3. Build structured evidence and expanded contexts
        evidence_items = []
        for chunk in selected_chunks:
            expanded = self.expander.expand_context(chunk)
            item = EvidenceBuilder.build_evidence_item(chunk, expanded)
            item["match_classification"] = chunk.get("match_classification", "related_context")
            evidence_items.append(item)

        # 4. Multi-file flow synthesis vs single-file synthesis
        primary = evidence_items[0]
        p_name = primary["chunk_name"]
        p_file = primary["file_path"]
        p_repo = primary["repo_id"]
        p_lines = f"{primary['start_line']}–{primary['end_line']}"
        p_type = primary["chunk_type"]
        p_parent = primary.get("parent_class")
        p_imports = primary.get("imports", [])
        p_classif = primary.get("match_classification", "related_context")

        q_lower = question.lower()
        explanation_lines = []

        if is_multi:
            # Multi-file flow synthesis
            explanation_lines.append(
                f"Architecture & Execution Flow for `{p_name}` across repository `{p_repo}`:"
            )
            # Step 1: Core definition
            explanation_lines.append(
                f"1. [Core Component]: Implemented in `{p_file}` (lines {p_lines}) as `{p_name}` ({p_type})."
            )

            # Query symbol graph for verified callers, callees, and tests if available
            symbol_relations = None
            if self.symbol_graph:
                symbol_relations = self.symbol_graph.get_symbol_relationships(p_name, repo_id=p_repo)

            # Step 2: Callers / Inbound Triggers
            callers_found = False
            if symbol_relations and symbol_relations.get("callers"):
                top_caller = symbol_relations["callers"][0]
                callers_found = True
                explanation_lines.append(
                    f"2. [Inbound Invocation]: Called from `{top_caller['caller_name']}` in `{top_caller['file_path']}` ({top_caller['lines']}) [{top_caller['verification']}]."
                )
                # If top caller is in symbol graph and not yet in evidence_items, check if we can add its chunk
                caller_cid = top_caller.get("chunk_id")
                if caller_cid and not any(e.get("chunk_id") == caller_cid for e in evidence_items):
                    caller_meta = getattr(self.symbol_graph, "chunk_by_id", {}).get(caller_cid)
                    if caller_meta:
                        exp = self.expander.expand_context(caller_meta)
                        c_item = EvidenceBuilder.build_evidence_item(caller_meta, exp)
                        c_item["match_classification"] = "related_context"
                        evidence_items.append(c_item)
            elif len(evidence_items) > 1:
                sec = evidence_items[1]
                explanation_lines.append(
                    f"2. [Supporting Component]: Interacts with `{sec['chunk_name']}` in `{sec['file_path']}` (lines {sec['start_line']}–{sec['end_line']})."
                )
                callers_found = True

            # Step 3: Outbound dependencies / Callees
            if symbol_relations and symbol_relations.get("callees"):
                verified_callees = [c["symbol_name"] for c in symbol_relations["callees"] if c["verification"] == "directly_verified"]
                if verified_callees:
                    explanation_lines.append(
                        f"3. [Internal Delegation]: Dispatches execution to internal symbols: {', '.join(verified_callees[:4])}."
                    )

            # Step 4: Test verification
            if symbol_relations and symbol_relations.get("related_tests"):
                top_test = symbol_relations["related_tests"][0]
                explanation_lines.append(
                    f"4. [Verification]: Verified and tested by `{top_test['test_name']}` in `{top_test['file_path']}` ({top_test['lines']})."
                )
                test_cid = top_test.get("chunk_id")
                if test_cid and not any(e.get("chunk_id") == test_cid for e in evidence_items):
                    test_meta = getattr(self.symbol_graph, "chunk_by_id", {}).get(test_cid)
                    if test_meta:
                        exp = self.expander.expand_context(test_meta)
                        t_item = EvidenceBuilder.build_evidence_item(test_meta, exp)
                        t_item["match_classification"] = "related_context"
                        evidence_items.append(t_item)

            # Missing evidence detection for multi-component queries
            if any(term in q_lower for term in ["registration", "register", "dispatch", "handler", "storage backend"]):
                has_reg = any("register" in e.get("chunk_name", "").lower() or "register" in e.get("code_text", "").lower() for e in evidence_items)
                if not has_reg:
                    explanation_lines.append(
                        "Note on missing evidence: The primary implementation and execution flow are verified in the cited files, "
                        "but the registration / dispatch wiring is not present in the retrieved index chunks."
                    )

        else:
            # Single-component grounded answer synthesis
            if p_classif == "exact_match":
                if any(w in q_lower for w in ["where", "location", "file", "find"]):
                    explanation_lines.append(
                        f"The symbol `{p_name}` ({p_type}) is implemented in repository `{p_repo}`, "
                        f"located in file `{p_file}` across lines {p_lines}."
                    )
                elif any(w in q_lower for w in ["parameter", "argument", "accept", "return"]):
                    explanation_lines.append(
                        f"The `{p_name}` component is implemented in `{p_file}` (lines {p_lines}). "
                        f"Reviewing the source implementation confirms its signature and definition inside `{p_type}`."
                    )
                elif any(w in q_lower for w in ["import", "depend", "package"]):
                    imp_str = ", ".join(p_imports[:5]) if p_imports else "no external package imports"
                    explanation_lines.append(
                        f"The `{p_name}` definition in `{p_file}` (lines {p_lines}) declares imports: {imp_str}."
                    )
                else:
                    explanation_lines.append(
                        f"Based on source evidence in `{p_repo}`, `{p_name}` is defined in `{p_file}` (lines {p_lines}) as an exact `{p_type}` match."
                    )
            elif p_classif == "related_context":
                is_test = "test" in p_file.lower() or p_name.lower().startswith("test")
                role_desc = "a related test function" if is_test else "a caller / reference site"
                explanation_lines.append(
                    f"The symbol `{p_name}` was located in `{p_file}` (lines {p_lines}) within `{p_repo}` as {role_desc}. "
                    f"Note: This is related context rather than a direct isolated definition."
                )
            else: # strong_semantic_match
                explanation_lines.append(
                    f"Relevant code matching your query was found in `{p_file}` (lines {p_lines}) defining `{p_name}` ({p_type})."
                )

            if p_parent:
                explanation_lines.append(f"It is defined within parent class `{p_parent['class_name']}`.")

            if len(evidence_items) > 1:
                sec = evidence_items[1]
                explanation_lines.append(
                    f"Supporting context is available in `{sec['file_path']}` (lines {sec['start_line']}–{sec['end_line']})."
                )

        answer_text = " ".join(explanation_lines)

        # Confidence indicator determination
        if p_classif == "exact_match":
            confidence = "high"
        elif p_classif == "strong_semantic_match":
            confidence = "high" if primary["score"] > 0.02 else "medium"
        elif p_classif == "related_context":
            confidence = "medium"
        else:
            confidence = "low"

        # Citation discipline: every file mentioned in answer must have a citation
        citations = []
        for e in evidence_items:
            cit = e.get("citation")
            if cit and cit not in citations:
                citations.append(cit)

        return {
            "question": question,
            "answer": answer_text,
            "is_answered": True,
            "confidence_indicator": confidence,
            "retrieval_method": mode,
            "evidence": evidence_items,
            "citations": citations
        }
