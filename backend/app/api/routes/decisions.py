from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.models.user import User
from app.schemas.decision_intelligence import DecisionRecommendation
from app.services.decision_intelligence_service import build_decision_recommendation

router = APIRouter()


@router.get("/{symbol}", response_model=DecisionRecommendation)
def decision_recommendation_endpoint(
    symbol: str,
    current_user: User = Depends(get_current_user),
) -> DecisionRecommendation:
    return build_decision_recommendation(symbol)
