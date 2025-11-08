"""Main API v1 router."""

from fastapi import APIRouter

# Import endpoint routers
from app.api import auth, users, files, classes, assignments, ai_agent, websocket, enhanced_grading, langgraph_grading

api_router = APIRouter()

# Health check endpoint for API
@api_router.get("/health")
async def api_health():
    """API health check."""
    return {"status": "ok", "api_version": "v1"}

# Include endpoint routers
api_router.include_router(auth.router)
api_router.include_router(users.router)
api_router.include_router(files.router)
api_router.include_router(classes.router)
api_router.include_router(assignments.router)
api_router.include_router(ai_agent.router)
api_router.include_router(enhanced_grading.router)
api_router.include_router(langgraph_grading.router)  # LangGraph-based grading
api_router.include_router(websocket.router)