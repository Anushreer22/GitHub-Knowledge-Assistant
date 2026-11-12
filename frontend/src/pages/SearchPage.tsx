import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { SearchResponse, EvidenceItem, RepositoryInfo } from '../types/api';
import { ClassificationBadge } from '../components/ClassificationBadge';
import { CodeViewer } from '../components/CodeViewer';
import {
  Search,
  Filter,
  Layers,
  FileCode,
  ArrowRight,
  ExternalLink,
  Sparkles,
  RefreshCw,
  Hash
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const SearchPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialQuery = searchParams.get('q') || '';
  const initialRepo = searchParams.get('repo') || '';

  const [query, setQuery] = useState(initialQuery);
  const [selectedRepo, setSelectedRepo] = useState(initialRepo);
  const [mode, setMode] = useState<'hybrid' | 'bm25' | 'dense'>('hybrid');
  const [topK, setTopK] = useState(10);
  const [repos, setRepos] = useState<RepositoryInfo[]>([]);

  const [results, setResults] = useState<EvidenceItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [hasSearched, setHasSearched] = useState(false);

  useEffect(() => {
    api.listRepositories()
      .then(setRepos)
      .catch((err) => console.error("Failed to load repositories:", err));

    if (initialQuery) {
      executeSearch(initialQuery, initialRepo, 'hybrid', 10);
    }
  }, []);

  const executeSearch = async (
    qText = query,
    rId = selectedRepo,
    searchMode = mode,
    k = topK
  ) => {
    const cleanQ = qText.trim();
    if (!cleanQ) return;

    setLoading(true);
    setHasSearched(true);
    setSearchParams({ q: cleanQ, ...(rId ? { repo: rId } : {}) });

    try {
      const res = await api.search({
        query: cleanQ,
        mode: searchMode,
        repo_id: rId || null,
        top_k: k
      });
      setResults(res.results || []);
    } catch (err) {
      console.error("Search failed:", err);
      setResults([]);
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch();
  };

  return (
    <div className="space-y-6 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
          <Search className="w-7 h-7 text-indigo-400" />
          Code Search Explorer
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          Perform high-precision BM25 lexical, dense semantic, or fused hybrid search across 243,411 AST chunks.
        </p>
      </div>

      {/* Search Bar & Filters Form */}
      <div className="p-4 sm:p-5 rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl space-y-4">
        <form onSubmit={handleFormSubmit} className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search symbols, identifiers, function names, classes (e.g. check_auth, Singleton)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors font-mono"
            />
          </div>

          <button
            type="submit"
            disabled={loading || !query.trim()}
            className="px-6 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-all flex items-center justify-center gap-2 shadow-md shadow-indigo-500/20 shrink-0"
          >
            {loading ? <RefreshCw className="w-4 h-4 animate-spin" /> : <Search className="w-4 h-4" />}
            Search
          </button>
        </form>

        {/* Filter controls */}
        <div className="flex flex-wrap items-center justify-between gap-3 text-xs pt-3 border-t border-slate-800/80">
          <div className="flex items-center gap-4 flex-wrap">
            {/* Repo selector */}
            <div className="flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-400" />
              <select
                value={selectedRepo}
                onChange={(e) => setSelectedRepo(e.target.value)}
                className="px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-xs"
              >
                <option value="">All Repositories</option>
                {repos.map(r => (
                  <option key={r.repo_id} value={r.repo_id}>
                    {r.full_name || r.repo_id}
                  </option>
                ))}
              </select>
            </div>

            {/* Mode selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-mono">Mode:</span>
              <div className="flex items-center p-0.5 rounded-lg bg-slate-950 border border-slate-800 font-mono">
                {(['hybrid', 'bm25', 'dense'] as const).map(m => (
                  <button
                    key={m}
                    type="button"
                    onClick={() => setMode(m)}
                    className={`px-2.5 py-1 rounded-md text-[11px] font-medium uppercase transition-colors ${
                      mode === m
                        ? 'bg-indigo-600 text-white shadow-sm'
                        : 'text-slate-400 hover:text-slate-200'
                    }`}
                  >
                    {m}
                  </button>
                ))}
              </div>
            </div>

            {/* Top-K selector */}
            <div className="flex items-center gap-1.5">
              <span className="text-slate-500 font-mono">Top-K:</span>
              <select
                value={topK}
                onChange={(e) => setTopK(Number(e.target.value))}
                className="px-2 py-1 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-xs"
              >
                <option value={5}>5</option>
                <option value={10}>10</option>
                <option value={20}>20</option>
              </select>
            </div>
          </div>

          <div className="text-slate-500 font-mono text-[11px]">
            {results.length > 0 && `${results.length} results returned`}
          </div>
        </div>
      </div>

      {/* Results List */}
      <div className="space-y-4">
        {loading ? (
          <div className="py-16 text-center text-slate-400 text-sm flex items-center justify-center gap-2">
            <RefreshCw className="w-5 h-5 text-indigo-400 animate-spin" />
            <span>Searching indexed code chunks...</span>
          </div>
        ) : hasSearched && results.length === 0 ? (
          <div className="py-16 text-center text-slate-500 text-sm rounded-2xl border border-slate-800 bg-slate-900/30">
            No matching code chunks found for "{query}".
          </div>
        ) : (
          results.map((item, idx) => (
            <div
              key={idx}
              className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60 hover:bg-slate-850/80 transition-all space-y-3"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center gap-2 flex-wrap text-xs">
                  <span className="w-6 h-6 rounded-full bg-slate-800 text-slate-300 flex items-center justify-center font-mono font-semibold text-xs">
                    #{idx + 1}
                  </span>
                  <span className="font-bold text-white font-mono text-sm">
                    {item.chunk_name}
                  </span>
                  <span className="px-2 py-0.5 rounded text-[10px] uppercase font-mono bg-slate-800 text-slate-400">
                    {item.chunk_type}
                  </span>
                  <ClassificationBadge classification={item.match_classification} />
                </div>

                <div className="flex items-center gap-3 text-xs font-mono">
                  <span className="text-slate-500">
                    Score: <strong className="text-indigo-300">{item.score.toFixed(4)}</strong>
                  </span>
                  {item.chunk_id && (
                    <Link
                      to={`/evidence/${encodeURIComponent(item.repo_id)}/${encodeURIComponent(item.chunk_id)}`}
                      className="inline-flex items-center gap-1 text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
                    >
                      Inspect Chunk <ExternalLink className="w-3 h-3" />
                    </Link>
                  )}
                </div>
              </div>

              <div className="flex items-center gap-2 text-xs text-slate-400 font-mono">
                <FileCode className="w-3.5 h-3.5 text-indigo-400 shrink-0" />
                <span className="text-slate-500">{item.repo_id} /</span>
                <span className="text-slate-300">{item.file_path}</span>
                <span className="text-slate-500">:L{item.start_line}-L{item.end_line}</span>
              </div>

              {item.code_snippet && (
                <div className="pt-1">
                  <CodeViewer
                    code={item.code_snippet}
                    language={item.language || 'python'}
                    filePath={item.file_path}
                    startLine={item.start_line}
                    endLine={item.end_line}
                    title={item.chunk_name}
                  />
                </div>
              )}
            </div>
          ))
        )}
      </div>
    </div>
  );
};
