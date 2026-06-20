from fastapi import APIRouter, Depends, HTTPException, status
from app.models.requests import ImproveUIRequest
from app.middleware.rate_limit import check_rate_limit
from app.db import supabase
from app.services import generator, validator
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/improve-ui")
async def improve_ui(request: ImproveUIRequest, user = Depends(check_rate_limit)):
    """Improve existing generated UI based on feedback instructions."""
    project_id_str = str(request.project_id)
    user_id_str = str(user.id)
    
    # 1. Fetch existing project details
    project = await supabase.get_project_by_id(project_id_str, user_id_str)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
        
    existing_code = project.get("generated_code") or ""
    
    # 2. Call the improvement service
    try:
        refined_code = await generator.improve(existing_code, request.instruction)
    except Exception as e:
        logger.error(f"Improvement generation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
        
    # 3. Validate the improved code (and sanitize if needed)
    validation_result = validator.validate(refined_code)
    
    # 4. Save the improved code to the database
    await supabase.update_project_code(project_id_str, refined_code)
    
    # Log successful generation metrics
    await supabase.log_generation(
        project_id=project_id_str,
        model="gpt-4o",
        tokens=0,
        latency=0,
        status="completed"
    )
    
    # Increment daily count for user
    await supabase.increment_generations(user_id_str)
    
    return {
        "code": refined_code
    }


