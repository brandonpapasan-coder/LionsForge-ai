from fastapi import APIRouter

router = APIRouter(prefix="/research", tags=["Research Missions"])


@router.post("/missions")
async def create_mission(payload: dict):
    return {
        "mission": payload,
        "state": "created",
    }


@router.get("/missions/{mission_id}")
async def get_mission(mission_id: str):
    return {
        "mission_id": mission_id,
        "state": "tracking",
    }
