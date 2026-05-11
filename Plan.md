# Day 08 Lab Plan - Target 90-100

## 1. Goal

Build a production-style LangGraph support-ticket workflow that:

- routes all sample and hidden scenarios by keyword/state logic, not scenario id
- has a bounded retry loop
- includes approval/HITL for risky actions
- persists state with a real checkpointer
- produces valid metrics and a complete report
- includes a lightweight UI to demonstrate Human in the Loop approval/reject flow
- includes at least one bonus extension with evidence

Primary target:

- `make test` passes
- `make run-scenarios` writes valid `outputs/metrics.json`
- `make grade-local` passes
- `reports/lab_report.md` is complete and demo-ready
- a simple UI exists to demonstrate the approval step end-to-end
- the UI is launchable with one documented command
- metrics include the required per-scenario fields, especially `latency_ms`
- at least one extension is implemented and documented

Recommended score strategy:

- finish the full core graph first
- implement SQLite persistence as the main 90+ extension
- implement real HITL plus a small demo UI right after the core graph is stable
- export a graph diagram as a low-risk supporting extension

## 1.1 Deliverables Manifest

Expected final artifacts:

- `src/langgraph_agent_lab/state.py`
- `src/langgraph_agent_lab/nodes.py`
- `src/langgraph_agent_lab/routing.py`
- `src/langgraph_agent_lab/graph.py`
- `src/langgraph_agent_lab/persistence.py`
- `src/langgraph_agent_lab/report.py`
- `outputs/metrics.json`
- `reports/lab_report.md`
- `configs/lab.yaml`
- one UI entrypoint such as `streamlit_app.py`
- optional checkpoint database such as `checkpoints.db`
- optional graph diagram file under `reports/` or `docs/`

Supporting hygiene artifacts if needed:

- `pyproject.toml` for UI dependencies
- `.env.example` for runtime configuration hints
- `README.md` or report notes showing how to launch the UI/demo

## 2. Rubric-To-Deliverable Map

| Rubric area | Points | What to deliver | Evidence |
|---|---:|---|---|
| Architecture and state schema | 20 | lean typed state, correct reducers, clean node boundaries | `state.py`, `nodes.py`, `graph.py`, explanation in report |
| Graph behavior | 25 | all routes correct, retry bounded, approval path works, all paths terminate | tests, `run-scenarios`, visible event trail in metrics |
| Persistence and recovery | 15 | checkpointer wired, thread id per run, state history or resume evidence | `persistence.py`, config update, report section, logs/screenshots |
| Metrics and tests | 20 | valid metrics file, scenario coverage, pass tests | `outputs/metrics.json`, `make test`, `make grade-local` |
| Report and demo | 15 | architecture summary, metrics table, failure analysis, improvement plan, UI demo flow | `reports/lab_report.md`, UI screenshot or demo notes |
| Production hygiene | 5 | config, env handling, lint/type discipline, runnable demo instructions | `configs/lab.yaml`, `.env.example`, `pyproject.toml`, `make lint`, `make typecheck` |

Minimum to avoid losing easy points:

- no hard-coded scenario ids
- no unbounded retry
- no route that skips `finalize -> END`
- risky scenarios must hit approval
- dead-letter path must work for `max_attempts = 1`

## 3. Implementation Order

### Phase 0 - Baseline and guardrails

- Run `make test` to see current baseline.
- Read `README.md`, `docs/LAB_GUIDE.md`, `docs/RUBRIC.md`, and `docs/METRICS.md`.
- Verify whether UI dependencies such as `streamlit` need to be added to `pyproject.toml`.
- Decide early whether UI launch will be a raw command or a helper target.
- Keep the target graph fixed unless there is a strong reason to change it:

```text
START -> intake -> classify
simple       -> answer -> finalize -> END
tool         -> tool -> evaluate -> answer -> finalize -> END
missing_info -> clarify -> finalize -> END
risky        -> risky_action -> approval -> tool -> evaluate -> answer -> finalize -> END
error        -> retry -> tool -> evaluate -> retry/tool loop -> dead_letter -> finalize -> END
```

### Phase 1 - Core graph first

Work these files in this order:

