from fastapi import APIRouter, Depends
from uuid import UUID
from datetime import datetime, timezone
from app.models.project import ProjectResponse
from app.middleware.auth import get_current_user

router = APIRouter()

# Dummy values for stubs
DUMMY_USER_ID = UUID("00000000-0000-0000-0000-000000000000")
DUMMY_PROJECT_ID = UUID("11111111-1111-1111-1111-111111111111")

@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(user = Depends(get_current_user)):
    """List all projects for the authenticated user."""
    return [
        ProjectResponse(
            id=DUMMY_PROJECT_ID,
            user_id=UUID(str(user.id)),
            title="Stub Project",
            prompt="Build a SaaS pricing page with 3 tiers",
            generated_code="export function PricingSection() {}",
            preview_url="https://example.com/preview/stub-id",
            created_at=datetime.now(timezone.utc)
        )
    ]

@router.get("/project/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, user = Depends(get_current_user)):
    """Retrieve details of a single project by ID."""
    return ProjectResponse(
        id=project_id,
        user_id=UUID(str(user.id)),
        title="Stub Project",
        prompt="Build a SaaS pricing page with 3 tiers",
        generated_code="export function PricingSection() {}",
        preview_url="https://example.com/preview/stub-id",
        created_at=datetime.now(timezone.utc)
    )

@router.delete("/project/{project_id}")
async def delete_project(project_id: UUID, user = Depends(get_current_user)):
    """Delete a project by ID."""
    return {"success": True, "deleted_by": str(user.id)}


