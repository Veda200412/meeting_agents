import type {
  AgentExecutionItem,
  FactItem,
  HandoffItem,
  PlanVersionData,
  ReviewFinding,
  RecommendationItem,
  UnresolvedQuestion,
  UserCorrectionItem,
  RunStatus,
} from '../types';

type Table<Row> = {
  Row: Row;
  Insert: Partial<Row>;
  Update: Partial<Row>;
  Relationships: [];
};

export interface Database {
  public: {
    Tables: {
      runs: Table<{
        id: string;
        owner_id: string | null;
        name: string | null;
        status: RunStatus;
        current_source_version: number;
        current_plan_version: number | null;
        review_cycle_count: number;
        max_review_cycles: number;
        fault_injection: string | null;
        error_message: string | null;
        created_at: string;
        updated_at: string;
      }>;
      source_versions: Table<{
        id: number;
        run_id: string;
        version: number;
        transcript: string;
        company_rules: string;
        created_at: string;
      }>;
      facts: Table<FactItem & {
        id: number;
        run_id: string;
        source_version: number;
      }>;
      plan_versions: Table<PlanVersionData & { id: number; run_id: string }>;
      review_results: Table<{
        id: number;
        run_id: string;
        plan_version: number;
        source_version: number;
        outcome: 'APPROVED' | 'NEEDS_CORRECTION' | 'UNRESOLVED';
        findings: ReviewFinding[];
        summary: string;
        open_questions: string[];
        created_at: string;
      }>;
      agent_executions: Table<AgentExecutionItem & {
        run_id: string;
        input_snapshot: Record<string, unknown> | null;
        output_snapshot: Record<string, unknown> | null;
      }>;
      user_corrections: Table<UserCorrectionItem & { run_id: string }>;
      workflow_events: Table<{
        id: number;
        run_id: string;
        event_type: string;
        agent_type: string | null;
        description: string;
        version_info: Record<string, unknown> | null;
        created_at: string;
      }>;
      handoff_records: Table<HandoffItem & {
        id: number;
        run_id: string;
        payload_summary: string;
      }>;
    };
    Views: Record<string, never>;
    Functions: Record<string, never>;
    Enums: Record<string, never>;
    CompositeTypes: Record<string, never>;
  };
}
