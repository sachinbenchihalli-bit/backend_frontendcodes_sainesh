# routers/__init__.py
"""
Media Dashboard API Routers

This package contains all the API routers for the media dashboard backend.
Each router handles a specific aspect of the media analytics:

- overview: Overview metrics and summary data
- sessions: Session analytics and user engagement
- queries: Query performance and intent analysis  
- agents: Agent execution performance and monitoring
- feedback: User feedback analysis and sentiment tracking
"""

from .overview import router as overview_router
from .sessions import router as sessions_router
from .queries import router as queries_router
from .agents import router as agents_router
from .feedback import router as feedback_router

__all__ = [
    "overview_router",
    "sessions_router", 
    "queries_router",
    "agents_router",
    "feedback_router"
]
