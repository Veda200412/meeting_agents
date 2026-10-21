import React from 'react';
import { RunSummary, RunStatus } from '../types';
import { Play, ArrowRight, CheckCircle2, AlertTriangle, Clock, Layers } from 'lucide-react';

interface RunDashboardProps {
  runs: RunSummary[];
  selectedRunId: string | null;
  onSelectRun: (id: string) => void;
  onNewRun: () => void;
}

export const RunDashboard: React.FC<RunDashboardProps> = ({
  runs,
  selectedRunId,
  onSelectRun,
  onNewRun,
}) => {
  const approvedCount = runs.filter((r) => r.status === 'APPROVED').length;
  const activeCount = runs.filter(
    (r) =>
      r.status === 'INTAKE_RUNNING' ||
      r.status === 'PLANNING_RUNNING' ||
      r.status === 'REVIEW_RUNNING' ||
      r.status === 'NEEDS_CORRECTION'
  ).length;

  const getStatusBadge = (status: RunStatus) => {
    switch (status) {
      case 'APPROVED':
        return 'status-approved';
      case 'INTAKE_RUNNING':
      case 'PLANNING_RUNNING':
      case 'REVIEW_RUNNING':
        return 'status-running';
      case 'NEEDS_CORRECTION':
        return 'status-correction';
      case 'FAILED':
      case 'INTERRUPTED':
        return 'status-failed';
      default:
        return 'status-created';
    }
  };

  return (
    <div className="space-y-6">
      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="glass-panel p-4">
          <div className="text-xs font-semibold text-slate-400 mb-1">Total Coordinations</div>
          <div className="text-2xl font-bold text-white">{runs.length}</div>
        </div>

        <div className="glass-panel p-4">
          <div className="text-xs font-semibold text-emerald-400 mb-1">Approved Plans</div>
          <div className="text-2xl font-bold text-emerald-300">{approvedCount}</div>
        </div>

        <div className="glass-panel p-4">
          <div className="text-xs font-semibold text-indigo-400 mb-1">In Pipeline / Cycles</div>
          <div className="text-2xl font-bold text-indigo-300">{activeCount}</div>
        </div>

        <div className="glass-panel p-4">
          <div className="text-xs font-semibold text-slate-400 mb-1">Agents Active</div>
          <div className="text-2xl font-bold text-white">3 Mini-Agents</div>
        </div>
      </div>

      {/* Runs Table / Cards */}
      <div className="glass-panel p-5 space-y-4">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <Layers className="w-4 h-4 text-indigo-400" />
            <span>Coordination Runs History</span>
          </h3>

          <button onClick={onNewRun} className="btn btn-primary text-xs py-1.5 px-3">
            <Play className="w-3.5 h-3.5 fill-current" />
            <span>New Run</span>
          </button>
        </div>

        {runs.length === 0 ? (
          <div className="p-8 text-center text-slate-400 text-sm">
            <p className="mb-3">No coordination runs yet. Launch a new run to see the multi-agent pipeline in action.</p>
            <button onClick={onNewRun} className="btn btn-primary text-xs">
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>Launch First Run</span>
            </button>
          </div>
        ) : (
          <div className="space-y-2.5">
            {runs.map((run) => (
              <div
                key={run.id}
                onClick={() => onSelectRun(run.id)}
                className={`p-3.5 rounded-xl border transition-all cursor-pointer flex flex-col sm:flex-row sm:items-center justify-between gap-3 ${
                  selectedRunId === run.id
                    ? 'bg-indigo-950/40 border-indigo-500/50 shadow-md shadow-indigo-500/10'
                    : 'bg-slate-900/50 border-slate-800/80 hover:bg-slate-900/80 hover:border-slate-700'
                }`}
              >
                <div>
                  <div className="flex flex-wrap items-center gap-2.5 mb-1.5">
                    <span className={`status-badge text-[11px] ${getStatusBadge(run.status)}`}>
                      {run.status.replace(/_/g, ' ')}
                    </span>
                    <h4 className="text-sm font-bold text-white hover:text-indigo-300 transition">
                      {run.title}
                    </h4>
                  </div>

                  <div className="flex flex-wrap items-center gap-3 text-xs text-slate-400">
                    <span className="font-mono text-slate-500">{run.id.slice(0, 8)}</span>
                    <span>Source: <strong>v{run.current_source_version}</strong></span>
                    <span>Plan: <strong>v{run.current_plan_version}</strong></span>
                    <span>Review Cycles: <strong>{run.review_cycle_count}</strong></span>
                    <span className="text-slate-500 font-mono">
                      {new Date(run.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                </div>

                <div className="flex items-center gap-2 text-xs text-indigo-400 font-medium self-end sm:self-auto">
                  <span>Open Details</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
