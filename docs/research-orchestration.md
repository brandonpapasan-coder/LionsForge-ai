# Multi-Agent Research Orchestration

LionsForge AI exposes an authenticated deterministic orchestration endpoint at:

`POST /api/v1/research-orchestration/run`

The endpoint coordinates four specialist roles:

- `research` frames the question and decision objective.
- `evidence` separates supplied evidence from assumptions and identifies missing support.
- `risk` tests downside cases, uncertainty, and disconfirming evidence.
- `synthesis` reconciles specialist outputs into an auditable conclusion and next actions.

## Request

- `question` is required.
- `project_id` is optional and must identify a research project owned by the authenticated user.
- `symbol` is optional and is normalized to uppercase.
- `context` contains user-supplied evidence and decision context.
- `requested_roles` optionally limits specialist execution; synthesis is always appended.

## Response

The response includes:

- a deterministic `run_id`
- the execution plan
- role-specific intermediate outputs
- findings, assumptions, and evidence gaps
- confidence
- alternative viewpoints
- recommended actions

The deterministic foundation does not retrieve external data or claim live validation. Only supplied context is treated as evidence. Future provider-backed specialist execution must preserve the same schemas, ownership boundary, auditability, and deterministic fallback behavior.
