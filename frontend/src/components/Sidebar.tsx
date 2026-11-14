import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import {
  BrainCircuit,
  LayoutDashboard,
  FolderGit2,
  MessageSquare,
  Search,
  History,
  Settings,
  PlusCircle,
  Sun,
  Moon,
  BookOpen,
  User,
  LogOut,
  ChevronLeft,
  ChevronRight,
  Sparkles
} from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { UserProfile } from '../types/api';

interface Props {
  collapsed: boolean;
  onToggleCollapse: () => void;
  onOpenAddModal: () => void;
  onOpenHelpModal: () => void;
  onOpenAuthModal: () => void;
  user: UserProfile | null;
  onLogout: () => void;
  isMobileOpen?: boolean;
  onCloseMobile?: () => void;
}

export const Sidebar: React.FC<Props> = ({
  collapsed,
  onToggleCollapse,
  onOpenAddModal,
  onOpenHelpModal,
  onOpenAuthModal,
  user,
  onLogout,
  isMobileOpen,
  onCloseMobile
}) => {
  const { theme, toggleTheme } = useTheme();

  const navItems = [
    { to: '/', label: 'Overview', icon: LayoutDashboard },
    { to: '/repositories', label: 'Repositories', icon: FolderGit2 },
    { to: '/assistant', label: 'Ask Assistant', icon: MessageSquare },
    { to: '/search', label: 'Search Code', icon: Search },
    { to: '/history', label: 'Indexing History', icon: History },
    { to: '/settings', label: 'Settings', icon: Settings },
  ];

  return (
    <>
      {/* Mobile Backdrop */}
      {isMobileOpen && (
        <div
          onClick={onCloseMobile}
          className="fixed inset-0 z-40 bg-slate-950/50 backdrop-blur-sm lg:hidden animate-in fade-in"
        />
      )}

      {/* Sidebar Container */}
      <aside
        className={`fixed top-0 bottom-0 left-0 z-40 flex flex-col bg-white dark:bg-slate-950 border-r border-slate-200 dark:border-slate-800 transition-all duration-300 ease-in-out ${
          collapsed ? 'w-20' : 'w-64'
        } ${
          isMobileOpen
            ? 'translate-x-0'
            : '-translate-x-full lg:translate-x-0'
        }`}
      >
        {/* Brand Header */}
        <div className="h-16 px-4 flex items-center justify-between border-b border-slate-200 dark:border-slate-800/80 shrink-0">
          <Link
            to="/"
            onClick={onCloseMobile}
            className={`flex items-center gap-2.5 overflow-hidden transition-opacity ${
              collapsed ? 'justify-center w-full' : ''
            }`}
          >
            <div className="w-9 h-9 rounded-xl bg-gradient-to-tr from-indigo-600 to-indigo-500 flex items-center justify-center text-white shadow-md shadow-indigo-500/20 shrink-0">
              <BrainCircuit className="w-5 h-5" />
            </div>
            {!collapsed && (
              <div className="truncate">
                <div className="text-sm font-bold text-slate-900 dark:text-white tracking-tight flex items-center gap-1.5">
                  <span>GitHub Assistant</span>
                  <span className="text-[10px] font-mono uppercase px-1.5 py-0.2 rounded bg-indigo-50 dark:bg-indigo-950 text-indigo-600 dark:text-indigo-400 border border-indigo-200 dark:border-indigo-800">
                    v5.0
                  </span>
                </div>
                <div className="text-[11px] text-slate-400 truncate">
                  Evidence-Grounded QA
                </div>
              </div>
            )}
          </Link>

          {!collapsed && (
            <button
              onClick={onToggleCollapse}
              className="hidden lg:flex p-1.5 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
              title="Collapse sidebar"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
          )}
        </div>

        {/* Primary Action Button (+ Add Repository) */}
        <div className="p-3 shrink-0">
          <button
            onClick={() => {
              if (onCloseMobile) onCloseMobile();
              onOpenAddModal();
            }}
            className={`w-full py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-all shadow-md shadow-indigo-500/20 flex items-center justify-center gap-2 group ${
              collapsed ? 'px-0' : 'px-3'
            }`}
            title="Add GitHub Repository"
          >
            <PlusCircle className="w-4 h-4 shrink-0 group-hover:rotate-90 transition-transform" />
            {!collapsed && <span>Add Repository</span>}
          </button>
        </div>

        {/* Navigation Items */}
        <nav className="flex-1 px-3 py-2 space-y-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon;
            return (
              <NavLink
                key={item.to}
                to={item.to}
                onClick={onCloseMobile}
                className={({ isActive }) =>
                  `flex items-center gap-3 px-3 py-2.5 rounded-xl text-xs font-medium transition-all ${
                    collapsed ? 'justify-center px-0' : ''
                  } ${
                    isActive
                      ? 'bg-indigo-50 dark:bg-indigo-950/60 text-indigo-600 dark:text-indigo-400 font-semibold shadow-xs'
                      : 'text-slate-600 dark:text-slate-400 hover:text-slate-900 dark:hover:text-slate-200 hover:bg-slate-100 dark:hover:bg-slate-900'
                  }`
                }
                title={collapsed ? item.label : undefined}
              >
                <Icon className="w-4 h-4 shrink-0" />
                {!collapsed && <span>{item.label}</span>}
              </NavLink>
            );
          })}
        </nav>

        {/* Desktop Expand Button when collapsed */}
        {collapsed && (
          <div className="hidden lg:flex justify-center p-2 border-t border-slate-200 dark:border-slate-800">
            <button
              onClick={onToggleCollapse}
              className="p-2 rounded-lg text-slate-400 hover:text-slate-600 dark:hover:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors"
              title="Expand sidebar"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        )}

        {/* Footer Utilities */}
        <div className="p-3 border-t border-slate-200 dark:border-slate-800/80 space-y-2 shrink-0 bg-slate-50/50 dark:bg-slate-950">
          {/* Theme Toggle & Docs Buttons */}
          <div className={`flex items-center gap-1.5 ${collapsed ? 'flex-col' : 'justify-between'}`}>
            <button
              onClick={toggleTheme}
              className={`p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors flex items-center gap-2 ${
                collapsed ? 'w-full justify-center' : 'flex-1 text-xs'
              }`}
              title={theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode'}
            >
              {theme === 'dark' ? (
                <>
                  <Sun className="w-4 h-4 text-amber-400" />
                  {!collapsed && <span>Light Mode</span>}
                </>
              ) : (
                <>
                  <Moon className="w-4 h-4 text-indigo-600" />
                  {!collapsed && <span>Dark Mode</span>}
                </>
              )}
            </button>

            <button
              onClick={onOpenHelpModal}
              className={`p-2 rounded-xl text-slate-500 hover:text-slate-900 dark:hover:text-slate-100 hover:bg-slate-100 dark:hover:bg-slate-900 transition-colors flex items-center gap-2 ${
                collapsed ? 'w-full justify-center' : 'text-xs'
              }`}
              title="Documentation & Guide"
            >
              <BookOpen className="w-4 h-4 text-sky-500" />
              {!collapsed && <span className="hidden sm:inline">Docs</span>}
            </button>
          </div>

          {/* User Profile / Auth Area */}
          <div className="pt-2 border-t border-slate-200/80 dark:border-slate-800/80">
            {user ? (
              <div
                className={`flex items-center justify-between p-2 rounded-xl bg-slate-100 dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-xs ${
                  collapsed ? 'flex-col gap-2' : ''
                }`}
              >
                <div className="flex items-center gap-2 overflow-hidden">
                  <div className="w-7 h-7 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-xs shrink-0 uppercase">
                    {user.username.slice(0, 2)}
                  </div>
                  {!collapsed && (
                    <div className="truncate">
                      <div className="font-semibold text-slate-900 dark:text-white truncate">
                        {user.username}
                      </div>
                      <div className="text-[10px] text-slate-400 truncate">
                        {user.saved_repositories?.length || 0} saved repos
                      </div>
                    </div>
                  )}
                </div>
                <button
                  onClick={onLogout}
                  className="p-1 text-slate-400 hover:text-rose-500 rounded transition-colors"
                  title="Sign Out"
                >
                  <LogOut className="w-3.5 h-3.5" />
                </button>
              </div>
            ) : (
              <button
                onClick={onOpenAuthModal}
                className={`w-full py-2 px-3 rounded-xl border border-slate-200 dark:border-slate-800 hover:border-indigo-400 dark:hover:border-indigo-600 text-xs text-slate-700 dark:text-slate-300 font-medium transition-colors flex items-center justify-center gap-2 ${
                  collapsed ? 'px-0' : ''
                }`}
                title="Sign In"
              >
                <User className="w-4 h-4 text-indigo-500" />
                {!collapsed && <span>Sign In</span>}
              </button>
            )}
          </div>
        </div>
      </aside>
    </>
  );
};
