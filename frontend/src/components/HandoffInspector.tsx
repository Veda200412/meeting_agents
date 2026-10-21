import React from 'react';
import { HandoffItem } from '../types';
import { ArrowRight, ArrowLeftRight } from 'lucide-react';

interface HandoffInspectorProps {
  handoffs: HandoffItem[];
}

export const HandoffInspector: React.FC<HandoffInspectorProps> = ({ handoffs }) => {
  if (handoffs.length === 0) {
    return (
      <div className="glass-panel p-8 text-center text-slate-400 text-sm">
        No formal agent handoffs recorded yet.
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2 text-sm font-bold text-white mb-2">
        <ArrowLeftRight className="w-4 h-4 text-indigo-400" />
        <span>Traceable Agent Handoff Records</span>
      </div>

      <div className="space-y-3">
        {handoffs.map((h, i) => (
          <div key={i} className="glass-panel p-4 space-y-3 hover:border-slate-600 transition">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-emerald-500/15 text-emerald-300 border border-emerald-500/30">
                  {h.from_agent}
                </span>
                <ArrowRight className="w-4 h-4 text-slate-500" />
                <span className="text-xs font-bold uppercase tracking-wider px-2 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                  {h.to_agent}
                </span>
              </div>

              <div className="flex items-center gap-3 text-xs text-slate-400">
                <span>Source: <strong>v{h.source_version}</strong></span>
                {h.plan_version && <span>Plan: <strong>v{h.plan_version}</strong></span>}
                <span className="font-mono text-slate-500">
                  {new Date(h.created_at).toLocaleTimeString()}
                </span>
              </div>
            </div>

            <p className="text-xs text-slate-200">{h.summary}</p>
            {h.payload && (
              <details className="rounded-lg border border-slate-800 bg-slate-950/45">
                <summary className="cursor-pointer px-3 py-2 text-xs font-medium text-indigo-300 hover:text-indigo-200">
                  Inspect validated handoff payload
                </summary>
                <pre className="max-h-96 overflow-auto border-t border-slate-800 p-3 text-[11px] leading-relaxed text-slate-300">
                  {JSON.stringify(h.payload, null, 2)}
                </pre>
              </details>
            )}
          </div>
        ))}
      </div>
    </div>
  );
};
