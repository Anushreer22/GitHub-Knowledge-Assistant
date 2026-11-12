import React, { useEffect, useState } from 'react';
import { Link, useLocation } from 'react-router-dom';
import {
  BrainCircuit,
  MessageSquare,
  Search,
  FolderGit2,
  LayoutDashboard,
  Database,
  CheckCircle2,
  AlertCircle
} from 'lucide-react';
import { api } from '../services/api';
import { HealthResponse } from '../types/api';

export const Navbar: React.FC = () => {
  const location = useLocation();
  const [health, setHealth] = useState<HealthResponse | null>(null);

  useEffect(() => {
    api.getHealth()
      .then(setHealth)
      .catch((err) => console.warn("Backend health check failed:", err));
  }, []);

  const navLinks = [
    { to: '/assistant', label: 'AI Assistant', icon: MessageSquare },
    { to: '/search', label: 'Code Search', icon: Search },
    { to: '/repositories', label: 'Repositories', icon: FolderGit2 },
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/indexing', label: 'Indexing', icon: Database },
  ];

  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-slate-950/80 border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <Link to="/" className="flex items-center gap-2.5 group">
          <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-400 flex items-center justify-center text-white shadow-lg shadow-indigo-500/25 group-hover:scale-105 transition-transform">
            <BrainCircuit className="w-5 h-5" />
          </div>
          <div>
            <div className="text-base font-bold text-white tracking-tight flex items-center gap-1.5">
              GitHub Knowledge Assistant
              <span className="text-[10px] uppercase font-mono px-1.5 py-0.2 rounded bg-indigo-500/20 text-indigo-400 border border-indigo-500/30">
                v4.0
              </span>
            </div>
            <div className="text-[11px] text-slate-400 -mt-0.5 hidden sm:block">
              Evidence-Grounded Code QA & Hybrid Retrieval
            </div>
          </div>
        </Link>

        {/* Navigation links */}
        <nav className="hidden md:flex items-center gap-1">
          {navLinks.map((link) => {
            const Icon = link.icon;
            const isActive = location.pathname === link.to;
            return (
              <Link
                key={link.to}
                to={link.to}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                  isActive
                    ? 'bg-slate-800 text-white shadow-sm'
                    : 'text-slate-400 hover:text-slate-200 hover:bg-slate-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-indigo-400' : 'text-slate-400'}`} />
                {link.label}
              </Link>
            );
          })}
        </nav>

        {/* Health status badge */}
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-900 border border-slate-800 text-xs">
            {health?.status === 'ok' ? (
              <>
                <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                <span className="text-slate-300 font-mono hidden sm:inline">Backend Ready</span>
                <span className="text-slate-500 text-[11px] font-mono hidden lg:inline">
                  ({health.repositories_count} repos)
                </span>
              </>
            ) : (
              <>
                <span className="w-2 h-2 rounded-full bg-amber-500"></span>
                <span className="text-amber-400 font-mono text-xs">Connecting...</span>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
};
