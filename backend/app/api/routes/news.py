from fastapi import APIRouter

router = APIRouter()


@router.get("/market")
def market_news():
    return {
        "status": "mock",
        "message": "Market news endpoint initialized. Connect a news provider to return live articles and business deal coverage.",
        "articles": [],
        "planned_sources": ["company news", "SEC filings", "press releases", "documented business deals"],
    }
