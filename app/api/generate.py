from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.models.requests import GenerateUIRequest
from app.services import orchestrator
from app.middleware.rate_limit import check_rate_limit

router = APIRouter()

@router.post("/generate-ui")
async def generate_ui(request: GenerateUIRequest, user = Depends(check_rate_limit)):
    """Generate React/Tailwind component code from a text prompt as an SSE stream."""
    return StreamingResponse(
        orchestrator.run(request, user_id=str(user.id)),
        media_type="text/event-stream"
    )




