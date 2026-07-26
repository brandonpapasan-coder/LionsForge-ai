from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.session import Base


class PracticumTemplate(Base):
    __tablename__ = "practicum_templates"
    __table_args__ = (UniqueConstraint("slug", "version", name="uq_practicum_template_slug_version"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    slug: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    estimated_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    prerequisite_lesson_slugs: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    status: Mapped[str] = mapped_column(String(24), default="active", index=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PracticumObjective(Base):
    __tablename__ = "practicum_objectives"
    __table_args__ = (
        UniqueConstraint("template_id", "objective_key", name="uq_practicum_objective_template_key"),
        UniqueConstraint("template_id", "sequence", name="uq_practicum_objective_template_sequence"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    template_id: Mapped[int] = mapped_column(
        ForeignKey("practicum_templates.id", ondelete="CASCADE"), index=True, nullable=False
    )
    objective_key: Mapped[str] = mapped_column(String(120), nullable=False)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(180), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    competency: Mapped[str] = mapped_column(String(120), index=True, nullable=False)
    required_evidence_categories: Mapped[list[str]] = mapped_column(JSON, default=list, nullable=False)
    minimum_evidence_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    reflection_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    human_review_required: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class PracticumEnrollment(Base):
    __tablename__ = "practicum_enrollments"
    __table_args__ = (
        UniqueConstraint(
            "user_id", "template_id", "research_project_id", name="uq_practicum_enrollment_user_template_project"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False)
    template_id: Mapped[int] = mapped_column(ForeignKey("practicum_templates.id"), index=True, nullable=False)
    template_version: Mapped[int] = mapped_column(Integer, nullable=False)
    research_project_id: Mapped[int] = mapped_column(
        ForeignKey("research_projects.id", ondelete="CASCADE"), index=True, nullable=False
    )
    status: Mapped[str] = mapped_column(String(32), default="not_started", index=True, nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    submitted_for_review_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class PracticumObjectiveProgress(Base):
    __tablename__ = "practicum_objective_progress"
    __table_args__ = (
        UniqueConstraint("enrollment_id", "objective_key", name="uq_practicum_progress_enrollment_objective"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("practicum_enrollments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    objective_key: Mapped[str] = mapped_column(String(120), nullable=False)
    reflection: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )


class PracticumEvidenceReference(Base):
    __tablename__ = "practicum_evidence_references"
    __table_args__ = (
        UniqueConstraint(
            "objective_progress_id", "research_evidence_id", name="uq_practicum_reference_progress_evidence"
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    objective_progress_id: Mapped[int] = mapped_column(
        ForeignKey("practicum_objective_progress.id", ondelete="CASCADE"), index=True, nullable=False
    )
    research_evidence_id: Mapped[int] = mapped_column(
        ForeignKey("research_evidence.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)


class PracticumReviewDecision(Base):
    __tablename__ = "practicum_review_decisions"

    id: Mapped[int] = mapped_column(primary_key=True)
    enrollment_id: Mapped[int] = mapped_column(
        ForeignKey("practicum_enrollments.id", ondelete="CASCADE"), index=True, nullable=False
    )
    reviewer_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True, nullable=False)
    decision: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True, nullable=False)
