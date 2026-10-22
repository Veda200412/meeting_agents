# CogniOps — AI Operations Coordinator

[![Backend Tests](https://img.shields.io/badge/pytest-45%20passed-emerald)](backend/tests/test_backend.py)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-19-61dafb)](https://react.dev)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178c6)](https://www.typescriptlang.org)
[![Vite](https://img.shields.io/badge/Vite-8-646cff)](https://vitejs.dev)

An enterprise-grade, multi-agent AI system that converts unstructured meeting transcripts and strict company rules into reviewed, traceable, and actionable operational execution plans.

Built with **three distinct, collaborating LLM-powered mini-agents**:
1. **Intake Agent**: Ground-truth extraction, verbatim evidence quote mapping, and uncertainty tagging.
2. **Planning Agent**: Evidence-based action synthesis, ownership confirmation, dependency scheduling, and open question resolution.
3. **Review Agent**: Independent compliance auditor that cross-verifies plans against transcripts and company policies, enforcing an automated correction loop.

---

## Architecture Overview

```
                                      +--------------------------+
                                      |    Meeting Transcript    |
                                      |            +             |
                                      |     Company Policies     |
                                      +------------+-------------+
                                                   |
                                                   v
                                      +--------------------------+
                                      |   1. Intake Agent        |
                                      |  (Factual Ground Truth)  |
                                      +------------+-------------+
                                                   |
                                                   | [Handoff: Validated Facts & Quotes]
                                                   v
                                      +--------------------------+
                                      |   2. Planning Agent      | <-----+
                                      | (Action Plan Synthesis)  |       |
                                      +------------+-------------+       |
                                                   |                     |
                                                   | [Handoff: Tasks &   | [Correction Loop]
                                                   |  Dependencies]      |
                                                   v                     |
                                      +--------------------------+       |
                                      |   3. Review Agent        |       |
                                      |  (Independent Auditor)   | ------+
                                      +------------+-------------+ (NEEDS_CORRECTION)
                                                   |
                                                   | (APPROVED)
                                                   v
                                      +--------------------------+
                                      |   Final Verified Plan    |
                                      +--------------------------+
```

---

## Key Features

### 1. Three Genuine LLM-Powered Mini-Agents
- **Intake Agent**: Extracts decisions, requirements, action items, risks, conflicts, and missing information. Every fact is bound to an exact verbatim source quote and character span.
- **Planning Agent**: Derives operational tasks (`T-001`, `T-002`, etc.) with strict distinction between *supported* tasks, *recommendations*, and *unresolved* issues. Complies with company policies regarding owner assignments and deadlines.
- **Review Agent**: Acts as an un-trusting, independent auditor. Analyzes the synthesized plan against raw inputs, flagging invented deadlines, missing dependencies, or unconfirmed owners with actionable audit findings.

### 2. Automated Review-Correction Loop
- When the Review Agent flags policy violations or unsupported claims, the workflow automatically transitions to `NEEDS_CORRECTION`.
- The Planning Agent receives the structured audit feedback, increments the plan version (`v1` ➔ `v2`), preserves compliant elements, and remedies the flagged items.

### 3. Human-in-the-Loop Fact Correction
- Operators can inspect extracted facts in the UI and apply inline corrections (e.g., assigning a confirmed owner or agreed deadline).
- Submitting a correction increments the source version (`sv1` ➔ `sv2`), invalidates downstream artifacts, and automatically triggers end-to-end re-planning.

### 4. Resilience & Fault Simulation (Demo Ready)
- Built-in fault injection triggers simulate model errors (`intake_failure`, `planning_failure`, `schema_failure`).
- The idempotent state machine records failed steps and allows operators to click **Resume Workflow** to pick up execution smoothly.
- Fault injection is disabled by default and must be explicitly enabled; injected failures are labelled `[SIMULATED]`.

### 5. Persisted, Inspectable Agent Handoffs
- Validated Intake → Planning and Planning → Review payloads are stored with run and source/plan versions.
- Review findings sent back to Planning are recorded as Review → Planning handoffs and can be inspected in the UI.
- Handoff writes are idempotent by run, stage pair, and context version.

### 6. Responsive Operations Workspace
- Built with React, TypeScript, Tailwind CSS utilities, and a custom dark visual system.
- Live pipeline visualizer, tabular fact inspector, versioned plan comparator, audit log viewer, chronological timeline, and inter-agent handoff inspector.

---

## Project Structure

```
├── backend/
│   ├── app/
│   │   ├── agents/              # Individual agent definitions & prompt engineering
│   │   │   ├── base.py          # Shared agent execution logic & structured generation
│   │   │   ├── intake_agent.py  # Fact extraction & verbatim quote linking
│   │   │   ├── planning_agent.py# Task creation, priority & dependency assignment
│   │   │   └── review_agent.py  # Independent compliance & factual auditor
│   │   ├── api/                 # FastAPI router, Supabase Auth & endpoint definitions
│   │   │   └── routes.py        # /runs, /events, /handoffs, /corrections, /resume
│   │   ├── core/                # Configuration settings & security sanitizers
│   │   ├── db/                  # Supabase Data API persistence and test-only SQLite
│   │   │   ├── models.py        # Runs, Facts, PlanVersions, ReviewResults, Events
│   │   │   ├── supabase_store.py # Server-side Supabase Data API client
│   │   │   └── repository.py    # Data API persistence and test repository dispatch
│   │   ├── llm/                 # Gemini API integration & deterministic mock provider
│   │   │   ├── provider.py      # LLMProvider abstraction & structured validation
│   │   │   └── schemas.py       # Pydantic v2 schemas for all inputs & outputs
│   │   ├── orchestration/       # State machine, handoff validation & workflow engine
│   │   │   ├── handoffs.py      # Inter-stage schema validators
│   │   │   ├── state_machine.py # State transitions & resume logic
│   │   │   └── workflow.py      # Multi-agent coordinator & review loop
│   │   └── main.py              # Application entrypoint & CORS lifecycle
│   ├── tests/
│   │   └── test_backend.py      # Backend tests with deterministic mocks and auth isolation
│   ├── requirements.txt         # Python dependencies
│   └── .env.example             # Safe environment-variable template
├── supabase/
│   └── migrations/              # RLS policies for authenticated, owner-scoped reads
├── api/
│   └── index.py                 # Vercel FastAPI serverless entry point
├── frontend/
│   ├── src/
│   │   ├── components/          # Modular UI components (Pipeline, Plan, Audit, etc.)
│   │   ├── services/            # API client and RLS-scoped Supabase JS reads
│   │   ├── types.ts             # TypeScript domain interfaces
│   │   ├── index.css            # Tailwind utilities and custom responsive dark theme
│   │   └── App.tsx              # Main dashboard application
│   ├── package.json             # NPM package scripts & dependencies
│   ├── .env.example             # Safe Supabase browser configuration template
│   └── vite.config.ts           # Vite bundler & API reverse proxy configuration
├── vercel.json                  # Full-stack Vercel build and API routing
├── requirements.txt             # Vercel Python function dependencies
└── README.md
```

---

## Quick Start Guide

### Prerequisites
- Python 3.10+
- Node.js 18+ and npm

### 1. Backend Setup
```bash
cd backend

# Install dependencies
python -m pip install -r requirements.txt

# Copy .env.example to .env, then set your Supabase project URL, anon key,
# server-only service role key, and GOOGLE_API_KEY for live Gemini calls.
# Use LLM_PROVIDER=mock for local deterministic demo runs.
# Never commit .env or API keys.

# Run unit tests
python -m pytest tests/test_backend.py -v

# Start the backend server (runs on port 8000)
python -m uvicorn app.main:app --port 8000
```

### 2. Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Copy .env.example to .env.local and set SUPABASE_URL and SUPABASE_ANON_KEY.
# Never put a service-role key here.

# Start the Vite development server (runs on port 5173)
npm run dev
```

Open `http://localhost:5173/` in your browser. Before using the app, create a Supabase project, apply both SQL migrations in order, and configure the backend and frontend environment variables. Enable the Email provider in Supabase Auth. For offline model runs, set `LLM_PROVIDER=mock`; the mock provider is deterministic and intended for local tests/demos, and does not make genuine model calls.

### Environment variables

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `LLM_PROVIDER` | `gemini` | `gemini` for real agent calls; `mock` for deterministic offline runs |
| `LLM_MODEL` | `gemini-2.0-flash` | Gemini model identifier |
| `GOOGLE_API_KEY` | empty | Gemini API key; required when `LLM_PROVIDER=gemini` |
| `SUPABASE_URL` | empty | Supabase project URL used by frontend build and backend |
| `SUPABASE_ANON_KEY` | empty | Public anon key used by frontend build and backend Auth verification |
| `SUPABASE_SERVICE_ROLE_KEY` | empty | Server-only key for backend Data API writes; never expose it to the browser |
| `MAX_REVIEW_CYCLES` | `2` | Maximum planning revisions after the initial plan |
| `LLM_MAX_RETRIES` | `2` | Retry limit for transient provider failures and invalid structured output |
| `REQUEST_TIMEOUT_SECONDS` | `60` | Provider timeout |
| `ENABLE_DEMO_FAULTS` | `false` | Enables clearly-labelled simulated failures in the new-run form |
| `FRONTEND_ORIGIN` | `http://localhost:5173` | Allowed frontend origin for CORS |

### Deploying with Supabase

The backend uses Supabase's HTTPS Data API for persistence; it does not use a database connection URI, driver, or direct database socket. SQLite and SQLAlchemy are retained only for isolated backend tests.

1. Create a Supabase project. In **Project Settings / API**, copy the Project URL and public anon/publishable key. Obtain the server-only service role key and keep it in backend secrets only.
2. Enable the **Email** provider in **Authentication / Sign In / Providers**. Set local and deployed frontend origins in **Authentication / URL Configuration** so confirmation links return users to the app.
3. Apply [`supabase/migrations/20261022010000_create_app_tables.sql`](./supabase/migrations/20261022010000_create_app_tables.sql), then [`supabase/migrations/20261022020000_run_ownership_rls.sql`](./supabase/migrations/20261022020000_run_ownership_rls.sql), in the Supabase SQL Editor. The first creates the application tables and the second enables owner-scoped browser reads. Existing rows without an owner remain inaccessible until explicitly assigned.
4. Configure backend secrets: `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `GOOGLE_API_KEY` (for live Gemini calls), `LLM_PROVIDER`, `LLM_MODEL`, and `FRONTEND_ORIGIN`. Deploy the backend as an API service. FastAPI validates each user's access token and checks run ownership before accessing private run data.
5. Configure frontend variables `SUPABASE_URL` and `SUPABASE_ANON_KEY`, then point the frontend's `/api` proxy or hosting rewrite to the backend URL. Browser reads use the signed-in user's session and RLS. Never set a service role key or LLM key in frontend variables.

Set backend values in `backend/.env` and frontend values in `frontend/.env.local` for local development, or use hosting-provider secret settings for deployment. The Vite build accepts `SUPABASE_URL` and `SUPABASE_ANON_KEY` (and the legacy `VITE_SUPABASE_URL` and `VITE_SUPABASE_ANON_KEY` names). It explicitly injects only the public URL and anon key into browser assets, never the server-only key. This workspace does not include valid project credentials; replace the placeholders locally and do not paste credentials into chat or commit `.env` files. Existing local database files are left untouched and are not migrated automatically.

### Deploying the full app to Vercel

The repository includes [`vercel.json`](./vercel.json), which builds the React app from `frontend`, serves the FastAPI app through the Python function in [`api/index.py`](./api/index.py), and routes `/api/*` requests to that function. Import the repository into Vercel and keep the project root set to the repository root. The configured install command installs frontend packages; Vercel installs the Python function dependencies from the root `requirements.txt`. The build command and output directory are also configured in `vercel.json`.

Add these Environment Variables in Vercel for **Production**, **Preview**, and **Development** as applicable:

| Vercel variable | Used by | Required |
| :--- | :--- | :--- |
| `SUPABASE_URL` | Browser build + API | Yes |
| `SUPABASE_ANON_KEY` | Browser build + API auth verification | Yes |
| `SUPABASE_SERVICE_ROLE_KEY` | API server only; never bundled into browser assets | Yes |
| `GOOGLE_API_KEY` | API server, for genuine Gemini agent runs | Yes |
| `LLM_PROVIDER` | API server; set to `gemini` | Optional (defaults to `gemini`) |
| `LLM_MODEL` | API server; defaults to `gemini-2.0-flash` | Optional |
| `FRONTEND_ORIGIN` | API CORS; Vercel serves frontend/API same-origin | Optional |

The user’s requested three Supabase values are needed, and `GOOGLE_API_KEY` is additionally required because the selected deployment uses genuine Gemini-powered agents. Save it as a Vercel secret/environment variable; it is not a browser variable. On Vercel, agent workflows run within the API request rather than an unreliable background thread. `vercel.json` allows up to 300 seconds; function duration limits depend on the Vercel plan.

Before deploying, create the Supabase project and apply both SQL migrations in order as described above. Configure Supabase Auth’s allowed redirect URLs with the Vercel production domain and any Preview domains you intend to use. After the Vercel build, register and sign in through the app to verify Auth, API routing, Gemini, and RLS-protected reads.

## Assignment demo walkthrough

1. **Complete three-agent run:** create a run with either sample preset and follow the Intake → Planning → Review stages. Open **Intake Facts**, **Operations Plan**, **Review & Audit**, and **Agent Handoffs** to inspect outputs and versioned handoff payloads.
2. **Review correction loop:** use the complex preset, whose conflicting dates and stated constraints give the reviewer concrete issues to check. When Review returns blocking findings, the Review → Planning handoff shows the requested corrections; plan revisions include their change summary. The correction loop is bounded by `MAX_REVIEW_CYCLES`.
3. **Changed source fact:** open **Intake Facts**, choose **Correct Fact**, submit a verified field value, then check the incremented source version and regenerated plan/review. A source correction invalidates all downstream artifacts for that run before rerunning Intake.
4. **Simulated model failure and recovery:** set `ENABLE_DEMO_FAULTS=true`, create a run with one of the fault options, confirm the run reports a `[SIMULATED]` failure, then use **Resume Workflow**. Completed steps are reused instead of duplicated.
5. **Run/session isolation:** create two runs with distinct transcripts and rules, switch between them in **All Runs**, and verify facts, sources, plans, and handoffs remain scoped to their run IDs. `test_run_isolation` and `test_cross_run_access` cover this boundary.
6. **Reset:** use **Reset Run** to delete the selected run and its associated records.

### Cost estimate

An uncomplicated live run makes three model calls (Intake, Planning, Review); each review-correction iteration adds two calls (Planning and Review). For short sample inputs using a low-cost Flash-tier model, budget approximately **US$0.01–$0.05 per successful run**, plus roughly the same amount per correction iteration. This is a planning estimate, not metered billing: transcript size, generated JSON, model/retry behavior, provider tier, and current prices affect the actual cost. Check the [Gemini API pricing page](https://ai.google.dev/gemini-api/docs/pricing) before deployment.

### Known limitations and submission checklist

- Supabase Auth protects the workspace. Browser reads are owner-scoped by RLS; FastAPI validates each access token and independently enforces run ownership. Existing unowned rows are not auto-assigned to a user.
- A model may produce different findings across runs; use the automated tests for repeatable correction-loop and failure-recovery verification.
- This repository does not itself deploy a public URL or record a Loom video. Before submission, deploy both assignments (or both routes in one app), keep the demo accessible for seven days, and add the live application URL, demo access steps, source repository URL, and 8–12 minute Loom URL here. Do not put secrets in the links or repository.

---

## Verification & Testing

The backend includes a comprehensive test suite covering:
- **Schema Validation**: Mandatory source quotes, nullability, confidence markers.
- **Handoff Validation**: Missing evidence rejection, duplicate task ID detection, dependency cycle detection.
- **State Machine Transitions**: Valid and invalid lifecycle transitions, resume capabilities.
- **API Endpoints**: Health, sample presets, run creation, pagination, events, and resets.
- **Database Repository**: Source versioning, run isolation, idempotent execution reuse.
- **End-to-End Workflow**: Full approved workflows, multi-cycle correction loops, fault simulation, and recovery.

To run the test suite:
```bash
python -m pytest backend/tests/test_backend.py -v
```

---

## API Reference Summary

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/api/health` | `GET` | Health check & LLM provider status |
| `/api/samples` | `GET` | Pre-configured meeting transcripts & company rules |
| `/api/runs` | `GET` | Paginated list of all coordination runs |
| `/api/runs` | `POST` | Create and automatically execute a new coordination run |
| `/api/runs/{id}` | `GET` | Full run detail including facts, plans, reviews & handoffs |
| `/api/runs/{id}/events` | `GET` | Chronological event audit trail for timeline view |
| `/api/runs/{id}/handoffs` | `GET` | Traceable inter-agent handoff payload records |
| `/api/runs/{id}/corrections` | `POST` | Submit human correction on a fact and trigger re-plan |
| `/api/runs/{id}/resume` | `POST` | Resume interrupted or failed workflow execution |
| `/api/runs/{id}/reset` | `POST` | Delete or reset run back to initial state |
