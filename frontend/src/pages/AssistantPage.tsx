import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { QueryResponse, RepositoryInfo, EvidenceItem } from '../types/api';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { ClassificationBadge } from '../components/ClassificationBadge';
import { CitationCard } from '../components/CitationCard';
import { CodeViewer } from '../components/CodeViewer';
import {
  MessageSquare,
  Send,
  Sparkles,
  Layers,
  ShieldCheck,
  HelpCircle,
  FileCode,
  ArrowRight,
  Filter,
  CheckCircle2,
  RefreshCw,
  X
} from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  data?: QueryResponse;
  timestamp: string;
}

export const AssistantPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const repoParam = searchParams.get('repo');

  const [repos, setRepos] = useState<RepositoryInfo[]>([]);
  const [selectedRepo, setSelectedRepo] = useState<string>(repoParam || '');
  const [mode, setMode] = useState<'hybrid' | 'bm25' | 'dense'>('hybrid');
  const [inputQuestion, setInputQuestion] = useState('');
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [selectedEvidence, setSelectedEvidence] = useState<EvidenceItem | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listRepositories()
      .then(setRepos)
      .catch((err) => console.error("Failed to load repositories:", err));
  }, []);

  useEffect(() => {
    if (repoParam) {
      setSelectedRepo(repoParam);
    }
  }, [repoParam]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, loading]);

  const handleSend = async (questionText?: string) => {
    const q = (questionText || inputQuestion).trim();
    if (!q || loading) return;

    const userMsg: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: 'user',
      text: q,
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setMessages(prev => [...prev, userMsg]);
    setInputQuestion('');
    setLoading(true);

    try {
      const response = await api.queryQA({
        question: q,
        mode: mode,
        repo_id: selectedRepo || null,
        top_k: 5
      });

      const assistantMsg: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: 'assistant',
        text: response.answer,
        data: response,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };

      setMessages(prev => [...prev, assistantMsg]);
      if (response.evidence && response.evidence.length > 0) {
        setSelectedEvidence(response.evidence[0]);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: `Error retrieving answer: ${err?.response?.data?.detail || err.message || 'Service unavailable'}`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages(prev => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const starterPrompts = [
    { label: "check_auth function", query: "Where is the check_auth function implemented?" },
    { label: "error_message function", query: "Where is the error_message function implemented?" },
    { label: "Singleton Pattern", query: "Where is the Singleton design pattern implemented?" },
    { label: "HTTP Parsing in Werkzeug", query: "Where are HTTP request headers or parsing handled?" },
    { label: "Unanswerable Query Demo", query: "Where is the non_existent_mystery_function defined?" }
  ];

  return (
    <div className="py-4 space-y-4">
      {/* Top Controls Bar */}
      <div className="p-4 rounded-2xl border border-slate-800 bg-slate-900/70 flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-4 h-4 text-indigo-400" />
          <span className="font-semibold text-white">AI Assistant Workspace</span>
          <span className="text-slate-500 font-mono hidden sm:inline">• Strict Code Grounding</span>
        </div>

        <div className="flex items-center gap-3 flex-wrap">
          {/* Repository Selector */}
          <div className="flex items-center gap-1.5">
            <Filter className="w-3.5 h-3.5 text-slate-400" />
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-950 border border-slate-800 text-slate-200 focus:outline-none focus:border-indigo-500 font-mono text-xs"
            >
              <option value="">All 10 Repositories</option>
              {repos.map(r => (
                <option key={r.repo_id} value={r.repo_id}>
                  {r.full_name || r.repo_id}
                </option>
              ))}
            </select>
          </div>

          {/* Mode Selector */}
          <div className="flex items-center p-0.5 rounded-lg bg-slate-950 border border-slate-800 font-mono">
            {(['hybrid', 'bm25', 'dense'] as const).map(m => (
              <button
                key={m}
                onClick={() => setMode(m)}
                className={`px-2.5 py-1 rounded-md text-[11px] font-medium uppercase transition-colors ${
                  mode === m
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200'
                }`}
              >
                {m}
              </button>
            ))}
          </div>
        </div>
      </div>

      {/* Main Workspace Layout */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 min-h-[640px]">
        {/* Chat Stream (Left / Main) */}
        <div className="lg:col-span-7 flex flex-col h-[700px] rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
          {/* Messages list */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-6">
            {messages.length === 0 ? (
              <div className="h-full flex flex-col items-center justify-center text-center max-w-md mx-auto space-y-4 text-slate-400">
                <div className="w-12 h-12 rounded-2xl bg-indigo-500/10 text-indigo-400 flex items-center justify-center shadow-lg shadow-indigo-500/10">
                  <Sparkles className="w-6 h-6" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white mb-1">
                    Ask About Repository Source Code
                  </h3>
                  <p className="text-xs text-slate-400">
                    Inquire about function implementations, class definitions, design patterns, or parameters. Every response is verified with exact citations.
                  </p>
                </div>

                {/* Starter Prompts */}
                <div className="w-full text-left pt-2 space-y-2">
                  <span className="text-[11px] uppercase font-mono tracking-wider text-slate-500 font-semibold">
                    Suggested Verification Prompts:
                  </span>
                  <div className="flex flex-col gap-1.5">
                    {starterPrompts.map((p, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(p.query)}
                        className="text-left px-3 py-2 rounded-xl bg-slate-950/80 hover:bg-slate-850 border border-slate-800 text-xs text-slate-300 hover:text-white transition-all flex items-center justify-between group"
                      >
                        <span className="truncate">{p.query}</span>
                        <ArrowRight className="w-3.5 h-3.5 text-indigo-400 opacity-0 group-hover:opacity-100 transition-opacity shrink-0" />
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} space-y-1`}
                >
                  <div className="text-[11px] text-slate-500 px-1 font-mono">
                    {msg.sender === 'user' ? 'You' : 'Assistant'} • {msg.timestamp}
                  </div>

                  {msg.sender === 'user' ? (
                    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 text-white px-4 py-3 text-sm font-medium shadow-md">
                      {msg.text}
                    </div>
                  ) : (
                    <div className="max-w-[95%] rounded-2xl rounded-tl-sm bg-slate-950/90 border border-slate-800 p-4 text-sm text-slate-200 space-y-3 shadow-lg">
                      {/* Meta badges */}
                      {msg.data && (
                        <div className="flex items-center gap-2 flex-wrap pb-2 border-b border-slate-800/80 text-xs">
                          <ConfidenceBadge confidence={msg.data.confidence_indicator} />
                          <ClassificationBadge classification={msg.data.match_classification} />
                          <span className="px-2 py-0.5 rounded text-[10px] font-mono uppercase bg-slate-800 text-slate-400">
                            {msg.data.retrieval_method}
                          </span>
                        </div>
                      )}

                      {/* Answer prose */}
                      <div className="leading-relaxed text-sm text-slate-200">
                        {msg.text}
                      </div>

                      {/* Evidence citation links */}
                      {msg.data && msg.data.evidence && msg.data.evidence.length > 0 && (
                        <div className="pt-2 border-t border-slate-800/80 space-y-1.5">
                          <div className="text-[11px] uppercase tracking-wider font-mono text-slate-400 font-semibold">
                            Source Citations ({msg.data.evidence.length}):
                          </div>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.data.evidence.map((ev, i) => (
                              <button
                                key={i}
                                onClick={() => setSelectedEvidence(ev)}
                                className={`text-left text-xs font-mono px-2.5 py-1 rounded-lg border transition-all flex items-center gap-1.5 ${
                                  selectedEvidence?.citation === ev.citation
                                    ? 'bg-indigo-600/20 border-indigo-500 text-indigo-300'
                                    : 'bg-slate-900 border-slate-800 hover:border-slate-700 text-slate-400 hover:text-slate-200'
                                }`}
                              >
                                <FileCode className="w-3.5 h-3.5 text-indigo-400" />
                                <span>{ev.file_path.split('/').pop()}</span>
                                <span className="text-slate-500 text-[10px]">L{ev.start_line}-L{ev.end_line}</span>
                              </button>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              ))
            )}

            {loading && (
              <div className="flex items-center gap-3 p-4 rounded-2xl bg-slate-950/80 border border-slate-800 text-xs text-slate-400">
                <RefreshCw className="w-4 h-4 text-indigo-400 animate-spin" />
                <span>Searching AST chunks, applying BM25 & dense RRF, and verifying code evidence...</span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat input box */}
          <div className="p-3 sm:p-4 bg-slate-950/90 border-t border-slate-800">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                placeholder="Ask a question about the indexed repositories..."
                value={inputQuestion}
                onChange={(e) => setInputQuestion(e.target.value)}
                disabled={loading}
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-900 border border-slate-800 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <button
                type="submit"
                disabled={loading || !inputQuestion.trim()}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-all flex items-center gap-1.5 shadow-md shadow-indigo-500/20"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Ask</span>
              </button>
            </form>
          </div>
        </div>

        {/* Evidence Inspector Side Panel (Right) */}
        <div className="lg:col-span-5 flex flex-col h-[700px] rounded-2xl border border-slate-800 bg-slate-900/50 overflow-hidden">
          <div className="p-4 bg-slate-950/80 border-b border-slate-800 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <ShieldCheck className="w-4 h-4 text-emerald-400" />
              <h3 className="font-semibold text-white text-sm">
                Evidence Inspector
              </h3>
            </div>
            {selectedEvidence && (
              <ClassificationBadge classification={selectedEvidence.match_classification} />
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {selectedEvidence ? (
              <div className="space-y-4">
                <CitationCard evidence={selectedEvidence} compact={false} />

                {selectedEvidence.code_snippet && (
                  <div>
                    <div className="text-xs font-mono text-slate-400 mb-1.5 font-semibold">
                      Source Code Implementation:
                    </div>
                    <CodeViewer
                      code={selectedEvidence.code_snippet}
                      language={selectedEvidence.language || 'python'}
                      filePath={selectedEvidence.file_path}
                      startLine={selectedEvidence.start_line}
                      endLine={selectedEvidence.end_line}
                      title={selectedEvidence.chunk_name}
                    />
                  </div>
                )}
              </div>
            ) : (
              <div className="h-full flex flex-col items-center justify-center text-center p-6 text-slate-500 text-xs">
                <FileCode className="w-10 h-10 text-slate-700 mb-2" />
                <span>Ask a question or select a citation chip to inspect code chunks and verification details.</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
