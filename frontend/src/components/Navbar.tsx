import React from 'react';
import { Bot, Play, Activity, ShieldCheck, RefreshCw, LogOut } from 'lucide-react';
import { SystemHealth } from '../types';

interface NavbarProps {
  health: SystemHealth | null;
  onNewRun: () => void;
  onRefresh: () => void;
  isRefreshing?: boolean;
  userEmail: string;
  onSignOut: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  health,
  onNewRun,
  onRefresh,
  isRefreshing = false,
  userEmail,
  onSignOut,
}) => {
  return (
    <header className="glass-header sticky top-0 z-40 px-6 py-3.5 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <span className="hidden text-xs text-slate-400 lg:inline">{userEmail}</span>
        <div className="relative flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 shadow-lg shadow-indigo-500/25">
          <Bot className="w-5 h-5 text-white" />
          <span className="absolute -top-0.5 -right-0.5 w-2.5 h-2.5 bg-emerald-400 rounded-full border-2 border-slate-950 animate-pulse" />
        </div>
        <div>
          <div className="flex items-center gap-2">
            <h1 className="text-lg font-bold tracking-tight text-white">CogniOps</h1>
            <span className="px-2 py-0.5 text-[10px] font-semibold bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-full">
              Multi-Agent AI
            </span>
          </div>
          <p className="text-xs text-slate-400 hidden sm:block">
            Autonomous Operations Coordinator • Intake ➔ Planning ➔ Review
          </p>
        </div>
      </div>

      <div className="flex items-center gap-3">
        {health && (
          <div className="hidden md:flex items-center gap-2.5 px-3 py-1.5 rounded-lg bg-slate-900/80 border border-slate-800 text-xs">
            <Activity className="w-3.5 h-3.5 text-emerald-400" />
            <span className="text-slate-400">Model:</span>
            <span className="font-semibold text-slate-200">{health.llm_model || health.llm_provider}</span>
            {health.llm_configured && (
              <span className="flex items-center gap-1 text-emerald-400 font-medium">
                <ShieldCheck className="w-3.5 h-3.5" /> Ready
              </span>
            )}
            {health.demo_faults_enabled && (
              <span className="text-amber-300 font-medium">Simulated faults enabled</span>
            )}
          </div>
        )}

        <button
          onClick={onRefresh}
          title="Refresh run state"
          className="btn btn-secondary p-2 rounded-lg text-slate-300 hover:text-white"
        >
          <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin' : ''}`} />
        </button>

        <button
          onClick={onNewRun}
          className="btn btn-primary shadow-lg shadow-indigo-500/20"
        >
          <Play className="w-4 h-4 fill-current" />
          <span>New Coordination</span>
        </button>
        <button
          onClick={onSignOut}
          title="Sign out"
          aria-label="Sign out"
          className="btn btn-secondary p-2"
        >
          <LogOut className="h-4 w-4" />
        </button>
      </div>
    </header>
  );
};
