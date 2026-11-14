import React, { useEffect, useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import { api } from '../services/api';
import { HealthResponse, UserProfile, IndexResponse } from '../types/api';
import {
  Settings,
  Sun,
  Moon,
  Database,
  Activity,
  ShieldCheck,
  User,
  LogOut,
  RefreshCw,
  CheckCircle2,
  AlertCircle,
  Cpu,
  Layers,
  BookOpen
} from 'lucide-react';

export const SettingsPage: React.FC = () => {
  const { theme, setTheme } = useTheme();

  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [user, setUser] = useState<UserProfile | null>(null);
  const [reindexing, setReindexing] = useState(false);
  const [reindexResult, setReindexResult] = useState<IndexResponse | null>(null);
  const [reindexError, setReindexError] = useState<string | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch((err) => console.warn('Health check failed:', err));

    const token = localStorage.getItem('token');
    if (token) {
      api.getMe()
        .then(setUser)
        .catch(() => setUser(null));
    }
  }, []);

  const handleReindex = async () => {
    setReindexing(true);
    setReindexResult(null);
    setReindexError(null);
    try {
      const res = await api.triggerIndexing(10000);
      setReindexResult(res);
      const updatedHealth = await api.getHealth();
      setHealth(updatedHealth);
    } catch (err: any) {
      setReindexError(err.response?.data?.detail || err.message || 'Indexing failed.');
    } finally {
      setReindexing(false);
    }
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setUser(null);
    window.location.reload();
  };

  return (
    <div className="max-w-4xl space-y-6 animate-in fade-in duration-200">
      {/* Header Card */}
      <div className="p-5 sm:p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs">
        <h1 className="text-xl sm:text-2xl font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-2">
          <Settings className="w-5 h-5 text-indigo-500" />
          <span>System Settings & Preferences</span>
        </h1>
        <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">
          Customize UI theme, inspect backend diagnostics, and manage search index health.
        </p>
      </div>

      {/* 1. Theme Preferences */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-4">
        <div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-white">
            Interface Theme
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Select your preferred display mode.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-md">
          {/* Dark Mode Card */}
          <div
            onClick={() => setTheme('dark')}
            className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center gap-3 ${
              theme === 'dark'
                ? 'border-indigo-500 bg-indigo-50/20 dark:bg-indigo-950/40 text-indigo-900 dark:text-white font-semibold'
                : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 dark:hover:border-slate-700 text-slate-600 dark:text-slate-400'
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-slate-900 text-amber-400 flex items-center justify-center shrink-0">
              <Moon className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold">Dark Theme</div>
              <div className="text-[11px] text-slate-400 font-normal">Sleek, low-contrast dark mode</div>
            </div>
          </div>

          {/* Light Mode Card */}
          <div
            onClick={() => setTheme('light')}
            className={`p-4 rounded-xl border cursor-pointer transition-all flex items-center gap-3 ${
              theme === 'light'
                ? 'border-indigo-500 bg-indigo-50/40 text-indigo-900 font-semibold'
                : 'border-slate-200 dark:border-slate-800 hover:border-slate-300 text-slate-600 dark:text-slate-400'
            }`}
          >
            <div className="w-8 h-8 rounded-lg bg-indigo-100 text-indigo-700 flex items-center justify-center shrink-0">
              <Sun className="w-4 h-4" />
            </div>
            <div>
              <div className="text-xs font-bold">Light Theme</div>
              <div className="text-[11px] text-slate-400 font-normal">Clean, high-readability daylight mode</div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Backend Health & Diagnostics */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald-500" />
              <span>Backend Retrieval Diagnostics</span>
            </h2>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              Status of local BM25 and dense Transformer embedding stores.
            </p>
          </div>

          <span
            className={`px-3 py-1 rounded-full text-xs font-mono font-medium flex items-center gap-1.5 ${
              health?.status === 'ok'
                ? 'bg-emerald-50 dark:bg-emerald-950 text-emerald-600 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-800'
                : 'bg-amber-50 dark:bg-amber-950 text-amber-600 dark:text-amber-400 border border-amber-200 dark:border-amber-800'
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
            <span>{health?.status === 'ok' ? 'Online' : 'Connecting'}</span>
          </span>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-slate-400 block text-[10px]">API VERSION</span>
            <span className="text-slate-800 dark:text-slate-200 font-bold">{health?.version || '5.0.0'}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-slate-400 block text-[10px]">REPOSITORIES</span>
            <span className="text-indigo-600 dark:text-indigo-400 font-bold">{health?.repositories_count || 0}</span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-slate-400 block text-[10px]">BM25 INDEX</span>
            <span className={health?.bm25_index_ready ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-rose-500 font-bold'}>
              {health?.bm25_index_ready ? 'Ready' : 'Not built'}
            </span>
          </div>
          <div className="p-3 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800">
            <span className="text-slate-400 block text-[10px]">DENSE VECTOR STORE</span>
            <span className={health?.dense_index_ready ? 'text-emerald-600 dark:text-emerald-400 font-bold' : 'text-rose-500 font-bold'}>
              {health?.dense_index_ready ? 'Ready' : 'Not built'}
            </span>
          </div>
        </div>

        {/* Rebuild Index action */}
        <div className="pt-2">
          <button
            onClick={handleReindex}
            disabled={reindexing}
            className="px-4 py-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 text-xs font-semibold text-slate-800 dark:text-slate-200 transition-colors flex items-center gap-2"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${reindexing ? 'animate-spin' : ''}`} />
            <span>{reindexing ? 'Rebuilding Persistent Indexes...' : 'Rebuild Indexes from Chunks'}</span>
          </button>
        </div>

        {reindexResult && (
          <div className="p-3 rounded-xl bg-emerald-50 dark:bg-emerald-950/40 border border-emerald-200 dark:border-emerald-800 text-xs text-emerald-800 dark:text-emerald-300">
            {reindexResult.message}
          </div>
        )}
        {reindexError && (
          <div className="p-3 rounded-xl bg-rose-50 dark:bg-rose-950/40 border border-rose-200 dark:border-rose-900 text-xs text-rose-700 dark:text-rose-400">
            {reindexError}
          </div>
        )}
      </div>

      {/* 3. User Account Section */}
      <div className="p-6 rounded-2xl border border-slate-200 dark:border-slate-800 bg-white dark:bg-slate-900 shadow-xs space-y-4">
        <div>
          <h2 className="text-sm font-bold text-slate-900 dark:text-white flex items-center gap-2">
            <User className="w-4 h-4 text-indigo-500" />
            <span>User Account</span>
          </h2>
          <p className="text-xs text-slate-500 dark:text-slate-400">
            Authentication state, saved repositories, and personal search history.
          </p>
        </div>

        {user ? (
          <div className="space-y-3">
            <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-9 h-9 rounded-xl bg-indigo-600 text-white font-bold text-sm flex items-center justify-center uppercase">
                  {user.username.slice(0, 2)}
                </div>
                <div>
                  <div className="text-sm font-bold text-slate-900 dark:text-white">{user.username}</div>
                  <div className="text-xs text-slate-400">{user.email}</div>
                </div>
              </div>

              <button
                onClick={handleLogout}
                className="px-3 py-1.5 rounded-lg border border-slate-200 dark:border-slate-800 text-slate-600 dark:text-slate-400 hover:text-rose-600 dark:hover:text-rose-400 hover:bg-slate-100 dark:hover:bg-slate-800 text-xs font-medium transition-colors flex items-center gap-1.5"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span>Sign Out</span>
              </button>
            </div>

            <div className="text-xs text-slate-500 dark:text-slate-400 font-mono">
              Saved Repositories: {user.saved_repositories?.length || 0} • Searches Recorded: {user.search_history?.length || 0}
            </div>
          </div>
        ) : (
          <div className="p-4 rounded-xl bg-slate-50 dark:bg-slate-950 border border-slate-200 dark:border-slate-800 text-xs text-slate-500 dark:text-slate-400 flex items-center justify-between">
            <span>You are currently exploring as an anonymous developer.</span>
            <span className="font-semibold text-indigo-600 dark:text-indigo-400">
              Sign in via the left sidebar to bookmark repositories.
            </span>
          </div>
        )}
      </div>
    </div>
  );
};
