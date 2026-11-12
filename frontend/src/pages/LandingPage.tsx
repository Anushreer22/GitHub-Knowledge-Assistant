import React from 'react';
import { Link } from 'react-router-dom';
import {
  MessageSquare,
  Search,
  FolderGit2,
  Cpu,
  Layers,
  ShieldCheck,
  ArrowRight,
  Sparkles,
  GitFork,
  FileCode2,
  CheckCircle2
} from 'lucide-react';

export const LandingPage: React.FC = () => {
  return (
    <div className="space-y-24 py-8">
      {/* Hero Section */}
      <section className="relative overflow-hidden pt-12 pb-20 text-center max-w-4xl mx-auto px-4">
        {/* Glow backdrop */}
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[300px] bg-indigo-500/10 blur-[100px] -z-10 rounded-full pointer-events-none" />

        <div className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs font-mono text-indigo-400 mb-8 shadow-sm">
          <Sparkles className="w-3.5 h-3.5" />
          <span>Phase 4 Production Release • Hybrid Retrieval Engine</span>
        </div>

        <h1 className="text-4xl sm:text-6xl font-extrabold text-white tracking-tight leading-tight sm:leading-none mb-6">
          Ask Code Questions. <br />
          <span className="bg-gradient-to-r from-indigo-400 via-sky-300 to-indigo-200 bg-clip-text text-transparent">
            Verify With Source Evidence.
          </span>
        </h1>

        <p className="text-lg sm:text-xl text-slate-400 leading-relaxed max-w-2xl mx-auto mb-10">
          A specialized repository QA system with custom-trained code embeddings, BM25 lexical fusion, exact symbol disambiguation, and verified file-and-line citations.
        </p>

        <div className="flex flex-wrap items-center justify-center gap-4">
          <Link
            to="/assistant"
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-semibold shadow-lg shadow-indigo-500/25 transition-all transform hover:-translate-y-0.5"
          >
            <MessageSquare className="w-5 h-5" />
            Launch AI Assistant
            <ArrowRight className="w-4 h-4 ml-1" />
          </Link>
          <Link
            to="/search"
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold transition-all"
          >
            <Search className="w-5 h-5 text-indigo-400" />
            Search Code Chunks
          </Link>
          <Link
            to="/repositories"
            className="flex items-center gap-2 px-6 py-3 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold transition-all"
          >
            <FolderGit2 className="w-5 h-5 text-indigo-400" />
            Explore Repositories
          </Link>
        </div>
      </section>

      {/* Live QA Preview Card */}
      <section className="max-w-4xl mx-auto px-4">
        <div className="rounded-2xl border border-slate-800 bg-slate-900/60 p-6 sm:p-8 backdrop-blur shadow-2xl relative">
          <div className="text-xs uppercase tracking-wider text-indigo-400 font-mono font-semibold mb-4 flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            Example Evidence-Grounded Answer
          </div>

          <div className="space-y-4">
            <div className="p-3.5 rounded-xl bg-slate-950/80 border border-slate-800/80 flex items-center justify-between text-sm">
              <span className="text-slate-300 font-medium">
                Q: "Where is the check_auth function implemented?"
              </span>
              <span className="text-xs px-2 py-0.5 rounded bg-indigo-500/10 text-indigo-300 border border-indigo-500/20 font-mono">
                Hybrid RRF
              </span>
            </div>

            <div className="p-4 rounded-xl bg-slate-950/50 border border-slate-800/60 text-sm leading-relaxed text-slate-300 space-y-3">
              <p>
                The symbol <code className="text-indigo-300 bg-slate-900 px-1.5 py-0.5 rounded">check_auth</code> (function_definition) is implemented in repository <code className="text-slate-200">public-apis__public-apis</code>, located in file <code className="text-slate-200">scripts/validate/format.py</code> across lines 129–142.
              </p>

              <div className="rounded-lg bg-[#090d16] border border-slate-800/80 p-3 font-mono text-xs text-slate-300 overflow-x-auto">
                <span className="text-slate-600 select-none mr-3">129</span>
                <span className="text-purple-400">def</span> <span className="text-blue-400">check_auth</span>(auth: str) -&gt; <span className="text-emerald-400">bool</span>:
                <br />
                <span className="text-slate-600 select-none mr-3">130</span>
                &nbsp;&nbsp;&nbsp;&nbsp;<span className="text-purple-400">return</span> auth <span className="text-purple-400">in</span> {"{"}<span className="text-emerald-300">'apiKey'</span>, <span className="text-emerald-300">'OAuth'</span>, <span className="text-emerald-300">'No'</span>{"}"}
              </div>

              <div className="flex items-center gap-3 pt-2 text-xs text-slate-400 font-mono">
                <span className="inline-flex items-center gap-1 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  Exact Match Verified
                </span>
                <span>•</span>
                <span>public-apis/scripts/validate/format.py#L129-L142</span>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Feature Highlights */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="text-center mb-12">
          <h2 className="text-2xl sm:text-3xl font-bold text-white mb-3">
            Architected for Code Verification
          </h2>
          <p className="text-slate-400 text-sm max-w-xl mx-auto">
            Traditional LLMs hallucinate non-existent functions. Our engine grounds every answer strictly in indexed AST chunks with exact line citations.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 hover:border-slate-700 transition-all">
            <div className="w-10 h-10 rounded-xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center mb-4">
              <Layers className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">Hybrid Reciprocal Rank Fusion</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Fuses BM25 identifier-aware tokenization with dense embeddings from our custom PyTorch Transformer CodeEncoder ($k=60$).
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 hover:border-slate-700 transition-all">
            <div className="w-10 h-10 rounded-xl bg-emerald-500/10 text-emerald-400 flex items-center justify-center mb-4">
              <CheckCircle2 className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">Exact Symbol Disambiguation</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Detects camelCase and snake_case targets, separating exact function implementations from callers and test functions.
            </p>
          </div>

          <div className="rounded-2xl border border-slate-800 bg-slate-900/40 p-6 hover:border-slate-700 transition-all">
            <div className="w-10 h-10 rounded-xl bg-sky-500/10 text-sky-400 flex items-center justify-center mb-4">
              <ShieldCheck className="w-5 h-5" />
            </div>
            <h3 className="text-base font-semibold text-white mb-2">Evidence-Grounded Citations</h3>
            <p className="text-slate-400 text-sm leading-relaxed">
              Every answer is accompanied by verifiable citations, start/end line bounds, and confidence classifications.
            </p>
          </div>
        </div>
      </section>

      {/* Dataset & Repositories Banner */}
      <section className="max-w-6xl mx-auto px-4">
        <div className="rounded-2xl border border-slate-800 bg-gradient-to-b from-slate-900/80 to-slate-950 p-8">
          <div className="flex flex-col md:flex-row items-center justify-between gap-6">
            <div>
              <h3 className="text-xl font-bold text-white mb-2">
                10 Production GitHub Repositories Indexed
              </h3>
              <p className="text-sm text-slate-400 max-w-xl">
                243,411 total code chunks across Python and Java codebases including Ghidra, Retrofit, Gson, TestNG, Werkzeug, Bottle, and Marshmallow.
              </p>
            </div>
            <Link
              to="/dashboard"
              className="px-5 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-white font-medium text-sm transition-colors shrink-0"
            >
              View System Dashboard
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
};
