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
    provider.last_status = "configured"
    provider.client = SimpleNamespace(
        responses=SimpleNamespace(create=Mock(return_value=SimpleNamespace(output_text=output_text)))
    )
    return provider


def valid_payload() -> dict:
    return {
        "answer": "Evidence supports a cautious next step.",
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
    provider.client.responses.create.assert_called_once()
    request = provider.client.responses.create.call_args.kwargs
    assert request["text"]["format"]["type"] == "json_schema"
    assert request["text"]["format"]["strict"] is True


def test_generate_rejects_malformed_json_and_falls_back() -> None:
    provider = provider_with_client("not-json")

    result = provider.generate(message="What next?", context={}, intent="research", persona="mentor")

    assert result is None
    assert provider.last_status == "degraded"


def test_generate_rejects_schema_mismatch_and_extra_fields() -> None:
    payload = valid_payload()
    payload["confidence"] = "certain"
    payload["unexpected"] = "must not pass validation"
    provider = provider_with_client(json.dumps(payload))

    result = provider.generate(message="What next?", context={}, intent="research", persona="mentor")

    assert result is None
    assert provider.last_status == "degraded"


def test_generate_uses_fallback_when_provider_is_disabled() -> None:
    provider = OpenAIMentorProvider.__new__(OpenAIMentorProvider)
    provider.enabled = False
    provider.model = "test-model"
    provider.timeout_seconds = 1.0
    provider.max_retries = 0
    provider.last_status = "disabled"
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
    }


def test_generate_hides_payload_when_unexpected_provider_error_occurs(caplog) -> None:
    provider = provider_with_client(json.dumps(valid_payload()))
    provider.client.responses.create.side_effect = RuntimeError("provider failure")
    secret_message = "private user research payload"

    result = provider.generate(message=secret_message, context={}, intent="research", persona="mentor")

    assert result is None
    assert provider.last_status == "degraded"
    assert secret_message not in caplog.text
