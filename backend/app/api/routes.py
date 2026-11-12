from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from ..schemas.retrieval_schemas import (
    HealthResponse,
    RepositoryInfo,
    IndexRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
    QueryRequest,
    QueryResponse,
    FileInfo,
    ChunkDetailResponse,
    EvidenceItemSchema
)
from ..services.retrieval_service import RetrievalService

router = APIRouter()


def validate_safe_id(identifier: str, field_name: str) -> None:
    """Validate that path parameters do not attempt directory traversal attacks."""
    if ".." in identifier or "/" in identifier or "\\" in identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Security violation: Invalid characters or path traversal sequence in {field_name}."
        )


@router.get("/health", response_model=HealthResponse, tags=["System"])
def get_health():
    """Health check endpoint providing status of indexes and repositories."""
    service = RetrievalService.get_instance()
    repos = service.list_repositories()
    return HealthResponse(
        status="ok",
        version="4.0.0",
        repositories_count=len(repos),
        bm25_index_ready=service.bm25 is not None and len(service.bm25.corpus_meta) > 0,
        dense_index_ready=service.dense is not None and len(service.dense.store) > 0
    )


@router.get("/api/repositories", response_model=List[RepositoryInfo], tags=["Repositories"])
def list_repositories():
    """List all available repositories and their chunk counts."""
    service = RetrievalService.get_instance()
    repos = service.list_repositories()
    return [RepositoryInfo(**r) for r in repos]


@router.post("/api/repositories/index", response_model=IndexResponse, tags=["Indexing"])
def trigger_indexing(request: IndexRequest):
    """Trigger background or immediate indexing of repository code chunks into BM25 and Dense vector indexes."""
    service = RetrievalService.get_instance()
    try:
        res = service.trigger_indexing(max_chunks=request.max_chunks or 10000)
        return IndexResponse(
            status="success",
            bm25_indexed_chunks=res["bm25_count"],
            dense_indexed_chunks=res["dense_count"],
            message=f"Indexed {res['bm25_count']} chunks for BM25 and {res['dense_count']} chunks for Dense search."
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Indexing failed: {str(e)}"
        )


@router.post("/api/search", response_model=SearchResponse, tags=["Retrieval"])
def search_chunks(request: SearchRequest):
    """Execute BM25, Dense, or Hybrid search across indexed code chunks."""
    service = RetrievalService.get_instance()
    try:
        results = service.search(
            query=request.query,
            top_k=request.top_k,
            mode=request.mode,
            repo_id=request.repo_id
        )
        formatted_results = []
        for r in results:
            item = dict(r)
            if not item.get("citation"):
                item["citation"] = f"{item.get('repo_id', '')}:{item.get('file_path', '')}#L{item.get('start_line', 1)}-L{item.get('end_line', 1)}"
            if not item.get("code_snippet"):
                item["code_snippet"] = item.get("code_text", "")[:400]
            if "match_classification" not in item:
                item["match_classification"] = "related_context"
            formatted_results.append(EvidenceItemSchema(**item))

        return SearchResponse(
            query=request.query,
            retrieval_method=request.mode,
            total_results=len(formatted_results),
            results=formatted_results
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Search failed: {str(e)}"
        )


@router.post("/api/query", response_model=QueryResponse, tags=["QA"])
def query_knowledge_assistant(request: QueryRequest):
    """Ask a natural-language question and receive an evidence-grounded answer with source citations."""
    service = RetrievalService.get_instance()
    try:
        qa_result = service.query_qa(
            question=request.question,
            top_k=request.top_k,
            mode=request.mode,
            repo_id=request.repo_id
        )
        formatted_evidence = []
        for ev in qa_result["evidence"]:
            item = dict(ev)
            if not item.get("citation"):
                item["citation"] = f"{item.get('repo_id', '')}:{item.get('file_path', '')}#L{item.get('start_line', 1)}-L{item.get('end_line', 1)}"
            if "match_classification" not in item:
                item["match_classification"] = "related_context"
            formatted_evidence.append(EvidenceItemSchema(**item))

        primary_classif = formatted_evidence[0].match_classification if formatted_evidence else "insufficient_evidence"

        return QueryResponse(
            question=qa_result["question"],
            answer=qa_result["answer"],
            is_answered=qa_result["is_answered"],
            confidence_indicator=qa_result["confidence_indicator"],
            retrieval_method=qa_result["retrieval_method"],
            evidence=formatted_evidence,
            citations=qa_result["citations"],
            match_classification=primary_classif
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"QA Query failed: {str(e)}"
        )


@router.get("/api/repositories/{repository_id}/files", response_model=List[FileInfo], tags=["Repositories"])
def list_repository_files(repository_id: str):
    """List indexed files for a given repository."""
    validate_safe_id(repository_id, "repository_id")
    service = RetrievalService.get_instance()
    files = service.list_files(repository_id)
    if not files:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Repository '{repository_id}' not found or has no indexed files."
        )
    return [FileInfo(**f) for f in files]


@router.get("/api/repositories/{repository_id}/chunks/{chunk_id}", response_model=ChunkDetailResponse, tags=["Repositories"])
def get_chunk_detail(repository_id: str, chunk_id: str):
    """Fetch full chunk details and source text."""
    validate_safe_id(repository_id, "repository_id")
    validate_safe_id(chunk_id, "chunk_id")
    service = RetrievalService.get_instance()
    chunk = service.get_chunk(repository_id, chunk_id)
    if not chunk:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Chunk '{chunk_id}' not found in repository '{repository_id}'."
        )
    return ChunkDetailResponse(
        chunk_id=chunk["chunk_id"],
        repo_id=chunk.get("repo_id", repository_id),
        file_path=chunk.get("file_path", ""),
        start_line=chunk.get("start_line", 1),
        end_line=chunk.get("end_line", 1),
        chunk_type=chunk.get("chunk_type", ""),
        chunk_name=chunk.get("chunk_name", ""),
        language=chunk.get("language", ""),
        code_text=chunk.get("code_text", ""),
        imports=chunk.get("imports", []),
        symbols_defined=chunk.get("symbols_defined", []),
        symbols_used=chunk.get("symbols_used", [])
    )
