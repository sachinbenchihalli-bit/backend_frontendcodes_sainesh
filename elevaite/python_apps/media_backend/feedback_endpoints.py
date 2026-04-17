"""
Feedback and Session Management API Endpoints

This module provides REST API endpoints for collecting feedback,
managing sessions, and retrieving analytics data.
"""

import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from fastapi import HTTPException
import logging
import json

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    logger.addHandler(handler)
from pydantic import BaseModel

from model import (
    FeedbackData, VotingData, FeedbackType, SessionMetadata, QueryExecutionData,
    SessionTopicAnalysis
)
from session_feedback_manager import SessionFeedbackManager

logger = logging.getLogger(__name__)

# ============================================================================
# REQUEST/RESPONSE MODELS
# ============================================================================

class VotingRequest(BaseModel):
    """Request model for submitting votes (following Arlo pattern)"""
    query_id: str
    user_id: str
    session_id: str
    vote: int  # -1 (down), 0 (neutral), 1 (up)

class FeedbackRequest(BaseModel):
    """Request model for submitting feedback"""
    query_id: str
    user_id: str
    session_id: str
    feedback_type: FeedbackType
    feedback_text: str  # Required for detailed feedback
    vote: int = 0  # -1 (down), 0 (neutral), 1 (up)

class FeedbackResponse(BaseModel):
    """Response model for feedback submission"""
    success: bool
    message: str
    feedback_id: str

class SessionCreateRequest(BaseModel):
    """Request model for creating a new session"""
    session_id: str
    user_id: str
    session_name: Optional[str] = None

class SessionUpdateRequest(BaseModel):
    """Request model for updating session name"""
    session_id: str
    new_name: str

class SessionListResponse(BaseModel):
    """Response model for listing user sessions"""
    sessions: List[SessionMetadata]
    total_count: int

class QueryExecutionResponse(BaseModel):
    """Response model for query execution details"""
    query_data: QueryExecutionData
    feedback: Optional[FeedbackData] = None

# class AgentAnalyticsResponse(BaseModel):
#     """Response model for agent performance analytics"""
#     agent_metrics: List[AgentPerformanceMetrics]
#     summary: Dict[str, Any]

class SessionAnalyticsResponse(BaseModel):
    """Response model for session analytics"""
    session_metadata: SessionMetadata
    query_details: List[QueryExecutionData]
    feedback_summary: Dict[str, Any]

# ============================================================================
# FEEDBACK ENDPOINTS
# ============================================================================

