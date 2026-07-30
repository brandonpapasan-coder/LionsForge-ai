from fastapi import APIRouter

router = APIRouter(prefix="/agents", tags=["Agents"])


@router.get("/status")
async def agent_status():
    return {
        "agents": "registered",
        "orchestration": "available",
    }
