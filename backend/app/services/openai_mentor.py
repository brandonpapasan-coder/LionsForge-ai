import json
import logging
from typing import Any, Literal

from openai import (
    APIConnectionError,
    APITimeoutError,
    AuthenticationError,
    BadRequestError,
    InternalServerError,
    OpenAI,
    RateLimitError,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class GeneratedRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    action_type: str = Field(min_length=1, max_length=100)
    action_target: str | None = Field(default=None, max_length=500)


class GeneratedMentorAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=12000)
    reasoning: list[str] = Field(default_factory=list, max_length=20)
    assumptions: list[str] = Field(default_factory=list, max_length=20)
    confidence: Literal["low", "medium", "high"]
    confidence_reason: str = Field(min_length=1, max_length=2000)
    alternative_viewpoints: list[str] = Field(default_factory=list, max_length=20)
    recommendations: list[GeneratedRecommendation] = Field(default_factory=list, max_length=20)


class OpenAIMentorProvider:
    """Generate validated mentor answers through the OpenAI Responses API."""

    def __init__(self) -> None:
        settings = get_settings()
        self.enabled = bool(settings.openai_api_key)
        self.model = settings.openai_model
        self.timeout_seconds = settings.openai_timeout_seconds
        self.max_retries = settings.openai_max_retries
        self.last_status: str = "configured" if self.enabled else "disabled"
        self.client = (
            OpenAI(
                api_key=settings.openai_api_key,
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
            if self.enabled
            else None
        )

    def health(self) -> dict[str, str | bool | int | float]:
        """Return local provider state without issuing a billable model request."""
        return {
            "provider": "openai",
            "enabled": self.enabled,
            "status": self.last_status,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
        }

    def generate(self, *, message: str, context: dict[str, Any], intent: str, persona: str) -> dict[str, Any] | None:
        if self.client is None:
            self.last_status = "disabled"
            return None

        system_prompt = (
            "You are LionsForge AI, an evidence-first research and education mentor. "
            "Follow the supplied JSON schema exactly. Never invent sources or claim live verification "
            "unless evidence is supplied. Confidence must be low, medium, or high."
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
                text={
                    "format": {
                        "type": "json_schema",
                        "name": "lionsforge_mentor_answer",
                        "schema": GeneratedMentorAnswer.model_json_schema(),
                        "strict": True,
                    }
                },
            )
            parsed = GeneratedMentorAnswer.model_validate_json(response.output_text)
            self.last_status = "healthy"
            return parsed.model_dump()
        except ValidationError:
            self.last_status = "degraded"
            logger.warning("OpenAI mentor returned output that failed schema validation")
        except APITimeoutError:
            self.last_status = "degraded"
            logger.warning("OpenAI mentor request timed out")
        except RateLimitError:
            self.last_status = "degraded"
            logger.warning("OpenAI mentor request was rate limited")
        except AuthenticationError:
            self.last_status = "misconfigured"
            logger.error("OpenAI mentor authentication failed; verify provider credentials")
        except BadRequestError:
            self.last_status = "misconfigured"
            logger.error("OpenAI mentor request was rejected; verify model and structured-output configuration")
        except (APIConnectionError, InternalServerError):
            self.last_status = "degraded"
            logger.warning("OpenAI mentor provider is temporarily unavailable")
        except Exception:
            self.last_status = "degraded"
            logger.exception("OpenAI mentor generation failed; deterministic fallback will be used")
        return None
