from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional

class ProjectResponse(BaseModel):
    """Response schema representing a UI Builder project."""
    id: UUID
    user_id: UUID
    title: str
    prompt: str
    generated_code: Optional[str] = Field(default=None, description="The React/Tailwind component code generated.")
    preview_url: Optional[str] = Field(default=None, description="Preview URL of the generated UI.")
    created_at: datetime

class GenerationResponse(BaseModel):
    """Response schema representing an AI generation log/attempt."""
    id: UUID
    project_id: UUID
    ai_model: Optional[str] = Field(default=None, description="The name/version of the AI model used.")
    prompt_tokens: Optional[int] = Field(default=None, description="Number of tokens in the input prompt.")
    response_tokens: Optional[int] = Field(default=None, description="Number of tokens in the generated response.")
    generation_status: str = Field(default="pending", description="Status of the generation process (e.g. pending, completed, failed).")
    latency_ms: Optional[int] = Field(default=None, description="Latency of the generation process in milliseconds.")
    created_at: datetime
