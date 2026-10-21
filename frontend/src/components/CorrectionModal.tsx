import React, { useState, useEffect } from 'react';
import { X, Edit3, CheckCircle } from 'lucide-react';
import { FactItem } from '../types';

interface CorrectionModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: {
    fact_id: string;
    field_name: string;
    corrected_value: string;
    correction_note: string;
  }) => Promise<void>;
  facts: FactItem[];
  initialFact?: FactItem | null;
}

export const CorrectionModal: React.FC<CorrectionModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  facts,
  initialFact,
}) => {
  const [selectedFactId, setSelectedFactId] = useState<string>('');
  const [fieldName, setFieldName] = useState<string>('owner');
  const [correctedValue, setCorrectedValue] = useState<string>('');
  const [note, setNote] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialFact) {
      setSelectedFactId(initialFact.fact_id);
      setFieldName('owner');
      setCorrectedValue(initialFact.owner || '');
      setNote('Human operator verified owner assignment');
    } else if (facts.length > 0 && !selectedFactId) {
      setSelectedFactId(facts[0].fact_id);
    }
  }, [initialFact, facts]);

  if (!isOpen) return null;

  const currentFact = facts.find((f) => f.fact_id === selectedFactId);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFactId || !fieldName || !correctedValue.trim()) {
      setError('Please fill in all required fields.');
      return;
    }

    try {
      setIsSubmitting(true);
      setError(null);
      await onSubmit({
        fact_id: selectedFactId,
        field_name: fieldName,
        corrected_value: correctedValue,
        correction_note: note,
      });
      onClose();
    } catch (err: any) {
      setError(err.message || 'Failed to submit correction');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="modal-backdrop">
      <div className="modal-content">
        <div className="p-5 border-b border-slate-800 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="p-2 rounded-lg bg-amber-500/20 text-amber-400">
              <Edit3 className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-base font-bold text-white">Human-in-the-Loop Fact Correction</h3>
              <p className="text-xs text-slate-400">
                Correct extracted facts to trigger downstream re-planning and audit verification
              </p>
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

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Target Fact</label>
            <select
              value={selectedFactId}
              onChange={(e) => {
                setSelectedFactId(e.target.value);
                const found = facts.find((f) => f.fact_id === e.target.value);
                if (found) {
                  setCorrectedValue(found.owner || found.deadline || found.content);
                }
              }}
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500 font-mono"
            >
              {facts.map((f) => (
                <option key={f.fact_id} value={f.fact_id}>
                  {f.fact_id} [{f.fact_type}]: {f.content.slice(0, 60)}...
                </option>
              ))}
            </select>
          </div>

          {currentFact && (
            <div className="p-3 rounded-lg bg-slate-950/70 border border-slate-800 text-xs space-y-1">
              <div className="text-slate-400 font-medium">Fact Details:</div>
              <div className="text-slate-200">{currentFact.content}</div>
              {currentFact.evidence_quote && (
                <div className="text-slate-400 italic">Quote: "{currentFact.evidence_quote}"</div>
              )}
            </div>
          )}

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Field to Correct</label>
              <select
                value={fieldName}
                onChange={(e) => setFieldName(e.target.value)}
                className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
              >
                <option value="owner">Owner (e.g. Assign Confirmed Person)</option>
                <option value="deadline">Deadline (e.g. Set Specific Date)</option>
                <option value="content">Content / Requirement Description</option>
                <option value="confidence">Confidence Level</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Corrected Value</label>
              <input
                type="text"
                value={correctedValue}
                onChange={(e) => setCorrectedValue(e.target.value)}
                placeholder="Enter new correct value..."
                className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
                required
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-semibold text-slate-300 mb-1">Correction Rationale / Note</label>
            <input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="e.g. Confirmed in offline Slack discussion with Engineering Lead"
              className="w-full px-3 py-2 bg-slate-900 border border-slate-800 rounded-lg text-xs text-white focus:outline-none focus:border-indigo-500"
            />
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
              className="btn btn-warning text-xs"
            >
              <CheckCircle className="w-3.5 h-3.5" />
              <span>{isSubmitting ? 'Submitting...' : 'Apply & Re-Plan'}</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
