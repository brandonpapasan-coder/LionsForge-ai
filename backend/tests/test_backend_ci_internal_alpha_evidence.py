from pathlib import Path


WORKFLOW = Path(__file__).resolve().parents[2] / ".github" / "workflows" / "backend-ci.yml"


def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_backend_ci_checks_internal_alpha_evidence_validator_quality():
    text = workflow_text()
    assert "../scripts/validate_internal_alpha_evidence.py" in text
    assert "tests/test_internal_alpha_evidence_validator.py" in text
    assert "tests/test_backend_ci_internal_alpha_evidence.py" in text


def test_backend_ci_executes_live_internal_alpha_evidence_validation():
    text = workflow_text()
    assert "Validate live Internal Alpha evidence references" in text
    assert "python ../scripts/validate_internal_alpha_evidence.py" in text
    assert "../docs/operations/internal-alpha-readiness-gate.md" in text
    assert "internal-alpha-evidence-validation.log" in text


def test_backend_ci_retains_internal_alpha_evidence_validation_log():
    text = workflow_text()
    assert "Upload backend quality artifacts" in text
    assert "backend/internal-alpha-evidence-validation.log" in text
