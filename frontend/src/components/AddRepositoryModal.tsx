import React, { useState, useEffect } from 'react';
import {
  X,
  PlusCircle,
  FolderGit2,
  CheckCircle2,
  AlertCircle,
  RefreshCw,
  ArrowRight,
  ShieldCheck,
  Sparkles,
  ExternalLink
} from 'lucide-react';
import { api } from '../services/api';
import { AddRepositoryResponse } from '../types/api';

interface Props {
  isOpen: boolean;
  onClose: () => void;
  onSuccess?: (repoId: string) => void;
}

const STAGES = [
  'Validating repository URL and accessibility',
  'Fetching repository metadata from GitHub',
  'Cloning repository shallow source (depth 1)',
  'Filtering supported source files (Python, Java)',
  'Parsing AST syntax and extracting code chunks',
  'Building lexical BM25 and dense Transformer embeddings',
  'Repository indexed and ready for exploration'
];

export const AddRepositoryModal: React.FC<Props> = ({ isOpen, onClose, onSuccess }) => {
  const [url, setUrl] = useState('');
  const [maxChunks, setMaxChunks] = useState(500);
  const [isValidUrl, setIsValidUrl] = useState<boolean | null>(null);
  const [validationMsg, setValidationMsg] = useState('');

  const [loading, setLoading] = useState(false);
  const [currentStageIdx, setCurrentStageIdx] = useState(0);
  const [result, setResult] = useState<AddRepositoryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Validate URL as user types
  useEffect(() => {
    const trimmed = url.trim();
    if (!trimmed) {
      setIsValidUrl(null);
      setValidationMsg('');
      return;
    }

    const githubRegex = /^(?:https:\/\/github\.com\/)?([a-zA-Z0-9_.-]+)\/([a-zA-Z0-9_.-]+?)(?:\.git|\/)?$/;
    const match = trimmed.match(githubRegex);

    if (match) {
      const owner = match[1];
      const repo = match[2];
      if (owner.startsWith('-') || repo.startsWith('-') || trimmed.includes('..')) {
        setIsValidUrl(false);
        setValidationMsg('Invalid owner or repository name.');
      } else {
        setIsValidUrl(true);
        setValidationMsg(`Target: ${owner}/${repo}`);
      }
    } else {
      setIsValidUrl(false);
      setValidationMsg('Enter a valid GitHub URL (https://github.com/owner/repo) or owner/repo format.');
    }
  }, [url]);

  // Stage progress animation timer while waiting for real backend response
  useEffect(() => {
    let interval: any;
    if (loading) {
      setCurrentStageIdx(0);
      interval = setInterval(() => {
        setCurrentStageIdx((prev) => (prev < STAGES.length - 2 ? prev + 1 : prev));
      }, 3500);
    }
    return () => clearInterval(interval);
  }, [loading]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!url.trim() || !isValidUrl || loading) return;

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      const res = await api.addRepository({
        url: url.trim(),
        max_chunks: maxChunks
      });
      setCurrentStageIdx(STAGES.length - 1); // Stage 7: Ready
      setResult(res);
      if (onSuccess) {
        onSuccess(res.repo_id);
      }
    } catch (err: any) {
      const msg = err.response?.data?.detail || err.message || 'Failed to add and index repository.';
      setError(typeof msg === 'string' ? msg : JSON.stringify(msg));
    } finally {
      setLoading(false);
    }
  };

  const handleReset = () => {
    setUrl('');
    setResult(null);
    setError(null);
    setCurrentStageIdx(0);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 dark:bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-xl bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Modal Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <PlusCircle className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                Add GitHub Repository
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Index source code into AST chunks, BM25, and dense embeddings
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            disabled={loading}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors disabled:opacity-50"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <div className="p-6">
          {!result && !loading && (
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* URL Input */}
              <div>
                <label className="block text-xs font-semibold text-slate-700 dark:text-slate-300 mb-1.5">
                  GitHub Repository URL or Shorthand
                </label>
                <div className="relative">
                  <input
                    type="text"
                    required
                    placeholder="https://github.com/psf/requests or pallets/flask"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    className={`w-full px-4 py-2.5 rounded-xl text-sm border bg-slate-50 dark:bg-slate-950 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none transition-colors ${
                      isValidUrl === true
                        ? 'border-emerald-500/80 focus:border-emerald-500'
                        : isValidUrl === false
                        ? 'border-rose-500/80 focus:border-rose-500'
                        : 'border-slate-300 dark:border-slate-800 focus:border-indigo-500'
                    }`}
                  />
                  {isValidUrl === true && (
                    <CheckCircle2 className="w-4 h-4 text-emerald-500 absolute right-3.5 top-3.5" />
                  )}
                  {isValidUrl === false && (
                    <AlertCircle className="w-4 h-4 text-rose-500 absolute right-3.5 top-3.5" />
                  )}
                </div>
                {validationMsg && (
                  <p
                    className={`text-xs mt-1.5 font-mono ${
                      isValidUrl ? 'text-emerald-600 dark:text-emerald-400' : 'text-rose-500'
                    }`}
                  >
                    {validationMsg}
                  </p>
                )}
              </div>

              {/* Quick suggestions */}
              <div>
                <span className="text-[11px] uppercase tracking-wider font-semibold text-slate-400 font-mono">
                  Quick Examples:
                </span>
                <div className="flex flex-wrap gap-2 mt-1.5">
                  {['psf/requests', 'pallets/flask', 'tiangolo/fastapi'].map((example) => (
                    <button
                      key={example}
                      type="button"
                      onClick={() => setUrl(`https://github.com/${example}`)}
                      className="px-2.5 py-1 text-xs rounded-lg bg-slate-100 dark:bg-slate-800/60 hover:bg-slate-200 dark:hover:bg-slate-800 text-slate-600 dark:text-slate-300 font-mono transition-colors"
                    >
                      {example}
                    </button>
                  ))}
                </div>
              </div>

              {/* Chunk Limit Option */}
              <div className="pt-2 border-t border-slate-100 dark:border-slate-800/80">
                <div className="flex items-center justify-between mb-1">
                  <label className="text-xs font-semibold text-slate-700 dark:text-slate-300">
                    Max Chunks to Index
                  </label>
                  <span className="text-xs font-mono font-medium text-indigo-600 dark:text-indigo-400">
                    {maxChunks} chunks
                  </span>
                </div>
                <input
                  type="range"
                  min="50"
                  max="2000"
                  step="50"
                  value={maxChunks}
                  onChange={(e) => setMaxChunks(Number(e.target.value))}
                  className="w-full accent-indigo-600 cursor-pointer"
                />
                <span className="text-[11px] text-slate-400 block mt-0.5">
                  Controls indexing depth and dense embedding memory usage.
                </span>
              </div>

              {/* Security Banner */}
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950/80 border border-slate-200 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 flex items-start gap-2.5">
                <ShieldCheck className="w-4 h-4 text-emerald-500 shrink-0 mt-0.5" />
                <span>
                  <strong>Sandbox Guarantee:</strong> Source code is cloned using shallow fetch (<code className="font-mono text-[10px]">--depth 1</code>) and analyzed statically. Cloned code is strictly <strong>never executed</strong>.
                </span>
              </div>

              {error && (
                <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900/50 text-xs text-rose-600 dark:text-rose-400">
                  <strong>Error:</strong> {error}
                </div>
              )}

              {/* Submit Button */}
              <button
                type="submit"
                disabled={!isValidUrl || loading}
                className="w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-all shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2 mt-4"
              >
                <span>Start Ingestion & Indexing</span>
                <ArrowRight className="w-4 h-4" />
              </button>
            </form>
          )}

          {/* Loading State with 7 Stages */}
          {loading && (
            <div className="py-6 space-y-6">
              <div className="text-center space-y-2">
                <div className="w-12 h-12 rounded-2xl bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 mx-auto animate-pulse">
                  <RefreshCw className="w-6 h-6 animate-spin" />
                </div>
                <h3 className="text-base font-bold text-slate-900 dark:text-white">
                  Indexing Repository
                </h3>
                <p className="text-xs text-slate-500 dark:text-slate-400">
                  Please wait while code is fetched, segmented, and embedded...
                </p>
              </div>

              {/* 7 Progress Stages */}
              <div className="space-y-2 max-w-md mx-auto">
                {STAGES.map((stage, idx) => {
                  const isDone = idx < currentStageIdx;
                  const isCurrent = idx === currentStageIdx;
                  return (
                    <div
                      key={idx}
                      className={`flex items-center gap-3 p-2.5 rounded-xl text-xs transition-all ${
                        isCurrent
                          ? 'bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-indigo-900 dark:text-indigo-300 font-medium'
                          : isDone
                          ? 'text-slate-600 dark:text-slate-300'
                          : 'text-slate-400 dark:text-slate-600'
                      }`}
                    >
                      {isDone ? (
                        <CheckCircle2 className="w-4 h-4 text-emerald-500 shrink-0" />
                      ) : isCurrent ? (
                        <RefreshCw className="w-4 h-4 text-indigo-500 shrink-0 animate-spin" />
                      ) : (
                        <div className="w-4 h-4 rounded-full border border-slate-300 dark:border-slate-700 shrink-0 flex items-center justify-center text-[10px]">
                          {idx + 1}
                        </div>
                      )}
                      <span>{stage}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Success State */}
          {result && (
            <div className="py-4 space-y-5 animate-in fade-in">
              <div className="flex items-center gap-3 p-4 rounded-xl bg-emerald-50 dark:bg-emerald-950/30 border border-emerald-200 dark:border-emerald-800/80">
                <CheckCircle2 className="w-6 h-6 text-emerald-600 dark:text-emerald-400 shrink-0" />
                <div>
                  <h4 className="text-sm font-bold text-slate-900 dark:text-white">
                    Repository Indexed Successfully!
                  </h4>
                  <p className="text-xs text-slate-600 dark:text-slate-400 mt-0.5">
                    {result.full_name} is now ready for semantic search and AI code QA.
                  </p>
                </div>
              </div>

              {/* Stats Box */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-400 uppercase font-mono">Chunks</div>
                  <div className="text-lg font-bold text-slate-900 dark:text-white mt-0.5">
                    {result.chunks_extracted}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-400 uppercase font-mono">BM25 Indexed</div>
                  <div className="text-lg font-bold text-indigo-600 dark:text-indigo-400 mt-0.5">
                    {result.bm25_indexed}
                  </div>
                </div>
                <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
                  <div className="text-[11px] text-slate-400 uppercase font-mono">Dense Vectors</div>
                  <div className="text-lg font-bold text-emerald-600 dark:text-emerald-400 mt-0.5">
                    {result.dense_indexed}
                  </div>
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center justify-end gap-3 pt-3 border-t border-slate-200 dark:border-slate-800">
                <button
                  type="button"
                  onClick={handleReset}
                  className="px-4 py-2 text-xs font-medium text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-white transition-colors"
                >
                  Add Another
                </button>
                <button
                  type="button"
                  onClick={onClose}
                  className="px-5 py-2 text-xs font-medium rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white transition-colors shadow-md shadow-indigo-500/20"
                >
                  Done
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
