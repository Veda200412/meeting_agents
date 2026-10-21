import React, { useState } from 'react';
import { FactItem } from '../types';
import { Quote, AlertCircle, User, Calendar, Edit3, Search } from 'lucide-react';

interface FactListProps {
  facts: FactItem[];
  onCorrectFact: (fact: FactItem) => void;
}

export const FactList: React.FC<FactListProps> = ({ facts, onCorrectFact }) => {
  const [filterType, setFilterType] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState<string>('');

  const factTypes = [
    { id: 'all', label: 'All Facts' },
    { id: 'decision', label: 'Decisions' },
    { id: 'requirement', label: 'Requirements' },
    { id: 'action_item', label: 'Action Items' },
    { id: 'risk', label: 'Risks' },
    { id: 'conflict', label: 'Conflicts' },
    { id: 'missing_info', label: 'Missing Info' },
  ];

  const filteredFacts = facts.filter((f) => {
    const matchesType = filterType === 'all' || f.fact_type === filterType;
    const matchesSearch =
      !searchTerm ||
      f.content.toLowerCase().includes(searchTerm.toLowerCase()) ||
      f.fact_id.toLowerCase().includes(searchTerm.toLowerCase()) ||
      (f.owner && f.owner.toLowerCase().includes(searchTerm.toLowerCase())) ||
      f.evidence_quote.toLowerCase().includes(searchTerm.toLowerCase());
    return matchesType && matchesSearch;
  });

  const getTypeBadge = (type: string) => {
    switch (type) {
      case 'decision':
        return 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30';
      case 'requirement':
        return 'bg-indigo-500/15 text-indigo-300 border-indigo-500/30';
      case 'action_item':
        return 'bg-cyan-500/15 text-cyan-300 border-cyan-500/30';
      case 'risk':
        return 'bg-rose-500/15 text-rose-300 border-rose-500/30';
      case 'conflict':
        return 'bg-amber-500/15 text-amber-300 border-amber-500/30';
      case 'missing_info':
        return 'bg-purple-500/15 text-purple-300 border-purple-500/30';
      default:
        return 'bg-slate-700 text-slate-300 border-slate-600';
    }
  };

  return (
    <div className="space-y-4">
      {/* Search and Category Filters */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex flex-wrap gap-1.5 w-full sm:w-auto">
          {factTypes.map((t) => (
            <button
              key={t.id}
              onClick={() => setFilterType(t.id)}
              className={`px-3 py-1 rounded-lg text-xs font-medium transition ${
                filterType === t.id
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'bg-slate-900/60 text-slate-400 hover:text-white hover:bg-slate-800'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>

        <div className="relative w-full sm:w-64">
          <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-500" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
            placeholder="Search facts or quotes..."
            className="w-full pl-9 pr-3 py-1.5 bg-slate-900/80 border border-slate-800 rounded-lg text-xs text-white placeholder-slate-500 focus:outline-none focus:border-indigo-500"
          />
        </div>
      </div>

      {/* Facts List */}
      {filteredFacts.length === 0 ? (
        <div className="glass-panel p-8 text-center text-slate-400 text-sm">
          No facts match the selected filter.
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-3.5">
          {filteredFacts.map((fact) => (
            <div
              key={fact.fact_id}
              className="glass-panel p-4 flex flex-col justify-between hover:border-slate-600 transition"
            >
              <div>
                <div className="flex items-center justify-between gap-2 mb-2">
                  <div className="flex items-center gap-2">
                    <span className="font-mono text-xs font-semibold px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-slate-300">
                      {fact.fact_id}
                    </span>
                    <span
                      className={`text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded border ${getTypeBadge(
                        fact.fact_type
                      )}`}
                    >
                      {fact.fact_type.replace('_', ' ')}
                    </span>
                  </div>

                  <span
                    className={`text-[10px] font-medium px-2 py-0.5 rounded capitalize ${
                      fact.confidence === 'explicit'
                        ? 'text-emerald-400 bg-emerald-500/10'
                        : fact.confidence === 'inferred'
                        ? 'text-amber-400 bg-amber-500/10'
                        : 'text-rose-400 bg-rose-500/10'
                    }`}
                  >
                    {fact.confidence}
                  </span>
                </div>

                <p className="text-sm font-medium text-slate-100 mb-3">
                  {fact.content}
                </p>

                {/* Evidence Quote */}
                {fact.evidence_quote && (
                  <div className="p-2.5 rounded-lg bg-slate-950/60 border border-slate-800/80 mb-3 text-xs text-slate-300 italic flex items-start gap-2">
                    <Quote className="w-3.5 h-3.5 text-indigo-400 shrink-0 mt-0.5" />
                    <div>
                      <span>"{fact.evidence_quote}"</span>
                      {fact.source_location && (
                        <span className="block not-italic text-[10px] text-slate-500 mt-1 font-mono">
                          Location: {fact.source_location}
                        </span>
                      )}
                    </div>
                  </div>
                )}
              </div>

              {/* Footer with Owner / Deadline and Correction Button */}
              <div className="pt-2 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <User className="w-3.5 h-3.5 text-slate-500" />
                    <span className={fact.owner ? 'text-slate-200' : 'text-slate-500 italic'}>
                      {fact.owner || 'Unassigned'}
                    </span>
                  </span>

                  <span className="flex items-center gap-1">
                    <Calendar className="w-3.5 h-3.5 text-slate-500" />
                    <span className={fact.deadline ? 'text-slate-200' : 'text-slate-500 italic'}>
                      {fact.deadline || 'No deadline'}
                    </span>
                  </span>
                </div>

                <button
                  onClick={() => onCorrectFact(fact)}
                  className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-indigo-400 transition"
                  title="Submit correction for this fact"
                >
                  <Edit3 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
