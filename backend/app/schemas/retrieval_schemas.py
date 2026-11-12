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
