import React from 'react';
import { ReviewResultData, ReviewFinding } from '../types';
import {
  ShieldCheck,
  AlertTriangle,
  HelpCircle,
  AlertCircle,
  FileSearch,
  CheckCircle,
} from 'lucide-react';

interface ReviewAuditProps {
  reviews: ReviewResultData[];
  currentPlanVersion: number;
}

export const ReviewAudit: React.FC<ReviewAuditProps> = ({
  reviews,
  currentPlanVersion,
}) => {
  const latestReview = reviews[reviews.length - 1];

  if (!latestReview) {
    return (
      <div className="glass-panel p-8 text-center text-slate-400 text-sm">
        No review audit conducted yet. The Review Agent will verify the plan once Planning completes.
      </div>
    );
  }

  const getSeverityBadge = (severity: ReviewFinding['severity']) => {
    switch (severity) {
      case 'critical':
        return 'bg-rose-500/20 text-rose-300 border-rose-500/40';
      case 'major':
        return 'bg-amber-500/20 text-amber-300 border-amber-500/40';
      case 'minor':
        return 'bg-indigo-500/20 text-indigo-300 border-indigo-500/40';
      case 'info':
        return 'bg-slate-700/50 text-slate-300 border-slate-600';
    }
  };

  return (
    <div className="space-y-6">
      {/* Outcome Banner */}
      <div
        className={`p-5 rounded-xl border flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 ${
          latestReview.outcome === 'APPROVED'
            ? 'bg-emerald-950/40 border-emerald-500/40 shadow-lg shadow-emerald-500/10'
            : latestReview.outcome === 'NEEDS_CORRECTION'
            ? 'bg-amber-950/40 border-amber-500/40 shadow-lg shadow-amber-500/10'
            : 'bg-purple-950/40 border-purple-500/40 shadow-lg shadow-purple-500/10'
        }`}
      >
        <div className="flex items-center gap-3.5">
          <div
            className={`p-2.5 rounded-xl ${
              latestReview.outcome === 'APPROVED'
                ? 'bg-emerald-500/20 text-emerald-400'
                : latestReview.outcome === 'NEEDS_CORRECTION'
                ? 'bg-amber-500/20 text-amber-400'
                : 'bg-purple-500/20 text-purple-400'
            }`}
          >
            {latestReview.outcome === 'APPROVED' ? (
              <ShieldCheck className="w-6 h-6" />
            ) : latestReview.outcome === 'NEEDS_CORRECTION' ? (
              <AlertTriangle className="w-6 h-6" />
            ) : (
              <HelpCircle className="w-6 h-6" />
            )}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-base font-bold text-white">
                Review Verdict: {latestReview.outcome.replace('_', ' ')}
              </h3>
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-900/80 border border-slate-700 text-slate-300">
                Plan v{latestReview.plan_version}
              </span>
            </div>
            <p className="text-xs text-slate-300 mt-1 max-w-xl">
              {latestReview.summary}
            </p>
          </div>
        </div>

        <div className="text-right text-xs">
          <div className="font-semibold text-slate-200">
            {latestReview.findings.length} Audit Finding(s)
          </div>
          <div className="text-slate-400">
            {latestReview.findings.filter((f) => f.blocks_approval).length} Blocking Approval
          </div>
        </div>
      </div>

      {/* Audit Findings */}
      <div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3 flex items-center gap-2">
          <FileSearch className="w-4 h-4 text-indigo-400" />
          <span>Independent Auditor Findings</span>
        </h4>

        {latestReview.findings.length === 0 ? (
          <div className="glass-panel p-6 text-center text-emerald-400 text-sm flex items-center justify-center gap-2">
            <CheckCircle className="w-4 h-4" />
            <span>Zero compliance or evidence violations detected. Plan passed all company rules.</span>
          </div>
        ) : (
          <div className="space-y-3">
            {latestReview.findings.map((f) => (
              <div
                key={f.finding_id}
                className="glass-panel p-4 hover:border-slate-600 transition space-y-2.5"
              >
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-200">
                      {f.finding_id}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getSeverityBadge(
                        f.severity
                      )}`}
                    >
                      {f.severity}
                    </span>
                    <span className="text-xs font-mono text-indigo-300 bg-indigo-500/10 px-2 py-0.5 rounded border border-indigo-500/20">
                      Affects {f.affected_id}
                    </span>
                  </div>

                  {f.blocks_approval && (
                    <span className="text-[10px] font-bold text-rose-400 bg-rose-500/10 border border-rose-500/20 px-2 py-0.5 rounded uppercase">
                      Blocks Approval
                    </span>
                  )}
                </div>

                <div className="text-xs text-slate-200 font-medium">{f.explanation}</div>

                {/* Evidence Quote / Rule */}
                <div className="p-2.5 rounded-lg bg-slate-950/70 border border-slate-800 text-xs text-slate-400 space-y-1">
                  <div className="text-[11px] font-semibold text-slate-300">Auditor Evidence / Rule Reference:</div>
                  <div className="italic text-slate-300">"{f.evidence}"</div>
                </div>

                {/* Required Correction */}
                <div className="p-2.5 rounded-lg bg-indigo-950/20 border border-indigo-500/20 text-xs text-indigo-300">
                  <strong>Required Action:</strong> {f.required_correction}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Review History if multiple cycles */}
      {reviews.length > 1 && (
        <div className="pt-4 border-t border-slate-800">
          <h4 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Review Cycle History
          </h4>
          <div className="space-y-2">
            {reviews.map((r, i) => (
              <div
                key={i}
                className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 flex items-center justify-between text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-slate-300">Cycle {i + 1}:</span>
                  <span className="font-mono text-indigo-300">Plan v{r.plan_version}</span>
                  <span className="text-slate-400">— {r.summary}</span>
                </div>
                <span
                  className={`font-semibold ${
                    r.outcome === 'APPROVED' ? 'text-emerald-400' : 'text-amber-400'
                  }`}
                >
                  {r.outcome}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
};
