import React, { useState, useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { api } from '../services/api';
import { QueryResponse, RepositoryInfo, EvidenceItem } from '../types/api';
import { ConfidenceBadge } from '../components/ConfidenceBadge';
import { ClassificationBadge } from '../components/ClassificationBadge';
import { CodeViewer } from '../components/CodeViewer';
import {
  MessageSquare,
  Send,
  Sparkles,
  Layers,
  ShieldCheck,
  FileCode,
  ArrowRight,
  Filter,
  CheckCircle2,
  RefreshCw,
  X,
  ThumbsUp,
  ThumbsDown,
  AlertTriangle,
  FileQuestion,
  Check,
  Copy,
  Trash2,
  HelpCircle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Cpu
} from 'lucide-react';

interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  text: string;
  data?: QueryResponse;
  timestamp: string;
}

const SUGGESTED_QUESTIONS = [
  'Where is authentication implemented?',
  'Explain the main application entry point.',
  'Which functions call validate_user()?',
  'Where is database connectivity configured?',
  'Which tests verify payment validation?',
  'How does the application process user requests?'
];

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
  const [feedbackStatus, setFeedbackStatus] = useState<{ [msgId: string]: string }>({});
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api.listRepositories()
      .then(setRepos)
      .catch((err) => console.error('Failed to load repositories:', err));
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

    setMessages((prev) => [...prev, userMsg]);
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

      setMessages((prev) => [...prev, assistantMsg]);
      if (response.evidence && response.evidence.length > 0) {
        setSelectedEvidence(response.evidence[0]);
      }
    } catch (err: any) {
      const errorMsg: ChatMessage = {
        id: `err-${Date.now()}`,
        sender: 'assistant',
        text: `Error connecting to assistant: ${err.response?.data?.detail || err.message || 'Service unavailable'}. Please verify the backend is running.`,
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setLoading(false);
    }
  };

  const handleFeedback = async (
    msgId: string,
    question: string,
    type: 'helpful' | 'not_helpful' | 'incorrect_citation' | 'missing_context',
    citation?: string
  ) => {
    try {
      await api.submitFeedback({
        query_or_question: question,
        feedback_type: type,
        citation: citation,
        repo_id: selectedRepo || undefined
      });
      setFeedbackStatus((prev) => ({ ...prev, [msgId]: type }));
    } catch (e) {
      console.error('Failed to submit feedback', e);
    }
  };

  const handleCopyAnswer = async (text: string, id: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedId(id);
      setTimeout(() => setCopiedId(null), 2000);
    } catch (e) {
      console.error('Copy failed', e);
    }
  };

  const handleClearChat = () => {
    setMessages([]);
    setSelectedEvidence(null);
  };

  const activeRepoObj = repos.find((r) => r.repo_id === selectedRepo);

  return (
    <div className="h-[calc(100vh-6.5rem)] flex flex-col space-y-4 animate-in fade-in duration-200">
      {/* 1. Header Toolbar */}
      <div className="p-4 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs flex flex-wrap items-center justify-between gap-3 shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shrink-0">
            <MessageSquare className="w-4 h-4" />
          </div>
          <div>
            <h1 className="text-base font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
              <span>AI Code Assistant</span>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded-full bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800 hidden sm:inline-flex items-center gap-1">
                <CheckCircle2 className="w-2.5 h-2.5" />
                <span>Evidence Grounded</span>
              </span>
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400 hidden md:block">
              Ask natural-language questions and receive answers supported by exact source code citations.
            </p>
          </div>
        </div>

        {/* Right controls: Repo Selector, Mode Toggle, Clear Chat */}
        <div className="flex items-center gap-2 flex-wrap ml-auto">
          {/* Repository Selector */}
          <div className="relative">
            <select
              value={selectedRepo}
              onChange={(e) => setSelectedRepo(e.target.value)}
              className="text-xs font-medium pl-3 pr-8 py-1.5 rounded-xl border border-slate-200 dark:border-slate-800 bg-slate-50 dark:bg-slate-950 text-slate-800 dark:text-slate-200 focus:outline-none focus:border-indigo-500 transition-colors cursor-pointer appearance-none"
            >
              <option value="">All Repositories ({repos.length})</option>
              {repos.map((r) => (
                <option key={r.repo_id} value={r.repo_id}>
                  {r.full_name || r.repo_id} ({r.chunk_count} chunks)
                </option>
              ))}
            </select>
            <ChevronDown className="w-3.5 h-3.5 text-slate-400 absolute right-2.5 top-2.5 pointer-events-none" />
          </div>

          {/* Retrieval Mode Selector */}
          <div className="flex items-center p-0.5 rounded-xl bg-slate-100 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs">
            <button
              onClick={() => setMode('hybrid')}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                mode === 'hybrid'
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
              title="Hybrid: Lexical BM25 + Semantic CodeEncoder with RRF & Symbol Boost"
            >
              Hybrid
            </button>
            <button
              onClick={() => setMode('bm25')}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                mode === 'bm25'
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
              title="BM25: Sub-token identifier lexical matching"
            >
              BM25
            </button>
            <button
              onClick={() => setMode('dense')}
              className={`px-2.5 py-1 rounded-lg font-medium transition-colors ${
                mode === 'dense'
                  ? 'bg-white dark:bg-slate-800 text-indigo-600 dark:text-indigo-400 shadow-xs'
                  : 'text-slate-500 hover:text-slate-900 dark:hover:text-slate-200'
              }`}
              title="Dense: Custom Transformer CodeEncoder embeddings"
            >
              Dense
            </button>
          </div>

          {/* Clear Chat Button */}
          {messages.length > 0 && (
            <button
              onClick={handleClearChat}
              className="p-1.5 rounded-xl border border-slate-200 dark:border-slate-800 text-slate-400 hover:text-rose-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
              title="Clear conversation"
            >
              <Trash2 className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>

      {/* 2. Split Workspace: Left Chat (60%), Right Evidence Inspector (40%) */}
      <div className="flex-1 grid grid-cols-1 lg:grid-cols-12 gap-4 overflow-hidden min-h-0">
        {/* Left Column: Chat History & Input */}
        <div className="lg:col-span-7 flex flex-col rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs overflow-hidden">
          {/* Chat Messages Stream */}
          <div className="flex-1 overflow-y-auto p-4 sm:p-6 space-y-5">
            {messages.length === 0 ? (
              /* Empty State */
              <div className="h-full flex flex-col items-center justify-center text-center p-6 space-y-6">
                <div className="w-16 h-16 rounded-3xl bg-indigo-50 dark:bg-indigo-950/60 border border-indigo-200 dark:border-indigo-800/80 flex items-center justify-center text-indigo-600 dark:text-indigo-400 shadow-sm">
                  <Sparkles className="w-8 h-8" />
                </div>

                <div className="space-y-1.5 max-w-md">
                  <h2 className="text-xl font-bold text-slate-900 dark:text-white">
                    Ask anything about your codebase.
                  </h2>
                  <p className="text-xs text-slate-500 dark:text-slate-400 leading-relaxed">
                    Explore logic, trace function callers, or inspect execution flows. Answers are mathematically grounded in verified AST chunks.
                  </p>
                </div>

                {/* Suggested Questions Grid */}
                <div className="w-full max-w-lg space-y-2">
                  <div className="text-[11px] uppercase tracking-wider font-semibold font-mono text-slate-400">
                    Suggested Questions
                  </div>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
                    {SUGGESTED_QUESTIONS.map((questionText, idx) => (
                      <button
                        key={idx}
                        onClick={() => handleSend(questionText)}
                        className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950/70 border border-slate-200 dark:border-slate-800/80 hover:border-indigo-400 dark:hover:border-indigo-600/70 text-slate-700 dark:text-slate-300 text-xs text-left transition-all group flex items-start gap-2 shadow-2xs"
                      >
                        <ArrowRight className="w-3.5 h-3.5 text-indigo-500 shrink-0 mt-0.5 group-hover:translate-x-0.5 transition-transform" />
                        <span className="leading-snug">{questionText}</span>
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : (
              /* Messages List */
              messages.map((msg) => (
                <div
                  key={msg.id}
                  className={`flex flex-col ${msg.sender === 'user' ? 'items-end' : 'items-start'} space-y-1`}
                >
                  <div className="text-[10px] text-slate-400 px-1 font-mono">
                    {msg.sender === 'user' ? 'You' : 'Knowledge Assistant'} • {msg.timestamp}
                  </div>

                  {msg.sender === 'user' ? (
                    <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-indigo-600 text-white px-4 py-2.5 text-sm font-medium shadow-sm">
                      {msg.text}
                    </div>
                  ) : (
                    /* Assistant Response Card */
                    <div className="w-full max-w-full rounded-2xl rounded-tl-sm bg-slate-50 dark:bg-slate-950/90 border border-slate-200 dark:border-slate-800 p-4 sm:p-5 text-sm text-slate-800 dark:text-slate-200 space-y-4 shadow-xs">
                      {/* Meta badges */}
                      {msg.data && (
                        <div className="flex items-center gap-2 flex-wrap pb-3 border-b border-slate-200 dark:border-slate-800/80 text-xs">
                          <ConfidenceBadge confidence={msg.data.confidence_indicator} />
                          <ClassificationBadge classification={msg.data.match_classification} />
                          <span className="px-2 py-0.5 rounded-full text-[10px] font-mono uppercase bg-slate-200 dark:bg-slate-800 text-slate-600 dark:text-slate-400">
                            {msg.data.retrieval_method}
                          </span>
                        </div>
                      )}

                      {/* Direct Answer Prose */}
                      <div className="leading-relaxed text-sm text-slate-800 dark:text-slate-200 space-y-2 whitespace-pre-line">
                        {msg.text}
                      </div>

                      {/* Evidence Citations Bar */}
                      {msg.data && msg.data.evidence && msg.data.evidence.length > 0 && (
                        <div className="pt-3 border-t border-slate-200 dark:border-slate-800/80 space-y-2">
                          <div className="text-[11px] uppercase tracking-wider font-mono text-slate-500 dark:text-slate-400 font-semibold flex items-center justify-between">
                            <span>Retrieved Source Evidence ({msg.data.evidence.length})</span>
                            <span className="text-[10px] text-slate-400 font-normal">Click citation to inspect</span>
                          </div>

                          <div className="flex flex-wrap gap-2">
                            {msg.data.evidence.map((ev, i) => {
                              const isSelected = selectedEvidence?.citation === ev.citation;
                              return (
                                <button
                                  key={i}
                                  onClick={() => setSelectedEvidence(ev)}
                                  className={`text-left text-xs font-mono px-3 py-1.5 rounded-xl border transition-all flex items-center gap-2 ${
                                    isSelected
                                      ? 'bg-indigo-50 dark:bg-indigo-950/50 border-indigo-400 dark:border-indigo-500 text-indigo-700 dark:text-indigo-300 font-semibold shadow-xs'
                                      : 'bg-white dark:bg-slate-900 border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400'
                                  }`}
                                >
                                  <FileCode className="w-3.5 h-3.5 text-indigo-500 shrink-0" />
                                  <span className="truncate max-w-[150px]">{ev.file_path.split('/').pop()}</span>
                                  <span className="text-slate-400 text-[10px]">
                                    L{ev.start_line}-L{ev.end_line}
                                  </span>
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      )}

                      {/* Response Footer: Copy & Feedback */}
                      <div className="pt-3 border-t border-slate-200 dark:border-slate-800/80 flex items-center justify-between flex-wrap gap-2 text-xs">
                        {/* Copy Answer */}
                        <button
                          onClick={() => handleCopyAnswer(msg.text, msg.id)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-slate-500 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-200/60 dark:hover:bg-slate-800 transition-colors text-xs font-medium"
                        >
                          {copiedId === msg.id ? (
                            <>
                              <Check className="w-3.5 h-3.5 text-emerald-500" />
                              <span className="text-emerald-500">Copied</span>
                            </>
                          ) : (
                            <>
                              <Copy className="w-3.5 h-3.5" />
                              <span>Copy Answer</span>
                            </>
                          )}
                        </button>

                        {/* User Feedback buttons */}
                        {msg.data && msg.data.is_answered && (
                          <div className="flex items-center gap-1">
                            {feedbackStatus[msg.id] ? (
                              <span className="flex items-center gap-1 text-[11px] font-mono text-emerald-600 dark:text-emerald-400">
                                <Check className="w-3.5 h-3.5" /> Feedback recorded
                              </span>
                            ) : (
                              <div className="flex items-center gap-1">
                                <button
                                  onClick={() => handleFeedback(msg.id, msg.data!.question, 'helpful', msg.data!.citations?.[0])}
                                  className="p-1.5 rounded-lg text-slate-400 hover:text-emerald-500 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                                  title="Helpful"
                                >
                                  <ThumbsUp className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleFeedback(msg.id, msg.data!.question, 'not_helpful', msg.data!.citations?.[0])}
                                  className="p-1.5 rounded-lg text-slate-400 hover:text-rose-500 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                                  title="Not helpful"
                                >
                                  <ThumbsDown className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleFeedback(msg.id, msg.data!.question, 'incorrect_citation', msg.data!.citations?.[0])}
                                  className="p-1.5 rounded-lg text-slate-400 hover:text-amber-500 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                                  title="Incorrect citation"
                                >
                                  <AlertTriangle className="w-3.5 h-3.5" />
                                </button>
                                <button
                                  onClick={() => handleFeedback(msg.id, msg.data!.question, 'missing_context', msg.data!.citations?.[0])}
                                  className="p-1.5 rounded-lg text-slate-400 hover:text-indigo-500 hover:bg-slate-200 dark:hover:bg-slate-800 transition-colors"
                                  title="Missing context"
                                >
                                  <FileQuestion className="w-3.5 h-3.5" />
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              ))
            )}

            {/* Loading Indicator */}
            {loading && (
              <div className="flex items-center gap-3 p-4 rounded-2xl bg-indigo-50 dark:bg-indigo-950/40 border border-indigo-200 dark:border-indigo-800 text-xs text-indigo-900 dark:text-indigo-300">
                <RefreshCw className="w-4 h-4 text-indigo-500 animate-spin shrink-0" />
                <span>
                  Segmenting AST tokens, executing hybrid retrieval (BM25 + CodeEncoder), and verifying code evidence...
                </span>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {/* Chat Input Bar */}
          <div className="p-3 sm:p-4 border-t border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900/90">
            <form
              onSubmit={(e) => {
                e.preventDefault();
                handleSend();
              }}
              className="flex items-center gap-2"
            >
              <input
                type="text"
                placeholder={
                  selectedRepo
                    ? `Ask a question about ${selectedRepo}...`
                    : 'Ask anything about your codebase (e.g., Where is check_auth defined?)...'
                }
                value={inputQuestion}
                onChange={(e) => setInputQuestion(e.target.value)}
                disabled={loading}
                className="flex-1 px-4 py-2.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-sm text-slate-900 dark:text-slate-100 placeholder-slate-400 dark:placeholder-slate-500 focus:outline-none focus:border-indigo-500 transition-colors"
              />
              <button
                type="submit"
                disabled={loading || !inputQuestion.trim()}
                className="px-4 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-medium text-sm transition-all shadow-md shadow-indigo-500/20 flex items-center gap-1.5"
              >
                <Send className="w-4 h-4" />
                <span className="hidden sm:inline">Ask</span>
              </button>
            </form>
          </div>
        </div>

        {/* Right Column: Code Evidence Inspector (Sticky on Desktop) */}
        <div className="hidden lg:flex lg:col-span-5 flex-col rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs overflow-hidden">
          {/* Inspector Header */}
          <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-950/50">
            <div className="flex items-center gap-2">
              <FileCode className="w-4 h-4 text-indigo-500" />
              <h3 className="text-xs font-bold text-slate-900 dark:text-white uppercase tracking-wider font-mono">
                Source Evidence Inspector
              </h3>
            </div>
            {selectedEvidence && (
              <ClassificationBadge classification={selectedEvidence.match_classification} />
            )}
          </div>

          {/* Inspector Body */}
          <div className="flex-1 overflow-y-auto p-4 space-y-4">
            {selectedEvidence ? (
              <div className="space-y-4">
                {/* File details card */}
                <div className="p-3.5 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 space-y-2">
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">FILE</span>
                    <span className="text-slate-800 dark:text-slate-200 font-semibold truncate max-w-[200px]" title={selectedEvidence.file_path}>
                      {selectedEvidence.file_path}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">RANGE</span>
                    <span className="text-indigo-600 dark:text-indigo-400 font-semibold">
                      Lines {selectedEvidence.start_line}–{selectedEvidence.end_line}
                    </span>
                  </div>
                  <div className="flex items-center justify-between text-xs font-mono">
                    <span className="text-slate-400">SYMBOL</span>
                    <span className="text-emerald-600 dark:text-emerald-400 font-semibold truncate">
                      {selectedEvidence.chunk_name} ({selectedEvidence.chunk_type})
                    </span>
                  </div>
                </div>

                {/* Code Viewer with Syntax Highlighting */}
                <div>
                  <div className="text-[11px] uppercase tracking-wider font-semibold font-mono text-slate-400 mb-1.5">
                    Source Code Snippet
                  </div>
                  <CodeViewer
                    code={selectedEvidence.code_snippet || ''}
                    language={selectedEvidence.language || 'python'}
                    filePath={selectedEvidence.file_path}
                    startLine={selectedEvidence.start_line}
                    endLine={selectedEvidence.end_line}
                  />
                </div>
              </div>
            ) : (
              /* No selection state */
              <div className="h-full flex flex-col items-center justify-center text-center p-8 space-y-3">
                <FileCode className="w-10 h-10 text-slate-300 dark:text-slate-700" />
                <h4 className="text-sm font-bold text-slate-700 dark:text-slate-300">
                  No Code Selected
                </h4>
                <p className="text-xs text-slate-400 max-w-xs leading-relaxed">
                  Ask a question on the left, then click any citation pill to inspect its syntax-highlighted source code here.
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
