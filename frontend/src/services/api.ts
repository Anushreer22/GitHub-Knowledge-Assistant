import axios from 'axios';
import {
  HealthResponse,
  RepositoryInfo,
  FileInfo,
  ChunkDetail,
  SearchResponse,
  QueryResponse,
  IndexResponse,
  AddRepositoryResponse,
  SyncRepositoryResponse,
  IndexingHistoryItem,
  UserProfile,
  AuthResponse,
  SymbolRelationships,
  FeedbackPayload
} from '../types/api';

const API_BASE = import.meta.env.VITE_API_BASE_URL || '';

const client = axios.create({
  baseURL: API_BASE,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

client.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token && config.headers) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
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

  async addRepository(params: { url: string; max_chunks?: number }): Promise<AddRepositoryResponse> {
    const res = await client.post<AddRepositoryResponse>('/api/repositories/add', {
      url: params.url,
      max_chunks: params.max_chunks ?? 500,
    });
    return res.data;
  },

  async syncRepository(repoId: string): Promise<SyncRepositoryResponse> {
    const res = await client.post<SyncRepositoryResponse>(
      `/api/repositories/${encodeURIComponent(repoId)}/sync`
    );
    return res.data;
  },

  async getRepositoryHistory(repoId: string): Promise<IndexingHistoryItem[]> {
    const res = await client.get<IndexingHistoryItem[]>(
      `/api/repositories/${encodeURIComponent(repoId)}/history`
    );
    return res.data;
  },

  async getAllHistory(): Promise<IndexingHistoryItem[]> {
    const res = await client.get<IndexingHistoryItem[]>('/api/history');
    return res.data;
  },

  async getSymbolRelationships(repoId: string, symbolName: string): Promise<SymbolRelationships> {
    const res = await client.get<SymbolRelationships>(
      `/api/repositories/${encodeURIComponent(repoId)}/symbols/${encodeURIComponent(symbolName)}`
    );
    return res.data;
  },

  async submitFeedback(payload: FeedbackPayload): Promise<{ status: string; feedback_id: string; message: string }> {
    const res = await client.post('/api/feedback', payload);
    return res.data;
  },

  async register(payload: { username: string; email: string; password: string }): Promise<AuthResponse> {
    const res = await client.post<AuthResponse>('/api/auth/register', payload);
    return res.data;
  },

  async login(payload: { username: string; password: string }): Promise<AuthResponse> {
    const res = await client.post<AuthResponse>('/api/auth/login', payload);
    return res.data;
  },

  async getMe(): Promise<UserProfile> {
    const res = await client.get<UserProfile>('/api/auth/me');
    return res.data;
  },

  async getSearchHistory(): Promise<Array<{ query: string; mode: string; timestamp: string }>> {
    const res = await client.get<Array<{ query: string; mode: string; timestamp: string }>>('/api/user/search-history');
    return res.data;
  },
};
