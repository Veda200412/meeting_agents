import React, { useState } from 'react';
import { PlanVersionData } from '../types';
import {
  CheckCircle2,
  AlertCircle,
  HelpCircle,
  UserCheck,
  UserX,
  Clock,
  ArrowRight,
  GitCommit,
  Lightbulb,
} from 'lucide-react';

interface PlanViewProps {
  plans: PlanVersionData[];
  currentVersion: number;
}

export const PlanView: React.FC<PlanViewProps> = ({ plans, currentVersion }) => {
  const [selectedVersion, setSelectedVersion] = useState<number>(currentVersion);

  const activePlan = plans.find((p) => p.version === selectedVersion) || plans[plans.length - 1];

  if (!activePlan) {
    return (
      <div className="glass-panel p-8 text-center text-slate-400 text-sm">
        No operations plan generated yet. The Planning Agent will produce a plan once Intake completes.
      </div>
    );
  }

  const getPriorityBadge = (priority: string) => {
    switch (priority) {
      case 'high':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      case 'medium':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'low':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  const getEvidenceBadge = (ev: string) => {
    switch (ev) {
      case 'supported':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'recommendation':
        return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30';
      case 'unresolved':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  return (
    <div className="space-y-6">
      {/* Header and Version Selector */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-3 border-b border-slate-800">
        <div>
          <h3 className="text-base font-bold text-white flex items-center gap-2">
            <span>Operations Action Plan</span>
            <span className="px-2 py-0.5 text-xs font-mono bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded">
              v{activePlan.version}
            </span>
          </h3>
          <p className="text-xs text-slate-400 mt-0.5">
            Derived from Source Version {activePlan.source_version} • {activePlan.tasks.length} actionable tasks
          </p>
        </div>

        {plans.length > 1 && (
          <div className="flex items-center gap-2 text-xs">
            <span className="text-slate-400">View Revision:</span>
            <div className="flex rounded-lg overflow-hidden border border-slate-700 bg-slate-900">
              {plans.map((p) => (
                <button
                  key={p.version}
                  onClick={() => setSelectedVersion(p.version)}
                  className={`px-3 py-1 font-mono transition ${
                    selectedVersion === p.version
                      ? 'bg-indigo-600 text-white font-bold'
                      : 'text-slate-400 hover:text-white hover:bg-slate-800'
                  }`}
                >
                  v{p.version}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Change Summary if multiple revisions */}
      {activePlan.change_summary && activePlan.change_summary.length > 0 && (
        <div className="p-3.5 rounded-xl bg-indigo-950/30 border border-indigo-500/30">
          <div className="flex items-center gap-2 text-xs font-semibold text-indigo-300 mb-2">
            <GitCommit className="w-4 h-4 text-indigo-400" />
            <span>Changes Made in v{activePlan.version} (Incorporating Review Findings)</span>
          </div>
          <div className="space-y-1.5 text-xs">
            {activePlan.change_summary.map((change, idx) => (
              <div key={idx} className="flex items-start gap-2 text-slate-300">
                <span className="font-mono text-indigo-400 shrink-0 font-medium">{change.task_id}:</span>
                <span>
                  Modified <strong>{change.field_changed}</strong> — {change.reason}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tasks List */}
      <div className="space-y-3.5">
        {activePlan.tasks.map((task) => (
          <div
            key={task.task_id}
            className="glass-panel p-4 hover:border-slate-600 transition flex flex-col justify-between"
          >
            <div>
              <div className="flex flex-wrap items-center justify-between gap-2 mb-2">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-mono text-xs font-bold px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-indigo-300">
                    {task.task_id}
                  </span>
                  <h4 className="text-sm font-semibold text-white">{task.title}</h4>
                </div>

                <div className="flex items-center gap-2">
                  <span
                    className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getEvidenceBadge(
                      task.evidence_classification
                    )}`}
                  >
                    {task.evidence_classification}
                  </span>
                  <span
                    className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getPriorityBadge(
                      task.priority
                    )}`}
                  >
                    {task.priority}
                  </span>
                </div>
              </div>

              <p className="text-xs text-slate-300 mb-3 leading-relaxed">{task.description}</p>

              {/* Supporting Facts Tag List */}
              {task.supporting_fact_ids.length > 0 && (
                <div className="flex items-center gap-1.5 mb-3 flex-wrap">
                  <span className="text-[11px] text-slate-400">Supported by:</span>
                  {task.supporting_fact_ids.map((fid) => (
                    <span
                      key={fid}
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700"
                    >
                      {fid}
                    </span>
                  ))}
                </div>
              )}

              {/* Dependencies if any */}
              {task.dependencies.length > 0 && (
                <div className="flex items-center gap-1.5 mb-3 flex-wrap">
                  <span className="text-[11px] text-slate-400 flex items-center gap-1">
                    <ArrowRight className="w-3 h-3 text-indigo-400" /> Depends on:
                  </span>
                  {task.dependencies.map((dep) => (
                    <span
                      key={dep}
                      className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-indigo-950/60 text-indigo-300 border border-indigo-500/30"
                    >
                      {dep}
                    </span>
                  ))}
                </div>
              )}

              {/* Open Questions for this task */}
              {task.open_questions && task.open_questions.length > 0 && (
                <div className="p-2.5 rounded-lg bg-amber-950/20 border border-amber-500/20 mb-3 text-xs text-amber-300 space-y-1">
                  <span className="font-semibold flex items-center gap-1 text-[11px]">
                    <HelpCircle className="w-3.5 h-3.5" /> Open Questions:
                  </span>
                  <ul className="list-disc list-inside space-y-0.5 text-slate-300 text-[11px]">
                    {task.open_questions.map((q, i) => (
                      <li key={i}>{q}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>

            {/* Owner & Deadline Row */}
            <div className="pt-2 border-t border-slate-800/80 flex flex-wrap items-center justify-between text-xs text-slate-400 gap-2">
              <div className="flex items-center gap-2">
                {task.owner_confirmed ? (
                  <span className="flex items-center gap-1 text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded border border-emerald-500/20">
                    <UserCheck className="w-3.5 h-3.5" />
                    <strong>{task.owner}</strong> (Confirmed)
                  </span>
                ) : (
                  <span className="flex items-center gap-1 text-amber-400 bg-amber-500/10 px-2 py-0.5 rounded border border-amber-500/20">
                    <UserX className="w-3.5 h-3.5" />
                    {task.owner ? `${task.owner} (Unconfirmed)` : 'Needs Assignment'}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                <Clock className="w-3.5 h-3.5 text-slate-500" />
                {task.deadline_confirmed ? (
                  <span className="text-emerald-400 font-medium">
                    {task.deadline} (Agreed)
                  </span>
                ) : (
                  <span className="text-slate-400 italic">
                    {task.deadline ? `${task.deadline} (Proposed)` : 'No deadline agreed'}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Recommendations & Unresolved Questions */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
        {/* Recommendations */}
        {activePlan.recommendations && activePlan.recommendations.length > 0 && (
          <div className="glass-panel p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-indigo-400 mb-3 flex items-center gap-1.5">
              <Lightbulb className="w-4 h-4" /> Agent Recommendations
            </h4>
            <div className="space-y-2.5">
              {activePlan.recommendations.map((rec) => (
                <div key={rec.rec_id} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                  <div className="font-semibold text-slate-200 mb-1">{rec.title}</div>
                  <div className="text-slate-400 mb-1.5">{rec.description}</div>
                  <div className="text-[11px] text-indigo-300 italic">Rationale: {rec.rationale}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Unresolved Questions */}
        {activePlan.unresolved_questions && activePlan.unresolved_questions.length > 0 && (
          <div className="glass-panel p-4">
            <h4 className="text-xs font-bold uppercase tracking-wider text-amber-400 mb-3 flex items-center gap-1.5">
              <HelpCircle className="w-4 h-4" /> Unresolved Questions & Missing Info
            </h4>
            <div className="space-y-2.5">
              {activePlan.unresolved_questions.map((uq) => (
                <div key={uq.question_id} className="p-2.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs">
                  <div className="font-semibold text-slate-200 mb-1">{uq.question}</div>
                  <div className="text-slate-400">{uq.context}</div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
