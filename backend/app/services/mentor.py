from dataclasses import dataclass

from app.schemas.mentor import EvidenceItem, MentorRecommendation


@dataclass(frozen=True)
class MentorPlan:
    intent: str
    persona: str


class MentorOrchestrator:
    _rules = (
        (("portfolio", "diversification", "allocation", "rebalance", "risk budget"), "portfolio", "Portfolio Mentor"),
        (("inflation", "interest rate", "federal reserve", "gdp", "recession", "economy"), "economics", "Economics Mentor"),
        (("evidence", "source", "research", "thesis", "company", "earnings", "filing"), "research", "Research Mentor"),
        (("lesson", "learn", "teach", "explain", "quiz", "study", "assessment"), "education", "Learning Coach"),
        (("valuation", "cash flow", "balance sheet", "income statement", "accounting", "finance"), "finance", "Finance Mentor"),
    )

    def classify(self, message: str) -> MentorPlan:
        normalized = message.casefold()
        for keywords, intent, persona in self._rules:
            if any(keyword in normalized for keyword in keywords):
                return MentorPlan(intent=intent, persona=persona)
        return MentorPlan(intent="general", persona="LionsForge Mentor")

    def compose(self, message: str, context: dict) -> dict:
        plan = self.classify(message)
        answer = self._answer(message, plan)
        evidence = self._evidence(plan, context)
        reasoning = [
            f"The request was classified as {plan.intent} based on its subject and requested action.",
            f"The {plan.persona} perspective was selected because it best matches the primary decision domain.",
            "The response separates general guidance from user-specific context and avoids presenting unsupported facts as verified evidence.",
        ]
        assumptions = [
            "No external live-data source was requested or supplied in this interaction.",
            "The user is seeking educational and analytical guidance rather than individualized regulated advice.",
        ]
        alternatives = self._alternatives(plan)
        recommendations = self._recommendations(plan, context)
        confidence = "moderate" if context else "low"
        confidence_reason = (
            "The response is grounded in supplied platform context, but no external primary sources were retrieved."
            if context
            else "The response is based on general domain principles because no lesson, report, or project context was supplied."
        )
        return {
            "intent": plan.intent,
            "persona": plan.persona,
            "answer": answer,
            "evidence": [item.model_dump() for item in evidence],
            "reasoning": reasoning,
            "assumptions": assumptions,
            "confidence": confidence,
            "confidence_reason": confidence_reason,
            "alternative_viewpoints": alternatives,
            "recommendations": [item.model_dump() for item in recommendations],
        }

    def _answer(self, message: str, plan: MentorPlan) -> str:
        return (
            f"From the {plan.persona} perspective, the best next step is to define the decision you are trying to make, "
            f"separate verified facts from assumptions, and test the strongest alternative explanation. "
            f"For your question — “{message.strip()}” — begin with the relevant evidence, identify the key uncertainty, "
            "then state what new information would change your conclusion."
        )

    def _evidence(self, plan: MentorPlan, context: dict) -> list[EvidenceItem]:
        items = [
            EvidenceItem(
                label="Intent classification",
                detail=f"Primary domain identified as {plan.intent}; routed to {plan.persona}.",
                source_type="mentor_runtime",
            )
        ]
        for key in ("active_lesson", "active_report", "goal", "mastery_gap"):
            value = context.get(key)
            if value:
                items.append(EvidenceItem(label=key.replace("_", " ").title(), detail=str(value)))
        return items

    def _alternatives(self, plan: MentorPlan) -> list[str]:
        common = [
            "A different conclusion may be reasonable if the underlying assumptions or time horizon change.",
            "The strongest counterargument should be evaluated before increasing confidence.",
        ]
        if plan.intent == "portfolio":
            common.append("A lower-risk allocation may be preferable when liquidity needs or loss tolerance are uncertain.")
        elif plan.intent == "research":
            common.append("Company-specific evidence may conflict with sector or macroeconomic evidence and should be weighed separately.")
        elif plan.intent == "economics":
            common.append("Economic relationships can vary by regime, lag, and policy response.")
        return common

    def _recommendations(self, plan: MentorPlan, context: dict) -> list[MentorRecommendation]:
        recommendations = [
            MentorRecommendation(
                title="State the evidence and assumption separately",
                reason="This improves reasoning clarity and makes later revisions auditable.",
                action_type="reflection",
            )
        ]
        if context.get("active_lesson"):
            recommendations.append(
                MentorRecommendation(
                    title="Apply the current lesson",
                    reason="Practical application reinforces the active learning objective.",
                    action_type="lesson",
                    action_target=str(context["active_lesson"]),
                )
            )
        elif plan.intent in {"finance", "education"}:
            recommendations.append(
                MentorRecommendation(
                    title="Review Finance Foundations",
                    reason="A prerequisite review can expose missing concepts before deeper analysis.",
                    action_type="lesson",
                    action_target="finance-foundations",
                )
            )
        if context.get("active_report"):
            recommendations.append(
                MentorRecommendation(
                    title="Reopen the active research report",
                    reason="Connect the mentor guidance directly to persisted evidence and assumptions.",
                    action_type="research_report",
                    action_target=str(context["active_report"]),
                )
            )
        return recommendations
