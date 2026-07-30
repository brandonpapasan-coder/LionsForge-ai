from fastapi import APIRouter

router = APIRouter(prefix="/ai", tags=["AI"])


@router.get("/status")
async def ai_status():
    return {
        "service": "Onyxmane AI orchestration",
        "status": "ready",
    }
