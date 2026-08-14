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


class GeneratedEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=300)
    detail: str = Field(min_length=1, max_length=2500)
    source_type: Literal["primary_source", "authoritative_source", "platform_context"]


class GeneratedRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=200)
    reason: str = Field(min_length=1, max_length=1000)
    action_type: str = Field(min_length=1, max_length=100)
    action_target: str | None = Field(default=None, max_length=500)


class GeneratedMentorAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=1, max_length=12000)
    evidence: list[GeneratedEvidence] = Field(default_factory=list, max_length=12)
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
        self.max_input_chars = settings.openai_max_input_chars
        self.max_output_tokens = settings.openai_max_output_tokens
        self.last_status: str = "configured" if self.enabled else "disabled"
        self.last_failure_reason: str | None = None
        self.last_input_tokens = 0
        self.last_output_tokens = 0
        self.last_total_tokens = 0
        self.client = (
            OpenAI(
                api_key=settings.openai_api_key,
                timeout=self.timeout_seconds,
                max_retries=self.max_retries,
            )
            if self.enabled
            else None
        )

    def health(self) -> dict[str, str | bool | int | float | None]:
        """Return local provider state without issuing a billable model request."""
        return {
            "provider": "openai",
            "enabled": self.enabled,
            "status": self.last_status,
            "model": self.model,
            "timeout_seconds": self.timeout_seconds,
            "max_retries": self.max_retries,
            "max_input_chars": self.max_input_chars,
            "max_output_tokens": self.max_output_tokens,
            "last_failure_reason": self.last_failure_reason,
            "last_input_tokens": self.last_input_tokens,
            "last_output_tokens": self.last_output_tokens,
            "last_total_tokens": self.last_total_tokens,
        }

    def _set_failure(self, status: str, reason: str) -> None:
        self.last_status = status
        self.last_failure_reason = reason

    def _capture_usage(self, response: Any) -> None:
        usage = getattr(response, "usage", None)
        self.last_input_tokens = int(getattr(usage, "input_tokens", 0) or 0)
        self.last_output_tokens = int(getattr(usage, "output_tokens", 0) or 0)
        self.last_total_tokens = int(getattr(usage, "total_tokens", 0) or 0)

    def generate(self, *, message: str, context: dict[str, Any], intent: str, persona: str) -> dict[str, Any] | None:
        if self.client is None:
            self._set_failure("disabled", "provider_disabled")
            return None

        research_mode = intent in {"research", "economics"}
        system_prompt = (
            "You are OnyxMane Intelligence, an evidence-first research and education mentor. "
            "Follow the supplied JSON schema exactly. Separate evidence from assumptions and internal routing metadata. "
            "For research or economics questions, use web search to retrieve current external evidence before answering. "
            "Prefer primary sources such as government publications, regulators, company filings, universities, and original research; "
            "use authoritative secondary sources only when a primary source is unavailable or insufficient. "
            "Every external evidence item must identify the source or publisher in its detail and must be supported by retrieved material. "
            "Never invent a source, statistic, study, quotation, or verification claim. If retrieval is unavailable or insufficient, say so, "
            "lower confidence, and state what evidence is still needed. Challenge the user's strongest assumptions rather than merely restating them. "
            "Give concrete validation steps. Confidence must be low, medium, or high."
        )
        user_payload = {
            "message": message,
            "context": context,
            "intent": intent,
            "persona": persona,
            "research_mode": research_mode,
        }
        serialized_input = json.dumps(user_payload, default=str)
        if len(serialized_input) > self.max_input_chars:
            self._set_failure("degraded", "input_budget_exceeded")
            logger.warning("OpenAI mentor request exceeded configured input budget")
            return None

        request: dict[str, Any] = {
            "model": self.model,
            "instructions": system_prompt,
            "input": serialized_input,
            "store": False,
            "max_output_tokens": self.max_output_tokens,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "onyxmane_mentor_answer",
                    "schema": GeneratedMentorAnswer.model_json_schema(),
                    "strict": True,
                }
            },
        }
        if research_mode:
            request["tools"] = [{"type": "web_search", "search_context_size": "high"}]

        try:
            response = self.client.responses.create(**request)
            self._capture_usage(response)
            parsed = GeneratedMentorAnswer.model_validate_json(response.output_text)
            self.last_status = "healthy"
            self.last_failure_reason = None
            return parsed.model_dump()
        except ValidationError:
            self._set_failure("degraded", "invalid_structured_output")
            logger.warning("OpenAI mentor returned output that failed schema validation")
        except APITimeoutError:
            self._set_failure("degraded", "timeout")
            logger.warning("OpenAI mentor request timed out")
        except RateLimitError:
            self._set_failure("degraded", "rate_limited")
            logger.warning("OpenAI mentor request was rate limited")
        except AuthenticationError:
            self._set_failure("misconfigured", "authentication_failed")
            logger.error("OpenAI mentor authentication failed; verify provider credentials")
        except BadRequestError:
            self._set_failure("misconfigured", "request_rejected")
            logger.error("OpenAI mentor request was rejected; verify model, web search, and structured-output configuration")
        except (APIConnectionError, InternalServerError):
            self._set_failure("degraded", "provider_unavailable")
            logger.warning("OpenAI mentor provider is temporarily unavailable")
        except Exception:
            self._set_failure("degraded", "unexpected_provider_error")
            logger.exception("OpenAI mentor generation failed; deterministic fallback will be used")
        return None
