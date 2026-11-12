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
