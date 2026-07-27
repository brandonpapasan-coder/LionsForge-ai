from pathlib import Path


def test_legacy_review_endpoint_remains_explicitly_tracked_for_service_consolidation():
    root = Path(__file__).parents[1]
    learner_route = (root / "app" / "api" / "routes" / "research_practica.py").read_text(
        encoding="utf-8"
    )
    reviewer_route = (
        root / "app" / "api" / "routes" / "research_practicum_reviews.py"
    ).read_text(encoding="utf-8")
    reviewer_service = (
        root / "app" / "services" / "research_practicum_reviewer.py"
    ).read_text(encoding="utf-8")

    assert '@router.post("/enrollments/{enrollment_id}/reviews"' in learner_route
    assert '@router.post("/enrollments/{enrollment_id}/decision"' in reviewer_route
    assert "expected_enrollment_updated_at" in reviewer_service
    assert "Practicum changed after the reviewer loaded it" in reviewer_service
    assert "from app.api.routes.research_practica import" not in reviewer_route
