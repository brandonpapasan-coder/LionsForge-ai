from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session
from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.mentor import MentorConversation
from app.models.research_project import ResearchProject
from app.models.research_session import ResearchSession
from app.models.user import User
from app.schemas.dashboard import DashboardAction, DashboardActivity, DashboardMetric, ExecutiveDashboard

router = APIRouter()


@router.get("", response_model=ExecutiveDashboard)
def get_executive_dashboard(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ExecutiveDashboard:
    active_projects = db.scalar(
        select(func.count(ResearchProject.id)).where(
            ResearchProject.owner_id == current_user.id,
            ResearchProject.status == "active",
        )
    ) or 0
    active_sessions = db.scalar(
        select(func.count(ResearchSession.id))
        .join(ResearchProject, ResearchSession.project_id == ResearchProject.id)
        .where(
            ResearchProject.owner_id == current_user.id,
            ResearchSession.status == "active",
        )
    ) or 0
    mentor_conversations = db.scalar(
        select(func.count(MentorConversation.id)).where(MentorConversation.user_id == current_user.id)
    ) or 0

    recent_projects = list(
        db.scalars(
            select(ResearchProject)
            .where(ResearchProject.owner_id == current_user.id)
            .order_by(desc(ResearchProject.updated_at))
            .limit(3)
        ).all()
    )
    recent_conversations = list(
        db.scalars(
            select(MentorConversation)
            .where(MentorConversation.user_id == current_user.id)
            .order_by(desc(MentorConversation.updated_at))
            .limit(3)
        ).all()
    )

    activities = [
        DashboardActivity(
            kind="research",
            title=project.title,
            summary=project.objective or project.description,
            href=f"/research/{project.id}",
            updated_at=project.updated_at,
        )
        for project in recent_projects
    ]
    activities.extend(
        DashboardActivity(
            kind="mentor",
            title=conversation.title,
            summary=conversation.summary,
            href=f"/mentor?conversation={conversation.id}",
            updated_at=conversation.updated_at,
        )
        for conversation in recent_conversations
    )
    activities.sort(key=lambda item: item.updated_at, reverse=True)

    actions: list[DashboardAction] = []
    if active_projects:
        actions.append(
            DashboardAction(
                title="Continue active research",
                reason="Advance an existing project before opening additional work.",
                href="/research",
                priority="high",
            )
        )
    else:
        actions.append(
            DashboardAction(
                title="Start your first research project",
                reason="Create a structured question, objective, and evidence trail.",
                href="/research/new",
                priority="high",
            )
        )
    actions.append(
        DashboardAction(
            title="Consult the AI Mentor",
            reason="Challenge assumptions and identify the next highest-value learning step.",
            href="/mentor",
            priority="medium",
        )
    )

    display_name = current_user.full_name or current_user.email.split("@", 1)[0]
    briefing = (
        f"You have {active_projects} active research project(s), {active_sessions} active research session(s), "
        f"and {mentor_conversations} saved mentor conversation(s). Focus on the highest-priority unfinished work."
    )

    return ExecutiveDashboard(
        greeting=f"Welcome back, {display_name}.",
        briefing=briefing,
        metrics=[
            DashboardMetric(label="Active projects", value=active_projects, detail="Research currently in progress"),
            DashboardMetric(label="Active sessions", value=active_sessions, detail="Focused research workspaces"),
            DashboardMetric(label="Mentor conversations", value=mentor_conversations, detail="Saved coaching history"),
        ],
        next_actions=actions,
        recent_activity=activities[:6],
    )
