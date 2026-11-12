export interface HealthResponse {
  status: string;
  version: string;
  repositories_count: number;
  bm25_index_ready: boolean;
  dense_index_ready: boolean;
}

export interface RepositoryInfo {
  repo_id: string;
  full_name: string;
  language?: string | null;
  stars?: number | null;
  license_spdx_id?: string | null;
  default_branch?: string | null;
  clone_status?: string | null;
  chunk_count: number;
}

export interface FileInfo {
  file_path: string;
  repo_id: string;
  chunk_count: number;
  language?: string | null;
}

export interface ChunkDetail {
  chunk_id: string;
  repo_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  chunk_type: string;
  chunk_name: string;
  language: string;
  code_text: string;
  imports: string[];
  symbols_defined: string[];
  symbols_used: string[];
}

export type MatchClassification =
  | 'exact_match'
  | 'strong_semantic_match'
  | 'related_context'
  | 'insufficient_evidence';

export type ConfidenceIndicator =
  | 'high'
  | 'medium'
  | 'low'
  | 'insufficient_evidence';

export interface EvidenceItem {
  citation?: string;
  repo_id: string;
  file_path: string;
  start_line: number;
  end_line: number;
  chunk_name: string;
  chunk_type: string;
  score: number;
  code_snippet?: string;
  language?: string | null;
  match_classification?: MatchClassification;
  chunk_id?: string;
}

export interface SearchResponse {
  query: string;
  retrieval_method: string;
  total_results: number;
  results: EvidenceItem[];
}

export interface QueryResponse {
  question: string;
  answer: string;
  is_answered: boolean;
  confidence_indicator: ConfidenceIndicator;
  retrieval_method: string;
  evidence: EvidenceItem[];
  citations: string[];
  match_classification?: MatchClassification;
}

export interface IndexResponse {
  status: string;
  bm25_indexed_chunks: number;
  dense_indexed_chunks: number;
  message: string;
}

export interface AddRepositoryResponse {
  status: string;
  repo_id: string;
  full_name: string;
  commit_sha: string;
  default_branch: string;
  language?: string | null;
  stars?: number;
  chunks_extracted: number;
  bm25_indexed: number;
  dense_indexed: number;
  message: string;
}

export interface SyncRepositoryResponse {
  status: string;
  repo_id: string;
  previous_commit: string;
  current_commit: string;
  files_added: string[];
  files_modified: string[];
  files_deleted: string[];
  chunks_added: number;
  chunks_removed: number;
  duration_seconds: number;
  message: string;
}

export interface IndexingHistoryItem {
  history_id: string;
  repo_id: string;
  previous_commit: string;
  current_commit: string;
  files_added: string[];
  files_modified: string[];
  files_deleted: string[];
  chunks_added: number;
  chunks_removed: number;
  duration_seconds: number;
  timestamp: string;
  status: string;
}

export interface UserProfile {
  user_id: string;
  username: string;
  email: string;
  saved_repositories: string[];
  search_history: Array<{ query: string; mode: string; timestamp: string }>;
}

export interface AuthResponse {
  token: string;
  user: UserProfile;
}

export interface SymbolCaller {
  chunk_id: string;
  caller_name: string;
  caller_type: string;
  file_path: string;
  lines: string;
  verification: string;
}

export interface SymbolCallee {
  symbol_name: string;
  verification: string;
}

export interface SymbolTest {
  chunk_id: string;
  test_name: string;
  file_path: string;
  lines: string;
  verification: string;
}

export interface SymbolRelationships {
  symbol_name: string;
  is_defined: boolean;
  definitions_count: number;
  definitions: Array<{
    chunk_id: string;
    repo_id: string;
    file_path: string;
    chunk_name: string;
    chunk_type: string;
    start_line: number;
    end_line: number;
  }>;
  callers: SymbolCaller[];
  callees: SymbolCallee[];
  inheritance: {
    base_classes: string[];
    subclasses: string[];
  };
  related_tests: SymbolTest[];
  file_dependencies: string[];
}

export interface FeedbackPayload {
  query_or_question: string;
  feedback_type: 'helpful' | 'not_helpful' | 'incorrect_citation' | 'missing_context';
  citation?: string;
  notes?: string;
  repo_id?: string;
}
