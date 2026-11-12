import re
import json
import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, HTTPException, Query, status, Depends

from dataset_pipeline.common import DATA
from ..schemas.retrieval_schemas import (
    HealthResponse,
    RepositoryInfo,
    AddRepositoryRequest,
    AddRepositoryResponse,
    SyncRepositoryResponse,
    IndexingHistoryItem,
    UserProfile,
    AuthResponse,
    RegisterRequest,
    LoginRequest,
    SaveRepoRequest,
    RecordSearchRequest,
    IndexRequest,
    IndexResponse,
    SearchRequest,
    SearchResponse,
    QueryRequest,
    QueryResponse,
    FileInfo,
    ChunkDetailResponse,
    EvidenceItemSchema,
    SymbolRelationshipsResponse,
    FeedbackRequest,
    FeedbackResponse
)
from ..services.retrieval_service import RetrievalService
from ..services.github_service import add_and_index_github_repo
from ..services.update_service import sync_repository, get_indexing_history
from ..services.auth_service import (
    register_user,
    authenticate_user,
    save_repository_for_user,
    remove_saved_repository_for_user,
    record_search_for_user
)
from .deps import get_current_user, get_current_user_optional

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
        version="5.0.0",
        repositories_count=len(repos),
        bm25_index_ready=service.bm25 is not None and len(service.bm25.corpus_meta) > 0,
        dense_index_ready=service.dense is not None and len(service.dense.store) > 0
    )


# -------------------------------------------------------------------------
# Phase 5C: Authentication & User Accounts Endpoints
# -------------------------------------------------------------------------

@router.post("/api/auth/register", response_model=AuthResponse, tags=["Authentication"])
def register(request: RegisterRequest):
    """Register a new user account with secure PBKDF2-HMAC password hashing and JWT issuance."""
    try:
        res = register_user(request.username, request.email, request.password)
        return AuthResponse(
            token=res["token"],
            user=UserProfile(**res["user"])
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )


@router.post("/api/auth/login", response_model=AuthResponse, tags=["Authentication"])
def login(request: LoginRequest):
    """Authenticate with username and password, returning JWT access token."""
    try:
        res = authenticate_user(request.username, request.password)
        return AuthResponse(
            token=res["token"],
            user=UserProfile(**res["user"])
        )
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(ve)
        )


@router.get("/api/auth/me", response_model=UserProfile, tags=["Authentication"])
def get_me(user: Dict[str, Any] = Depends(get_current_user)):
    """Fetch profile of currently authenticated user."""
    return UserProfile(**user)


@router.post("/api/user/saved-repositories", response_model=List[str], tags=["User Collections"])
def save_repo(request: SaveRepoRequest, user: Dict[str, Any] = Depends(get_current_user)):
    """Add a repository to the user's personal saved collection."""
    return save_repository_for_user(user["user_id"], request.repo_id)


@router.delete("/api/user/saved-repositories/{repository_id}", response_model=List[str], tags=["User Collections"])
def delete_saved_repo(repository_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    """Remove a repository from the user's personal saved collection."""
    validate_safe_id(repository_id, "repository_id")
    return remove_saved_repository_for_user(user["user_id"], repository_id)


@router.get("/api/user/saved-repositories", response_model=List[str], tags=["User Collections"])
def get_saved_repos(user: Dict[str, Any] = Depends(get_current_user)):
    """List repositories saved in user's personal collection."""
    return user.get("saved_repositories", [])


@router.get("/api/user/search-history", response_model=List[Dict[str, Any]], tags=["User Collections"])
def get_search_history(user: Dict[str, Any] = Depends(get_current_user)):
    """Retrieve search and question history for authenticated user."""
    return user.get("search_history", [])


@router.get("/api/repositories", response_model=List[RepositoryInfo], tags=["Repositories"])
def list_repositories():
    """List all available repositories and their chunk counts."""
    service = RetrievalService.get_instance()
    repos = service.list_repositories()
    return [RepositoryInfo(**r) for r in repos]


@router.post("/api/repositories/add", response_model=AddRepositoryResponse, tags=["Repositories"])
def add_repository(request: AddRepositoryRequest):
    """Validate, fetch metadata, shallow clone, parse AST chunks, and index a live public GitHub repository."""
    try:
        result = add_and_index_github_repo(
            url=request.url,
            max_chunks=request.max_chunks or 500
        )
        return AddRepositoryResponse(**result)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(ve)
        )
    except RuntimeError as re:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(re)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Live repository ingestion failed: {str(e)}"
        )


@router.post("/api/repositories/{repository_id}/sync", response_model=SyncRepositoryResponse, tags=["Repositories"])
def update_repository(repository_id: str):
    """Detect remote commits, inspect git diff, prune outdated chunks, generate new AST chunks, and sync indexes."""
    validate_safe_id(repository_id, "repository_id")
    try:
        res = sync_repository(repository_id)
        return SyncRepositoryResponse(**res)
    except ValueError as ve:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(ve)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Incremental sync failed: {str(e)}"
        )


@router.get("/api/repositories/{repository_id}/history", response_model=List[IndexingHistoryItem], tags=["Repositories"])
def get_repository_history(repository_id: str):
    """Fetch persistent indexing history for a specific repository."""
    validate_safe_id(repository_id, "repository_id")
    history = get_indexing_history(repository_id)
    return [IndexingHistoryItem(**h) for h in history]


@router.get("/api/history", response_model=List[IndexingHistoryItem], tags=["Repositories"])
def get_all_indexing_history():
    """Fetch global indexing history across all repositories."""
    history = get_indexing_history()
    return [IndexingHistoryItem(**h) for h in history]


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
def search_chunks(request: SearchRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Execute BM25, Dense, or Hybrid search across indexed code chunks."""
    service = RetrievalService.get_instance()
    try:
        if user:
            record_search_for_user(user["user_id"], request.query, request.mode)
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
def query_knowledge_assistant(request: QueryRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Ask a natural-language question and receive an evidence-grounded answer with source citations."""
    service = RetrievalService.get_instance()
    try:
        if user:
            record_search_for_user(user["user_id"], request.question, request.mode)
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


@router.get("/api/repositories/{repository_id}/symbols/{symbol_name}", response_model=SymbolRelationshipsResponse, tags=["Symbols"])
def get_symbol_relationships(repository_id: str, symbol_name: str):
    """Fetch complete static symbol relationships including definitions, callers, callees, inheritance, and tests."""
    validate_safe_id(repository_id, "repository_id")
    service = RetrievalService.get_instance()
    res = service.get_symbol_relationships(symbol_name=symbol_name, repo_id=repository_id)
    return SymbolRelationshipsResponse(**res)


@router.post("/api/feedback", response_model=FeedbackResponse, tags=["Feedback"])
def submit_feedback(request: FeedbackRequest, user: Optional[Dict[str, Any]] = Depends(get_current_user_optional)):
    """Submit user feedback on answer accuracy, citations, and relevance."""
    feedback_file = DATA / "reports" / "feedback.jsonl"
    feedback_file.parent.mkdir(parents=True, exist_ok=True)
    feedback_id = f"fb_{uuid.uuid4().hex[:8]}"
    entry = {
        "feedback_id": feedback_id,
        "user_id": user["user_id"] if user else "anonymous",
        "query_or_question": request.query_or_question,
        "feedback_type": request.feedback_type,
        "citation": request.citation,
        "notes": request.notes,
        "repo_id": request.repo_id,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    with open(feedback_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")
    return FeedbackResponse(
        status="received",
        feedback_id=feedback_id,
        message=f"Thank you for your feedback ({request.feedback_type})."
    )
