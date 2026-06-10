from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.api import generate, improve, projects, export

app = FastAPI(
    title="Autonomous UI Builder Agent - Backend",
    description="FastAPI backend for orchestrating UI planning and generation agents.",
    version="1.0.0"
)

# Configure CORS
# Allow both FRONTEND_URL from settings and localhost:3000 for local development
origins = list({settings.frontend_url, "http://localhost:3000", "http://127.0.0.1:3000"})

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)


@app.get("/health", tags=["System"])
async def health_check():
    """Health check route to verify that the service is running."""
    return {
        "status": "ok",
        "environment": settings.environment
    }

# Register routers
app.include_router(generate.router)
app.include_router(improve.router)
app.include_router(projects.router)
app.include_router(export.router)
