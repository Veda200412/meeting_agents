import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Session } from '@supabase/supabase-js';
import { api } from './services/api';
import { requireSupabase, supabase, supabaseConfigured } from './services/supabase';
import { supabaseData } from './services/supabaseData';
import {
  RunSummary,
  RunDetail,
  EventItem,
  SystemHealth,
  SampleData,
  FactItem,
} from './types';
import { Navbar } from './components/Navbar';
import { AgentPipeline } from './components/AgentPipeline';
import { RunSummaryBar } from './components/RunSummaryBar';
import { FactList } from './components/FactList';
import { PlanView } from './components/PlanView';
import { ReviewAudit } from './components/ReviewAudit';
import { TimelineView } from './components/TimelineView';
import { HandoffInspector } from './components/HandoffInspector';
import { SourceInspector } from './components/SourceInspector';
import { RunDashboard } from './components/RunDashboard';
import { NewRunModal } from './components/NewRunModal';
import { CorrectionModal } from './components/CorrectionModal';
import { AuthGate } from './components/AuthGate';
import {
  FileText,
  CalendarCheck,
  ShieldAlert,
  Clock,
  ArrowLeftRight,
  BookOpen,
  LayoutDashboard,
  Layers,
} from 'lucide-react';

export const App: React.FC = () => {
  const [runs, setRuns] = useState<RunSummary[]>([]);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);
  const [runDetail, setRunDetail] = useState<RunDetail | null>(null);
  const [events, setEvents] = useState<EventItem[]>([]);
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [samples, setSamples] = useState<SampleData | null>(null);
  const [session, setSession] = useState<Session | null>(null);
  const [isAuthLoading, setIsAuthLoading] = useState(true);

  const [activeTab, setActiveTab] = useState<
    'plan' | 'facts' | 'review' | 'timeline' | 'handoffs' | 'source' | 'dashboard'
  >('plan');

  const [isNewRunOpen, setIsNewRunOpen] = useState(false);
  const [isCorrectionOpen, setIsCorrectionOpen] = useState(false);
  const [correctingFact, setCorrectingFact] = useState<FactItem | null>(null);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [isActionLoading, setIsActionLoading] = useState(false);

  const pollIntervalRef = useRef<number | null>(null);

  useEffect(() => {
    if (!supabase) {
      setIsAuthLoading(false);
      return;
    }

    let isMounted = true;
    supabase.auth
      .getSession()
      .then(({ data, error }) => {
        if (error) console.error('Failed to load Supabase session:', error);
        if (isMounted) setSession(data.session);
      })
      .catch((error: unknown) => {
        console.error('Failed to load Supabase session:', error);
      })
      .finally(() => {
        if (isMounted) setIsAuthLoading(false);
      });

    const { data } = supabase.auth.onAuthStateChange((_event, nextSession) => {
      setSession(nextSession);
      setIsAuthLoading(false);
    });

    return () => {
      isMounted = false;
      data.subscription.unsubscribe();
    };
  }, []);

  // Load public status and samples, and user-scoped runs after sign-in.
  useEffect(() => {
    if (!session) {
      setRuns([]);
      setSelectedRunId(null);
      setRunDetail(null);
      setEvents([]);
      return;
    }
    api.getHealth().then(setHealth).catch(console.error);
    api.getSamples().then(setSamples).catch(console.error);
    loadRuns();
  }, [session]);

  const loadRuns = async () => {
    try {
      const runList = await supabaseData.listRuns();
      setRuns(runList);
      if (runList.length > 0 && !selectedRunId) {
        setSelectedRunId(runList[0].id);
      }
    } catch (err) {
      console.error('Failed to load runs:', err);
    }
  };

  const loadRunDetail = useCallback(async (runId: string) => {
    try {
      const detail = await supabaseData.getRun(runId);
      setRunDetail(detail);

      const evList = await supabaseData.getEvents(runId);
      setEvents(evList);
    } catch (err) {
      console.error(`Failed to load detail for run ${runId}:`, err);
    }
  }, []);

  useEffect(() => {
    if (selectedRunId) {
      loadRunDetail(selectedRunId);
    } else {
      setRunDetail(null);
      setEvents([]);
    }
  }, [selectedRunId, loadRunDetail]);

  // Polling logic when a run is active
  useEffect(() => {
    if (pollIntervalRef.current) {
      window.clearInterval(pollIntervalRef.current);
    }

    const isRunning =
      runDetail &&
      (runDetail.status === 'CREATED' ||
        runDetail.status === 'INTAKE_RUNNING' ||
        runDetail.status === 'PLANNING_RUNNING' ||
        runDetail.status === 'REVIEW_RUNNING');

    if (isRunning && selectedRunId) {
      pollIntervalRef.current = window.setInterval(async () => {
        await loadRunDetail(selectedRunId);
        const updatedRuns = await supabaseData.listRuns();
        setRuns(updatedRuns);
      }, 2000);
    }

    return () => {
      if (pollIntervalRef.current) {
        window.clearInterval(pollIntervalRef.current);
      }
    };
  }, [runDetail, selectedRunId, loadRunDetail]);

  const handleRefresh = async () => {
    setIsRefreshing(true);
    await loadRuns();
    if (selectedRunId) {
      await loadRunDetail(selectedRunId);
    }
    setIsRefreshing(false);
  };

  const handleSignOut = async () => {
    const { error } = await requireSupabase().auth.signOut();
    if (error) alert(`Sign out failed: ${error.message}`);
  };

  const handleCreateRun = async (data: {
    title: string;
    transcript: string;
    company_rules: string;
    max_review_cycles: number;
    fault_injection: string | null;
  }) => {
    const res = await api.createRun(data);
    await loadRuns();
    setSelectedRunId(res.id);
    setActiveTab('plan');
  };

  const handleResume = async () => {
    if (!selectedRunId) return;
    try {
      setIsActionLoading(true);
      await api.resumeRun(selectedRunId);
      await loadRunDetail(selectedRunId);
    } catch (err: any) {
      alert(`Resume failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleReset = async () => {
    if (!selectedRunId) return;
    if (!confirm('Are you sure you want to reset this run back to CREATED state?')) return;
    try {
      setIsActionLoading(true);
      await api.resetRun(selectedRunId);
      await loadRunDetail(selectedRunId);
      await loadRuns();
    } catch (err: any) {
      alert(`Reset failed: ${err.message}`);
    } finally {
      setIsActionLoading(false);
    }
  };

  const handleOpenCorrection = (fact?: FactItem) => {
    setCorrectingFact(fact || null);
    setIsCorrectionOpen(true);
  };

  const handleSubmitCorrection = async (data: {
    fact_id: string;
    field_name: string;
    corrected_value: string;
    correction_note: string;
  }) => {
    if (!selectedRunId) return;
    await api.submitCorrection(selectedRunId, data);
    await loadRunDetail(selectedRunId);
    await loadRuns();
  };

  if (isAuthLoading) {
    return (
      <main className="flex min-h-screen items-center justify-center text-sm text-slate-400">
        Loading secure workspace…
      </main>
    );
  }

  if (!supabaseConfigured || !session || !supabase) {
    return <AuthGate />;
  }

  return (
    <div className="min-h-screen flex flex-col">
      <Navbar
        health={health}
        onNewRun={() => setIsNewRunOpen(true)}
        onRefresh={handleRefresh}
        isRefreshing={isRefreshing}
        userEmail={session.user.email || 'Signed in'}
        onSignOut={handleSignOut}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto p-4 sm:p-6 space-y-6">
        {runDetail ? (
          <>
            {/* Top Pipeline Flow and Summary Bar */}
            <div className="space-y-4">
              <AgentPipeline
                status={runDetail.status}
                cycleCount={runDetail.review_cycle_count}
                maxCycles={runDetail.max_review_cycles}
              />

              <RunSummaryBar
                run={runDetail}
                onResume={handleResume}
                onReset={handleReset}
                onOpenCorrection={() => handleOpenCorrection()}
                isActionLoading={isActionLoading}
              />
            </div>

            {/* Navigation Tabs */}
            <div className="flex items-center justify-between border-b border-slate-800 overflow-x-auto">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setActiveTab('plan')}
                  className={`tab-btn flex items-center gap-2 ${activeTab === 'plan' ? 'active' : ''}`}
                >
                  <CalendarCheck className="w-4 h-4" />
                  <span>Operations Plan</span>
                  {runDetail.all_plans.length > 0 && (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-indigo-500/20 text-indigo-300">
                      v{runDetail.current_plan_version}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('facts')}
                  className={`tab-btn flex items-center gap-2 ${activeTab === 'facts' ? 'active' : ''}`}
                >
                  <FileText className="w-4 h-4" />
                  <span>Intake Facts</span>
                  {runDetail.facts.length > 0 && (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-emerald-500/20 text-emerald-300">
                      {runDetail.facts.length}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('review')}
                  className={`tab-btn flex items-center gap-2 ${activeTab === 'review' ? 'active' : ''}`}
                >
                  <ShieldAlert className="w-4 h-4" />
                  <span>Review & Audit</span>
                  {runDetail.all_reviews.length > 0 && (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-amber-500/20 text-amber-300">
                      {runDetail.all_reviews.length}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('timeline')}
                  className={`tab-btn flex items-center gap-2 ${activeTab === 'timeline' ? 'active' : ''}`}
                >
                  <Clock className="w-4 h-4" />
                  <span>Timeline</span>
                  {events.length > 0 && (
                    <span className="px-1.5 py-0.2 rounded text-[10px] font-mono bg-slate-800 text-slate-400">
                      {events.length}
                    </span>
                  )}
                </button>

                <button
                  onClick={() => setActiveTab('handoffs')}
                  className={`tab-btn flex items-center gap-2 ${activeTab === 'handoffs' ? 'active' : ''}`}
                >
                  <ArrowLeftRight className="w-4 h-4" />
                  <span>Agent Handoffs</span>
                </button>

                <button
                  onClick={() => setActiveTab('source')}
                  className={`tab-btn flex items-center gap-2 ${activeTab === 'source' ? 'active' : ''}`}
                >
                  <BookOpen className="w-4 h-4" />
                  <span>Ground Truth</span>
                </button>
              </div>

              <button
                onClick={() => setActiveTab('dashboard')}
                className={`tab-btn text-xs flex items-center gap-1.5 text-slate-400 hover:text-white ${
                  activeTab === 'dashboard' ? 'active' : ''
                }`}
              >
                <LayoutDashboard className="w-3.5 h-3.5" />
                <span>All Runs ({runs.length})</span>
              </button>
            </div>

            {/* Tab Contents */}
            <div className="pt-2">
              {activeTab === 'plan' && (
                <PlanView
                  plans={runDetail.all_plans}
                  currentVersion={runDetail.current_plan_version}
                />
              )}

              {activeTab === 'facts' && (
                <FactList
                  facts={runDetail.facts}
                  onCorrectFact={handleOpenCorrection}
                />
              )}

              {activeTab === 'review' && (
                <ReviewAudit
                  reviews={runDetail.all_reviews}
                  currentPlanVersion={runDetail.current_plan_version}
                />
              )}

              {activeTab === 'timeline' && <TimelineView events={events} />}

              {activeTab === 'handoffs' && <HandoffInspector handoffs={runDetail.handoffs} />}

              {activeTab === 'source' && (
                <SourceInspector
                  transcript={runDetail.source.transcript}
                  companyRules={runDetail.source.company_rules}
                  sourceVersion={runDetail.source.version}
                />
              )}

              {activeTab === 'dashboard' && (
                <RunDashboard
                  runs={runs}
                  selectedRunId={selectedRunId}
                  onSelectRun={(id) => {
                    setSelectedRunId(id);
                    setActiveTab('plan');
                  }}
                  onNewRun={() => setIsNewRunOpen(true)}
                />
              )}
            </div>
          </>
        ) : (
          <RunDashboard
            runs={runs}
            selectedRunId={selectedRunId}
            onSelectRun={(id) => setSelectedRunId(id)}
            onNewRun={() => setIsNewRunOpen(true)}
          />
        )}
      </main>

      {/* Modals */}
      <NewRunModal
        isOpen={isNewRunOpen}
        onClose={() => setIsNewRunOpen(false)}
        onSubmit={handleCreateRun}
        samples={samples}
      />

      <CorrectionModal
        isOpen={isCorrectionOpen}
        onClose={() => setIsCorrectionOpen(false)}
        onSubmit={handleSubmitCorrection}
        facts={runDetail?.facts || []}
        initialFact={correctingFact}
      />
    </div>
  );
};
