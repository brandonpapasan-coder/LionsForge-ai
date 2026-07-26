from app.models.research_practicum import (
    PracticumEnrollment,
    PracticumEvidenceReference,
    PracticumObjective,
    PracticumObjectiveProgress,
    PracticumReviewDecision,
    PracticumTemplate,
)
from app.services.research_practicum_templates import (
    PRACTICUM_TEMPLATES,
    get_active_practicum_templates,
    get_practicum_template,
)


def test_practicum_template_definitions_are_versioned_and_deterministic():
    active = get_active_practicum_templates()

    assert active
    assert active == sorted(active, key=lambda template: (template["slug"], template["version"]))

    for template in active:
        assert template["version"] >= 1
        objectives = template["objectives"]
        assert objectives == sorted(objectives, key=lambda objective: (objective["sequence"], objective["objective_key"]))
        assert len({objective["objective_key"] for objective in objectives}) == len(objectives)
        assert all(objective["human_review_required"] for objective in objectives)


def test_latest_template_lookup_is_stable():
    definition = PRACTICUM_TEMPLATES[0]

    latest = get_practicum_template(definition["slug"])
    exact = get_practicum_template(definition["slug"], definition["version"])

    assert latest == exact == definition
    assert get_practicum_template("missing-template") is None


def test_practicum_model_tables_and_evidence_delete_boundary():
    assert PracticumTemplate.__tablename__ == "practicum_templates"
    assert PracticumObjective.__tablename__ == "practicum_objectives"
    assert PracticumEnrollment.__tablename__ == "practicum_enrollments"
    assert PracticumObjectiveProgress.__tablename__ == "practicum_objective_progress"
    assert PracticumEvidenceReference.__tablename__ == "practicum_evidence_references"
    assert PracticumReviewDecision.__tablename__ == "practicum_review_decisions"

    evidence_fk = next(
        foreign_key
        for foreign_key in PracticumEvidenceReference.__table__.foreign_keys
        if foreign_key.parent.name == "research_evidence_id"
    )
    assert evidence_fk.ondelete == "RESTRICT"


def test_review_decisions_have_no_update_timestamp():
    column_names = {column.name for column in PracticumReviewDecision.__table__.columns}

    assert "created_at" in column_names
    assert "updated_at" not in column_names
