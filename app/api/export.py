from fastapi import APIRouter, Depends
from app.models.requests import ExportRequest
from app.middleware.auth import get_current_user

router = APIRouter()

@router.post("/export-project")
async def export_project(request: ExportRequest, user = Depends(get_current_user)):
    """Export the project code and return a download URL."""
    return {
        "download_url": f"https://example.com/download/{request.project_id}",
        "user_id": str(user.id)
    }


