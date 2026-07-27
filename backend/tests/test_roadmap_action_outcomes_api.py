from pathlib import Path


def test_outcome_routes_forward_authenticated_owner_and_filters():
    route = Path("app/api/routes/roadmap_action_outcomes.py").read_text()
    assert "current_user: User = Depends(get_current_user)" in route
    assert "user=current_user" in route
    for field in (
        "template_slug=template_slug",
        "reason_code=reason_code",
        "outcome_status=outcome_status",
        "acted_after=acted_after",
        "acted_before=acted_before",
        "completed_after=completed_after",
        "completed_before=completed_before",
    ):
        assert field in route


def test_outcome_export_is_owner_scoped_bounded_and_completion_audit_bound():
    service = Path("app/services/roadmap_action_outcome_export.py").read_text()
    assert "RoadmapActionRecord.learner_user_id == user.id" in service
    assert ".limit(MAX_QUERY_ROWS)" in service
    assert "MAX_QUERY_ROWS = 225" in service
    assert "export_completion_bundle" in service
    assert "validate_completion_receipt" in service
    assert 'enrollment.status == "completed"' in service
    assert 'bundle["receipt"]["record_sha256"]' in service
    assert "validate_entry(entry, learner_user_id=user.id)" in service
    assert "stored outcome failed integrity requirements" in service


def test_outcome_routes_are_registered_in_openapi():
    main = Path("app/main.py").read_text()
    assert "roadmap_action_outcomes_router" in main
    assert 'prefix=f"{settings.api_prefix}/education/roadmap-action-outcomes"' in main
    assert 'tags=["education-roadmap-action-outcomes"]' in main


def test_outcome_validation_endpoint_is_fail_closed():
    route = Path("app/api/routes/roadmap_action_outcomes.py").read_text()
    service = Path("app/services/roadmap_action_outcome_export.py").read_text()
    assert '@router.post("/validate")' in route
    assert "validate_roadmap_action_outcome_bundle(payload)" in route
    assert 'set(payload) != {"report", "receipt"}' in service
    assert 'return {"valid": False, "findings": ["bundle fields are invalid"]}' in service
