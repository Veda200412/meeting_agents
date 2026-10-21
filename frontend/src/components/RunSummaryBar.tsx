import React from 'react';
import { Copy, RotateCcw, PlayCircle, Edit3, Check, AlertTriangle } from 'lucide-react';
import { RunDetail } from '../types';

interface RunSummaryBarProps {
  run: RunDetail;
  onResume: () => void;
  onReset: () => void;
  onOpenCorrection: () => void;
  isActionLoading?: boolean;
}

export const RunSummaryBar: React.FC<RunSummaryBarProps> = ({
  run,
  onResume,
  onReset,
  onOpenCorrection,
  isActionLoading = false,
}) => {
  const [copied, setCopied] = React.useState(false);

  const copyId = () => {
    navigator.clipboard.writeText(run.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getStatusClass = () => {
    switch (run.status) {
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
      case 'COMPLETED_WITH_UNRESOLVED_ISSUES':
        return 'status-unresolved';
      default:
        return 'status-created';
    }
  };

  const canResume = run.status === 'FAILED' || run.status === 'INTERRUPTED';

  return (
    <div className="glass-panel p-5 flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
      <div>
        <div className="flex flex-wrap items-center gap-3">
          <span className={`status-badge ${getStatusClass()}`}>
            <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
            {run.status.replace(/_/g, ' ')}
          </span>
          <h2 className="text-xl font-bold text-white">{run.title}</h2>
        </div>

        <div className="flex flex-wrap items-center gap-4 mt-2 text-xs text-slate-400">
          <button
            onClick={copyId}
            className="flex items-center gap-1.5 hover:text-slate-200 transition font-mono bg-slate-900/60 px-2 py-0.5 rounded border border-slate-800"
            title="Click to copy ID"
          >
            <span>{run.id.slice(0, 8)}...</span>
            {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
          </button>
          <span>Source: <strong className="text-slate-200">v{run.current_source_version}</strong></span>
          <span>Plan: <strong className="text-slate-200">v{run.current_plan_version}</strong></span>
          <span>
            Review Cycles:{' '}
            <strong className="text-slate-200">
              {run.review_cycle_count} / {run.max_review_cycles}
            </strong>
          </span>
          {run.fault_injection && (
            <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
              <AlertTriangle className="w-3.5 h-3.5" /> Demo Fault: {run.fault_injection}
            </span>
          )}
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2 self-stretch md:self-auto justify-end">
        {canResume && (
          <button
            onClick={onResume}
            disabled={isActionLoading}
            className="btn btn-primary"
          >
            <PlayCircle className="w-4 h-4" />
            <span>Resume Workflow</span>
          </button>
        )}

        <button
          onClick={onOpenCorrection}
          disabled={isActionLoading || run.facts.length === 0}
          className="btn btn-warning"
          title="Submit a human correction to a fact to test re-planning loop"
        >
          <Edit3 className="w-4 h-4" />
          <span>Correct Fact</span>
        </button>

        <button
          onClick={onReset}
          disabled={isActionLoading}
          className="btn btn-secondary text-slate-300"
          title="Reset run back to initial created state"
        >
          <RotateCcw className="w-4 h-4" />
          <span>Reset Run</span>
        </button>
      </div>
    </div>
  );
};
