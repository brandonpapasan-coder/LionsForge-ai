from importlib import import_module

from app.db.session import Base, engine
from app.models import (
    AssessmentAttempt,
    Company,
    EvidenceRecord,
    LessonProgress,
    MentorConversation,
    Mission,
    ResearchProject,
    ResearchSession,
    User,
)

# Keep representative active model references so their metadata is registered before
# development and test startup calls create_all(). Related active model modules are
# imported by app.models as part of the supported research and education surface.
_active_models = (
    User,
    Company,
    EvidenceRecord,
    LessonProgress,
    AssessmentAttempt,
    MentorConversation,
    Mission,
    ResearchProject,
    ResearchSession,
)

_COMPATIBILITY_MODEL_MODULES = (
    "app.models.alert",
    "app.models.alert_automation_rule",
    "app.models.alert_notification",
    "app.models.market_simulator",
    "app.models.portfolio",
    "app.models.research_report",
    "app.models.watchlist",
)


def _load_compatibility_models() -> None:
    """Register historical finance metadata for controlled compatibility use."""
    for module_name in _COMPATIBILITY_MODEL_MODULES:
        import_module(module_name)


def init_db(*, include_legacy_models: bool = False) -> None:
    """Create active tables, optionally including historical compatibility tables."""
    if include_legacy_models:
        _load_compatibility_models()
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    # Preserve the historical command-line initializer for migration and recovery
    # workflows while normal application startup remains active-scope only.
    init_db(include_legacy_models=True)
    print("Database initialized.")
