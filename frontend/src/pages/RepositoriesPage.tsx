import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import {
  RepositoryInfo,
  FileInfo,
  AddRepositoryResponse,
  SyncRepositoryResponse,
  IndexingHistoryItem
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
  PlusCircle,
  X,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Github,
  GitBranch,
  History,
  Clock
} from 'lucide-react';
import { Link } from 'react-router-dom';

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

  // Add Repository Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [newRepoUrl, setNewRepoUrl] = useState('');
  const [newRepoMaxChunks, setNewRepoMaxChunks] = useState(500);
  const [addingRepo, setAddingRepo] = useState(false);
  const [addStep, setAddStep] = useState<string>('');
  const [addResult, setAddResult] = useState<AddRepositoryResponse | null>(null);
  const [addError, setAddError] = useState<string | null>(null);

  // Sync Repository State
  const [syncingRepo, setSyncingRepo] = useState(false);
  const [syncResult, setSyncResult] = useState<SyncRepositoryResponse | null>(null);
  const [syncError, setSyncError] = useState<string | null>(null);
  const [history, setHistory] = useState<IndexingHistoryItem[]>([]);
  const [showHistory, setShowHistory] = useState(false);

  const loadRepos = () => {
    setLoadingRepos(true);
    api.listRepositories()
      .then((data) => {
        setRepos(data);
        if (selectedRepoParam) {
          const match = data.find(r => r.repo_id === selectedRepoParam);
          if (match) setSelectedRepo(match);
        }
      })
      .catch((err) => console.error("Error loading repositories:", err))
      .finally(() => setLoadingRepos(false));
  };

  useEffect(() => {
    loadRepos();
  }, [selectedRepoParam]);

  useEffect(() => {
    let result = repos;
    if (langFilter !== 'all') {
      result = result.filter(r => r.language?.toLowerCase() === langFilter);
    }
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(r =>
        r.repo_id.toLowerCase().includes(q) ||
        r.full_name.toLowerCase().includes(q)
      );
    }
    setFilteredRepos(result);
  }, [repos, langFilter, searchQuery]);

  useEffect(() => {
    if (selectedRepo) {
      setLoadingFiles(true);
      api.listRepositoryFiles(selectedRepo.repo_id)
        .then(setFiles)
        .catch((err) => {
          console.error("Failed to load repo files:", err);
          setFiles([]);
        })
        .finally(() => setLoadingFiles(false));

      api.getRepositoryHistory(selectedRepo.repo_id)
        .then(setHistory)
        .catch((err) => console.warn("Could not load repo history:", err));
    } else {
      setFiles([]);
      setHistory([]);
      setSyncResult(null);
      setSyncError(null);
      setShowHistory(false);
    }
  }, [selectedRepo]);

  const handleSelectRepo = (repo: RepositoryInfo) => {
    setSelectedRepo(repo);
    setSearchParams({ repo: repo.repo_id });
  };

  const handleBackToRepos = () => {
    setSelectedRepo(null);
    setSearchParams({});
  };

  const handleAddRepository = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newRepoUrl.trim() || addingRepo) return;

    setAddingRepo(true);
    setAddError(null);
    setAddResult(null);
    setAddStep("Validating GitHub URL & retrieving metadata...");

    try {
      setAddStep("Cloning repository & extracting AST chunks...");
      const res = await api.addRepository({
        url: newRepoUrl.trim(),
        max_chunks: newRepoMaxChunks
      });

      setAddStep("Updating BM25 lexical and Dense vector indexes...");
      setAddResult(res);
      setNewRepoUrl('');
      loadRepos();
    } catch (err: any) {
      setAddError(err?.response?.data?.detail || err.message || "Failed to add repository.");
    } finally {
      setAddingRepo(false);
      setAddStep('');
    }
  };

  const handleSyncRepository = async () => {
    if (!selectedRepo || syncingRepo) return;

    setSyncingRepo(true);
    setSyncError(null);
    setSyncResult(null);

    try {
      const res = await api.syncRepository(selectedRepo.repo_id);
      setSyncResult(res);
      // Reload history & repo stats
      loadRepos();
      const updatedHistory = await api.getRepositoryHistory(selectedRepo.repo_id);
      setHistory(updatedHistory);
    } catch (err: any) {
      setSyncError(err?.response?.data?.detail || err.message || "Sync failed.");
    } finally {
      setSyncingRepo(false);
    }
  };

  const filteredFiles = files.filter(f =>
    f.file_path.toLowerCase().includes(fileSearchQuery.toLowerCase())
  );

  return (
    <div className="space-y-6 py-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight flex items-center gap-2.5">
            <FolderGit2 className="w-7 h-7 text-indigo-400" />
            Repository Explorer
          </h1>
          <p className="text-sm text-slate-400 mt-1">
            Browse indexed repositories, inspect directory file layouts, add live repos, and sync changes.
          </p>
        </div>

        <div className="flex items-center gap-3">
          {selectedRepo ? (
            <button
              onClick={handleBackToRepos}
              className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white transition-colors"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to all repositories
            </button>
          ) : (
            <button
              onClick={() => setIsAddModalOpen(true)}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold shadow-lg shadow-indigo-500/20 transition-all transform hover:-translate-y-0.5"
            >
              <PlusCircle className="w-4 h-4" />
              Add GitHub Repository
            </button>
          )}
        </div>
      </div>

      {/* Main Content Area */}
      {!selectedRepo ? (
        /* Repository Cards View */
        <div className="space-y-6">
          {/* Controls */}
          <div className="flex flex-col sm:flex-row gap-3 items-center justify-between">
            <div className="relative w-full sm:w-80">
              <Search className="w-4 h-4 text-slate-500 absolute left-3.5 top-1/2 -translate-y-1/2" />
              <input
                type="text"
                placeholder="Filter repositories..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-10 pr-4 py-2 rounded-xl bg-slate-900/80 border border-slate-800 text-sm text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
            </div>

            <div className="flex items-center gap-1.5 bg-slate-900/80 p-1 rounded-xl border border-slate-800 text-xs self-stretch sm:self-auto">
              <button
                onClick={() => setLangFilter('all')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  langFilter === 'all'
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                All ({repos.length})
              </button>
              <button
                onClick={() => setLangFilter('python')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  langFilter === 'python'
                    ? 'bg-sky-500/20 text-sky-300 border border-sky-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Python
              </button>
              <button
                onClick={() => setLangFilter('java')}
                className={`px-3 py-1.5 rounded-lg font-medium transition-colors ${
                  langFilter === 'java'
                    ? 'bg-amber-500/20 text-amber-300 border border-amber-500/30'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                Java
              </button>
            </div>
          </div>

          {/* Repos Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {filteredRepos.map((r) => {
              const isJava = r.language?.toLowerCase() === 'java';
              return (
                <div
                  key={r.repo_id}
                  onClick={() => handleSelectRepo(r)}
                  className="p-5 rounded-2xl border border-slate-800 bg-slate-900/50 hover:bg-slate-850 hover:border-slate-700 cursor-pointer transition-all group relative overflow-hidden"
                >
                  <div className="flex items-start justify-between gap-3 mb-3">
                    <div>
                      <h3 className="font-bold text-white group-hover:text-indigo-400 transition-colors font-mono text-base flex items-center gap-2">
                        {r.full_name || r.repo_id}
                      </h3>
                      <div className="text-xs text-slate-500 font-mono mt-0.5">
                        ID: {r.repo_id}
                      </div>
                    </div>
                    <span className={`px-2.5 py-1 rounded-full text-xs font-mono font-medium ${
                      isJava
                        ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                        : 'bg-sky-500/10 text-sky-300 border border-sky-500/20'
                    }`}>
                      {r.language || 'Unknown'}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs text-slate-400 pt-3 border-t border-slate-800/60 font-mono">
                    <span className="flex items-center gap-1.5">
                      <Layers className="w-3.5 h-3.5 text-indigo-400" />
                      {r.chunk_count?.toLocaleString() || 0} chunks
                    </span>
                    <span className="flex items-center gap-1.5">
                      <Star className="w-3.5 h-3.5 text-amber-400" />
                      {r.stars ? r.stars.toLocaleString() : '—'}
                    </span>
                    <span className="text-slate-500">
                      {r.license_spdx_id || 'Open Source'}
                    </span>
                    <span className="ml-auto text-indigo-400 flex items-center gap-0.5 group-hover:translate-x-1 transition-transform">
                      Inspect <ChevronRight className="w-3.5 h-3.5" />
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      ) : (
        /* Repository Files Detail View */
        <div className="space-y-6">
          {/* Selected Repo Header Card */}
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/70 space-y-4">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="text-xs font-mono text-indigo-400 uppercase tracking-wider mb-1">
                  Selected Repository
                </div>
                <h2 className="text-2xl font-bold text-white font-mono">
                  {selectedRepo.full_name || selectedRepo.repo_id}
                </h2>
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-2 font-mono flex-wrap">
                  <span>Language: <strong className="text-slate-200">{selectedRepo.language}</strong></span>
                  <span>•</span>
                  <span>Indexed Chunks: <strong className="text-slate-200">{selectedRepo.chunk_count?.toLocaleString()}</strong></span>
                  <span>•</span>
                  <span>License: <strong className="text-slate-200">{selectedRepo.license_spdx_id || 'Open Source'}</strong></span>
                </div>
              </div>

              <div className="flex items-center gap-2 flex-wrap">
                <button
                  onClick={handleSyncRepository}
                  disabled={syncingRepo}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 disabled:opacity-50 text-white font-medium text-xs transition-colors border border-slate-700 flex items-center gap-1.5"
                  title="Detect latest remote commits, reprocess modified files, and incrementally update indexes"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${syncingRepo ? 'animate-spin text-indigo-400' : 'text-slate-400'}`} />
                  <span>{syncingRepo ? 'Syncing...' : 'Sync Updates'}</span>
                </button>

                <button
                  onClick={() => setShowHistory(!showHistory)}
                  className={`px-3.5 py-2 rounded-xl border text-xs font-medium transition-colors flex items-center gap-1.5 ${
                    showHistory
                      ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                      : 'bg-slate-800 hover:bg-slate-700 text-slate-200 border-slate-700'
                  }`}
                >
                  <History className="w-3.5 h-3.5 text-indigo-400" />
                  <span>History ({history.length})</span>
                </button>

                <Link
                  to={`/assistant?repo=${encodeURIComponent(selectedRepo.repo_id)}`}
                  className="px-3.5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-md shadow-indigo-500/20"
                >
                  Ask Assistant
                </Link>
                <Link
                  to={`/search?repo=${encodeURIComponent(selectedRepo.repo_id)}`}
                  className="px-3.5 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition-colors border border-slate-700"
                >
                  Search Chunks
                </Link>
              </div>
            </div>

            {/* Sync Feedback Alert */}
            {syncResult && (
              <div className="p-3.5 rounded-xl bg-emerald-950/40 border border-emerald-800/60 text-emerald-300 text-xs font-mono space-y-1">
                <div className="flex items-center gap-2 font-semibold">
                  <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0" />
                  <span>{syncResult.message}</span>
                </div>
                <div className="text-[11px] text-emerald-400/70 pl-6">
                  Prev: {syncResult.previous_commit?.slice(0, 8)} → Current: {syncResult.current_commit?.slice(0, 8)} • Duration: {syncResult.duration_seconds}s
                </div>
              </div>
            )}

            {syncError && (
              <div className="p-3.5 rounded-xl bg-rose-950/40 border border-rose-800/60 text-rose-300 text-xs font-mono flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                <span>{syncError}</span>
              </div>
            )}
          </div>

          {/* Indexing History Drawer / Section */}
          {showHistory && (
            <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <History className="w-5 h-5 text-indigo-400" />
                  <h3 className="font-semibold text-white text-base">
                    Incremental Indexing History
                  </h3>
                </div>
                <button
                  onClick={() => setShowHistory(false)}
                  className="text-xs text-slate-400 hover:text-white"
                >
                  Close
                </button>
              </div>

              {history.length === 0 ? (
                <div className="text-xs text-slate-500 py-6 text-center font-mono">
                  No synchronization history recorded yet for this repository. Click "Sync Updates" to check for remote commits.
                </div>
              ) : (
                <div className="divide-y divide-slate-800/60 max-h-64 overflow-y-auto pr-1">
                  {history.map((h) => (
                    <div key={h.history_id} className="py-3 px-2 flex flex-col sm:flex-row sm:items-center justify-between gap-2 text-xs font-mono">
                      <div>
                        <div className="text-slate-300 font-semibold flex items-center gap-2">
                          <span className={`w-2 h-2 rounded-full ${h.status === 'success' || h.status === 'up_to_date' ? 'bg-emerald-400' : 'bg-rose-400'}`}></span>
                          <span>Commit: {h.current_commit?.slice(0, 8)}</span>
                          <span className="text-slate-500 text-[11px]">(from {h.previous_commit?.slice(0, 8)})</span>
                        </div>
                        <div className="text-[11px] text-slate-400 mt-0.5">
                          +{h.files_added?.length || 0} files added, ~{h.files_modified?.length || 0} modified, -{h.files_deleted?.length || 0} deleted • Chunks: +{h.chunks_added} / -{h.chunks_removed}
                        </div>
                      </div>

                      <div className="text-right text-slate-500 text-[11px] shrink-0">
                        <span className="flex items-center gap-1">
                          <Clock className="w-3 h-3 text-slate-500" />
                          {h.timestamp ? new Date(h.timestamp).toLocaleString() : ''} ({h.duration_seconds}s)
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Files List */}
          <div className="rounded-2xl border border-slate-800 bg-slate-900/50 p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-4">
              <div className="flex items-center gap-2">
                <FileCode className="w-5 h-5 text-indigo-400" />
                <h3 className="font-semibold text-white text-base">
                  Indexed Files ({files.length})
                </h3>
              </div>

              <div className="relative w-full sm:w-72">
                <Search className="w-4 h-4 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
                <input
                  type="text"
                  placeholder="Filter files..."
                  value={fileSearchQuery}
                  onChange={(e) => setFileSearchQuery(e.target.value)}
                  className="w-full pl-9 pr-3 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono"
                />
              </div>
            </div>

            {loadingFiles ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                Loading repository files...
              </div>
            ) : filteredFiles.length === 0 ? (
              <div className="py-12 text-center text-slate-500 text-sm">
                No matching files found.
              </div>
            ) : (
              <div className="divide-y divide-slate-800/60 max-h-[500px] overflow-y-auto pr-1">
                {filteredFiles.map((f) => (
                  <div
                    key={f.file_path}
                    className="py-2.5 px-3 flex items-center justify-between hover:bg-slate-850/60 rounded-lg transition-colors text-xs font-mono"
                  >
                    <div className="flex items-center gap-2 truncate">
                      <FileCode className="w-4 h-4 text-slate-500 shrink-0" />
                      <span className="text-slate-300 truncate" title={f.file_path}>
                        {f.file_path}
                      </span>
                    </div>

                    <div className="flex items-center gap-3 shrink-0">
                      <span className="text-slate-500 text-[11px]">
                        {f.chunk_count} chunk{f.chunk_count === 1 ? '' : 's'}
                      </span>
                      <Link
                        to={`/search?repo=${encodeURIComponent(selectedRepo.repo_id)}&q=${encodeURIComponent(f.file_path.split('/').pop() || '')}`}
                        className="text-indigo-400 hover:text-indigo-300 text-[11px] font-semibold"
                      >
                        Search chunks →
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      )}

      {/* Add Repository Modal */}
      {isAddModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-slate-800 bg-slate-900 p-6 shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between border-b border-slate-800/80 pb-3">
              <div className="flex items-center gap-2">
                <Github className="w-5 h-5 text-indigo-400" />
                <h3 className="font-bold text-white text-base">Add Live GitHub Repository</h3>
              </div>
              <button
                onClick={() => {
                  setIsAddModalOpen(false);
                  setAddError(null);
                  setAddResult(null);
                }}
                disabled={addingRepo}
                className="text-slate-400 hover:text-white p-1 rounded-lg"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <p className="text-xs text-slate-400 leading-relaxed">
              Enter any public GitHub repository URL or shorthand. The system will retrieve metadata, shallow clone the codebase, parse AST code chunks, and index it into the BM25 and Dense retrieval engines without executing untrusted code.
            </p>

            <form onSubmit={handleAddRepository} className="space-y-4">
              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1.5 font-semibold">
                  GitHub Repository URL:
                </label>
                <input
                  type="text"
                  placeholder="https://github.com/psf/requests or owner/repo"
                  value={newRepoUrl}
                  onChange={(e) => setNewRepoUrl(e.target.value)}
                  disabled={addingRepo}
                  required
                  className="w-full px-3.5 py-2.5 rounded-xl bg-slate-950 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 font-mono transition-colors"
                />
              </div>

              <div>
                <label className="block text-xs font-mono text-slate-300 mb-1.5 font-semibold">
                  Maximum Chunks to Extract:
                </label>
                <input
                  type="number"
                  min={10}
                  max={5000}
                  step={50}
                  value={newRepoMaxChunks}
                  onChange={(e) => setNewRepoMaxChunks(Number(e.target.value))}
                  disabled={addingRepo}
                  className="w-full px-3.5 py-2 rounded-xl bg-slate-950 border border-slate-800 text-xs text-slate-100 font-mono focus:outline-none focus:border-indigo-500"
                />
                <span className="text-[11px] text-slate-500 font-mono mt-1 block">
                  Recommended: 100–500 for responsive indexing.
                </span>
              </div>

              {/* Progress message */}
              {addingRepo && (
                <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800 flex items-center gap-3 text-xs text-indigo-300 font-mono">
                  <RefreshCw className="w-4 h-4 animate-spin shrink-0 text-indigo-400" />
                  <span>{addStep}</span>
                </div>
              )}

              {/* Success result */}
              {addResult && (
                <div className="p-3.5 rounded-xl bg-emerald-950/50 border border-emerald-800/60 text-emerald-300 text-xs font-mono space-y-1">
                  <div className="flex items-center gap-2 font-semibold">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                    <span>{addResult.message}</span>
                  </div>
                  <div className="text-[11px] text-emerald-400/80 pl-6">
                    Commit: {addResult.commit_sha.slice(0, 8)} • Chunks: {addResult.chunks_extracted} • Indexed
                  </div>
                </div>
              )}

              {/* Error result */}
              {addError && (
                <div className="p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-xs font-mono flex items-center gap-2">
                  <AlertCircle className="w-4 h-4 text-rose-400 shrink-0" />
                  <span>{addError}</span>
                </div>
              )}

              <div className="flex items-center justify-end gap-3 pt-2">
                <button
                  type="button"
                  onClick={() => setIsAddModalOpen(false)}
                  disabled={addingRepo}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-medium transition-colors"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={addingRepo || !newRepoUrl.trim()}
                  className="px-5 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white text-xs font-semibold shadow-md shadow-indigo-500/20 transition-all flex items-center gap-2"
                >
                  {addingRepo ? (
                    <>
                      <RefreshCw className="w-3.5 h-3.5 animate-spin" />
                      <span>Ingesting...</span>
                    </>
                  ) : (
                    <span>Add & Index</span>
                  )}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
