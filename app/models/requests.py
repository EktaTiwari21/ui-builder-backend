from pydantic import BaseModel, Field
from uuid import UUID

class GenerateUIRequest(BaseModel):
    """Request schema for UI generation."""
    prompt: str = Field(..., description="Prompt describing the UI components to build.")
    style: str = Field(default="minimal", description="Design style (e.g., minimal, neon, glassmorphism).")
    framework: str = Field(default="react-tailwind", description="Frontend framework and styling library combination.")

class ImproveUIRequest(BaseModel):
    """Request schema for improving an existing UI."""
    project_id: UUID = Field(..., description="The ID of the project to improve.")
    instruction: str = Field(..., description="Feedback instruction on what needs to be improved or modified.")

class ExportRequest(BaseModel):
    """Request schema for exporting a project."""
    project_id: UUID = Field(..., description="The ID of the project to export.")
