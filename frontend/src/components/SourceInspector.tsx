import React, { useState } from 'react';
import { FileText, BookOpen } from 'lucide-react';

interface SourceInspectorProps {
  transcript: string;
  companyRules: string;
  sourceVersion: number;
}

export const SourceInspector: React.FC<SourceInspectorProps> = ({
  transcript,
  companyRules,
  sourceVersion,
}) => {
  const [activeTab, setActiveTab] = useState<'both' | 'transcript' | 'rules'>('both');

  return (
    <div className="space-y-4">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 pb-2 border-b border-slate-800">
        <div>
          <h3 className="text-sm font-bold text-white flex items-center gap-2">
            <span>Source Ground Truth & Guidelines</span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-300">
              Source v{sourceVersion}
            </span>
          </h3>
          <p className="text-xs text-slate-400">
            Raw meeting inputs and company constraints used by the Intake and Review agents
          </p>
        </div>

        <div className="flex rounded-lg overflow-hidden border border-slate-800 bg-slate-900 text-xs">
          <button
            onClick={() => setActiveTab('both')}
            className={`px-3 py-1 font-medium transition ${
              activeTab === 'both' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Split View
          </button>
          <button
            onClick={() => setActiveTab('transcript')}
            className={`px-3 py-1 font-medium transition ${
              activeTab === 'transcript' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Transcript Only
          </button>
          <button
            onClick={() => setActiveTab('rules')}
            className={`px-3 py-1 font-medium transition ${
              activeTab === 'rules' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
            }`}
          >
            Rules Only
          </button>
        </div>
      </div>

      <div className={`grid gap-4 ${activeTab === 'both' ? 'grid-cols-1 md:grid-cols-2' : 'grid-cols-1'}`}>
        {(activeTab === 'both' || activeTab === 'transcript') && (
          <div className="glass-panel p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-emerald-400 uppercase tracking-wider">
              <FileText className="w-4 h-4" />
              <span>Meeting Transcript</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-900 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed max-h-[460px] overflow-y-auto">
              {transcript}
            </div>
          </div>
        )}

        {(activeTab === 'both' || activeTab === 'rules') && (
          <div className="glass-panel p-4 space-y-2">
            <div className="flex items-center gap-2 text-xs font-bold text-indigo-400 uppercase tracking-wider">
              <BookOpen className="w-4 h-4" />
              <span>Company Operations Rules</span>
            </div>
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-900 text-xs text-slate-300 font-mono whitespace-pre-wrap leading-relaxed max-h-[460px] overflow-y-auto">
              {companyRules}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