| File | Required work | Why it matters |
|---|---|---|
| `src/langgraph_agent_lab/state.py` | confirm append-only fields, keep serializable state, preserve `evaluation_result` | reducers and state design are directly graded |
| `src/langgraph_agent_lab/nodes.py` | implement stable node outputs, approval flow, retry bookkeeping, final answers, dead-letter behavior | most graph behavior points live here |
| `src/langgraph_agent_lab/routing.py` | safe conditional routing after classify, evaluate, retry, approval | hidden scenarios will stress routing logic |
| `src/langgraph_agent_lab/graph.py` | wire every path to `finalize -> END` and preserve the retry loop | termination and correctness depend on this |
| `tests/` | add targeted tests for edge cases | protects against regressions and hidden grading cases |

Definition of done for Phase 1:

- all 7 sample scenarios route correctly
- risky scenarios pass through approval
- error scenarios retry and then either recover or dead-letter
- every successful or clarify path returns either `final_answer` or `pending_question`
- no route depends on sample scenario ids or exact full-query matching

### Phase 2 - Persistence and recovery

Main 90+ extension:

- implement SQLite checkpointer in `src/langgraph_agent_lab/persistence.py`
- prefer `sqlite3.connect(...)` plus WAL mode
- do not rely on `SqliteSaver.from_conn_string()` if the lab expects the newer 3.x API
- keep `thread_id` stable per scenario run
- collect evidence of resume or state history for the report

Suggested implementation target:

- `memory` for simple local runs
- `sqlite` for the final demo path
- optional `postgres` only if the local environment already supports it

Definition of done for Phase 2:

- graph compiles with SQLite checkpointer
- same scenario can be inspected or resumed by `thread_id`
- report includes persistence evidence, not just code

### Phase 3 - HITL UI demo

Additional lab requirement for this plan:

- provide a minimal UI to demonstrate Human in the Loop
- the UI should allow a reviewer to inspect the proposed risky action
- the UI should allow `approve` and ideally `reject`
- the UI should be connected to the LangGraph approval step, not a fake standalone mockup

Recommended implementation:

- use Streamlit for the fastest working demo
- expose one risky sample scenario and one non-risky sample scenario
- when `LANGGRAPH_INTERRUPT=true`, surface the interrupt payload in the UI
- allow the reviewer to submit an approval decision and resume the graph
- make approve and reject lead to visibly different graph outcomes

Definition of done for Phase 3:

- UI starts locally with one command
- risky scenario visibly pauses for approval
- user can approve or reject from the UI
- graph resumes and reaches a terminal state
- report includes one screenshot or explanation of the UI flow
- the UI uses the real graph approval state, not a duplicated mock-only branch

### Phase 4 - Metrics and report

- Ensure `outputs/metrics.json` matches `MetricsReport`.
- Confirm scenario metrics include route, retries, interrupts, and errors.
- Make `reports/lab_report.md` useful, not boilerplate.
- Explain why the numbers look the way they do.

Definition of done for Phase 4:

- `make run-scenarios` writes metrics
- `make grade-local` validates metrics
- report includes architecture, state schema, metrics table, failure analysis, persistence evidence, extension section, improvement plan
- `outputs/metrics.json` contains all required top-level and scenario-level fields

### Phase 5 - Bonus polish

Recommended order by return on effort:

1. SQLite persistence with evidence
2. Real HITL using `LANGGRAPH_INTERRUPT=true` plus UI demo
3. Mermaid graph export and include it in report
4. Time-travel replay from checkpoint history
5. Parallel fan-out only if the rest is already stable

Reason for this ordering:

- SQLite directly supports both rubric points and bonus expectations
- HITL plus UI is strong demo evidence and makes the approval path easy to explain
- graph diagram is low-risk and visually strong in demo/report
- fan-out is useful, but it is not the safest first extension under time pressure

## 4. Routing Policy To Implement

Use keyword heuristics with clear priority:

| Priority | Route | Example triggers |
|---|---|---|
| 1 | `risky` | `refund`, `delete`, `send`, `cancel`, `remove`, `revoke` |
| 2 | `tool` | `status`, `order`, `lookup`, `check`, `track`, `find`, `search` |
| 3 | `missing_info` | very short vague prompts, especially whole-word pronouns like `it` |
| 4 | `error` | `timeout`, `fail`, `error`, `crash`, `unavailable` |
| 5 | `simple` | default fallback |

Rules to keep:

- risky keywords win over tool keywords
- punctuation should be stripped before token checks
- whole-word matching matters for `it`
- unknown or malformed route values should fall back safely

Recommended hidden-scenario tests:

- `Refund and check order status` should go to `risky`
- `Can you fix it?!` should go to `missing_info`
- `Timeout error on lookup` should follow your chosen priority consistently
- `max_attempts = 1` should dead-letter cleanly

## 5. File-By-File Plan

