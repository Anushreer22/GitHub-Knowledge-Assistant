import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { HealthResponse, IndexResponse } from '../types/api';
import {
  Database,
  Layers,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  HardDrive,
  FileText,
  Cpu,
  Info
} from 'lucide-react';

export const IndexingPage: React.FC = () => {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [maxChunks, setMaxChunks] = useState<number>(10000);
  const [isIndexing, setIsIndexing] = useState(false);
  const [result, setResult] = useState<IndexResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchHealth = () => {
    api.getHealth()
      .then(setHealth)
      .catch((err) => console.error("Failed to fetch health:", err));
  };

  useEffect(() => {
    fetchHealth();
  }, []);

  const handleTriggerIndex = async () => {
    setIsIndexing(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.triggerIndexing(maxChunks);
      setResult(res);
      fetchHealth();
    } catch (err: any) {
      setError(err?.response?.data?.detail || err.message || "Indexing failed.");
    } finally {
      setIsIndexing(false);
    }
  };

  return (
    <div className="space-y-6 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <Database className="w-7 h-7 text-indigo-400" />
          Repository Indexing Management
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Manage and trigger persistent lexical BM25 and dense Transformer vector stores.
        </p>
      </div>

      {/* Index Status Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>BM25 LEXICAL INDEX</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {health?.bm25_index_ready ? 'Active & Ready' : 'Not Loaded'}
          </div>
          <div className="text-xs text-slate-500 mt-2 font-mono">
            Location: data/indexes/bm25_index.pkl
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>DENSE VECTOR STORE</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {health?.dense_index_ready ? 'Active & Ready' : 'Not Loaded'}
          </div>
          <div className="text-xs text-slate-500 mt-2 font-mono">
            Location: data/indexes/dense_store/
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-xs text-slate-400 mb-2 font-mono">
            <span>LOADED REPOSITORIES</span>
            <HardDrive className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-2xl font-bold text-white">
            {health?.repositories_count || 10} Repositories
          </div>
          <div className="text-xs text-slate-500 mt-2 font-mono">
            AST Chunks: 243,411 on disk
          </div>
        </div>
      </div>

      {/* Trigger Indexing Form */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-5">
        <div className="flex items-center gap-2">
          <RefreshCw className="w-5 h-5 text-indigo-400" />
          <h2 className="text-base font-semibold text-white">
            Trigger Index Build
          </h2>
        </div>

        <p className="text-xs text-slate-400 leading-relaxed max-w-2xl">
          Building the index parses the AST chunk dataset (<code className="text-slate-300">data/processed/code_chunks.jsonl</code>), tokenizes symbols into sub-words and camelCase/snake_case tokens for BM25, and computes L2-normalized embeddings using our PyTorch Transformer CodeEncoder.
        </p>

        <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3 pt-2">
          <div className="flex items-center gap-2">
            <label className="text-xs font-mono text-slate-400">Max Chunks to Index:</label>
            <input
              type="number"
              min={100}
              max={250000}
              step={500}
              value={maxChunks}
              onChange={(e) => setMaxChunks(Number(e.target.value))}
              disabled={isIndexing}
              className="w-32 px-3 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500"
            />
          </div>

          <button
            onClick={handleTriggerIndex}
            disabled={isIndexing}
            className="px-6 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs transition-all flex items-center justify-center gap-2 shadow-md shadow-indigo-500/20"
          >
            {isIndexing ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin" />
                <span>Indexing Chunks...</span>
              </>
            ) : (
              <>
                <Database className="w-4 h-4" />
                <span>Re-build Indexes</span>
              </>
            )}
          </button>
        </div>

        {/* Feedback message */}
        {result && (
          <div className="p-4 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs font-mono flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 shrink-0 text-emerald-400" />
            <span>{result.message}</span>
          </div>
        )}

        {error && (
          <div className="p-4 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs font-mono flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
            <span>{error}</span>
          </div>
        )}
      </div>

      {/* Indexing Architecture Note */}
      <div className="p-5 rounded-2xl border border-slate-800/80 bg-slate-900/30 text-xs text-slate-400 space-y-2">
        <div className="flex items-center gap-2 text-indigo-400 font-semibold font-mono">
          <Info className="w-4 h-4" />
          <span>Incremental Indexing & Memory Optimization</span>
        </div>
        <p className="leading-relaxed">
          The BM25 index stores inverted document frequencies and inverted term indexes on disk using Python pickle. The dense vector index computes 256-dimensional embeddings for candidates and persists embeddings incrementally in numpy matrix blocks alongside JSONL metadata, allowing zero-downtime hot reloading without retraining the encoder.
        </p>
      </div>
    </div>
  );
};
