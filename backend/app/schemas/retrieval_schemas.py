from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    version: str = "4.0.0"
    repositories_count: int
    bm25_index_ready: bool
    dense_index_ready: bool


class RepositoryInfo(BaseModel):
    repo_id: str
    full_name: str
    language: Optional[str] = None
    stars: Optional[int] = None
    license_spdx_id: Optional[str] = None
    default_branch: Optional[str] = None
    clone_status: Optional[str] = None
    chunk_count: int = 0


class AddRepositoryRequest(BaseModel):
    url: str = Field(..., min_length=3, description="GitHub repository URL (e.g. https://github.com/owner/repo) or 'owner/repo'")
    max_chunks: Optional[int] = Field(default=500, ge=10, le=5000, description="Max chunks to extract")


class AddRepositoryResponse(BaseModel):
    status: str
    repo_id: str
    full_name: str
    commit_sha: str
    default_branch: str
    language: Optional[str] = None
    stars: Optional[int] = 0
    chunks_extracted: int
    bm25_indexed: int
    dense_indexed: int
    message: str


class SyncRepositoryResponse(BaseModel):
    status: str
    repo_id: str
    previous_commit: str
    current_commit: str
    files_added: List[str] = []
    files_modified: List[str] = []
    files_deleted: List[str] = []
    chunks_added: int = 0
    chunks_removed: int = 0
    duration_seconds: float = 0.0
    message: str


class IndexingHistoryItem(BaseModel):
    history_id: str
    repo_id: str
    previous_commit: str
    current_commit: str
    files_added: List[str] = []
    files_modified: List[str] = []
    files_deleted: List[str] = []
    chunks_added: int = 0
    chunks_removed: int = 0
    duration_seconds: float = 0.0
    timestamp: str
    status: str


class UserProfile(BaseModel):
    user_id: str
    username: str
    email: str
    saved_repositories: List[str] = []
    search_history: List[Dict[str, Any]] = []


class AuthResponse(BaseModel):
    token: str
    user: UserProfile


class RegisterRequest(BaseModel):
    username: str = Field(..., min_length=3, max_length=30)
    email: str = Field(..., min_length=5)
    password: str = Field(..., min_length=6)


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class SaveRepoRequest(BaseModel):
    repo_id: str


class RecordSearchRequest(BaseModel):
    query: str
    mode: str = "hybrid"


class IndexRequest(BaseModel):
    repo_ids: Optional[List[str]] = None
    max_chunks: Optional[int] = Field(default=None, description="Max chunks to index")


class IndexResponse(BaseModel):
    status: str
    bm25_indexed_chunks: int
    dense_indexed_chunks: int
    message: str


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Search query string")
    top_k: int = Field(default=10, ge=1, le=50)
    mode: str = Field(default="hybrid", pattern="^(hybrid|bm25|dense)$")
    repo_id: Optional[str] = None


class EvidenceItemSchema(BaseModel):
    citation: Optional[str] = None
    repo_id: str
    file_path: str
    start_line: int
    end_line: int
    chunk_name: str
    chunk_type: str
    score: float = 0.0
    code_snippet: Optional[str] = ""
    language: Optional[str] = None
    match_classification: Optional[str] = "related_context"


class SearchResponse(BaseModel):
    query: str
    retrieval_method: str
    total_results: int
    results: List[EvidenceItemSchema]


class QueryRequest(BaseModel):
    question: str = Field(..., min_length=1, description="Natural language question about repository")
    top_k: int = Field(default=5, ge=1, le=20)
    mode: str = Field(default="hybrid", pattern="^(hybrid|bm25|dense)$")
    repo_id: Optional[str] = None


class QueryResponse(BaseModel):
    question: str
    answer: str
    is_answered: bool
    confidence_indicator: str
    retrieval_method: str
    evidence: List[EvidenceItemSchema]
    citations: List[str]
    match_classification: Optional[str] = None


class FileInfo(BaseModel):
    file_path: str
    repo_id: str
    chunk_count: int
    language: Optional[str] = None


class ChunkDetailResponse(BaseModel):
    chunk_id: str
    repo_id: str
    file_path: str
    start_line: int
    end_line: int
    chunk_type: str
    chunk_name: str
    language: str
    code_text: str
    imports: List[str] = []
    symbols_defined: List[str] = []
    symbols_used: List[str] = []


class SymbolCallerSchema(BaseModel):
    chunk_id: str
    caller_name: str
    caller_type: str
    file_path: str
    lines: str
    verification: str


class SymbolCalleeSchema(BaseModel):
    symbol_name: str
    verification: str


class SymbolTestSchema(BaseModel):
    chunk_id: str
    test_name: str
    file_path: str
    lines: str
    verification: str


class SymbolInheritanceSchema(BaseModel):
    base_classes: List[str] = []
    subclasses: List[str] = []


class SymbolRelationshipsResponse(BaseModel):
    symbol_name: str
    is_defined: bool
    definitions_count: int
    definitions: List[Dict[str, Any]] = []
    callers: List[SymbolCallerSchema] = []
    callees: List[SymbolCalleeSchema] = []
    inheritance: SymbolInheritanceSchema = Field(default_factory=SymbolInheritanceSchema)
    related_tests: List[SymbolTestSchema] = []
    file_dependencies: List[str] = []


class FeedbackRequest(BaseModel):
    query_or_question: str
    feedback_type: str = Field(..., pattern="^(helpful|not_helpful|incorrect_citation|missing_context)$")
    citation: Optional[str] = None
    notes: Optional[str] = None
    repo_id: Optional[str] = None


class FeedbackResponse(BaseModel):
    status: str = "received"
    feedback_id: str
    message: str