### `src/langgraph_agent_lab/state.py`

- Keep append-only reducers for `messages`, `tool_results`, `errors`, and `events`.
- Keep overwrite semantics for `route`, `risk_level`, `attempt`, `approval`, and `evaluation_result`.
- Keep state lean and serializable.
- Do not add large opaque objects to state.

### `src/langgraph_agent_lab/nodes.py`

- `intake_node`: normalize query and append audit event.
- `classify_node`: implement deterministic keyword routing with priority.
- `ask_clarification_node`: ask a specific missing-info question based on the query.
- `tool_node`: make tool behavior idempotent enough for retries and support transient error simulation.
- `risky_action_node`: produce a concrete `proposed_action` and risk rationale.
- `approval_node`: default to mock approval, support interrupt path for demo.
- `retry_or_fallback_node`: increment attempt count, record retry metadata, keep errors append-only.
- `evaluate_node`: inspect latest tool result and set `evaluation_result` to `success` or `needs_retry`.
- `answer_node`: produce a grounded answer from tool results or safe direct response.
- `dead_letter_node`: create a final manual-review message and log the failure.
- `finalize_node`: always emit a final audit event.

### `src/langgraph_agent_lab/routing.py`

- map route values explicitly
- ensure `needs_retry -> retry`
- ensure `attempt >= max_attempts -> dead_letter`
- ensure rejected approval returns a safe path like `clarify`

### `src/langgraph_agent_lab/graph.py`

- verify `classify -> error -> retry`
- verify `retry -> tool` and `retry -> dead_letter`
- verify `tool -> evaluate`
- verify `answer`, `clarify`, and `dead_letter` all go to `finalize`
- verify `finalize -> END`

### `src/langgraph_agent_lab/persistence.py`

- support `memory` and `sqlite`
- set SQLite to WAL mode
- keep connection setup explicit and easy to explain in demo
- only keep `postgres` if it is real and tested locally

### `src/langgraph_agent_lab/report.py`

- replace the stub with a report that follows `reports/lab_report_template.md`
- use generated metrics to prefill the metrics section if possible
- keep the rest easy to edit manually before submission

### `src/langgraph_agent_lab/metrics.py`

- ensure top-level metrics include:
  - `total_scenarios`
  - `success_rate`
  - `avg_nodes_visited`
  - `total_retries`
  - `total_interrupts`
  - `resume_success`
- ensure scenario metrics include:
  - `scenario_id`
  - `success`
  - `expected_route`
  - `actual_route`
  - `nodes_visited`
  - `retry_count`
  - `interrupt_count`
  - `approval_required`
  - `approval_observed`
  - `latency_ms`
  - `errors`
- only set `resume_success=true` if resume or replay is actually demonstrated

### `configs/lab.yaml`

- keep the config aligned with the final demo mode
- use `checkpointer: memory` during fast iteration if needed
- switch to `checkpointer: sqlite` for the persistence demo
- ensure `report_path` points to `reports/lab_report.md`

### `pyproject.toml`, `.env.example`, and optional `Makefile`

- add `streamlit` dependency only if the UI truly uses it
- document any extra dependency needed for SQLite or UI
- update `.env.example` if you introduce new variables such as `LANGGRAPH_INTERRUPT` or a SQLite path
- optionally add a helper target or a clearly documented launch command for the UI

### `streamlit_app.py` or `src/.../ui.py`

- build a minimal UI for the HITL demo
- show query, classified route, proposed action, risk level, and approval status
- provide `Approve` and `Reject` controls
- resume the graph after reviewer input
- keep the UI intentionally small and reliable

## 6. Testing Plan

Mandatory commands:

```bash
make test
make run-scenarios
make grade-local
make lint
make typecheck
```

Recommended test additions:

- route priority tests for overlapping keywords
- retry bound tests for `max_attempts = 1` and `max_attempts = 3`
- approval-path tests for risky scenarios
- smoke test that every terminal route returns an answer or clarification
- persistence test if SQLite is enabled locally
- basic UI smoke check if the UI entrypoint is added
- metrics validation test for `latency_ms` and other required schema fields
- at least one custom scenario beyond the provided 7 to reduce hidden-scenario risk

Pass criteria:

- no failing unit tests
- no invalid metrics schema
- sample scenarios all marked successful
- no route hangs or loops forever
- at least 6 scenarios are present in the final metrics file

## 7. Report Plan

Fill `reports/lab_report.md` with:

