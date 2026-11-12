from typing import List, Dict, Any


class EvidenceBuilder:
    """Formats retrieved code chunks into standardized citations and evidence blocks."""

    @staticmethod
    def build_evidence_item(chunk: Dict[str, Any], expanded_ctx: Dict[str, Any]) -> Dict[str, Any]:
        """Create a structured evidence citation item."""
        repo = chunk.get("repo_id", "")
        fpath = chunk.get("file_path", "")
        start = chunk.get("start_line", 1)
        end = chunk.get("end_line", 1)
        name = chunk.get("chunk_name", "")
        typ = chunk.get("chunk_type", "")
        score = chunk.get("score", 0.0)

        citation_str = f"{repo}:{fpath}#L{start}-L{end}"

        return {
            "citation": citation_str,
            "repo_id": repo,
            "file_path": fpath,
            "start_line": start,
            "end_line": end,
            "chunk_name": name,
            "chunk_type": typ,
            "score": score,
            "code_snippet": chunk.get("code_snippet") or chunk.get("code_text", "")[:400],
            "language": chunk.get("language", ""),
            "parent_class": expanded_ctx.get("parent_class"),
            "imports": expanded_ctx.get("imports", {}).get("items", []),
            "same_file_siblings": [s["name"] for s in expanded_ctx.get("same_file_siblings", [])]
        }

    @staticmethod
    def format_citations_markdown(evidence_list: List[Dict[str, Any]]) -> str:
        """Render evidence list as GitHub Markdown citation references."""
        lines = ["### Source Evidence Citations:"]
        for idx, ev in enumerate(evidence_list, 1):
            lines.append(
                f"{idx}. **[{ev['repo_id']}]** `{ev['file_path']}` (Lines {ev['start_line']}–{ev['end_line']}) "
                f"— `{ev['chunk_type']}` **{ev['chunk_name']}** (Score: {ev['score']})"
            )
        return "\n".join(lines)
