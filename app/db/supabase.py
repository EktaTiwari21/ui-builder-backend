from supabase import acreate_client, AsyncClient
from app.config import settings
from typing import Optional

_supabase_client: Optional[AsyncClient] = None

async def get_supabase_client() -> AsyncClient:
    """Initialize or return the global singleton asynchronous Supabase client.
    
    Returns:
        AsyncClient: The initialized Supabase client instance.
    """
    global _supabase_client
    if _supabase_client is None:
        _supabase_client = await acreate_client(
            settings.supabase_url,
            settings.supabase_service_key
        )
    return _supabase_client

async def get_projects(user_id: str) -> list[dict]:
    """Retrieve all projects for a specific user.
    
    Args:
        user_id: The UUID string of the user.
        
    Returns:
        list[dict]: A list of matching project rows.
    """
    client = await get_supabase_client()
    response = await client.table("projects").select("*").eq("user_id", user_id).execute()
    return response.data

async def get_project_by_id(project_id: str, user_id: str) -> Optional[dict]:
    """Retrieve details of a single project by ID and user ID.
    
    Args:
        project_id: The project UUID string.
        user_id: The user UUID string.
        
    Returns:
        dict | None: The project row if found, otherwise None.
    """
    client = await get_supabase_client()
    response = await client.table("projects").select("*").eq("id", project_id).eq("user_id", user_id).execute()
    return response.data[0] if response.data else None

async def create_project(user_id: str, title: str, prompt: str) -> Optional[dict]:
    """Create a new project row in the database.
    
    Args:
        user_id: The user UUID string.
        title: Title of the project.
        prompt: Raw prompt text.
        
    Returns:
        dict | None: The newly created project row details.
    """
    client = await get_supabase_client()
    response = await client.table("projects").insert({
        "user_id": user_id,
        "title": title,
        "prompt": prompt
    }).execute()
    return response.data[0] if response.data else None

async def update_project_code(project_id: str, generated_code: str) -> Optional[dict]:
    """Update the generated React component code of an existing project.
    
    Args:
        project_id: The project UUID string.
        generated_code: The JSX code block.
        
    Returns:
        dict | None: The updated project row details.
    """
    client = await get_supabase_client()
    response = await client.table("projects").update({
        "generated_code": generated_code
    }).eq("id", project_id).execute()
    return response.data[0] if response.data else None

async def delete_project(project_id: str, user_id: str) -> Optional[dict]:
    """Delete a project by ID and user ID.
    
    Args:
        project_id: The project UUID string.
        user_id: The user UUID string.
        
    Returns:
        dict | None: The deleted project row details.
    """
    client = await get_supabase_client()
    response = await client.table("projects").delete().eq("id", project_id).eq("user_id", user_id).execute()
    return response.data[0] if response.data else None

async def log_generation(
    project_id: Optional[str],
    model: str,
    tokens: int | dict,
    latency: int,
    status: str
) -> Optional[dict]:
    """Insert a new audit record logging an AI generation attempt.
    
    Args:
        project_id: The project UUID string (can be None if generation failed before project was saved).
        model: The AI model name/version used (e.g. gpt-4o).
        tokens: The total integer token count, or a dict containing 'prompt' and 'response' keys.
        latency: Execution latency of the AI generation in milliseconds.
        status: Status string (e.g. completed, failed).
        
    Returns:
        dict | None: The logged generation row details.
    """
    client = await get_supabase_client()
    
    prompt_tokens = 0
    response_tokens = 0
    
    if isinstance(tokens, dict):
        prompt_tokens = tokens.get("prompt", 0)
        response_tokens = tokens.get("response", 0)
    elif isinstance(tokens, int):
        prompt_tokens = tokens  # Fallback: log total as prompt tokens, or separate if known
        
    response = await client.table("generations").insert({
        "project_id": project_id,
        "ai_model": model,
        "prompt_tokens": prompt_tokens,
        "response_tokens": response_tokens,
        "generation_status": status,
        "latency_ms": latency
    }).execute()
    return response.data[0] if response.data else None

async def increment_generations(user_id: str) -> None:
    """Increment the profiles.generations_today counter for the user.
    
    Args:
        user_id: The user UUID string.
    """
    import logging
    client = await get_supabase_client()
    try:
        response = await client.table("profiles").select("generations_today").eq("id", user_id).execute()
        current = response.data[0].get("generations_today", 0) if response.data else 0
        await client.table("profiles").update({"generations_today": current + 1}).eq("id", user_id).execute()
    except Exception as e:
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to increment generations counter for user {user_id}: {e}")

