import json
import logging
from typing import Any

from openai import OpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class OpenAIMentorProvider:
    """Generate structured mentor answers through the OpenAI Responses API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = bool(settings.openai_api_key)
        self.model = settings.openai_model
        self.timeout_seconds = settings.openai_timeout_seconds
        self.client = (
            OpenAI(api_key=settings.openai_api_key, timeout=self.timeout_seconds)
            if self.enabled
            else None
        )

    def generate(self, *, message: str, context: dict[str, Any], intent: str, persona: str) -> dict[str, Any] | None:
        if self.client is None:
            return None

        system_prompt = (
            "You are LionsForge AI, an evidence-first research and education mentor. "
            "Return valid JSON only with keys answer, reasoning, assumptions, confidence, "
            "confidence_reason, alternative_viewpoints, and recommendations. "
            "Recommendations must be objects with title, reason, action_type, and optional action_target. "
            "Never invent sources or claim live verification unless evidence is supplied."
        )
        user_payload = {
            "message": message,
            "context": context,
            "intent": intent,
            "persona": persona,
        }

        try:
            response = self.client.responses.create(
                model=self.model,
                instructions=system_prompt,
                input=json.dumps(user_payload, default=str),
            )
            parsed = json.loads(response.output_text)
            return parsed if isinstance(parsed, dict) else None
        except Exception:
            logger.exception("OpenAI mentor generation failed; deterministic fallback will be used")
            return None
