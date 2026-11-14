import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { IndexingHistoryItem, RepositoryInfo } from '../types/api';
import {
  History,
  GitCommit,
  Clock,
  CheckCircle2,
  AlertCircle,
  FilePlus,
  FileEdit,
  FileMinus,
  RefreshCw,
  Search,
  Filter,
  X,
  ExternalLink,
  ChevronRight
} from 'lucide-react';

export const IndexingHistoryPage: React.FC = () => {
  const [history, setHistory] = useState<IndexingHistoryItem[]>([]);
  const [repos, setRepos] = useState<RepositoryInfo[]>([]);
  const [selectedRepoFilter, setSelectedRepoFilter] = useState('');
  const [loading, setLoading] = useState(true);
  const [selectedRecord, setSelectedRecord] = useState<IndexingHistoryItem | null>(null);

  const loadData = async () => {
    setLoading(true);
    try {
      const [histData, repoData] = await Promise.all([
        api.getAllHistory().catch(() => []),
        api.listRepositories().catch(() => [])
      ]);
      setHistory(histData);
      setRepos(repoData);
    } catch (err) {
      console.error('Failed to load indexing history:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const filteredHistory = history.filter((item) =>
    selectedRepoFilter ? item.repo_id === selectedRepoFilter : true
  );

  return (
    <div className="space-y-6 animate-in fade-in duration-200">
      {/* 1. Header Card */}
      <div className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs flex flex-wrap items-center justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
            <History className="w-5 h-5 text-indigo-500" />
            <span>Indexing & Sync History</span>
          </h1>
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
            Audit trail of Git commit comparisons, incremental AST chunk updates, and synchronization runs.
          </p>
        </div>

        <button
          onClick={loadData}
          disabled={loading}
          className="px-3.5 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium text-slate-700 dark:text-slate-300 transition-colors flex items-center gap-1.5"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 2. Filter Bar */}
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-slate-400" />
          <select
            value={selectedRepoFilter}
            onChange={(e) => setSelectedRepoFilter(e.target.value)}
            className="text-xs font-medium px-3 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer"
          >
            <option value="">All Repositories ({history.length} records)</option>
            {repos.map((r) => (
              <option key={r.repo_id} value={r.repo_id}>
                {r.full_name || r.repo_id}
              </option>
            ))}
          </select>
        </div>

        <span className="text-xs font-mono text-slate-400">
          Showing {filteredHistory.length} events
        </span>
      </div>

      {/* 3. History Timeline / Table */}
      {loading ? (
        <div className="p-12 text-center rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
          <RefreshCw className="w-8 h-8 text-indigo-500 animate-spin mx-auto" />
          <h3 className="text-sm font-bold text-slate-800 dark:text-slate-200">
            Loading Synchronization History...
          </h3>
        </div>
      ) : filteredHistory.length === 0 ? (
        <div className="p-12 text-center rounded-2xl border border-dashed border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 space-y-3">
          <Clock className="w-10 h-10 text-slate-300 dark:text-slate-700 mx-auto" />
          <h3 className="text-base font-bold text-slate-800 dark:text-slate-200">
            No synchronization events yet
          </h3>
          <p className="text-xs text-slate-400 max-w-sm mx-auto">
            When you add or sync repositories, the commit diff audit records will appear here.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {filteredHistory.map((item) => {
            const isCompleted = item.status.toLowerCase() === 'completed' || item.status.toLowerCase() === 'up to date';
            const isFailed = item.status.toLowerCase().includes('fail');

            return (
              <div
                key={item.history_id}
                onClick={() => setSelectedRecord(item)}
                className="p-4 sm:p-5 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 hover:border-indigo-400 dark:hover:border-indigo-600/70 transition-all shadow-xs cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-4 group"
              >
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="text-xs font-bold font-mono text-slate-900 dark:text-white group-hover:text-indigo-600 dark:group-hover:text-indigo-400 transition-colors">
                      {item.repo_id}
                    </span>
                    <span
                      className={`px-2 py-0.5 rounded-full text-[10px] font-mono uppercase font-semibold border ${
                        isCompleted
                          ? 'bg-emerald-50 dark:bg-emerald-950/60 text-emerald-600 dark:text-emerald-400 border-emerald-200 dark:border-emerald-800'
                          : isFailed
                          ? 'bg-rose-50 dark:bg-rose-950/60 text-rose-600 dark:text-rose-400 border-rose-200 dark:border-rose-900'
                          : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 border-slate-200 dark:border-slate-700'
                      }`}
                    >
                      {item.status}
                    </span>
                  </div>

                  <div className="flex items-center gap-4 text-xs font-mono text-slate-500 dark:text-slate-400 flex-wrap">
                    <span className="flex items-center gap-1">
                      <GitCommit className="w-3.5 h-3.5 text-slate-400" />
                      <span>{item.current_commit.slice(0, 7)}</span>
                    </span>
                    <span>•</span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3.5 h-3.5 text-slate-400" />
                      <span>{new Date(item.timestamp).toLocaleString()}</span>
                    </span>
                    {item.duration_seconds > 0 && (
                      <>
                        <span>•</span>
                        <span>{item.duration_seconds.toFixed(2)}s</span>
                      </>
                    )}
                  </div>
                </div>

                {/* Diff stats summary */}
                <div className="flex items-center gap-4 self-end sm:self-center font-mono text-xs">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1 text-emerald-600 dark:text-emerald-400" title="Added files">
                      <FilePlus className="w-3.5 h-3.5" />
                      <span>+{item.files_added?.length || 0}</span>
                    </span>
                    <span className="flex items-center gap-1 text-amber-600 dark:text-amber-400" title="Modified files">
                      <FileEdit className="w-3.5 h-3.5" />
                      <span>~{item.files_modified?.length || 0}</span>
                    </span>
                    <span className="flex items-center gap-1 text-rose-600 dark:text-rose-400" title="Deleted files">
                      <FileMinus className="w-3.5 h-3.5" />
                      <span>-{item.files_deleted?.length || 0}</span>
                    </span>
                  </div>

                  <ChevronRight className="w-4 h-4 text-slate-400 group-hover:translate-x-0.5 transition-transform" />
                </div>
              </div>
            );
          })}
        </div>
      )}

      {/* 4. Inspection Detail Modal */}
      {selectedRecord && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 dark:bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
          <div className="w-full max-w-xl max-h-[85vh] bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl flex flex-col overflow-hidden">
            <div className="flex items-center justify-between p-5 border-b border-slate-200 dark:border-slate-800">
              <div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white font-mono">
                  Sync Record: {selectedRecord.repo_id}
                </h3>
                <span className="text-xs text-slate-400 font-mono">
                  {new Date(selectedRecord.timestamp).toLocaleString()}
                </span>
              </div>
              <button
                onClick={() => setSelectedRecord(null)}
                className="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="p-6 space-y-4 overflow-y-auto text-xs font-mono">
              <div className="grid grid-cols-2 gap-3 p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                <div>
                  <span className="text-slate-400 block text-[10px]">PREVIOUS COMMIT</span>
                  <span className="text-slate-800 dark:text-slate-200 font-bold truncate block">
                    {selectedRecord.previous_commit || 'None (Initial)'}
                  </span>
                </div>
                <div>
                  <span className="text-slate-400 block text-[10px]">CURRENT COMMIT</span>
                  <span className="text-indigo-600 dark:text-indigo-400 font-bold truncate block">
                    {selectedRecord.current_commit}
                  </span>
                </div>
              </div>

              {/* Added Files */}
              <div className="space-y-1">
                <span className="text-emerald-600 dark:text-emerald-400 font-bold flex items-center gap-1.5">
                  <FilePlus className="w-3.5 h-3.5" /> Added Files ({selectedRecord.files_added?.length || 0})
                </span>
                {selectedRecord.files_added?.length ? (
                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 max-h-28 overflow-y-auto space-y-1">
                    {selectedRecord.files_added.map((f, i) => (
                      <div key={i} className="text-slate-600 dark:text-slate-300">{f}</div>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-400 block pl-5 text-[11px]">None</span>
                )}
              </div>

              {/* Modified Files */}
              <div className="space-y-1">
                <span className="text-amber-600 dark:text-amber-400 font-bold flex items-center gap-1.5">
                  <FileEdit className="w-3.5 h-3.5" /> Modified Files ({selectedRecord.files_modified?.length || 0})
                </span>
                {selectedRecord.files_modified?.length ? (
                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 max-h-28 overflow-y-auto space-y-1">
                    {selectedRecord.files_modified.map((f, i) => (
                      <div key={i} className="text-slate-600 dark:text-slate-300">{f}</div>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-400 block pl-5 text-[11px]">None</span>
                )}
              </div>

              {/* Deleted Files */}
              <div className="space-y-1">
                <span className="text-rose-600 dark:text-rose-400 font-bold flex items-center gap-1.5">
                  <FileMinus className="w-3.5 h-3.5" /> Deleted Files ({selectedRecord.files_deleted?.length || 0})
                </span>
                {selectedRecord.files_deleted?.length ? (
                  <div className="p-2.5 rounded-lg bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 max-h-28 overflow-y-auto space-y-1">
                    {selectedRecord.files_deleted.map((f, i) => (
                      <div key={i} className="text-slate-600 dark:text-slate-300">{f}</div>
                    ))}
                  </div>
                ) : (
                  <span className="text-slate-400 block pl-5 text-[11px]">None</span>
                )}
              </div>
            </div>

            <div className="p-4 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950/50 flex justify-end">
              <button
                onClick={() => setSelectedRecord(null)}
                className="px-4 py-2 rounded-xl bg-slate-200 dark:bg-slate-800 text-slate-800 dark:text-slate-200 text-xs font-semibold hover:bg-slate-300 dark:hover:bg-slate-700 transition-colors"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
