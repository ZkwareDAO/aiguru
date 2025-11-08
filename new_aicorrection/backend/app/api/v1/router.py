"""Main API v1 router."""

from fastapi import APIRouter

# Import endpoint routers
<<<<<<< HEAD
from app.api import auth, users, files, classes, assignments, ai_agent, websocket, enhanced_grading
from app.api.v1 import grading_v2
=======
from app.api import auth, users, files, classes, assignments, ai_agent, websocket, enhanced_grading, langgraph_grading
>>>>>>> b42dfdc87b0c14ed38790b4ae0a68ff39e132e3d

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
<<<<<<< HEAD
api_router.include_router(websocket.router)

# Include new Agent-based grading API
api_router.include_router(grading_v2.router)
=======
api_router.include_router(langgraph_grading.router)  # LangGraph-based grading
api_router.include_router(websocket.router)
>>>>>>> b42dfdc87b0c14ed38790b4ae0a68ff39e132e3d
