import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { RepositoryInfo, FileInfo } from '../types/api';
import {
  FolderGit2,
  FileCode,
  Search,
  Star,
  Layers,
  ChevronRight,
  ExternalLink,
  Code,
  ArrowLeft
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

  useEffect(() => {
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
    } else {
      setFiles([]);
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
            Browse indexed repositories and inspect directory file layouts.
          </p>
        </div>

        {selectedRepo && (
          <button
            onClick={handleBackToRepos}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-slate-900 border border-slate-800 text-xs font-medium text-slate-300 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" /> Back to all repositories
          </button>
        )}
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
                      {r.license_spdx_id || 'Apache-2.0'}
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
          <div className="p-6 rounded-2xl border border-slate-800 bg-slate-900/70">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div>
                <div className="text-xs font-mono text-indigo-400 uppercase tracking-wider mb-1">
                  Selected Repository
                </div>
                <h2 className="text-2xl font-bold text-white font-mono">
                  {selectedRepo.full_name || selectedRepo.repo_id}
                </h2>
                <div className="flex items-center gap-4 text-xs text-slate-400 mt-2 font-mono">
                  <span>Language: <strong className="text-slate-200">{selectedRepo.language}</strong></span>
                  <span>•</span>
                  <span>Indexed Chunks: <strong className="text-slate-200">{selectedRepo.chunk_count?.toLocaleString()}</strong></span>
                  <span>•</span>
                  <span>License: <strong className="text-slate-200">{selectedRepo.license_spdx_id || 'Apache-2.0'}</strong></span>
                </div>
              </div>

              <div className="flex items-center gap-2">
                <Link
                  to={`/assistant?repo=${encodeURIComponent(selectedRepo.repo_id)}`}
                  className="px-4 py-2 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-colors shadow-md shadow-indigo-500/20"
                >
                  Ask about this repo
                </Link>
                <Link
                  to={`/search?repo=${encodeURIComponent(selectedRepo.repo_id)}`}
                  className="px-4 py-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium text-xs transition-colors border border-slate-700"
                >
                  Search in this repo
                </Link>
              </div>
            </div>
          </div>

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
    </div>
  );
};
