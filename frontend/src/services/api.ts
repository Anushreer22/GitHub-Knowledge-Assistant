import axios from 'axios';
import {
  HealthResponse,
  RepositoryInfo,
  FileInfo,
  ChunkDetail,
  SearchResponse,
  QueryResponse,
  IndexResponse
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

export const api = {
  async getHealth(): Promise<HealthResponse> {
    const res = await client.get<HealthResponse>('/health');
    return res.data;
  },

  async listRepositories(): Promise<RepositoryInfo[]> {
    const res = await client.get<RepositoryInfo[]>('/api/repositories');
    return res.data;
  },

  async listRepositoryFiles(repoId: string): Promise<FileInfo[]> {
    const res = await client.get<FileInfo[]>(`/api/repositories/${encodeURIComponent(repoId)}/files`);
    return res.data;
  },

  async getChunkDetail(repoId: string, chunkId: string): Promise<ChunkDetail> {
    const res = await client.get<ChunkDetail>(
      `/api/repositories/${encodeURIComponent(repoId)}/chunks/${encodeURIComponent(chunkId)}`
    );
    return res.data;
  },

  async search(params: {
    query: string;
    top_k?: number;
    mode?: 'hybrid' | 'bm25' | 'dense';
    repo_id?: string | null;
  }): Promise<SearchResponse> {
    const res = await client.post<SearchResponse>('/api/search', {
      query: params.query,
      top_k: params.top_k ?? 10,
      mode: params.mode ?? 'hybrid',
      repo_id: params.repo_id || undefined,
    });
    return res.data;
  },

  async queryQA(params: {
    question: string;
    top_k?: number;
    mode?: 'hybrid' | 'bm25' | 'dense';
    repo_id?: string | null;
  }): Promise<QueryResponse> {
    const res = await client.post<QueryResponse>('/api/query', {
      question: params.question,
      top_k: params.top_k ?? 5,
      mode: params.mode ?? 'hybrid',
      repo_id: params.repo_id || undefined,
    });
    return res.data;
  },

  async triggerIndexing(maxChunks?: number): Promise<IndexResponse> {
    const res = await client.post<IndexResponse>('/api/repositories/index', {
      max_chunks: maxChunks,
    });
    return res.data;
  },
};
