import React from 'react';
import {
  Menu,
  PlusCircle,
  FolderGit2,
  CheckCircle2,
  AlertCircle,
  Search,
  Sparkles
} from 'lucide-react';
import { HealthResponse, UserProfile } from '../types/api';
import { Link } from 'react-router-dom';

interface Props {
  onToggleMobileMenu: () => void;
  onOpenAddModal: () => void;
  health: HealthResponse | null;
  user: UserProfile | null;
  onOpenAuthModal: () => void;
}

export const HeaderBar: React.FC<Props> = ({
  onToggleMobileMenu,
  onOpenAddModal,
  health,
  user,
  onOpenAuthModal
}) => {
  return (
    <header className="sticky top-0 z-30 h-16 bg-white/80 dark:bg-slate-950/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 flex items-center justify-between px-4 sm:px-6">
      {/* Left: Mobile Toggle & Quick Action */}
      <div className="flex items-center gap-3">
        <button
          onClick={onToggleMobileMenu}
          className="lg:hidden p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
          title="Open Menu"
        >
          <Menu className="w-5 h-5" />
        </button>

        {/* Global Quick Search Shortcut */}
        <Link
          to="/search"
          className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 hover:border-slate-300 dark:hover:border-slate-700 transition-all w-48 md:w-64"
        >
          <Search className="w-3.5 h-3.5 text-slate-400" />
          <span className="truncate">Search functions, classes...</span>
          <kbd className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 text-slate-400">
            /
          </kbd>
        </Link>
      </div>

      {/* Right: Health Badge & Primary Action */}
      <div className="flex items-center gap-3">
        {/* Backend Status Pill */}
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs">
          {health?.status === 'ok' ? (
            <>
              <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" />
              <span className="text-slate-700 dark:text-slate-300 font-mono text-[11px] hidden sm:inline">
                Backend Ready
              </span>
              <span className="text-slate-400 font-mono text-[10px] hidden md:inline">
                ({health.repositories_count} repos)
              </span>
            </>
          ) : (
            <>
              <span className="w-2 h-2 rounded-full bg-amber-500" />
              <span className="text-amber-600 dark:text-amber-400 font-mono text-[11px]">
                Connecting...
              </span>
            </>
          )}
        </div>

        {/* Quick Add Repository button on desktop */}
        <button
          onClick={onOpenAddModal}
          className="hidden md:flex items-center gap-1.5 px-3 py-1.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-medium transition-colors shadow-sm"
        >
          <PlusCircle className="w-3.5 h-3.5" />
          <span>Add Repo</span>
        </button>
      </div>
    </header>
  );
};
