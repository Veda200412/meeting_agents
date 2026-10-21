import React from 'react';
import { EventItem } from '../types';
import { Clock, Play, CheckCircle, AlertTriangle, RefreshCw } from 'lucide-react';

interface TimelineViewProps {
  events: EventItem[];
  isLoading?: boolean;
}

export const TimelineView: React.FC<TimelineViewProps> = ({ events, isLoading = false }) => {
  if (isLoading) {
    return <div className="glass-panel p-8 text-center text-slate-400 text-sm">Loading timeline events...</div>;
  }

  if (events.length === 0) {
    return (
      <div className="glass-panel p-8 text-center text-slate-400 text-sm">
        No events recorded for this workflow yet.
      </div>
    );
  }

  const getEventIcon = (type: string) => {
    if (type.includes('started')) return <Play className="w-3.5 h-3.5 text-indigo-400" />;
    if (type.includes('completed') || type.includes('approved'))
      return <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
    if (type.includes('failed') || type.includes('error'))
      return <AlertTriangle className="w-3.5 h-3.5 text-rose-400" />;
    return <Clock className="w-3.5 h-3.5 text-slate-400" />;
  };

  return (
    <div className="glass-panel p-5 space-y-4">
      <h3 className="text-sm font-bold text-white flex items-center gap-2">
        <Clock className="w-4 h-4 text-indigo-400" />
        <span>Workflow Event Audit Trail ({events.length} events)</span>
      </h3>

      <div className="relative pl-6 space-y-4 border-l border-slate-800 ml-2">
        {events.map((ev) => (
          <div key={ev.id} className="relative group">
            {/* Timeline node icon */}
            <div className="absolute -left-[31px] top-0.5 p-1 rounded-full bg-slate-900 border border-slate-700">
              {getEventIcon(ev.event_type)}
            </div>

            <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-700 transition">
              <div className="flex flex-wrap items-center justify-between gap-2 mb-1">
                <div className="flex items-center gap-2">
                  <span className="font-mono text-xs font-semibold text-slate-200">
                    {ev.event_type.replace(/_/g, ' ')}
                  </span>
                  {ev.agent_type && (
                    <span className="text-[10px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded bg-indigo-500/15 text-indigo-300 border border-indigo-500/30">
                      {ev.agent_type}
                    </span>
                  )}
                </div>

                <span className="text-[10px] font-mono text-slate-500">
                  {new Date(ev.timestamp).toLocaleTimeString()}
                </span>
              </div>

              <p className="text-xs text-slate-300">{ev.description}</p>

              {ev.details && Object.keys(ev.details).length > 0 && (
                <pre className="mt-2 p-2 rounded bg-slate-950 text-[11px] font-mono text-slate-400 overflow-x-auto">
                  {JSON.stringify(ev.details, null, 2)}
                </pre>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
