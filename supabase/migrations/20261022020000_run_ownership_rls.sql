ALTER TABLE public.runs
  ADD COLUMN IF NOT EXISTS owner_id uuid;

CREATE INDEX IF NOT EXISTS ix_runs_owner_created
  ON public.runs (owner_id, created_at DESC);

ALTER TABLE public.runs ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS "Users can read their own runs" ON public.runs;
CREATE POLICY "Users can read their own runs"
  ON public.runs
  FOR SELECT
  TO authenticated
  USING (owner_id = (SELECT auth.uid()));

DO $$
DECLARE
  table_name text;
BEGIN
  FOREACH table_name IN ARRAY ARRAY[
    'source_versions',
    'facts',
    'user_corrections',
    'agent_executions',
    'plan_versions',
    'review_results',
    'workflow_events',
    'handoff_records'
  ]
  LOOP
    EXECUTE format('ALTER TABLE public.%I ENABLE ROW LEVEL SECURITY', table_name);
    EXECUTE format('DROP POLICY IF EXISTS "Users can read own %I" ON public.%I', table_name, table_name);
    EXECUTE format(
      'CREATE POLICY "Users can read own %I" ON public.%I FOR SELECT TO authenticated USING (EXISTS (SELECT 1 FROM public.runs r WHERE r.id = run_id AND r.owner_id = (SELECT auth.uid())))',
      table_name,
      table_name
    );
  END LOOP;
END
$$;