- student info, repo/commit, and date
- architecture overview of nodes, edges, and why the graph is structured this way
- state schema table showing append-only vs overwrite fields
- scenario metrics table copied from `outputs/metrics.json`
- top-level metrics summary:
  - `total_scenarios`
  - `success_rate`
  - `avg_nodes_visited`
  - `total_retries`
  - `total_interrupts`
  - `resume_success`
- failure analysis for:
  - transient tool failure and retry
  - risky action without approval
- persistence evidence:
  - SQLite enabled
  - stable `thread_id`
  - state history or crash-resume proof
- UI demonstration evidence:
  - screenshot of approval screen
  - brief explanation of approve/reject flow
- extension section:
  - SQLite persistence
  - real HITL plus UI
  - graph diagram export
- improvement plan:
  - structured tool results
  - richer evaluator
  - real dead-letter sink
  - auth, tracing, and monitoring

The report should answer one important question clearly:

- why the graph behaves the way it does when things go wrong

## 8. 90+ Extension Strategy

### Extension 1 - SQLite persistence

Target outcome:

- switch `configs/lab.yaml` from `memory` to `sqlite` for the final run
- keep a real database file for checkpoints
- demonstrate that state survives process restarts or can be replayed

Evidence to collect:

- config snippet
- path to the SQLite file
- screenshot or log of state history / second run with same `thread_id`
- mention `resume_success` behavior in metrics/report if implemented

### Extension 2 - Graph diagram

Target outcome:

- export Mermaid graph text from LangGraph
- save it under `reports/` or `docs/`
- reference it in the report

Why this helps:

- makes architecture explanation faster during demo
- strengthens the "production-style workflow" presentation

### Extension 3 - Real HITL

Target outcome:

- enable `LANGGRAPH_INTERRUPT=true`
- show approval data entering the graph at runtime
- connect the interrupt flow to the demo UI

Use only after core flow is stable.

## 9. UI Demo Plan

Recommended UI scope:

- one page
- one risky sample selector
- one free-text input for custom query
- a `Run` action to start the graph
- an approval panel shown only when the graph pauses at HITL
- `Approve` and `Reject` buttons
- a result panel showing final answer, retry count, and event trail

Recommended technical approach:

- `Streamlit` for speed and low ceremony
- use the same graph builder and checkpointer as CLI
- keep approval state in session state
- keep one clear entrypoint command such as `streamlit run streamlit_app.py`
- keep the UI intentionally narrow and avoid adding unrelated chat features

Definition of done:

- reviewer can launch the UI without editing code
- risky scenario pauses and asks for approval
- reviewer decision changes the graph outcome
- UI is stable enough for live demo

## 10. Demo Checklist

- Show one simple route.
- Show one risky route that goes through approval.
- Show the UI pause at approval and resume after reviewer input.
- Show one error route that retries.
- Show the dead-letter path for retry exhaustion.
- Show `outputs/metrics.json`.
- Show `reports/lab_report.md`.
- Show the extension evidence:
  - SQLite checkpoint or state history
  - UI approval screen
  - graph diagram

## 11. Common Pitfalls To Avoid

- hard-coding by scenario id or exact sample text
- checking route priority in the wrong order
- matching `it` as a substring instead of a word
- forgetting to increment retry attempt
- retrying forever without a cap
- using a SQLite API version that does not match the installed package
- forgetting that risky flows need approval before tool/action
- building a UI that is disconnected from the real graph approval step
- making the UI too ambitious instead of making the approval demo reliable
- claiming `resume_success=true` without an actual replay or resume demonstration
- forgetting to record `latency_ms` even though it is required in `scenario_metrics`
- leaving report sections as placeholders
- shipping metrics without explaining them in the report

## 12. Final Submission Checklist

- [ ] All `TODO(student)` sections needed for the graded flow are completed
- [ ] `make test` passes
- [ ] `make run-scenarios` generates `outputs/metrics.json`
- [ ] `make grade-local` passes
- [ ] `make lint` passes
- [ ] `make typecheck` passes
- [ ] `reports/lab_report.md` is complete
- [ ] UI demonstrates the Human in the Loop approval flow
- [ ] at least one extension is implemented and documented
- [ ] I can explain one route and one failure mode in under 2 minutes

## 13. Recommended Execution Sequence

If time is limited, do the work in this exact order:

1. fix routing correctness
2. fix retry loop and dead-letter
3. fix approval path
4. run tests and scenarios
5. implement SQLite persistence
6. implement real HITL plus the demo UI
7. regenerate metrics and complete report
8. add graph diagram
9. polish the live demo flow
