from hashlib import sha256

from app.schemas.research_orchestration import (
    ConfidenceLevel,
    ResearchAgentOutput,
    ResearchOrchestrationRequest,
    ResearchOrchestrationResponse,
    ResearchPlanStep,
    ResearchRole,
    ResearchSynthesis,
)


class ResearchOrchestrator:
    """Coordinate deterministic specialist roles with auditable intermediate output."""

    _default_roles: tuple[ResearchRole, ...] = ("research", "evidence", "risk", "synthesis")
    _objectives: dict[ResearchRole, str] = {
        "research": "Frame the decision, scope the question, and identify the primary analytical drivers.",
        "evidence": "Separate supplied evidence from assumptions and identify missing support.",
        "risk": "Test downside cases, uncertainty, and disconfirming evidence.",
        "synthesis": "Combine specialist outputs into an auditable conclusion and next actions.",
    }

    def plan(self, request: ResearchOrchestrationRequest) -> list[ResearchPlanStep]:
        requested = request.requested_roles or list(self._default_roles)
        roles = list(dict.fromkeys(requested))
        if "synthesis" not in roles:
            roles.append("synthesis")
        return [
            ResearchPlanStep(order=index, role=role, objective=self._objectives[role])
            for index, role in enumerate(roles, start=1)
        ]

    def run(self, request: ResearchOrchestrationRequest, user_id: int) -> ResearchOrchestrationResponse:
        plan = self.plan(request)
        outputs = [self._execute(step.role, request) for step in plan]
        gaps = list(dict.fromkeys(gap for output in outputs for gap in output.evidence_gaps))
        assumptions = list(dict.fromkeys(item for output in outputs for item in output.assumptions))
        confidence = self._confidence(request, gaps)
        symbol = request.symbol.upper() if request.symbol else None
        run_material = f"{user_id}:{request.project_id}:{request.question.strip()}:{symbol or ''}:{','.join(step.role for step in plan)}"
        run_id = sha256(run_material.encode()).hexdigest()[:16]
        key_drivers = [output.findings[0] for output in outputs if output.findings]

        return ResearchOrchestrationResponse(
            run_id=run_id,
            question=request.question.strip(),
            project_id=request.project_id,
            symbol=symbol,
            plan=plan,
            agent_outputs=outputs,
            synthesis=ResearchSynthesis(
                conclusion=(
                    "The research question has been decomposed across specialist roles. "
                    "The current conclusion remains provisional until the identified evidence gaps are resolved."
                ),
                key_drivers=key_drivers,
                alternative_viewpoints=[
                    "A different conclusion may be reasonable if the time horizon or decision objective changes.",
                    "Disconfirming evidence may outweigh the supplied context when primary-source validation is added.",
                ],
                recommended_actions=[
                    "Validate the highest-impact evidence gap with a primary source.",
                    "State which assumption would most change the conclusion if proven false.",
                    "Re-run the orchestration after adding verified context.",
                ],
            ),
            evidence_gaps=gaps,
            assumptions=assumptions,
            confidence=confidence,
        )

    def _execute(self, role: ResearchRole, request: ResearchOrchestrationRequest) -> ResearchAgentOutput:
        has_context = bool(request.context)
        symbol_text = f" for {request.symbol.upper()}" if request.symbol else ""
        assumptions = [
            "Only user-supplied context is treated as evidence in this deterministic orchestration run.",
            "No live external source was retrieved by this service.",
        ]
        findings: list[str]
        gaps: list[str]

        if role == "research":
            findings = [
                f"The primary decision question{symbol_text} is: {request.question.strip()}",
                "The decision objective, time horizon, and success criteria should be explicit.",
            ]
            gaps = [] if has_context else ["Decision context and source material were not supplied."]
        elif role == "evidence":
            findings = [
                "Supplied context must be separated into verified facts, interpretations, and assumptions.",
                f"The orchestration received {len(request.context)} context fields.",
            ]
            gaps = ["Primary-source citations and source dates require validation."]
        elif role == "risk":
            findings = [
                "The strongest downside scenario and disconfirming signal should be tested before confidence increases.",
                "Uncertainty should be tied to a measurable trigger or missing fact.",
            ]
            gaps = ["Downside magnitude and probability are not quantified."]
        else:
            findings = [
                "Specialist conclusions should be reconciled before a final decision is made.",
                "The synthesis must preserve unresolved disagreements and evidence gaps.",
            ]
            gaps = ["Independent validation is still required before production use."]

        return ResearchAgentOutput(
            role=role,
            summary=f"{role.title()} specialist completed its assigned objective.",
            findings=findings,
            assumptions=assumptions,
            evidence_gaps=gaps,
            confidence="moderate" if has_context else "low",
        )

    def _confidence(self, request: ResearchOrchestrationRequest, gaps: list[str]) -> ConfidenceLevel:
        if not request.context:
            return "low"
        if len(gaps) > 2:
            return "moderate"
        return "high"
