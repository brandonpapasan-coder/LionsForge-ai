from datetime import datetime, timedelta, timezone
from decimal import Decimal

from app.schemas.event_intelligence import EventImpactSummary, MarketEvent, MarketEventList
from app.services.market_providers import normalize_symbol

SEVERITY_WEIGHT = {
    "low": Decimal("20"),
    "medium": Decimal("45"),
    "high": Decimal("75"),
    "critical": Decimal("100"),
}


def list_market_events(symbol: str | None = None, category: str | None = None) -> MarketEventList:
    events = _seed_events()
    if symbol:
        normalized = normalize_symbol(symbol)
        events = [event for event in events if normalized in event.affected_symbols]
    if category:
        events = [event for event in events if event.category == category]
    events = sorted(events, key=lambda event: event.occurred_at, reverse=True)
    return MarketEventList(count=len(events), events=events)


def get_market_event(event_id: str) -> MarketEvent | None:
    return next((event for event in _seed_events() if event.event_id == event_id), None)


def build_symbol_event_impact(symbol: str) -> EventImpactSummary:
    normalized = normalize_symbol(symbol)
    events = list_market_events(symbol=normalized).events
    if not events:
        return EventImpactSummary(
            symbol=normalized,
            event_count=0,
            highest_severity="none",
            impact_score=Decimal("0.000000"),
            events=[],
            follow_up_actions=["No seeded events found. Continue monitoring company and macro sources."],
        )

    highest = max(events, key=lambda event: SEVERITY_WEIGHT[event.severity]).severity
    impact_score = (
        sum(SEVERITY_WEIGHT[event.severity] * event.confidence for event in events) / Decimal(len(events))
    ).quantize(Decimal("0.000001"))
    return EventImpactSummary(
        symbol=normalized,
        event_count=len(events),
        highest_severity=highest,
        impact_score=impact_score,
        events=events,
        follow_up_actions=_follow_up_actions(events),
    )


def _follow_up_actions(events: list[MarketEvent]) -> list[str]:
    actions: list[str] = []
    categories = {event.category for event in events}
    if "earnings" in categories:
        actions.append("Review the latest earnings release, guidance, and management commentary.")
    if "filing" in categories:
        actions.append("Inspect the underlying regulatory filing and compare it with prior disclosures.")
    if "analyst" in categories:
        actions.append("Validate analyst changes against fundamentals and consensus revisions.")
    if "macro" in categories:
        actions.append("Assess sensitivity to the macro event across revenue, margins, and valuation.")
    if not actions:
        actions.append("Review the event evidence and update the research thesis if material.")
    return actions


def _seed_events() -> list[MarketEvent]:
    now = datetime.now(timezone.utc)
    return [
        MarketEvent(
            event_id="evt-nvda-earnings",
            symbol="NVDA",
            category="earnings",
            severity="high",
            title="NVIDIA earnings review required",
            summary="A seeded earnings event flags revenue growth, guidance, and data-center demand for review.",
            confidence=Decimal("0.900000"),
            occurred_at=now - timedelta(hours=4),
            source="mock-event-provider",
            evidence=["Seeded earnings event", "Factor profile should be refreshed after earnings"],
            affected_symbols=["NVDA", "QQQ"],
        ),
        MarketEvent(
            event_id="evt-aapl-filing",
            symbol="AAPL",
            category="filing",
            severity="medium",
            title="Apple regulatory filing available",
            summary="A seeded filing event requires comparison with prior risk factors and capital allocation disclosures.",
            confidence=Decimal("0.850000"),
            occurred_at=now - timedelta(hours=10),
            source="mock-event-provider",
            evidence=["Seeded filing event"],
            affected_symbols=["AAPL", "SPY", "QQQ"],
        ),
        MarketEvent(
            event_id="evt-msft-analyst",
            symbol="MSFT",
            category="analyst",
            severity="low",
            title="Microsoft analyst estimate revision",
            summary="A seeded analyst event indicates an estimate revision that should be validated against primary evidence.",
            confidence=Decimal("0.700000"),
            occurred_at=now - timedelta(days=1),
            source="mock-event-provider",
            evidence=["Seeded analyst revision"],
            affected_symbols=["MSFT", "QQQ"],
        ),
        MarketEvent(
            event_id="evt-macro-rates",
            symbol=None,
            category="macro",
            severity="high",
            title="Interest-rate decision impact review",
            summary="A seeded macro event flags rate-sensitive holdings and valuation assumptions for reassessment.",
            confidence=Decimal("0.950000"),
            occurred_at=now - timedelta(days=2),
            source="mock-macro-provider",
            evidence=["Seeded central-bank event"],
            affected_symbols=["SPY", "QQQ", "JPM", "AAPL", "MSFT", "NVDA"],
        ),
    ]
