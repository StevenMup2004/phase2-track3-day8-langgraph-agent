# Day 08 Lab Report

## 1. Team / student

- Name: Vu Hai Dang - 2A202600339
- Date: 2026-05-11 

## 2. Architecture

The workflow is a LangGraph support-ticket agent with explicit nodes for intake, classification,
tool execution, evaluation, retry, risky-action approval, clarification, dead-letter handling, and
finalization. The graph keeps routing deterministic and auditable: `classify` selects a route,
conditional edges choose the next node, and every route eventually reaches `finalize -> END`.

Target flow:

```text
START -> intake -> classify
simple       -> answer -> finalize -> END
tool         -> tool -> evaluate -> answer -> finalize -> END
missing_info -> clarify -> finalize -> END
risky        -> risky_action -> approval -> tool -> evaluate -> answer -> finalize -> END
error        -> retry -> tool -> evaluate -> retry/tool loop -> dead_letter -> finalize -> END
```

## 3. State schema

| Field | Reducer | Why |
|---|---|---|
| `thread_id` | overwrite | stable checkpoint key per run |
| `scenario_id` | overwrite | scenario identity for metrics only |
| `query` | overwrite | normalized user request |
| `route` | overwrite | current routing decision |
| `risk_level` | overwrite | approval and demo context |
| `attempt` | overwrite | bounded retry counter |
| `max_attempts` | overwrite | per-scenario retry cap |
| `final_answer` | overwrite | terminal answer |
| `pending_question` | overwrite | clarification or rejected-approval follow-up |
| `proposed_action` | overwrite | risky action awaiting approval |
| `approval` | overwrite | latest reviewer decision |
| `evaluation_result` | overwrite | retry-loop gate |
| `messages` | append | lightweight conversation/audit notes |
| `tool_results` | append | all tool attempts for debugging |
| `errors` | append | retry and dead-letter evidence |
| `events` | append | node visit trail for grading and metrics |

## 4. Scenario results

Top-level metrics:

| Metric | Value |
|---|---:|
| Total scenarios | 7 |
| Success rate | 100.00% |
| Average nodes visited | 6.43 |
| Total retries | 3 |
| Total interrupts | 2 |
| Resume/state-history success | True |

Per-scenario metrics:

| Scenario | Expected | Actual | Success | Retries | Interrupts | Approval | Latency ms |
|---|---|---|---:|---:|---:|---:|---:|
| S01_simple | simple | simple | True | 0 | 0 | False | 25 |
| S02_tool | tool | tool | True | 0 | 0 | False | 27 |
| S03_missing | missing_info | missing_info | True | 0 | 0 | False | 19 |
| S04_risky | risky | risky | True | 0 | 1 | True | 32 |
| S05_error | error | error | True | 2 | 0 | False | 33 |
| S06_delete | risky | risky | True | 0 | 1 | True | 28 |
| S07_dead_letter | error | error | True | 1 | 0 | False | 16 |

Metrics interpretation:

- All sample scenarios passed the route and output checks.
- Retry counts should be non-zero for transient error scenarios.
- Interrupt counts reflect visits to the approval node for risky scenarios.

## 5. Failure analysis

Retry or tool failure:

The graph routes error-like requests to `retry`, increments `attempt`, then calls the mock tool.
`evaluate` inspects the latest tool result and either routes back through `retry` or proceeds to
`answer`. `route_after_retry` enforces `attempt >= max_attempts -> dead_letter`, so the loop is
bounded.

Risky action without approval:

Risky keywords route to `risky_action`, which builds a concrete proposed action. The graph then
requires `approval` before tool execution. A rejected approval routes to `clarify`, producing a safe
follow-up instead of performing the action.

## 6. Persistence / recovery evidence

The graph is compiled with a configurable checkpointer. Each scenario run uses a unique `thread_id`
derived from the scenario id plus a run id, so repeated SQLite runs do not mix new metrics with old
checkpoint state. The generated metric `resume_success` is set from the compiled graph's
state-history availability for the first scenario run. For restart-survival evidence, run the final
demo with `checkpointer: sqlite` and include the checkpoint database path or state-history output.

## 7. Extension work

- SQLite persistence: run with `configs/lab.sqlite.yaml`; checkpoint evidence is stored in
  `outputs/checkpoints.db`.
- Human in the Loop UI: launch with `streamlit run streamlit_app.py`, choose `Risky sample`, then
  approve or reject the interrupted approval payload.
- Graph diagram: Mermaid text is exported to `reports/graph.mmd`.

## 8. Improvement plan

With one more day, productionize structured tool outputs first, then replace keyword routing with a
tested classifier policy, persist dead-letter events to a real queue, and add tracing around every
node for operational debugging.
