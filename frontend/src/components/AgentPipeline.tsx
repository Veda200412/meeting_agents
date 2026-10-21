import React from 'react';
import { FileText, CalendarCheck, ShieldAlert, ArrowRight, CheckCircle2, Loader2, AlertCircle } from 'lucide-react';
import { RunStatus } from '../types';

interface AgentPipelineProps {
  status: RunStatus;
  cycleCount: number;
  maxCycles: number;
}

export const AgentPipeline: React.FC<AgentPipelineProps> = ({
  status,
  cycleCount,
  maxCycles,
}) => {
  const isIntakeRunning = status === 'INTAKE_RUNNING';
  const isIntakeCompleted = status !== 'CREATED' && status !== 'INTAKE_RUNNING';

  const isPlanningRunning = status === 'PLANNING_RUNNING';
  const isPlanningCompleted = [
    'PLANNING_COMPLETED',
    'REVIEW_RUNNING',
    'NEEDS_CORRECTION',
    'APPROVED',
    'COMPLETED_WITH_UNRESOLVED_ISSUES',
  ].includes(status);

  const isReviewRunning = status === 'REVIEW_RUNNING';
  const isReviewApproved = status === 'APPROVED';
  const isReviewCorrection = status === 'NEEDS_CORRECTION';
  const isFailed = status === 'FAILED';

  return (
    <div className="glass-panel p-5 relative overflow-hidden">
      <div className="flex flex-col md:flex-row items-center justify-between gap-4">
        {/* Stage 1: Intake Agent */}
        <div
          className={`flex-1 w-full p-4 rounded-xl border transition-all duration-300 ${
            isIntakeRunning
              ? 'bg-emerald-950/30 border-emerald-500/50 shadow-lg shadow-emerald-500/10'
              : isIntakeCompleted
              ? 'bg-slate-900/60 border-emerald-500/30'
              : 'bg-slate-900/30 border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div
                className={`p-2 rounded-lg ${
                  isIntakeRunning
                    ? 'bg-emerald-500/20 text-emerald-400'
                    : isIntakeCompleted
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : 'bg-slate-800 text-slate-500'
                }`}
              >
                <FileText className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">1. Intake Agent</h4>
                <p className="text-[11px] text-slate-400">Ground Truth & Facts</p>
              </div>
            </div>
            {isIntakeRunning ? (
              <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
            ) : isIntakeCompleted ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : null}
          </div>
          <p className="text-xs text-slate-400 line-clamp-2">
            Extracts decisions, requirements, owners & evidence quotes from transcript.
          </p>
        </div>

        <ArrowRight className="hidden md:block w-5 h-5 text-slate-600 shrink-0" />

        {/* Stage 2: Planning Agent */}
        <div
          className={`flex-1 w-full p-4 rounded-xl border transition-all duration-300 ${
            isPlanningRunning
              ? 'bg-indigo-950/30 border-indigo-500/50 shadow-lg shadow-indigo-500/10'
              : isPlanningCompleted
              ? 'bg-slate-900/60 border-indigo-500/30'
              : 'bg-slate-900/30 border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div
                className={`p-2 rounded-lg ${
                  isPlanningRunning
                    ? 'bg-indigo-500/20 text-indigo-400'
                    : isPlanningCompleted
                    ? 'bg-indigo-500/10 text-indigo-400'
                    : 'bg-slate-800 text-slate-500'
                }`}
              >
                <CalendarCheck className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">2. Planning Agent</h4>
                <p className="text-[11px] text-slate-400">Plan Synthesis & Schedule</p>
              </div>
            </div>
            {isPlanningRunning ? (
              <Loader2 className="w-4 h-4 text-indigo-400 animate-spin" />
            ) : isPlanningCompleted ? (
              <CheckCircle2 className="w-4 h-4 text-indigo-400" />
            ) : null}
          </div>
          <p className="text-xs text-slate-400 line-clamp-2">
            Transforms validated facts into tasks, dependencies, and questions.
          </p>
        </div>

        <ArrowRight className="hidden md:block w-5 h-5 text-slate-600 shrink-0" />

        {/* Stage 3: Review Agent */}
        <div
          className={`flex-1 w-full p-4 rounded-xl border transition-all duration-300 ${
            isReviewRunning
              ? 'bg-amber-950/30 border-amber-500/50 shadow-lg shadow-amber-500/10'
              : isReviewApproved
              ? 'bg-emerald-950/30 border-emerald-500/50'
              : isReviewCorrection
              ? 'bg-amber-950/30 border-amber-500/40'
              : 'bg-slate-900/30 border-slate-800'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <div
                className={`p-2 rounded-lg ${
                  isReviewRunning
                    ? 'bg-amber-500/20 text-amber-400'
                    : isReviewApproved
                    ? 'bg-emerald-500/10 text-emerald-400'
                    : isReviewCorrection
                    ? 'bg-amber-500/10 text-amber-400'
                    : 'bg-slate-800 text-slate-500'
                }`}
              >
                <ShieldAlert className="w-5 h-5" />
              </div>
              <div>
                <h4 className="text-sm font-semibold text-white">3. Review Agent</h4>
                <p className="text-[11px] text-slate-400">
                  Audit & Approval {cycleCount > 0 && `(Cycle ${cycleCount}/${maxCycles})`}
                </p>
              </div>
            </div>
            {isReviewRunning ? (
              <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
            ) : isReviewApproved ? (
              <CheckCircle2 className="w-4 h-4 text-emerald-400" />
            ) : isReviewCorrection ? (
              <AlertCircle className="w-4 h-4 text-amber-400" />
            ) : null}
          </div>
          <p className="text-xs text-slate-400 line-clamp-2">
            Verifies tasks against transcript evidence and enforces company rules.
          </p>
        </div>
      </div>

      {isFailed && (
        <div className="mt-3 py-2 px-3 rounded-lg bg-rose-950/40 border border-rose-500/30 flex items-center gap-2 text-xs text-rose-300">
          <AlertCircle className="w-4 h-4 shrink-0 text-rose-400" />
          <span>Workflow encountered an interruption or failure. Use Resume to re-attempt from last state.</span>
        </div>
      )}
    </div>
  );
};
