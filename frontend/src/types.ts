export type RunStatus =
  | 'CREATED'
  | 'INTAKE_RUNNING'
  | 'INTAKE_COMPLETED'
  | 'PLANNING_RUNNING'
  | 'PLANNING_COMPLETED'
  | 'REVIEW_RUNNING'
  | 'NEEDS_CORRECTION'
  | 'APPROVED'
  | 'COMPLETED_WITH_UNRESOLVED_ISSUES'
  | 'FAILED'
  | 'INTERRUPTED';

export interface FactItem {
  fact_id: string;
  fact_type: 'decision' | 'requirement' | 'constraint' | 'action_item' | 'risk' | 'conflict' | 'missing_info';
  content: string;
  evidence_quote: string;
  source_location?: string;
  confidence: 'explicit' | 'inferred' | 'missing';
  owner?: string | null;
  deadline?: string | null;
  missing_fields: string[];
  notes?: string;
}

export interface TaskItem {
  task_id: string;
  title: string;
  description: string;
  supporting_fact_ids: string[];
  supporting_source_references: string[];
  owner?: string | null;
  owner_confirmed: boolean;
  deadline?: string | null;
  deadline_confirmed: boolean;
  priority: 'high' | 'medium' | 'low';
  dependencies: string[];
  status: 'proposed' | 'confirmed';
  evidence_classification: 'supported' | 'recommendation' | 'unresolved';
  open_questions: string[];
}

export interface RecommendationItem {
  rec_id: string;
  title: string;
  description: string;
  rationale: string;
  confidence: 'high' | 'medium' | 'low';
}

export interface UnresolvedQuestion {
  question_id: string;
  question: string;
  context: string;
  related_fact_ids: string[];
}

export interface ReviewFinding {
  finding_id: string;
  severity: 'critical' | 'major' | 'minor' | 'info';
  category: 'unsupported_fact' | 'rule_violation' | 'missing_evidence' | 'fabricated_fact' | 'dependency_error' | 'missing_requirement' | 'conflicting_info';
  affected_id: string;
  explanation: string;
  evidence: string;
  required_correction: string;
  blocks_approval: boolean;
}

export interface PlanVersionData {
  version: number;
  source_version: number;
  tasks: TaskItem[];
  supported_facts: string[];
  recommendations: RecommendationItem[];
  unresolved_questions: UnresolvedQuestion[];
  dependency_graph: { from_task: string; to_task: string; dependency_type: string }[];
  change_summary: { change_id: string; task_id: string; field_changed: string; old_value?: string; new_value?: string; reason: string }[];
  created_at: string;
}

export interface ReviewResultData {
  plan_version: number;
  source_version: number;
  outcome: 'APPROVED' | 'NEEDS_CORRECTION' | 'UNRESOLVED';
  findings: ReviewFinding[];
  summary: string;
  open_questions: string[];
  created_at: string;
}

export interface EventItem {
  id: number;
  event_type: string;
  agent_type?: string | null;
  description: string;
  details?: Record<string, unknown> | null;
  timestamp: string;
}

export interface HandoffItem {
  from_agent: string;
  to_agent: string;
  summary: string;
  payload?: Record<string, unknown> | null;
  source_version: number;
  plan_version?: number | null;
  created_at: string;
}

export interface AgentExecutionItem {
  id: number;
  agent_type: string;
  step_id: string;
  attempt_number: number;
  status: string;
  started_at: string;
  completed_at?: string | null;
  error_message?: string | null;
  source_version: number;
  plan_version?: number | null;
}

export interface UserCorrectionItem {
  id: number;
  fact_id: string;
  field_name: string;
  original_value?: string | null;
  corrected_value: string;
  correction_note: string;
  new_source_version: number;
  created_at: string;
}

export interface RunDetail {
  id: string;
  title: string;
  status: RunStatus;
  current_source_version: number;
  current_plan_version: number;
  review_cycle_count: number;
  max_review_cycles: number;
  error_message?: string | null;
  fault_injection?: string | null;
  created_at: string;
  updated_at: string;
  source: {
    version: number;
    transcript: string;
    company_rules: string;
  };
  facts: FactItem[];
  current_plan?: PlanVersionData | null;
  all_plans: PlanVersionData[];
  current_review?: ReviewResultData | null;
  all_reviews: ReviewResultData[];
  executions: AgentExecutionItem[];
  corrections: UserCorrectionItem[];
  handoffs: HandoffItem[];
}

export interface RunSummary {
  id: string;
  title: string;
  status: RunStatus;
  current_source_version: number;
  current_plan_version: number;
  review_cycle_count: number;
  created_at: string;
  updated_at: string;
}

export interface SystemHealth {
  status: string;
  llm_provider: string;
  llm_model: string;
  llm_configured: boolean;
  demo_faults_enabled: boolean;
}

export interface SampleData {
  transcripts: Record<string, string>;
  rules: Record<string, string>;
}
