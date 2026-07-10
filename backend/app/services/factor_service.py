from decimal import Decimal

from app.schemas.factor import FactorBreakdown, FactorCompareResponse, FactorRankingResponse, FactorScore, ScreenerRequest
from app.services.market_data_service import get_quote
from app.services.market_providers import normalize_symbol

FACTOR_WEIGHTS: dict[str, Decimal] = {
    "value": Decimal("0.20"),
    "growth": Decimal("0.20"),
    "quality": Decimal("0.15"),
    "momentum": Decimal("0.15"),
    "financial_strength": Decimal("0.10"),
    "volatility": Decimal("0.10"),
    "earnings_stability": Decimal("0.10"),
}

MOCK_FACTOR_DATA: dict[str, dict[str, Decimal]] = {
    "AAPL": {"value": 68, "growth": 74, "quality": 91, "momentum": 72, "financial_strength": 88, "volatility": 64, "earnings_stability": 86},
    "MSFT": {"value": 63, "growth": 78, "quality": 94, "momentum": 76, "financial_strength": 92, "volatility": 69, "earnings_stability": 90},
    "NVDA": {"value": 42, "growth": 96, "quality": 84, "momentum": 93, "financial_strength": 82, "volatility": 45, "earnings_stability": 76},
    "TSLA": {"value": 38, "growth": 82, "quality": 61, "momentum": 71, "financial_strength": 58, "volatility": 32, "earnings_stability": 48},
    "JPM": {"value": 77, "growth": 55, "quality": 76, "momentum": 58, "financial_strength": 84, "volatility": 70, "earnings_stability": 73},
    "JNJ": {"value": 70, "growth": 49, "quality": 82, "momentum": 50, "financial_strength": 79, "volatility": 82, "earnings_stability": 88},
}


def get_factor_score(symbol: str) -> FactorScore:
    normalized = normalize_symbol(symbol)
    raw_scores = MOCK_FACTOR_DATA.get(normalized, _default_factor_data(normalized))
    factors: list[FactorBreakdown] = []
    composite = Decimal("0")

    for factor_name, weight in FACTOR_WEIGHTS.items():
        raw_score = _clamp_score(raw_scores[factor_name])
        contribution = (raw_score * weight).quantize(Decimal("0.000001"))
        composite += contribution
        factors.append(
            FactorBreakdown(
                name=factor_name,
                raw_score=raw_score,
                normalized_score=raw_score,
                weight=weight,
                contribution=contribution,
                confidence="high" if normalized in MOCK_FACTOR_DATA else "medium",
                explanation=_factor_explanation(factor_name=factor_name, score=raw_score, symbol=normalized),
            )
        )

    composite = composite.quantize(Decimal("0.000001"))
    return FactorScore(
        symbol=normalized,
        composite_score=composite,
        rating=_rating_for(composite),
        factors=factors,
        explanation=_composite_explanation(symbol=normalized, composite=composite),
    )


def rank_factors(symbols: list[str]) -> FactorRankingResponse:
    scores = [get_factor_score(symbol) for symbol in _unique_symbols(symbols)]
    ranked = sorted(scores, key=lambda score: score.composite_score, reverse=True)
    for index, score in enumerate(ranked, start=1):
        score.rank = index
    return FactorRankingResponse(count=len(ranked), results=ranked)


def screen_factors(payload: ScreenerRequest) -> FactorRankingResponse:
    ranked = rank_factors(payload.symbols).results
    filtered = ranked
    if payload.min_score is not None:
        filtered = [score for score in filtered if score.composite_score >= payload.min_score]
    if payload.rating is not None:
        filtered = [score for score in filtered if score.rating == payload.rating]
    for index, score in enumerate(filtered, start=1):
        score.rank = index
    return FactorRankingResponse(count=len(filtered), results=filtered)


def compare_factors(symbols: list[str]) -> FactorCompareResponse:
    ranked = rank_factors(symbols).results
    return FactorCompareResponse(
        symbols=[score.symbol for score in ranked],
        leaders=ranked[:3],
        laggards=list(reversed(ranked[-3:])),
    )


def _unique_symbols(symbols: list[str]) -> list[str]:
    return sorted({normalize_symbol(symbol) for symbol in symbols if normalize_symbol(symbol)})


def _default_factor_data(symbol: str) -> dict[str, Decimal]:
    quote = get_quote(symbol)
    price_anchor = min(Decimal("100"), max(Decimal("0"), quote.price % Decimal("100")))
    return {
        "value": Decimal("55") + (Decimal("50") - price_anchor) / Decimal("10"),
        "growth": Decimal("60") + price_anchor / Decimal("20"),
        "quality": Decimal("65"),
        "momentum": Decimal("50") + price_anchor / Decimal("10"),
        "financial_strength": Decimal("62"),
        "volatility": Decimal("58"),
        "earnings_stability": Decimal("60"),
    }


def _clamp_score(value: Decimal | int) -> Decimal:
    decimal_value = Decimal(value)
    return max(Decimal("0"), min(Decimal("100"), decimal_value)).quantize(Decimal("0.000001"))


def _rating_for(score: Decimal) -> str:
    if score >= Decimal("80"):
        return "outperform"
    if score >= Decimal("65"):
        return "neutral"
    if score >= Decimal("50"):
        return "watch"
    return "avoid"


def _factor_explanation(factor_name: str, score: Decimal, symbol: str) -> str:
    readable_name = factor_name.replace("_", " ").title()
    if score >= Decimal("75"):
        tone = "strong"
    elif score >= Decimal("60"):
        tone = "constructive"
    elif score >= Decimal("45"):
        tone = "mixed"
    else:
        tone = "weak"
    return f"{symbol} has a {tone} {readable_name} factor score of {score}."


def _composite_explanation(symbol: str, composite: Decimal) -> str:
    rating = _rating_for(composite)
    return f"{symbol} receives a composite LionsForge factor score of {composite}, mapped to {rating}."
