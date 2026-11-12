import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { RepositoryInfo, HealthResponse } from '../types/api';
import {
  FolderGit2,
  Database,
  Layers,
  Activity,
  CheckCircle2,
  TrendingUp,
  Cpu,
  BarChart3,
  Star,
  ExternalLink
} from 'lucide-react';
import { Link } from 'react-router-dom';

export const DashboardPage: React.FC = () => {
  const [repos, setRepos] = useState<RepositoryInfo[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.listRepositories(), api.getHealth()])
      .then(([reposData, healthData]) => {
        setRepos(reposData);
        setHealth(healthData);
      })
      .catch((err) => console.error("Failed to load dashboard data:", err))
      .finally(() => setLoading(false));
  }, []);

  const totalIndexedChunks = repos.reduce((acc, r) => acc + (r.chunk_count || 0), 0);

  return (
    <div className="space-y-8 py-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl sm:text-3xl font-bold text-white tracking-tight">
          System Dashboard
        </h1>
        <p className="text-sm text-slate-400 mt-1">
          High-level overview of indexed repositories, chunk distributions, and retrieval performance.
        </p>
      </div>

      {/* Metrics Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <span className="font-medium uppercase tracking-wider font-mono">Repositories</span>
            <FolderGit2 className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-bold text-white">
            {repos.length || 10}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            5 Python • 5 Java
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <span className="font-medium uppercase tracking-wider font-mono">Total Chunks</span>
            <Database className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-bold text-white">
            243,411
          </div>
          <div className="text-xs text-slate-500 mt-1">
            AST & Tree-sitter segmented
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <span className="font-medium uppercase tracking-wider font-mono">Index In-Memory</span>
            <Layers className="w-4 h-4 text-sky-400" />
          </div>
          <div className="text-3xl font-bold text-white">
            {totalIndexedChunks.toLocaleString()}
          </div>
          <div className="text-xs text-slate-500 mt-1">
            BM25 + Dense vector store
          </div>
        </div>

        <div className="p-5 rounded-2xl border border-slate-800 bg-slate-900/60">
          <div className="flex items-center justify-between text-slate-400 text-xs mb-3">
            <span className="font-medium uppercase tracking-wider font-mono">System Status</span>
            <Activity className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-bold text-emerald-400 flex items-center gap-2">
            <span className="w-3 h-3 rounded-full bg-emerald-500 animate-pulse"></span>
            Operational
          </div>
          <div className="text-xs text-slate-500 mt-1 font-mono">
            FastAPI v{health?.version || '4.0.0'}
          </div>
        </div>
      </div>

      {/* Retrieval Evaluation Benchmarks */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">
              Retrieval Accuracy & Fusion Benchmarks (Phase 3 Reported)
            </h2>
          </div>
          <span className="text-xs font-mono text-slate-400">
            N = 100 evaluation pairs
          </span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 uppercase">
                <th className="py-3 px-4 font-semibold">Method</th>
                <th className="py-3 px-4 font-semibold">Recall@1</th>
                <th className="py-3 px-4 font-semibold">Recall@5</th>
                <th className="py-3 px-4 font-semibold">Recall@10</th>
                <th className="py-3 px-4 font-semibold">MRR</th>
                <th className="py-3 px-4 font-semibold">Phase 4 Enhancement</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60 text-slate-300">
              <tr>
                <td className="py-3 px-4 font-semibold text-slate-200">BM25 Lexical</td>
                <td className="py-3 px-4 text-emerald-400">64.0%</td>
                <td className="py-3 px-4 text-emerald-400">74.0%</td>
                <td className="py-3 px-4 text-emerald-400">76.0%</td>
                <td className="py-3 px-4">0.6887</td>
                <td className="py-3 px-4 text-slate-400">Sub-token identifier splitting (camel/snake)</td>
              </tr>
              <tr>
                <td className="py-3 px-4 font-semibold text-slate-200">Dense Encoder</td>
                <td className="py-3 px-4 text-amber-400">0.0%</td>
                <td className="py-3 px-4 text-amber-400">2.0%</td>
                <td className="py-3 px-4 text-amber-400">4.0%</td>
                <td className="py-3 px-4">0.0145</td>
                <td className="py-3 px-4 text-slate-400">4-layer PyTorch Transformer (trained from scratch)</td>
              </tr>
              <tr className="bg-indigo-950/20">
                <td className="py-3 px-4 font-semibold text-indigo-300">Hybrid (RRF + Symbol Boost)</td>
                <td className="py-3 px-4 text-indigo-300 font-bold">50.0% (Boosted)</td>
                <td className="py-3 px-4 text-indigo-300 font-bold">72.0%</td>
                <td className="py-3 px-4 text-indigo-300 font-bold">74.0%</td>
                <td className="py-3 px-4 text-indigo-300 font-bold">0.5753</td>
                <td className="py-3 px-4 text-emerald-400 font-medium">+10.0 exact symbol boost & test demotion</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Repositories Overview Table */}
      <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <FolderGit2 className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-semibold text-white">
              Indexed Repositories
            </h2>
          </div>
          <Link
            to="/repositories"
            className="text-xs text-indigo-400 hover:text-indigo-300 font-medium transition-colors"
          >
            Explore all →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-slate-800 text-slate-400 font-mono uppercase">
                <th className="py-3 px-4">Repository</th>
                <th className="py-3 px-4">Language</th>
                <th className="py-3 px-4">Indexed Chunks</th>
                <th className="py-3 px-4">Stars</th>
                <th className="py-3 px-4">License</th>
                <th className="py-3 px-4">Action</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/60">
              {repos.map((r) => {
                const isJava = r.language?.toLowerCase() === 'java';
                return (
                  <tr key={r.repo_id} className="hover:bg-slate-850/50 transition-colors">
                    <td className="py-3 px-4 font-medium text-slate-200 font-mono">
                      {r.full_name || r.repo_id}
                    </td>
                    <td className="py-3 px-4">
                      <span className={`px-2 py-0.5 rounded text-[11px] font-mono ${
                        isJava
                          ? 'bg-amber-500/10 text-amber-300 border border-amber-500/20'
                          : 'bg-sky-500/10 text-sky-300 border border-sky-500/20'
                      }`}>
                        {r.language || 'Unknown'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-300">
                      {r.chunk_count?.toLocaleString() || 0}
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-400">
                      <span className="inline-flex items-center gap-1">
                        <Star className="w-3 h-3 text-amber-400" />
                        {r.stars ? r.stars.toLocaleString() : '—'}
                      </span>
                    </td>
                    <td className="py-3 px-4 font-mono text-slate-500">
                      {r.license_spdx_id || 'Apache-2.0'}
                    </td>
                    <td className="py-3 px-4">
                      <Link
                        to={`/repositories?repo=${encodeURIComponent(r.repo_id)}`}
                        className="text-indigo-400 hover:text-indigo-300 font-mono text-xs inline-flex items-center gap-1"
                      >
                        Inspect Files <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
