import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { api } from '../services/api';
import {
  RepositoryInfo,
  FileInfo,
  SyncRepositoryResponse,
  IndexingHistoryItem,
  SymbolRelationships
} from '../types/api';
import {
  FolderGit2,
  FileCode,
  Search,
  Star,
  Layers,
  ChevronRight,
  ExternalLink,
  Code,
  ArrowLeft,
  ArrowRight,
  PlusCircle,
  X,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Github,
  GitBranch,
  History,
  Clock,
  Network,
  Share2,
  ShieldCheck,
  MessageSquare,
  Sparkles
} from 'lucide-react';
import { AddRepositoryModal } from '../components/AddRepositoryModal';

export const RepositoriesPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const selectedRepoParam = searchParams.get('repo');

  const [repos, setRepos] = useState<RepositoryInfo[]>([]);
  const [filteredRepos, setFilteredRepos] = useState<RepositoryInfo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<RepositoryInfo | null>(null);
  const [files, setFiles] = useState<FileInfo[]>([]);
  const [loadingRepos, setLoadingRepos] = useState(true);
  const [loadingFiles, setLoadingFiles] = useState(false);

  const [searchQuery, setSearchQuery] = useState('');
  const [langFilter, setLangFilter] = useState<'all' | 'python' | 'java'>('all');
  const [fileSearchQuery, setFileSearchQuery] = useState('');

  // Active Tab when a repo is open
  const [activeTab, setActiveTab] = useState<'overview' | 'files' | 'symbols' | 'history'>('overview');

  // Add Repository Modal
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);

  // Sync State
  const [syncing, setSyncing] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncRepositoryResponse | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [repoHistory, setRepoHistory] = useState<IndexingHistoryItem[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  // Symbol Graph Explorer State
  const [symbolQuery, setSymbolQuery] = useState('');
  const [symbolData, setSymbolData] = useState<SymbolRelationships | null>(null);
  const [symbolLoading, setSymbolLoading] = useState(false);
  const [symbolError, setSymbolError] = useState<string | null>(null);

  const loadRepos = async () => {
    setLoadingRepos(true);
    try {
      const data = await api.listRepositories();
      setRepos(data);
      if (selectedRepoParam) {
        const match = data.find((r) => r.repo_id === selectedRepoParam);
        if (match) setSelectedRepo(match);
      }
    } catch (err) {
      console.error('Error loading repositories:', err);
    } finally {
      setLoadingRepos(false);
    }
  };

  useEffect(() => {
    loadRepos();
  }, [selectedRepoParam]);

  useEffect(() => {
    let result = repos;
    if (langFilter !== 'all') {
      result = result.filter((r) => r.language?.toLowerCase() === langFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(
        (r) =>
          r.repo_id.toLowerCase().includes(q) ||
          r.full_name.toLowerCase().includes(q)
      );
    }
    setFilteredRepos(result);
  }, [repos, langFilter, searchQuery]);

  // Load files and history when repo is selected
  useEffect(() => {
    if (selectedRepo) {
      setLoadingFiles(true);
      api.listRepositoryFiles(selectedRepo.repo_id)
        .then(setFiles)
        .catch((err) => {
          console.warn('Failed to load files:', err);
          setFiles([]);
        })
        .finally(() => setLoadingFiles(false));

      setLoadingHistory(true);
      api.getRepositoryHistory(selectedRepo.repo_id)
        .then(setRepoHistory)
        .catch(() => setRepoHistory([]))
        .finally(() => setLoadingHistory(false));
    }
  }, [selectedRepo]);

  const handleSelectRepo = (repo: RepositoryInfo) => {
    setSelectedRepo(repo);
    setSearchParams({ repo: repo.repo_id });
    setActiveTab('overview');
    setSyncResult(null);
    setSyncError(null);
    setSymbolData(null);
    setSymbolQuery('');
  };

  const handleBackToList = () => {
    setSelectedRepo(null);
    setSearchParams({});
  };

  const handleSync = async () => {
    if (!selectedRepo) return;
    setSyncing(true);
    setSyncError(null);
    setSyncResult(null);
    try {
      const res = await api.syncRepository(selectedRepo.repo_id);
      setSyncResult(res);
      // Reload history and repos
      const updatedHistory = await api.getRepositoryHistory(selectedRepo.repo_id).catch(() => []);
      setRepoHistory(updatedHistory);
      loadRepos();
    } catch (err: any) {
      setSyncError(err.response?.data?.detail || err.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const handleLookupSymbol = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!symbolQuery.trim() || !selectedRepo) return;
    setSymbolLoading(true);
    setSymbolError(null);
    try {
      const res = await api.getSymbolRelationships(selectedRepo.repo_id, symbolQuery.trim());
      setSymbolData(res);
    } catch (err: any) {
      setSymbolError(err.response?.data?.detail || 'Symbol lookup failed.');
      setSymbolData(null);
    } finally {
      setSymbolLoading(false);
    }
  };

  const filteredFiles = files.filter((f) =>
    f.file_path.toLowerCase().includes(fileSearchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* View 1: Catalog List (When no repo is selected) */}
      {!selectedRepo ? (
        <div className="space-y-6">
          {/* Header Card */}
          <div className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs flex flex-wrap items-center justify-between gap-4">
            <div>
              <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
                <FolderGit2 className="w-5 h-5 text-indigo-500" />
                <span>Repositories Catalog</span>
              </h1>
              <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                Explore indexed repositories, inspect file chunk counts, and analyze code relationships.
              </p>
            </div>

            <button
              onClick={() => setIsAddModalOpen(true)}
              className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-all shadow-md shadow-indigo-500/20 flex items-center gap-2"
            >
              <PlusCircle className="w-4 h-4" />
              <span>Add Repository</span>
            </button>
          </div>

          {/* Search & Filter Bar */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3">
            {/* Search Input */}
            <div className="relative flex-1 max-w-md">
              <input
                type="text"
                placeholder="Filter repositories by name..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-9 pr-4 py-2 rounded-xl text-xs border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <Search className="w-3.5 h-3.5 text-slate-400 absolute left-3 top-2.5" />
            </div>

            {/* Language filter pills */}
            <div className="flex items-center gap-1.5 self-start sm:self-auto p-1 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
              <button
                onClick={() => setLangFilter('all')}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  langFilter === 'all'
                    ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                All ({repos.length})
              </button>
              <button
                onClick={() => setLangFilter('python')}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  langFilter === 'python'
                    ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Python
              </button>
              <button
                onClick={() => setLangFilter('java')}
                className={`px-3 py-1 rounded-lg font-medium transition-colors ${
                  langFilter === 'java'
                    ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Java
              </button>
            </div>
          </div>

          {/* Repositories Grid */}
          {loadingRepos ? (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {[1, 2, 3, 4, 5, 6].map((i) => (
                <div
                  key={i}
                  className="h-44 rounded-2xl bg-slate-100 dark:bg-slate-900 animate-pulse border border-slate-200 dark:border-slate-800"
                />
              ))}
            </div>
          ) : filteredRepos.length === 0 ? (
            <div className="p-12 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
              <FolderGit2 className="w-10 h-10 text-slate-400 mx-auto" />
              <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
                No matching repositories
              </h3>
              <p className="text-xs text-slate-400">
                Try searching with a different keyword or adding a new repository above.
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredRepos.map((repo) => {
                const [owner, name] = repo.full_name
                  ? repo.full_name.split('/')
                  : repo.repo_id.split('__');

                return (
                  <div
                    key={repo.repo_id}
                    onClick={() => handleSelectRepo(repo)}
                    className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-400 dark:hover:border-indigo-600/70 transition-all shadow-xs cursor-pointer flex flex-col justify-between space-y-4 group"
                  >
                    <div className="space-y-3">
                      <div className="flex items-start justify-between gap-2">
                        <div className="truncate">
                          <span className="text-[11px] font-mono text-slate-400 block truncate">
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

                      <div className="grid grid-cols-2 gap-2 text-xs font-mono text-slate-500 dark:text-slate-400 pt-1">
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

                    <div className="pt-3 border-t border-slate-100 dark:border-slate-800/80 flex items-center justify-between text-xs">
                      <span className="text-emerald-600 dark:text-emerald-400 font-mono text-[11px] font-medium flex items-center gap-1">
                        <CheckCircle2 className="w-3.5 h-3.5" /> Indexed
                      </span>
                      <span className="text-indigo-600 dark:text-indigo-400 font-medium flex items-center gap-1 group-hover:translate-x-0.5 transition-transform">
                        <span>Details</span>
                        <ChevronRight className="w-3.5 h-3.5" />
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      ) : (
        /* View 2: Detailed Repository View (When a repo is open) */
        <div className="space-y-6 animate-in fade-in">
          {/* Back Button */}
          <button
            onClick={handleBackToList}
            className="inline-flex items-center gap-1.5 text-xs text-slate-500 hover:text-slate-900 dark:hover:text-slate-200 font-medium transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to All Repositories</span>
          </button>

          {/* Repository Hero Header */}
          <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-4">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div className="space-y-1">
                <div className="flex items-center gap-2 flex-wrap">
                  <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight">
                    {selectedRepo.full_name || selectedRepo.repo_id}
                  </h1>
                  <span className="px-2.5 py-0.5 rounded-full text-xs font-mono uppercase bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                    {selectedRepo.language || 'Code'}
                  </span>
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400 font-mono flex items-center gap-3">
                  <span>Branch: {selectedRepo.default_branch || 'main'}</span>
                  <span>•</span>
                  <span>{selectedRepo.chunk_count?.toLocaleString()} indexed chunks</span>
                </p>
              </div>

              {/* Action Buttons */}
              <div className="flex items-center gap-2 flex-wrap">
                <a
                  href={`https://github.com/${selectedRepo.full_name?.replace('__', '/') || selectedRepo.repo_id.replace('__', '/')}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs text-slate-700 dark:text-slate-300 font-medium transition-colors flex items-center gap-1.5"
                >
                  <Github className="w-3.5 h-3.5" />
                  <span>GitHub</span>
                  <ExternalLink className="w-3 h-3 text-slate-400" />
                </a>

                <button
                  onClick={handleSync}
                  disabled={syncing}
                  className="px-3.5 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium transition-colors shadow-xs flex items-center gap-1.5"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${syncing ? 'animate-spin' : ''}`} />
                  <span>{syncing ? 'Syncing...' : 'Sync Updates'}</span>
                </button>
              </div>
            </div>

            {/* Sync feedback */}
            {syncResult && (
              <div className="p-3.5 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800/80 text-xs text-emerald-800 dark:text-emerald-300 flex items-center justify-between">
                <div>
                  <strong>Sync Complete:</strong> {syncResult.message} ({syncResult.chunks_added} chunks added, {syncResult.chunks_removed} removed).
                </div>
                <button onClick={() => setSyncResult(null)} className="text-slate-400 hover:text-slate-600">×</button>
              </div>
            )}
            {syncError && (
              <div className="p-3.5 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 text-xs text-rose-700 dark:text-rose-400 flex items-center justify-between">
                <div><strong>Sync Error:</strong> {syncError}</div>
                <button onClick={() => setSyncError(null)} className="text-slate-400 hover:text-slate-600">×</button>
              </div>
            )}

            {/* Navigation Tabs */}
            <div className="flex items-center gap-2 border-t border-slate-100 dark:border-slate-800/80 pt-3 overflow-x-auto text-xs">
              <button
                onClick={() => setActiveTab('overview')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === 'overview'
                    ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 font-semibold'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Overview
              </button>
              <button
                onClick={() => setActiveTab('files')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === 'files'
                    ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 font-semibold'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Files ({files.length})
              </button>
              <button
                onClick={() => setActiveTab('symbols')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors flex items-center gap-1.5 ${
                  activeTab === 'symbols'
                    ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 font-semibold'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                <Network className="w-3.5 h-3.5 text-indigo-500" />
                <span>Symbol Graph Explorer</span>
              </button>
              <button
                onClick={() => setActiveTab('history')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  activeTab === 'history'
                    ? 'bg-slate-100 dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 font-semibold'
                    : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
                }`}
              >
                Indexing History ({repoHistory.length})
              </button>
            </div>
          </div>

          {/* Tab 1: Overview */}
          {activeTab === 'overview' && (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
              <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
                <span className="text-[11px] uppercase tracking-wider font-mono text-slate-400">Total Files</span>
                <div className="text-2xl font-bold text-slate-900 dark:text-white">
                  {files.length}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  AST parsed source files segmented into distinct functions and classes.
                </p>
              </div>

              <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
                <span className="text-[11px] uppercase tracking-wider font-mono text-slate-400">Indexed Chunks</span>
                <div className="text-2xl font-bold text-indigo-600 dark:text-indigo-400">
                  {selectedRepo.chunk_count?.toLocaleString()}
                </div>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Represented in persistent BM25 index and custom Transformer vector store.
                </p>
              </div>

              <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
                <span className="text-[11px] uppercase tracking-wider font-mono text-slate-400">Quick Actions</span>
                <div className="space-y-2 pt-1">
                  <Link
                    to={`/assistant?repo=${encodeURIComponent(selectedRepo.repo_id)}`}
                    className="w-full py-2 px-3 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 text-indigo-700 dark:text-indigo-300 border border-indigo-200 dark:border-indigo-800 text-xs font-semibold flex items-center justify-between"
                  >
                    <span>Ask Questions on this Repo</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                  <Link
                    to={`/search?repo=${encodeURIComponent(selectedRepo.repo_id)}`}
                    className="w-full py-2 px-3 rounded-xl bg-slate-50 dark:bg-slate-800/60 text-slate-700 dark:text-slate-300 border border-slate-200 dark:border-slate-700 text-xs font-semibold flex items-center justify-between"
                  >
                    <span>Search Code Chunks</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </Link>
                </div>
              </div>
            </div>
          )}

          {/* Tab 2: Files List */}
          {activeTab === 'files' && (
            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
              <div className="flex items-center justify-between gap-3">
                <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                  Indexed Repository Files ({filteredFiles.length})
                </h3>
                <input
                  type="text"
                  placeholder="Filter files..."
                  value={fileSearchQuery}
                  onChange={(e) => setFileSearchQuery(e.target.value)}
                  className="px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-xs text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500 w-56"
                />
              </div>

              {loadingFiles ? (
                <div className="py-8 text-center text-xs text-slate-400">Loading files...</div>
              ) : filteredFiles.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">No files found.</div>
              ) : (
                <div className="divide-y divide-slate-100 dark:divide-slate-800 max-h-96 overflow-y-auto">
                  {filteredFiles.map((file, idx) => (
                    <div key={idx} className="py-2.5 flex items-center justify-between text-xs font-mono">
                      <div className="flex items-center gap-2 truncate text-slate-700 dark:text-slate-300">
                        <FileCode className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                        <span className="truncate">{file.file_path}</span>
                      </div>
                      <span className="px-2 py-0.5 rounded bg-slate-100 dark:bg-slate-800 text-slate-500 dark:text-slate-400 shrink-0">
                        {file.chunk_count} chunks
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Tab 3: Symbol Graph Explorer */}
          {activeTab === 'symbols' && (
            <div className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-5">
              <div>
                <h3 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
                  <Network className="w-4 h-4 text-indigo-500" />
                  <span>Static Symbol Relationship Graph</span>
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
                  Inspect class inheritance, callers, callees, and associated tests for any symbol in this repository without executing code.
                </p>
              </div>

              {/* Symbol Input */}
              <form onSubmit={handleLookupSymbol} className="flex gap-2 max-w-md">
                <input
                  type="text"
                  placeholder="Enter symbol name (e.g. check_auth, BaseService)..."
                  value={symbolQuery}
                  onChange={(e) => setSymbolQuery(e.target.value)}
                  className="flex-1 px-3.5 py-2 rounded-xl text-xs border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-indigo-500"
                />
                <button
                  type="submit"
                  disabled={symbolLoading || !symbolQuery.trim()}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-medium transition-colors"
                >
                  {symbolLoading ? 'Exploring...' : 'Inspect'}
                </button>
              </form>

              {symbolError && (
                <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 text-xs text-rose-600 dark:text-rose-400 font-mono">
                  {symbolError}
                </div>
              )}

              {/* Symbol Results Display */}
              {symbolData && (
                <div className="space-y-4 pt-2">
                  {/* Status Card */}
                  <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
                    <div>
                      <span className="text-[10px] font-mono uppercase text-slate-400">Target Symbol</span>
                      <h4 className="text-base font-bold text-slate-900 dark:text-white font-mono">
                        {symbolData.symbol_name}
                      </h4>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-mono font-medium ${
                      symbolData.is_defined
                        ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                        : 'bg-amber-50 dark:bg-amber-950/60 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
                    }`}>
                      {symbolData.is_defined ? 'Defined in Repository' : 'Inferred / External Reference'}
                    </span>
                  </div>

                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {/* Callers */}
                    <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                      <div className="text-xs font-bold text-slate-900 dark:text-white flex items-center justify-between">
                        <span>Inbound Callers ({symbolData.callers.length})</span>
                      </div>
                      {symbolData.callers.length === 0 ? (
                        <div className="text-xs text-slate-400 py-2">No callers indexed.</div>
                      ) : (
                        <div className="space-y-1.5 max-h-48 overflow-y-auto">
                          {symbolData.callers.map((c, i) => (
                            <div key={i} className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono">
                              <div className="font-semibold text-indigo-600 dark:text-indigo-400">{c.caller_name}</div>
                              <div className="text-[11px] text-slate-400">{c.file_path} ({c.lines})</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>

                    {/* Related Tests */}
                    <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                      <div className="text-xs font-bold text-slate-900 dark:text-white flex items-center justify-between">
                        <span>Verification Tests ({symbolData.related_tests.length})</span>
                      </div>
                      {symbolData.related_tests.length === 0 ? (
                        <div className="text-xs text-slate-400 py-2">No direct test suites indexed.</div>
                      ) : (
                        <div className="space-y-1.5 max-h-48 overflow-y-auto">
                          {symbolData.related_tests.map((t, i) => (
                            <div key={i} className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs font-mono">
                              <div className="font-semibold text-emerald-600 dark:text-emerald-400">{t.test_name}</div>
                              <div className="text-[11px] text-slate-400">{t.file_path} ({t.lines})</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Tab 4: Indexing History */}
          {activeTab === 'history' && (
            <div className="p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-4">
              <h3 className="text-sm font-bold text-slate-900 dark:text-white">
                Synchronization & Indexing Audit Log
              </h3>
              {loadingHistory ? (
                <div className="py-8 text-center text-xs text-slate-400">Loading history...</div>
              ) : repoHistory.length === 0 ? (
                <div className="py-8 text-center text-xs text-slate-400">
                  No synchronization runs recorded yet for this repository.
                </div>
              ) : (
                <div className="space-y-3">
                  {repoHistory.map((item) => (
                    <div
                      key={item.history_id}
                      className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs space-y-2 font-mono"
                    >
                      <div className="flex items-center justify-between flex-wrap gap-2">
                        <span className="font-semibold text-slate-900 dark:text-white">
                          Commit {item.current_commit.slice(0, 7)}
                        </span>
                        <span className="text-slate-400">
                          {new Date(item.timestamp).toLocaleString()}
                        </span>
                      </div>
                      <div className="text-[11px] text-slate-500">
                        Added: {item.files_added?.length || 0} files • Modified: {item.files_modified?.length || 0} files • Deleted: {item.files_deleted?.length || 0} files
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Add Modal */}
      <AddRepositoryModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSuccess={() => loadRepos()}
      />
    </div>
  );
};
