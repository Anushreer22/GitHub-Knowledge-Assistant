import React, { useEffect } from 'react';
import {
  X,
  BookOpen,
  Layers,
  ShieldCheck,
  Search,
  GitBranch,
  FileCode,
  CheckCircle2
} from 'lucide-react';

interface Props {
  isOpen: boolean;
  onClose: () => void;
}

export const HelpModal: React.FC<Props> = ({ isOpen, onClose }) => {
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    if (isOpen) {
      window.addEventListener('keydown', handleKeyDown);
    }
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/60 dark:bg-slate-950/80 backdrop-blur-sm animate-in fade-in duration-200">
      <div className="w-full max-w-2xl max-h-[85vh] flex flex-col bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 rounded-2xl shadow-2xl overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-indigo-50 dark:bg-indigo-950/50 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400">
              <BookOpen className="w-4 h-4" />
            </div>
            <div>
              <h2 className="text-base font-bold text-slate-900 dark:text-white">
                GitHub Knowledge Assistant Documentation
              </h2>
              <p className="text-xs text-slate-500 dark:text-slate-400">
                Guide to evidence-grounded code retrieval and understanding
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 text-sm text-slate-600 dark:text-slate-300">
          {/* Section 1 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-900 dark:text-white font-semibold">
              <Layers className="w-4 h-4 text-indigo-500" />
              <span>1. How Hybrid Retrieval Works</span>
            </div>
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Our system combines two complementary search engines using Reciprocal Rank Fusion (RRF):
            </p>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-1">
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800/80">
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1">
                  BM25 Lexical Index
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  Splits code identifiers (camelCase & snake_case) to locate exact variable, function, and class names.
                </div>
              </div>
              <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800/80">
                <div className="text-xs font-semibold text-slate-800 dark:text-slate-200 mb-1">
                  Custom CodeEncoder
                </div>
                <div className="text-[11px] text-slate-500 dark:text-slate-400">
                  A 4-layer PyTorch Transformer generating 256-D embeddings to grasp conceptual intent and semantics.
                </div>
              </div>
            </div>
          </div>

          {/* Section 2 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-900 dark:text-white font-semibold">
              <ShieldCheck className="w-4 h-4 text-emerald-500" />
              <span>2. Strict Evidence Grounding & Zero Hallucination</span>
            </div>
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              Unlike generic LLM chat tools that make up code syntax or guess file locations:
            </p>
            <ul className="space-y-1.5 text-xs text-slate-500 dark:text-slate-400 list-disc list-inside">
              <li>Every answer is bound to verified AST chunks with exact file and line citations (<code className="font-mono text-[11px] bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">file.py#L20-40</code>).</li>
              <li>When a requested component is absent, the engine explicitly reports <strong className="text-amber-500">Insufficient Evidence</strong>.</li>
              <li>Our symbol disambiguator boosts true definitions (+10.0 boost) above unit tests and caller sites.</li>
            </ul>
          </div>

          {/* Section 3 */}
          <div className="space-y-2">
            <div className="flex items-center gap-2 text-slate-900 dark:text-white font-semibold">
              <GitBranch className="w-4 h-4 text-sky-500" />
              <span>3. Incremental Updates & Zero Code Execution</span>
            </div>
            <p className="text-xs leading-relaxed text-slate-500 dark:text-slate-400">
              When a repository changes, clicking <strong>Sync Updates</strong> inspects commit diffs (<code className="font-mono text-[11px] bg-slate-100 dark:bg-slate-800 px-1 py-0.5 rounded">git diff A/M/D</code>), updating only modified files. Cloned code is analyzed statically and strictly <strong>never executed</strong>.
            </p>
          </div>
        </div>

        {/* Footer */}
        <div className="flex items-center justify-between px-6 py-3.5 border-t border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-900/50">
          <span className="text-xs font-mono text-slate-400">
            Version 5.0.0 • Apache 2.0 License
          </span>
          <button
            onClick={onClose}
            className="px-4 py-1.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors"
          >
            Got it
          </button>
        </div>
      </div>
    </div>
  );
};