class FeedbackEndpoints:
    """Handles all feedback-related API endpoints"""

    def __init__(self):
        self.manager = SessionFeedbackManager()

    async def submit_vote(self, request: VotingRequest) -> Dict[str, str]:
        """Submit user vote for a query (following Arlo pattern)"""
        try:
            # Create voting data
            vote_data = VotingData(
                query_id=request.query_id,
                user_id=request.user_id,
                session_id=request.session_id,
                vote=request.vote,
                timestamp=datetime.now()
            )

            # Save vote
            result = await self.manager.save_vote(vote_data)

            return {"message": result}

        except Exception as e:
            logger.error(f"Error submitting vote: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def submit_feedback(self, request: FeedbackRequest) -> Dict[str, str]:
        """Submit user feedback for a query"""
        try:
            # Create feedback data
            feedback_data = FeedbackData(
                query_id=request.query_id,
                user_id=request.user_id,
                session_id=request.session_id,
                feedback_type=request.feedback_type,
                feedback_text=request.feedback_text,
                vote=request.vote,
                timestamp=datetime.now()
            )

            # Save feedback
            result = await self.manager.save_feedback(feedback_data)

            return {"message": result}

        except Exception as e:
            logger.error(f"Error submitting feedback: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_feedback(self, query_id: str) -> Optional[FeedbackData]:
        """Retrieve feedback for a specific query"""
        try:
            feedback = await self.manager.get_feedback(query_id)
            return feedback

        except Exception as e:
            logger.error(f"Error retrieving feedback: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_session_feedback(self, session_id: str) -> List[FeedbackData]:
        """Get all feedback for a session"""
        try:
            feedback_list = await self.manager.get_session_feedback(session_id)
            return feedback_list

        except Exception as e:
            logger.error(f"Error retrieving session feedback: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# SESSION MANAGEMENT ENDPOINTS
# ============================================================================

class SessionEndpoints:
    """Handles all session management API endpoints"""

    def __init__(self):
        self.manager = SessionFeedbackManager()

    async def create_session(self, request: SessionCreateRequest) -> SessionMetadata:
        """Create a new session"""
        try:
            logger.info(f"Creating session: session_id={request.session_id}, user_id={request.user_id}, session_name={request.session_name}")
            session_metadata = await self.manager.create_session(
                session_id=request.session_id,
                user_id=request.user_id,
                session_name=request.session_name
            )
            logger.info(f"Session created successfully: {session_metadata.session_id}")
            return session_metadata

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_session(self, session_id: str) -> Optional[SessionMetadata]:
        """Get session metadata"""
        try:
            session_metadata = await self.manager.get_session_metadata(session_id)
            return session_metadata

        except Exception as e:
            logger.error(f"Error retrieving session: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def update_session_name(self, request: SessionUpdateRequest) -> bool:
        """Update session name"""
        try:
            success = await self.manager.update_session_name(
                session_id=request.session_id,
                new_name=request.new_name
            )

            if not success:
                raise HTTPException(status_code=404, detail="Session not found")

            return success

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating session name: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_user_sessions(self, user_id: str, limit: int = 50):
        """List all sessions for a user"""
        try:
            logger.info(f"Loading sessions for user: {user_id}, limit: {limit}")
            result = await self.manager.list_user_sessions(user_id, limit)
            logger.info(f"Found {len(result.get('sessions', []))} sessions for user {user_id}")
            logger.debug(f"Session data: {result}")
            return result

        except Exception as e:
            logger.error(f"Error listing user sessions: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_session_with_queries(self, session_id: str):
        """Get session with all query details"""
        try:
            logger.info(f"Loading session with queries for session_id: {session_id}")
            result = await self.manager.get_session_with_queries(session_id)

            if not result:
                logger.warning(f"Session {session_id} not found")
                raise HTTPException(status_code=404, detail="Session not found")

            # Log the structure of what we're returning
            session_metadata = result.get('session_metadata')
            query_details = result.get('query_details', [])

            logger.info(f"Session {session_id} found with {len(query_details)} queries")
            if session_metadata:
                logger.info(f"Session metadata: user_id={session_metadata.user_id}, name={session_metadata.session_name}")

            # Log query details
            for i, query in enumerate(query_details):
                logger.info(f"Query {i+1}: query_id={query.query_id}, original_query='{query.original_query[:50]}...', final_response='{query.final_response[:50] if query.final_response else 'None'}...'")

            logger.debug(f"Full session data: {result}")
            return result

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting session with queries: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    async def flush_session_to_database(self, session_id: str, user_id: str):
        """Flush all pending session data from cache to database"""
        try:
            logger.info(f"Flushing session {session_id} data to database")

            # Import here to avoid circular imports
            from cache_control import CacheControl
            from llm_rag_inference import store_session_data_to_db

            # Get session data from cache
            cache_control = CacheControl()
            cache_key = f"{user_id}:{session_id}"
            existing_data_json = cache_control.get(cache_key)

            if not existing_data_json:
                logger.info(f"No cached data found for session {session_id}")
                return {"message": "No data to flush"}

            existing_data = json.loads(existing_data_json)

            # Store all queries from this session to database
            stored_count = await store_session_data_to_db(
                user_id=user_id,
                session_id=session_id,
                session_data_list=existing_data
            )

            logger.info(f"Flushed {stored_count} queries from session {session_id} to database")
            return {"message": f"Flushed {stored_count} queries to database"}

        except Exception as e:
            logger.error(f"Error flushing session to database: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# QUERY EXECUTION ENDPOINTS
# ============================================================================

class QueryEndpoints:
    """Handles query execution tracking endpoints"""

    def __init__(self):
        self.manager = SessionFeedbackManager()

    async def get_query_details(self, query_id: str) -> QueryExecutionResponse:
        """Get detailed execution data for a query"""
        try:
            query_data = await self.manager.get_query_execution_data(query_id)
            if not query_data:
                raise HTTPException(status_code=404, detail="Query not found")

            feedback = await self.manager.get_feedback(query_id)

            return QueryExecutionResponse(
                query_data=query_data,
                feedback=feedback
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving query details: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ANALYTICS ENDPOINTS
# ============================================================================

class AnalyticsEndpoints:
    """Handles analytics and performance monitoring endpoints"""

    def __init__(self):
        self.manager = SessionFeedbackManager()

    # async def get_agent_analytics(self, agent_name: Optional[str] = None) -> AgentAnalyticsResponse:
    #     """Get agent performance analytics"""
    #     try:
    #         # This would need to be implemented in the manager
    #         # For now, return empty response
    #         return AgentAnalyticsResponse(
    #             agent_metrics=[],
    #             summary={}
    #         )

    #     except Exception as e:
    #         logger.error(f"Error retrieving agent analytics: {e}")
    #         raise HTTPException(status_code=500, detail=str(e))

    async def get_session_analytics(self, session_id: str) -> SessionAnalyticsResponse:
        """Get comprehensive session analytics"""
        try:
            session_metadata = await self.manager.get_session_metadata(session_id)
            if not session_metadata:
                raise HTTPException(status_code=404, detail="Session not found")

            # Get query details for the session
            query_details = []
            for query_id in session_metadata.query_ids:
                query_data = await self.manager.get_query_execution_data(query_id)
                if query_data:
                    query_details.append(query_data)

            # Get feedback summary
            feedback_list = await self.manager.get_session_feedback(session_id)
            feedback_summary = {
                "total_feedback": len(feedback_list),
                "positive_feedback": sum(1 for f in feedback_list if f.vote == 1),
                "negative_feedback": sum(1 for f in feedback_list if f.vote == -1),
                "detailed_feedback": sum(1 for f in feedback_list if f.feedback_text),
            }

            return SessionAnalyticsResponse(
                session_metadata=session_metadata,
                query_details=query_details,
                feedback_summary=feedback_summary
            )

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error retrieving session analytics: {e}")
            raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# ENDPOINT INSTANCES
# ============================================================================

# Create endpoint instances for use in main.py
feedback_endpoints = FeedbackEndpoints()
session_endpoints = SessionEndpoints()
query_endpoints = QueryEndpoints()
analytics_endpoints = AnalyticsEndpoints()
