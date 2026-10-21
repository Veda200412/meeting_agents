import React, { useState, useEffect } from 'react';
import { X, Play, Sparkles, AlertTriangle, Layers } from 'lucide-react';
import { SampleData } from '../types';

interface NewRunModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    title: string;
    transcript: string;
    company_rules: string;
    max_review_cycles: number;
    fault_injection: string | null;
  }) => Promise<void>;
  samples: SampleData | null;
}

export const NewRunModal: React.FC<NewRunModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  samples,
}) => {
  const [activeTab, setActiveTab] = useState<'preset_simple' | 'preset_complex' | 'custom'>('preset_simple');
  const [title, setTitle] = useState('Operations Onboarding Run');
  const [transcript, setTranscript] = useState('');
  const [companyRules, setCompanyRules] = useState('');
  const [maxCycles, setMaxCycles] = useState(2);
  const [faultInjection, setFaultInjection] = useState<string>('none');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (activeTab === 'preset_simple') {
      setTitle('Simple Demo: Onboarding Checklist');
      setTranscript(
        samples?.transcripts?.simple ||
          'During the operations meeting, the team agreed to prepare the customer onboarding checklist before the next review meeting. Priya will draft the checklist. The engineering team must confirm the API dependencies before implementation starts. No exact deadline was agreed for the API dependency review.'
      );
      setCompanyRules(
        samples?.rules?.simple ||
          'Company Operations Rules:\n1. Only explicitly confirmed owners from the meeting transcript may be treated as confirmed task owners.\n2. Do not invent exact deadlines that were not agreed upon in the meeting.\n3. All tasks must respect their stated dependencies before starting.\n4. Recommendations must be clearly labelled separately from confirmed facts.\n5. If a task has no confirmed owner, it must be flagged for assignment.\n6. Priority should be based on dependency criticality and explicit urgency.'
      );
    } else if (activeTab === 'preset_complex') {
      setTitle('Complex Demo: Payment Migration & Conflicts');
      setTranscript(
        samples?.transcripts?.complex ||
          'The Q3 planning meeting covered multiple topics. Sarah mentioned that the migration to the new payment provider must be completed by end of October. However, David disagreed and said the legal review hasn\'t finished yet, so October is not realistic. The team discussed the customer feedback dashboard — Alex volunteered to lead the frontend work, but no backend owner was identified. Maria raised a risk about the data pipeline reliability: "We had three outages last month and the root cause analysis is still pending." The security audit was mentioned as a dependency for the payment migration, but nobody confirmed who would schedule it. Budget allocation for the new hire was approved, but the job description hasn\'t been written yet. Tom suggested deploying to staging by next Friday, while Sarah said the staging environment won\'t be ready until the following Monday. There was no resolution on this conflict.'
      );
      setCompanyRules(
        samples?.rules?.complex ||
          'Company Operations Rules:\n1. Only explicitly confirmed owners may be treated as confirmed.\n2. Do not invent deadlines not agreed upon in the meeting.\n3. Tasks must respect dependencies.\n4. Recommendations must be labelled separately from facts.\n5. Security audits must be completed before any payment-related changes.\n6. Legal review completion is a prerequisite for external vendor changes.\n7. All conflicting statements must be preserved and flagged for resolution.\n8. Budget approvals require documented job descriptions before hiring begins.\n9. Staging deployments require environment readiness confirmation.\n10. Risk items with pending root cause analysis must be treated as blockers.'
      );
    }
  }, [activeTab, samples]);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim() || !transcript.trim() || !companyRules.trim()) {
      setError('Please fill in title, transcript, and company rules.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmit({
        title,
        transcript,
        company_rules: companyRules,
        max_review_cycles: maxCycles,
        fault_injection: faultInjection === 'none' ? null : faultInjection,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to start run');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-indigo-500/20 text-indigo-400">
              <Sparkles className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Start New AI Coordination</h3>
              <p className="text-xs text-slate-400">Configure meeting inputs, rules, and demo fault simulations</p>
            </div>
          </div>
          <button onClick={onClose} className="p-1 rounded text-slate-400 hover:text-white">
            <X className="w-5 h-5" />
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-5 space-y-4">
          {error && (
            <div className="p-3 rounded-lg bg-rose-950/50 border border-rose-500/30 text-xs text-rose-300">
              {error}
            </div>
          )}

          {/* Preset Switcher */}
          <div className="flex rounded-lg overflow-hidden border border-slate-800 bg-slate-900/80 text-xs">
            <button
              type="button"
              onClick={() => setActiveTab('preset_simple')}
              className={`flex-1 py-2 font-medium transition ${
                activeTab === 'preset_simple' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Preset 1: Simple Onboarding
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('preset_complex')}
              className={`flex-1 py-2 font-medium transition ${
                activeTab === 'preset_complex' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Preset 2: Complex Conflicts
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('custom')}
              className={`flex-1 py-2 font-medium transition ${
                activeTab === 'custom' ? 'bg-indigo-600 text-white' : 'text-slate-400 hover:text-white'
              }`}
            >
              Custom Input
            </button>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Coordination Run Title</label>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
              placeholder="e.g. Q3 Operations Sync"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Meeting Transcript</label>
            <textarea
              rows={4}
              value={transcript}
              onChange={(e) => setTranscript(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500 leading-relaxed"
              placeholder="Paste or write meeting notes and transcript..."
              required
            />
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Company Operations Rules</label>
            <textarea
              rows={4}
              value={companyRules}
              onChange={(e) => setCompanyRules(e.target.value)}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-slate-200 font-mono focus:outline-none focus:border-indigo-500 leading-relaxed"
              placeholder="Paste company policy rules..."
              required
            />
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-1">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">
                Max Review Cycles: <strong className="text-indigo-400">{maxCycles}</strong>
              </label>
              <input
                type="range"
                min={1}
                max={4}
                value={maxCycles}
                onChange={(e) => setMaxCycles(parseInt(e.target.value))}
                className="w-full accent-indigo-500 cursor-pointer"
              />
              <span className="text-[10px] text-slate-400">Controls automated correction attempts before completing</span>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1 flex items-center gap-1">
                <AlertTriangle className="w-3.5 h-3.5 text-amber-400" />
                <span>Simulate Demo Fault (Resilience Test)</span>
              </label>
              <select
                value={faultInjection}
                onChange={(e) => setFaultInjection(e.target.value)}
                className="w-full px-3 py-1.5 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="none">None (Normal Execution)</option>
                <option value="intake_failure">Simulate Intake Agent Failure</option>
                <option value="planning_failure">Simulate Planning Agent Failure</option>
                <option value="schema_failure">Simulate Schema Validation Failure</option>
              </select>
            </div>
          </div>

          <div className="pt-4 border-t border-slate-800 flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              className="btn btn-secondary text-xs"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isSubmitting}
              className="btn btn-primary text-xs"
            >
              <Play className="w-3.5 h-3.5 fill-current" />
              <span>{isSubmitting ? 'Starting...' : 'Execute Coordination'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
