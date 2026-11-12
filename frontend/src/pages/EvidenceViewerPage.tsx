import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import { ChunkDetail } from '../types/api';
import { CodeViewer } from '../components/CodeViewer';
import {
  FileCode,
  FolderGit2,
  Tag,
  Layers,
  ArrowLeft,
  MessageSquare,
  Sparkles,
  RefreshCw,
  Hash
} from 'lucide-react';

export const EvidenceViewerPage: React.FC = () => {
  const { repoId, chunkId } = useParams<{ repoId: string; chunkId: string }>();
  const [chunk, setChunk] = useState<ChunkDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!repoId || !chunkId) return;

    setLoading(true);
    setError(null);
    api.getChunkDetail(repoId, chunkId)
      .then(setChunk)
      .catch((err) => {
        console.error("Failed to load chunk detail:", err);
        setError(err?.response?.data?.detail || "Chunk not found.");
      })
      .finally(() => setLoading(false));
  }, [repoId, chunkId]);

  if (loading) {
    return (
      <div className="py-24 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
        <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
        <span>Loading chunk details from AST repository index...</span>
      </div>
    );
  }

  if (error || !chunk) {
    return (
      <div className="py-16 max-w-xl mx-auto text-center space-y-4">
        <div className="p-6 rounded-2xl border border-rose-900/60 bg-rose-950/20 text-rose-300">
          <h2 className="text-lg font-bold mb-1">Failed to Load Chunk</h2>
          <p className="text-xs font-mono">{error || "Chunk could not be resolved."}</p>
        </div>
        <Link
          to="/search"
          className="inline-flex items-center gap-1.5 px-4 py-2 rounded-xl bg-slate-900 border border-slate-800 text-xs text-slate-300 hover:text-white"
        >
          <ArrowLeft className="w-4 h-4" /> Back to Search
        </Link>
      </div>
    );
  }

  return (
    <div className="space-y-6 py-6">
      {/* Top Navigation */}
      <div className="flex items-center justify-between gap-4">
        <Link
          to={`/repositories?repo=${encodeURIComponent(chunk.repo_id)}`}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white transition-colors"
        >
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Repository
        </Link>

        <Link
          to={`/assistant?repo=${encodeURIComponent(chunk.repo_id)}`}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-xs font-medium text-white transition-colors shadow-sm"
        >
          <MessageSquare className="w-3.5 h-3.5" /> Ask Assistant About This Code
        </Link>
      </div>

      {/* Header Info Card */}
      <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/60 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
          <div>
            <div className="flex items-center gap-2 text-xs font-mono text-indigo-400 uppercase tracking-wider mb-1">
              <Layers className="w-3.5 h-3.5" />
              <span>{chunk.chunk_type}</span>
            </div>
            <h1 className="text-2xl font-bold text-white font-mono">
              {chunk.chunk_name}
            </h1>
          </div>

          <div className="text-right">
            <span className="text-xs font-mono px-2.5 py-1 rounded bg-slate-800 text-slate-300 border border-slate-700">
              Lines {chunk.start_line} – {chunk.end_line}
            </span>
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-4 text-xs font-mono text-slate-400 pt-3 border-t border-slate-800/60">
          <span className="flex items-center gap-1.5">
            <FolderGit2 className="w-3.5 h-3.5 text-slate-500" />
            Repository: <strong className="text-slate-200">{chunk.repo_id}</strong>
          </span>
          <span>•</span>
          <span className="flex items-center gap-1.5">
            <FileCode className="w-3.5 h-3.5 text-slate-500" />
            File: <strong className="text-slate-200">{chunk.file_path}</strong>
          </span>
          <span>•</span>
          <span>Language: <strong className="text-slate-200">{chunk.language}</strong></span>
          <span>•</span>
          <span>Chunk ID: <strong className="text-slate-400">{chunk.chunk_id}</strong></span>
        </div>

        {/* Symbols & Imports Chips */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 pt-3 border-t border-slate-800/60 text-xs">
          {/* Symbols Defined */}
          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/60">
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2">
              Symbols Defined ({chunk.symbols_defined?.length || 0}):
            </div>
            <div className="flex flex-wrap gap-1">
              {chunk.symbols_defined && chunk.symbols_defined.length > 0 ? (
                chunk.symbols_defined.map((s, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-mono text-[11px]">
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-slate-600 font-mono text-[11px]">None detected</span>
              )}
            </div>
          </div>

          {/* Symbols Used */}
          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/60">
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2">
              Symbols Used ({chunk.symbols_used?.length || 0}):
            </div>
            <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
              {chunk.symbols_used && chunk.symbols_used.length > 0 ? (
                chunk.symbols_used.slice(0, 15).map((s, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono text-[11px]">
                    {s}
                  </span>
                ))
              ) : (
                <span className="text-slate-600 font-mono text-[11px]">None detected</span>
              )}
            </div>
          </div>

          {/* Imports */}
          <div className="p-3 rounded-xl bg-slate-950/70 border border-slate-800/60">
            <div className="text-[11px] font-mono uppercase tracking-wider text-slate-400 font-semibold mb-2">
              Imports ({chunk.imports?.length || 0}):
            </div>
            <div className="flex flex-wrap gap-1 max-h-24 overflow-y-auto">
              {chunk.imports && chunk.imports.length > 0 ? (
                chunk.imports.map((imp, i) => (
                  <span key={i} className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-[11px]">
                    {imp}
                  </span>
                ))
              ) : (
                <span className="text-slate-600 font-mono text-[11px]">No external imports</span>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Full Source Code */}
      <div className="space-y-2">
        <h2 className="text-base font-semibold text-white">
          Full AST Code Implementation
        </h2>
        <CodeViewer
          code={chunk.code_text}
          language={chunk.language}
          filePath={chunk.file_path}
          startLine={chunk.start_line}
          endLine={chunk.end_line}
          title={chunk.chunk_name}
        />
      </div>
    </div>
  );
};
