import { EventItem, RunDetail, RunSummary } from '../types';
import type { Database } from '../types/database';
import { requireSupabase } from './supabase';

type Tables = Database['public']['Tables'];
type RunRow = Tables['runs']['Row'];
type SourceRow = Tables['source_versions']['Row'];
type FactRow = Tables['facts']['Row'];
type PlanRow = Tables['plan_versions']['Row'];
type ReviewRow = Tables['review_results']['Row'];
type ExecutionRow = Tables['agent_executions']['Row'];
type CorrectionRow = Tables['user_corrections']['Row'];
type HandoffRow = Tables['handoff_records']['Row'];
type EventRow = Tables['workflow_events']['Row'];

async function queryData<T>(
  query: PromiseLike<{ data: T | null; error: { message: string } | null }>
): Promise<T> {
  const { data, error } = await query;
  if (error) throw new Error(error.message);
  if (data === null) throw new Error('Supabase returned an empty result.');
  return data;
}

export const supabaseData = {
  async listRuns(): Promise<RunSummary[]> {
    const client = requireSupabase();
    const rows = await queryData<RunRow[]>(
      client.from('runs').select('*').order('created_at', { ascending: false })
    );
    return rows.map((run) => ({
      id: run.id,
      title: run.name || 'Operations Coordination',
      status: run.status,
      current_source_version: run.current_source_version,
      current_plan_version: run.current_plan_version || 0,
      review_cycle_count: run.review_cycle_count,
      created_at: run.created_at,
      updated_at: run.updated_at,
    }));
  },

  async getRun(runId: string): Promise<RunDetail> {
    const client = requireSupabase();
    const run = await queryData<RunRow>(
      client.from('runs').select('*').eq('id', runId).single()
    );

    const [
      sourceResult,
      factsResult,
      plansResult,
      reviewsResult,
      executionsResult,
      correctionsResult,
      handoffsResult,
    ] = await Promise.all([
      queryData<SourceRow>(
        client
          .from('source_versions')
          .select('*')
          .eq('run_id', runId)
          .eq('version', run.current_source_version)
          .single()
      ),
      queryData<FactRow[]>(
        client.from('facts').select('*').eq('run_id', runId).eq('source_version', run.current_source_version)
      ),
      queryData<PlanRow[]>(
        client.from('plan_versions').select('*').eq('run_id', runId).order('version')
      ),
      queryData<ReviewRow[]>(
        client.from('review_results').select('*').eq('run_id', runId).order('plan_version')
      ),
      queryData<ExecutionRow[]>(
        client.from('agent_executions').select('*').eq('run_id', runId).order('started_at')
      ),
      queryData<CorrectionRow[]>(
        client.from('user_corrections').select('*').eq('run_id', runId).order('created_at')
      ),
      queryData<HandoffRow[]>(
        client.from('handoff_records').select('*').eq('run_id', runId).order('created_at')
      ),
    ]);

    const source = sourceResult;
    const facts = factsResult;
    const plansData = plansResult;
    const reviewsData = reviewsResult;
    const executions = executionsResult;
    const corrections = correctionsResult;
    const handoffs = handoffsResult;

    const reviews = reviewsData.map((review) => ({
      plan_version: review.plan_version,
      source_version: review.source_version,
      outcome: review.outcome,
      findings: review.findings || [],
      summary: review.summary || '',
      open_questions: review.open_questions || [],
      created_at: review.created_at,
    }));

    const plans = plansData.map((plan) => ({
      version: plan.version,
      source_version: plan.source_version,
      tasks: plan.tasks || [],
      supported_facts: plan.supported_facts || [],
      recommendations: plan.recommendations || [],
      unresolved_questions: plan.unresolved_questions || [],
      dependency_graph: plan.dependency_graph || [],
      change_summary: plan.change_summary || [],
      created_at: plan.created_at,
    }));

    return {
      id: run.id,
      title: run.name || 'Operations Coordination',
      status: run.status,
      current_source_version: run.current_source_version,
      current_plan_version: run.current_plan_version || 0,
      review_cycle_count: run.review_cycle_count,
      max_review_cycles: run.max_review_cycles,
      error_message: run.error_message,
      fault_injection: run.fault_injection,
      created_at: run.created_at,
      updated_at: run.updated_at,
      source: {
        version: source.version,
        transcript: source.transcript,
        company_rules: source.company_rules,
      },
      facts: facts.map((fact) => ({
        fact_id: fact.fact_id,
        fact_type: fact.fact_type,
        content: fact.content,
        evidence_quote: fact.evidence_quote,
        source_location: fact.source_location,
        confidence: fact.confidence,
        owner: fact.owner,
        deadline: fact.deadline,
        missing_fields: fact.missing_fields || [],
        notes: fact.notes || '',
      })),
      current_plan: plans.find((plan) => plan.version === run.current_plan_version) || null,
      all_plans: plans,
      current_review:
        reviews.find((review) => review.plan_version === run.current_plan_version) || null,
      all_reviews: reviews,
      executions: executions.map((execution) => ({
        id: execution.id,
        agent_type: execution.agent_type,
        step_id: execution.step_id,
        attempt_number: execution.attempt_number,
        status: execution.status,
        started_at: execution.started_at,
        completed_at: execution.completed_at,
        error_message: execution.error_message,
        source_version: execution.source_version,
        plan_version: execution.plan_version,
      })),
      corrections: corrections.map((correction) => ({
        id: correction.id,
        fact_id: correction.fact_id,
        field_name: correction.field_name,
        original_value: correction.original_value,
        corrected_value: correction.corrected_value,
        correction_note: correction.correction_note,
        new_source_version: correction.new_source_version,
        created_at: correction.created_at,
      })),
      handoffs: handoffs.map((handoff) => ({
        from_agent: handoff.from_agent,
        to_agent: handoff.to_agent,
        summary: handoff.payload_summary,
        payload: handoff.payload,
        source_version: handoff.source_version,
        plan_version: handoff.plan_version,
        created_at: handoff.created_at,
      })),
    };
  },

  async getEvents(runId: string): Promise<EventItem[]> {
    const client = requireSupabase();
    const rows = await queryData<EventRow[]>(
      client
        .from('workflow_events')
        .select('*')
        .eq('run_id', runId)
        .order('created_at')
    );
    return rows.map((event) => ({
      id: event.id,
      event_type: event.event_type,
      agent_type: event.agent_type,
      description: event.description,
      details: event.version_info,
      timestamp: event.created_at,
    }));
  },
};
