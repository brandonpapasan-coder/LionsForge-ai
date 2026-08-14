import json
from types import SimpleNamespace
from unittest.mock import Mock

from app.services.openai_mentor import OpenAIMentorProvider


def provider_with_client(output_text: str) -> OpenAIMentorProvider:
    provider = OpenAIMentorProvider.__new__(OpenAIMentorProvider)
    provider.enabled = True
    provider.model = "test-model"
    provider.timeout_seconds = 1.0
    provider.max_retries = 0
    provider.max_input_chars = 24000
    provider.max_output_tokens = 4000
    provider.last_status = "configured"
    provider.last_failure_reason = None
    provider.last_input_tokens = 0
    provider.last_output_tokens = 0
    provider.last_total_tokens = 0
    response = SimpleNamespace(
        output_text=output_text,
        usage=SimpleNamespace(input_tokens=120, output_tokens=80, total_tokens=200),
    )
    provider.client = SimpleNamespace(responses=SimpleNamespace(create=Mock(return_value=response)))
    return provider


def valid_payload() -> dict:
    return {
        "answer": "Evidence supports a cautious next step.",
        "evidence": [],
        "reasoning": ["The available evidence is incomplete."],
        "assumptions": ["The supplied context is current."],
        "confidence": "medium",
        "confidence_reason": "The evidence is relevant but limited.",
        "alternative_viewpoints": ["Additional evidence may change the conclusion."],
        "recommendations": [
            {
                "title": "Validate the evidence",
                "reason": "A stronger baseline reduces uncertainty.",
                "action_type": "review",
                "action_target": "evidence backlog",
            }
        ],
    }


def test_generate_returns_validated_structured_output() -> None:
    provider = provider_with_client(json.dumps(valid_payload()))

    result = provider.generate(message="What next?", context={}, intent="research", persona="mentor")

    assert result == valid_payload()
    assert provider.last_status == "healthy"
    assert provider.last_failure_reason is None
    assert provider.last_input_tokens == 120
    assert provider.last_output_tokens == 80
    assert provider.last_total_tokens == 200
    provider.client.responses.create.assert_called_once()
    request = provider.client.responses.create.call_args.kwargs
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True
    assert request["max_output_tokens"] == 4000


def test_generate_rejects_malformed_json_and_falls_back() -> None:
    provider = provider_with_client("not-json")

    result = provider.generate(message="What next?", context={}, intent="research", persona="mentor")

    assert result is None
    assert provider.last_status == "degraded"
    assert provider.last_failure_reason == "invalid_structured_output"


def test_generate_rejects_schema_mismatch_and_extra_fields() -> None:
    payload = valid_payload()
    payload["confidence"] = "certain"
    payload["unexpected"] = "must not pass validation"
    provider = provider_with_client(json.dumps(payload))

    result = provider.generate(message="What next?", context={}, intent="research", persona="mentor")

    assert result is None
    assert provider.last_status == "degraded"
    assert provider.last_failure_reason == "invalid_structured_output"


def test_generate_uses_fallback_when_provider_is_disabled() -> None:
    provider = OpenAIMentorProvider.__new__(OpenAIMentorProvider)
    provider.enabled = False
    provider.model = "test-model"
    provider.timeout_seconds = 1.0
    provider.max_retries = 0
    provider.max_input_chars = 24000
    provider.max_output_tokens = 4000
    provider.last_status = "disabled"
    provider.last_failure_reason = None
    provider.last_input_tokens = 0
    provider.last_output_tokens = 0
    provider.last_total_tokens = 0
    provider.client = None

    result = provider.generate(message="What next?", context={}, intent="research", persona="mentor")

    assert result is None
    assert provider.health() == {
        "provider": "openai",
        "enabled": False,
        "status": "disabled",
        "model": "test-model",
        "timeout_seconds": 1.0,
        "max_retries": 0,
        "max_input_chars": 24000,
        "max_output_tokens": 4000,
        "last_failure_reason": "provider_disabled",
        "last_input_tokens": 0,
        "last_output_tokens": 0,
        "last_total_tokens": 0,
    }


def test_generate_rejects_input_over_budget_without_provider_call() -> None:
    provider = provider_with_client(json.dumps(valid_payload()))
    provider.max_input_chars = 32

    result = provider.generate(
        message="This request is intentionally longer than the configured provider input budget.",
        context={},
        intent="research",
        persona="mentor",
    )

    assert result is None
    assert provider.last_status == "degraded"
    assert provider.last_failure_reason == "input_budget_exceeded"
    provider.client.responses.create.assert_not_called()


def test_generate_hides_payload_when_unexpected_provider_error_occurs(caplog) -> None:
    provider = provider_with_client(json.dumps(valid_payload()))
    provider.client.responses.create.side_effect = RuntimeError("provider failure")
    secret_message = "private user research payload"

    result = provider.generate(message=secret_message, context={}, intent="research", persona="mentor")

    assert result is None
    assert provider.last_status == "degraded"
    assert provider.last_failure_reason == "unexpected_provider_error"
    assert secret_message not in caplog.text
