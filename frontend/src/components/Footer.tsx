import React from 'react';
import { GitBranch, ShieldCheck, Terminal, Cpu } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="border-t border-slate-900 bg-slate-950 py-8 mt-auto">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4 text-xs text-slate-500">
        <div className="flex items-center gap-2">
          <Cpu className="w-4 h-4 text-indigo-400" />
          <span>GitHub Knowledge Assistant — Phase 4 Web Application</span>
        </div>
        <div className="flex items-center gap-6">
          <span className="flex items-center gap-1.5">
            <GitBranch className="w-3.5 h-3.5 text-slate-400" />
            10 Repositories (Python & Java)
          </span>
          <span className="flex items-center gap-1.5">
            <Terminal className="w-3.5 h-3.5 text-slate-400" />
            BM25 + Dense RRF Hybrid Retrieval
          </span>
          <span className="flex items-center gap-1.5">
            <ShieldCheck className="w-3.5 h-3.5 text-emerald-400" />
            Evidence-Grounded Citations
          </span>
        </div>
      </div>
    </footer>
  );
};
