import React, { useEffect, useState } from 'react';
import { Link, useOutletContext } from 'react-router-dom';
import {
  FolderGit2,
  Database,
  Layers,
  Activity,
  PlusCircle,
  MessageSquare,
  ArrowRight,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Star,
  ExternalLink,
  Clock,
  Sparkles,
  GitBranch,
  Search,
  Code
} from 'lucide-react';
import { api } from '../services/api';
import { RepositoryInfo, HealthResponse, IndexingHistoryItem } from '../types/api';

export const DashboardPage: React.FC = () => {
  const context = useOutletContext<{ onOpenAddModal?: () => void }>();

  const [repos, setRepos] = useState<RepositoryInfo[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [history, setHistory] = useState<IndexingHistoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [syncingRepoId, setSyncingRepoId] = useState<string | null>(null);
  const [syncNotice, setSyncNotice] = useState<string | null>(null);

  const fetchData = async () => {
    setLoading(true);
    setError(null);
    try {
      const [reposData, healthData, historyData] = await Promise.all([
        api.listRepositories(),
        api.getHealth().catch(() => null),
        api.getAllHistory().catch(() => [])
      ]);
      setRepos(reposData);
      setHealth(healthData);
      setHistory(historyData);
    } catch (err: any) {
      console.error('Failed to load dashboard data:', err);
      setError('Failed to connect to backend service. Please ensure the server is running.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleSyncRepo = async (repoId: string) => {
    setSyncingRepoId(repoId);
    setSyncNotice(null);
    try {
      const res = await api.syncRepository(repoId);
      setSyncNotice(`Synced ${repoId}: ${res.message}`);
      await fetchData();
    } catch (err: any) {
      setSyncNotice(`Sync failed for ${repoId}: ${err.response?.data?.detail || err.message}`);
    } finally {
      setSyncingRepoId(null);
    }
  };

  // Compute live statistics
  const totalRepos = repos.length;
  const totalChunks = repos.reduce((acc, r) => acc + (r.chunk_count || 0), 0);
  const uniqueLangs = Array.from(
    new Set(repos.map((r) => r.language).filter(Boolean))
  ) as string[];

  const lastSync = history.length > 0 ? history[0] : null;

  return (
    <div className="space-y-8 animate-in fade-in duration-200">
      {/* 1. Welcome Section */}
      <section className="relative overflow-hidden rounded-3xl border border-slate-200 dark:border-slate-800/80 bg-gradient-to-br from-indigo-50/60 via-white to-slate-50 dark:from-indigo-950/20 dark:via-slate-900/40 dark:to-slate-950 p-6 sm:p-8 lg:p-10 shadow-sm">
        <div className="max-w-2xl space-y-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-100 dark:bg-indigo-950/70 border border-indigo-200 dark:border-indigo-800 text-indigo-700 dark:text-indigo-300 text-xs font-medium font-mono">
            <Sparkles className="w-3.5 h-3.5 text-indigo-500" />
            <span>AI-Powered Code Understanding</span>
          </div>

          <h1 className="text-3xl sm:text-4xl font-extrabold text-slate-900 dark:text-white tracking-tight">
            Understand your codebase faster.
          </h1>

          <p className="text-base text-slate-600 dark:text-slate-400 leading-relaxed">
            Ask questions, explore implementations, and discover how your repository works with exact source code citations.
          </p>

          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => context?.onOpenAddModal?.()}
              className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-md shadow-indigo-500/20 flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Add Repository</span>
            </button>

            <Link
              to="/assistant"
              className="px-5 py-2.5 rounded-xl bg-white dark:bg-slate-900 hover:bg-slate-100 dark:hover:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-800 dark:text-slate-200 font-medium text-sm transition-colors flex items-center gap-2"
            >
              <MessageSquare className="w-4 h-4 text-indigo-500" />
              <span>Explore Assistant</span>
            </Link>
          </div>
        </div>
      </section>

      {/* Sync feedback alert if any */}
      {syncNotice && (
        <div className="p-4 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-900 dark:text-indigo-300 flex items-center justify-between">
          <span>{syncNotice}</span>
          <button
            onClick={() => setSyncNotice(null)}
            className="text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            ×
          </button>
        </div>
      )}

      {/* 2. Overview Statistics Cards */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
            System Overview
          </h2>
          <button
            onClick={fetchData}
            disabled={loading}
            className="text-xs text-indigo-600 dark:text-indigo-400 hover:underline flex items-center gap-1"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button>
        </div>

        {loading ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {[1, 2, 3, 4].map((i) => (
              <div
                key={i}
                className="h-28 rounded-2xl bg-slate-100 dark:bg-slate-900 animate-pulse border border-slate-200 dark:border-slate-800"
              />
            ))}
          </div>
        ) : error ? (
          <div className="p-6 rounded-2xl border border-rose-200 dark:border-rose-900 bg-rose-50 dark:bg-rose-950/30 text-rose-600 dark:text-rose-400 text-sm flex items-center gap-3">
            <AlertCircle className="w-5 h-5 shrink-0" />
            <span>{error}</span>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {/* Total Repositories */}
            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs mb-2">
                <span className="font-semibold uppercase tracking-wider font-mono">Total Repositories</span>
                <FolderGit2 className="w-4 h-4 text-indigo-500" />
              </div>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white">
                {totalRepos}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                {repos.filter((r) => r.clone_status === 'success' || r.chunk_count > 0).length} indexed & active
              </div>
            </div>

            {/* Indexed Code Chunks */}
            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs mb-2">
                <span className="font-semibold uppercase tracking-wider font-mono">Indexed Chunks</span>
                <Database className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white">
                {totalChunks.toLocaleString()}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                AST & Tree-sitter segmented
              </div>
            </div>

            {/* Supported Languages */}
            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs mb-2">
                <span className="font-semibold uppercase tracking-wider font-mono">Supported Languages</span>
                <Code className="w-4 h-4 text-sky-500" />
              </div>
              <div className="text-3xl font-extrabold text-slate-900 dark:text-white">
                {uniqueLangs.length}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 font-mono">
                {uniqueLangs.join(', ') || 'Python, Java'}
              </div>
            </div>

            {/* Last Sync Status */}
            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
              <div className="flex items-center justify-between text-slate-500 dark:text-slate-400 text-xs mb-2">
                <span className="font-semibold uppercase tracking-wider font-mono">Last Sync Status</span>
                <Activity className="w-4 h-4 text-amber-500" />
              </div>
              <div className="text-lg font-bold text-slate-900 dark:text-white truncate">
                {lastSync ? (
                  <span className="capitalize">{lastSync.status}</span>
                ) : (
                  'Up to date'
                )}
              </div>
              <div className="text-xs text-slate-500 dark:text-slate-400 mt-1 flex items-center gap-1 truncate font-mono">
                <Clock className="w-3 h-3 text-slate-400" />
                <span>
                  {lastSync
                    ? new Date(lastSync.timestamp).toLocaleDateString()
                    : 'Indexes healthy'}
                </span>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* 3. Recent Repositories Grid */}
      <section className="space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base font-bold text-slate-900 dark:text-white tracking-tight">
              Indexed Repositories
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Repositories ready for semantic query and code understanding
            </p>
          </div>
          <Link
            to="/repositories"
            className="text-xs text-indigo-600 dark:text-indigo-400 font-medium hover:underline flex items-center gap-1"
          >
            <span>View All ({repos.length})</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        {repos.length === 0 && !loading ? (
          <div className="p-12 text-center border border-dashed border-slate-300 dark:border-slate-800 rounded-3xl space-y-3">
            <FolderGit2 className="w-10 h-10 text-slate-400 mx-auto" />
            <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
              No repositories added yet
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 max-w-sm mx-auto">
              Add your first public GitHub repository to start exploring source code and asking questions.
            </p>
            <button
              onClick={() => context?.onOpenAddModal?.()}
              className="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-500 transition-colors"
            >
              Add Repository
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {repos.slice(0, 6).map((repo) => {
              const [owner, name] = repo.full_name
                ? repo.full_name.split('/')
                : repo.repo_id.split('__');
              const isSyncing = syncingRepoId === repo.repo_id;

              return (
                <div
                  key={repo.repo_id}
                  className="group rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-5 hover:border-indigo-400 dark:hover:border-indigo-600/70 transition-all shadow-xs flex flex-col justify-between"
                >
                  <div className="space-y-3">
                    <div className="flex items-start justify-between gap-2">
                      <div className="truncate">
                        <span className="text-[11px] font-mono text-slate-400 dark:text-slate-500 block truncate">
                          {owner || 'repository'}
                        </span>
                        <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors truncate">
                          {name || repo.repo_id}
                        </h3>
                      </div>
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border border-slate-200 dark:border-slate-700 shrink-0">
                        {repo.language || 'Code'}
                      </span>
                    </div>

                    <div className="grid grid-cols-2 gap-2 text-xs text-slate-500 dark:text-slate-400 font-mono pt-1">
                      <div>
                        <span className="text-[10px] text-slate-400 block">CHUNKS</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200">
                          {repo.chunk_count?.toLocaleString() || 0}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 block">BRANCH</span>
                        <span className="font-semibold text-slate-800 dark:text-slate-200 truncate block">
                          {repo.default_branch || 'main'}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* Actions Bar */}
                  <div className="mt-4 pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                    <div className="flex items-center gap-1.5 text-emerald-600 dark:text-emerald-400 text-[11px] font-medium font-mono">
                      <CheckCircle2 className="w-3.5 h-3.5" />
                      <span>Ready</span>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSyncRepo(repo.repo_id)}
                        disabled={isSyncing}
                        className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                        title="Sync Git Updates"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin text-indigo-500' : ''}`} />
                      </button>

                      <Link
                        to={`/repositories?repo=${encodeURIComponent(repo.repo_id)}`}
                        className="px-3 py-1 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-slate-800 dark:text-slate-200 font-medium text-xs transition-colors flex items-center gap-1"
                      >
                        <span>Open</span>
                        <ArrowRight className="w-3 h-3" />
                      </Link>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </section>

      {/* 4. Getting Started 3-Step Guide */}
      <section className="rounded-3xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 p-6 sm:p-8 space-y-6 shadow-xs">
        <div>
          <h2 className="text-lg font-bold text-slate-900 dark:text-white tracking-tight">
            Getting Started with GitHub Knowledge Assistant
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            Follow these 3 simple steps to extract knowledge and find answers from any repository.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Step 1 */}
          <div
            onClick={() => context?.onOpenAddModal?.()}
            className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 space-y-3 cursor-pointer hover:border-indigo-400 dark:hover:border-indigo-600 transition-all group"
          >
            <div className="w-8 h-8 rounded-xl bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shadow-sm shadow-indigo-500/30">
              1
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
              Add a GitHub Repository
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Paste any public GitHub URL (e.g., <code className="font-mono text-[11px] bg-slate-200 dark:bg-slate-800 px-1 py-0.5 rounded">psf/requests</code>). Our shallow cloner ingests code safely without execution.
            </p>
          </div>

          {/* Step 2 */}
          <div className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 space-y-3">
            <div className="w-8 h-8 rounded-xl bg-emerald-600 text-white flex items-center justify-center font-bold text-xs shadow-sm shadow-emerald-500/30">
              2
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white">
              Wait for Indexing
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Tree-sitter extracts functions, classes, and imports. Dual indexes (BM25 and dense Transformer embeddings) are built automatically.
            </p>
          </div>

          {/* Step 3 */}
          <Link
            to="/assistant"
            className="p-5 rounded-2xl bg-slate-50 dark:bg-slate-950/60 border border-slate-200 dark:border-slate-800/80 space-y-3 hover:border-indigo-400 dark:hover:border-indigo-600 transition-all group block"
          >
            <div className="w-8 h-8 rounded-xl bg-sky-600 text-white flex items-center justify-center font-bold text-xs shadow-sm shadow-sky-500/30">
              3
            </div>
            <h3 className="text-sm font-bold text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
              Ask Questions About Code
            </h3>
            <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
              Ask in natural English (e.g., <em>"Where is authentication handled?"</em>) and get factual answers with exact line numbers and citations.
            </p>
          </Link>
        </div>
      </section>
    </div>
  );
};
