from fastapi import APIRouter, Depends, HTTPException
from uuid import UUID
from datetime import datetime, timezone
from app.models.project import ProjectResponse
from app.middleware.auth import get_current_user
from app.db import supabase as db

router = APIRouter()

@router.get("/projects", response_model=list[ProjectResponse])
async def list_projects(user = Depends(get_current_user)):
    """List all projects for the authenticated user from the database."""
    projects = await db.get_projects(user_id=str(user.id))
    return [
        ProjectResponse(
            id=UUID(p["id"]),
            user_id=UUID(p["user_id"]),
            title=p.get("title", "Untitled Project"),
            prompt=p.get("prompt", ""),
            generated_code=p.get("generated_code") or "",
            preview_url=p.get("preview_url"),
            created_at=datetime.fromisoformat(p["created_at"]) if isinstance(p.get("created_at"), str) else (p.get("created_at") or datetime.now(timezone.utc))
        )
        for p in projects
    ]

@router.get("/project/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: UUID, user = Depends(get_current_user)):
    """Retrieve a single project by ID from the database."""
    project = await db.get_project_by_id(project_id=str(project_id), user_id=str(user.id))
    if not project:
        raise HTTPException(status_code=404, detail="Project not found.")
    return ProjectResponse(
        id=UUID(project["id"]),
        user_id=UUID(project["user_id"]),
        title=project.get("title", "Untitled Project"),
        prompt=project.get("prompt", ""),
        generated_code=project.get("generated_code") or "",
        preview_url=project.get("preview_url"),
        created_at=datetime.fromisoformat(project["created_at"]) if isinstance(project.get("created_at"), str) else (project.get("created_at") or datetime.now(timezone.utc))
    )

@router.delete("/project/{project_id}")
async def delete_project(project_id: UUID, user = Depends(get_current_user)):
    """Delete a project by ID."""
    deleted_project = await db.delete_project(project_id=str(project_id), user_id=str(user.id))
    if not deleted_project:
        raise HTTPException(status_code=404, detail="Project not found or not owned by user.")
    return {"success": True, "deleted_by": str(user.id)}


