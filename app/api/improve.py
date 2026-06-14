from fastapi import APIRouter, Depends
from app.models.requests import ImproveUIRequest
from app.middleware.rate_limit import check_rate_limit

router = APIRouter()

@router.post("/improve-ui")
async def improve_ui(request: ImproveUIRequest, user = Depends(check_rate_limit)):
    """Improve existing generated UI based on feedback instructions."""
    return {
        "status": "stub",
        "message": "Improve UI endpoint stub",
        "received": {
            "project_id": str(request.project_id),
            "instruction": request.instruction
        },
        "user_id": str(user.id)
    }


