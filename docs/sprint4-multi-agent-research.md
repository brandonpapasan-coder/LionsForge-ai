# Sprint 4: Multi-Agent Research Orchestration Foundation

## Objective

Introduce an auditable orchestration layer that coordinates specialist research roles and produces a structured synthesis for authenticated LionsForge AI users.

## Initial agent roles

- **Research Analyst** — frames the question, scope, and decision objective.
- **Evidence Analyst** — separates supplied evidence from assumptions and identifies missing support.
- **Risk Analyst** — identifies downside scenarios, uncertainty, and disconfirming evidence.
- **Synthesis Analyst** — combines outputs into a traceable conclusion, confidence assessment, and next actions.

## Proposed API

`POST /api/v1/research-orchestration/run`

Request fields:

- `question`
- `symbol` (optional)
- `context`
- `requested_roles` (optional)

Response fields:

- `run_id`
- `plan`
- `agent_outputs`
- `synthesis`
- `evidence_gaps`
- `assumptions`
- `confidence`
- `alternative_viewpoints`
- `recommended_actions`

## Implementation phases

1. Add request, plan, agent-output, and synthesis schemas.
2. Add deterministic role planner and orchestration service.
3. Add authenticated API route.
4. Add unit and integration tests.
5. Expand OpenAPI validation and CI coverage.
6. Add frontend research workspace integration.

## Exit criteria

- Backend CI passes.
- Frontend CI remains green.
- Deployment Validation passes.
- Authenticated orchestration API is documented and tested.
- Intermediate agent outputs are visible and auditable.
- User-provided context remains isolated by authentication boundaries.
