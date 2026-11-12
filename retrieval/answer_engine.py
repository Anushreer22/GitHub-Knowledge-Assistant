import re
from typing import Dict, Any, List, Optional

from .hybrid_retriever import HybridRetriever
from .context_expander import ContextExpander
from .evidence_builder import EvidenceBuilder

QUESTION_STOPWORDS = {
    "where", "is", "the", "how", "does", "what", "which", "file", "in", "to",
    "of", "and", "or", "a", "an", "by", "for", "with", "from", "implemented",
    "defined", "code", "method", "function", "class", "operate", "work", "do"
}


def extract_content_tokens(text: str) -> List[str]:
    """Extract substantive keywords from question query."""
    tokens = re.findall(r"[A-Za-z0-9_]+", text.lower())
    return [t for t in tokens if len(t) >= 3 and t not in QUESTION_STOPWORDS]


class AnswerEngine:
    """Evidence-Grounded Question Answering Engine for GitHub Repositories.
    Generates factual explanations strictly supported by verified source code evidence.
    """

    def __init__(self, retriever: HybridRetriever, expander: ContextExpander, min_evidence_threshold: float = 0.005):
        self.retriever = retriever
        self.expander = expander
        self.min_evidence_threshold = min_evidence_threshold

    def answer_question(
        self,
        question: str,
        repo_id: Optional[str] = None,
        top_k: int = 5,
        mode: str = "hybrid"
    ) -> Dict[str, Any]:
        """Retrieve code evidence, expand context, and generate a factual evidence-grounded answer."""
        retrieved_chunks = self.retriever.search(
            query=question,
            top_k=top_k,
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
            top_text = (
                retrieved_chunks[0].get("file_path", "") + " " +
                retrieved_chunks[0].get("chunk_name", "") + " " +
                retrieved_chunks[0].get("code_text", "")
            ).lower()
            if content_keywords and not any(kw in top_text for kw in content_keywords):
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

        # 2. Build structured evidence and expanded contexts
        evidence_items = []
        for chunk in retrieved_chunks:
            expanded = self.expander.expand_context(chunk)
            item = EvidenceBuilder.build_evidence_item(chunk, expanded)
            item["match_classification"] = chunk.get("match_classification", "related_context")
            evidence_items.append(item)

        # 3. Grounded answer synthesis
        primary = evidence_items[0]
        p_name = primary["chunk_name"]
        p_file = primary["file_path"]
        p_repo = primary["repo_id"]
        p_lines = f"{primary['start_line']}–{primary['end_line']}"
        p_type = primary["chunk_type"]
        p_parent = primary.get("parent_class")
        p_imports = primary.get("imports", [])
        p_classif = primary.get("match_classification", "related_context")

        # Factual synthesis based on query intent & classification
        q_lower = question.lower()
        explanation_lines = []

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

        return {
            "question": question,
            "answer": answer_text,
            "is_answered": True,
            "confidence_indicator": confidence,
            "retrieval_method": mode,
            "evidence": evidence_items,
            "citations": [e["citation"] for e in evidence_items]
        }
