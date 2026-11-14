import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
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
  Hash,
  ChevronDown,
  X,
  Copy,
  Check
} from 'lucide-react';

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
  const [selectedItem, setSelectedItem] = useState<EvidenceItem | null>(null);

  useEffect(() => {
    api.listRepositories()
      .then(setRepos)
      .catch((err) => console.error('Failed to load repositories:', err));

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
      if (res.results && res.results.length > 0) {
        setSelectedItem(res.results[0]);
      } else {
        setSelectedItem(null);
      }
    } catch (err) {
      console.error('Search failed:', err);
      setResults([]);
      setSelectedItem(null);
    } finally {
      setLoading(false);
    }
  };

  const handleFormSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    executeSearch();
  };

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* 1. Header & Controls Card */}
      <div className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <Search className="w-5 h-5 text-indigo-500" />
            <span>Code Search</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Search symbols, functions, classes, and logic across AST chunks with lexical or semantic modes.
          </p>
        </div>

        {/* Search Input Bar */}
        <form onSubmit={handleFormSubmit} className="space-y-3">
          <div className="relative">
            <input
              type="text"
              placeholder="Search code identifiers, function names, classes (e.g. check_auth, validate_format)..."
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-full pl-11 pr-24 py-3 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 placeholder-slate-400 text-sm focus:outline-none focus:border-indigo-500 transition-colors"
            />
            <Search className="w-4 h-4 text-slate-400 absolute left-4 top-3.5" />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="absolute right-2 top-2 px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-xs transition-colors shadow-xs"
            >
              Search
            </button>
          </div>

          {/* Filters Bar */}
          <div className="flex flex-wrap items-center justify-between gap-3 pt-1">
            <div className="flex flex-wrap items-center gap-3">
              {/* Repository Selector */}
              <div className="relative">
                <select
                  value={selectedRepo}
                  onChange={(e) => setSelectedRepo(e.target.value)}
                  className="text-xs font-medium pl-3 pr-8 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-700 dark:text-slate-300 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer appearance-none"
                >
                  <option value="">All Repositories ({repos.length})</option>
                  {repos.map((r) => (
                    <option key={r.repo_id} value={r.repo_id}>
                      {r.full_name || r.repo_id}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
              </div>

              {/* Mode Toggle */}
              <div className="flex items-center p-0.5 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs">
                <button
                  type="button"
                  onClick={() => setMode('hybrid')}
                  className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                    mode === 'hybrid'
                      ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  Hybrid RRF
                </button>
                <button
                  type="button"
                  onClick={() => setMode('bm25')}
                  className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                    mode === 'bm25'
                      ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  BM25 Lexical
                </button>
                <button
                  type="button"
                  onClick={() => setMode('dense')}
                  className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                    mode === 'dense'
                      ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                      : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                  }`}
                >
                  Dense Semantic
                </button>
              </div>
            </div>

            {/* Quick Count Pill */}
            {hasSearched && !loading && (
              <span className="text-xs font-mono text-slate-500 dark:text-slate-400">
                {results.length} results found
              </span>
            )}
          </div>
        </form>
      </div>

      {/* 2. Results Layout */}
      {loading ? (
        <div className="p-12 text-center rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin mx-auto" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
            Searching Code Chunks...
          </h3>
          <p className="text-xs text-slate-400">
            Computing lexical token scores and 256-dimensional Transformer similarity...
          </p>
        </div>
      ) : hasSearched && results.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
          <FileCode className="w-10 h-10 text-slate-300 dark:text-slate-700 mx-auto" />
          <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
            No matching code found
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Try adjusting your search terms, removing repository filters, or switching to Hybrid mode.
          </p>
        </div>
      ) : hasSearched ? (
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">
          {/* Results List (Left 6 cols on large screens) */}
          <div className="lg:col-span-6 space-y-3">
            {results.map((item, idx) => {
              const isSelected = selectedItem === item;
              return (
                <div
                  key={idx}
                  onClick={() => setSelectedItem(item)}
                  className={`p-4 rounded-2xl border transition-all cursor-pointer shadow-xs space-y-3 ${
                    isSelected
                      ? 'border-indigo-400 dark:border-indigo-500/80 bg-indigo-50/40 dark:bg-indigo-950/20'
                      : 'border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-slate-300 dark:hover:border-slate-700'
                  }`}
                >
                  {/* File & Line header */}
                  <div className="flex items-start justify-between gap-2">
                    <div className="truncate">
                      <div className="flex items-center gap-1.5 text-xs font-mono font-semibold text-slate-900 dark:text-white truncate">
                        <FileCode className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                        <span className="truncate">{item.file_path}</span>
                      </div>
                      <span className="text-[11px] font-mono text-slate-400">
                        Lines {item.start_line}–{item.end_line} • {item.repo_id}
                      </span>
                    </div>

                    <div className="flex items-center gap-1.5 shrink-0">
                      <ClassificationBadge classification={item.match_classification} />
                      <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300">
                        #{idx + 1}
                      </span>
                    </div>
                  </div>

                  {/* Defined symbol badge */}
                  <div className="flex items-center gap-2">
                    <span className="px-2 py-0.5 rounded text-[11px] font-mono font-medium bg-indigo-50 dark:bg-indigo-950 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800">
                      {item.chunk_name} ({item.chunk_type})
                    </span>
                  </div>

                  {/* Code snippet preview (few lines) */}
                  <pre className="p-2.5 rounded-xl bg-slate-900 dark:bg-slate-950 text-slate-200 text-xs font-mono overflow-x-auto max-h-24">
                    <code>{item.code_snippet?.slice(0, 200)}...</code>
                  </pre>
                </div>
              );
            })}
          </div>

          {/* Code Viewer Panel (Right 6 cols sticky) */}
          <div className="hidden lg:block lg:col-span-6 sticky top-20 max-h-[calc(100vh-8rem)] overflow-y-auto space-y-4">
            {selectedItem ? (
              <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-3">
                <div className="flex items-center justify-between pb-3 border-b border-slate-100 dark:border-slate-800">
                  <div className="truncate">
                    <h3 className="text-sm font-bold text-slate-900 dark:text-white truncate">
                      {selectedItem.chunk_name}
                    </h3>
                    <span className="text-xs font-mono text-slate-400 truncate block">
                      {selectedItem.file_path}
                    </span>
                  </div>
                  <ClassificationBadge classification={selectedItem.match_classification} />
                </div>

                <CodeViewer
                  code={selectedItem.code_snippet || ''}
                  language={selectedItem.language || 'python'}
                  filePath={selectedItem.file_path}
                  startLine={selectedItem.start_line}
                  endLine={selectedItem.end_line}
                />
              </div>
            ) : null}
          </div>
        </div>
      ) : (
        /* Starter State */
        <div className="p-12 text-center rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
          <Sparkles className="w-8 h-8 text-indigo-500 mx-auto" />
          <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
            Enter a search term above
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            Search for any function, class, or identifier across all indexed repositories using BM25, dense embeddings, or combined hybrid retrieval.
          </p>
        </div>
      )}
    </div>
  );
};
