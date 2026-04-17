"""
Session and Feedback Management Service for Media Backend

This module provides comprehensive session tracking, feedback collection,
and agent performance monitoring capabilities using PostgreSQL.
"""

import logging
from datetime import datetime
from typing import List, Optional
from postgresql_session_manager import PostgreSQLSessionManager
from model import (
    FeedbackData, VotingData, AgentExecutionStep, QueryExecutionData,
    SessionMetadata
)

logger = logging.getLogger(__name__)

class SessionFeedbackManager:
    """Manages session data, feedback collection, and agent performance tracking using PostgreSQL"""

    def __init__(self):
        self.postgresql_manager = PostgreSQLSessionManager()

    # ============================================================================
    # FEEDBACK MANAGEMENT - Delegating to PostgreSQL Manager
    # ============================================================================

    async def save_vote(self, vote_data: VotingData) -> str:
        """Save user vote (thumbs up/down) for a specific query"""
        return await self.postgresql_manager.save_vote(vote_data)

    async def save_feedback(self, feedback_data: FeedbackData) -> str:
        """Save user feedback for a specific query"""
        return await self.postgresql_manager.save_feedback(feedback_data)

    async def get_feedback(self, query_id: str) -> Optional[FeedbackData]:
        """Retrieve feedback for a specific query"""
        return await self.postgresql_manager.get_feedback(query_id)

    # ============================================================================
    # QUERY EXECUTION TRACKING - Delegating to PostgreSQL Manager
    # ============================================================================

    async def start_query_tracking(self, query_id: str, user_id: str, session_id: str,
                                 original_query: str) -> QueryExecutionData:
        """Initialize query execution tracking"""
        return await self.postgresql_manager.start_query_tracking(query_id, user_id, session_id, original_query)

    async def add_agent_execution_step(self, query_id: str, step: AgentExecutionStep) -> bool:
        """Add an agent execution step to a query"""
        try:
            # Log the step details
            logger.info(f"Adding execution step for query {query_id}, agent {step.agent_name}, step_type {step.step_type}")

            # Ensure we have a valid query_id
            if not query_id:
                logger.error("Cannot add execution step: query_id is empty")
                return False

            # Ensure we have a valid step
            if not step or not step.agent_name:
                logger.error("Cannot add execution step: step is invalid")
                return False

            # Add the step to the database
            result = await self.postgresql_manager.add_agent_execution_step(query_id, step)

            if result:
                logger.info(f"Successfully added execution step for query {query_id}, agent {step.agent_name}")
            else:
                logger.error(f"Failed to add execution step for query {query_id}, agent {step.agent_name}")

            return result

        except Exception as e:
            logger.error(f"Error adding execution step: {e}")
            return False

    async def complete_query_tracking(self, query_id: str, final_response: str,
                                    success: bool = True, error_details: Optional[str] = None,
                                    end_time: Optional[datetime] = None, intent_detected: Optional[str] = None) -> bool:
        """Complete query execution tracking"""
        return await self.postgresql_manager.complete_query_tracking(query_id, final_response, success, error_details, end_time, intent_detected)

    async def get_query_execution_data(self, query_id: str) -> Optional[QueryExecutionData]:
        """Retrieve query execution data"""
        return await self.postgresql_manager.get_query_execution_data(query_id)

    # ============================================================================
    # SESSION MANAGEMENT - Delegating to PostgreSQL Manager
    # ============================================================================

    async def create_session(self, session_id: str, user_id: str,
                           session_name: Optional[str] = None) -> SessionMetadata:
        """Create a new session"""
        return await self.postgresql_manager.create_session(session_id, user_id, session_name)

    async def get_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Retrieve session metadata"""
        return await self.postgresql_manager.get_session_metadata(session_id)

    async def update_session_name(self, session_id: str, new_name: str) -> bool:
        """Update session name"""
        return await self.postgresql_manager.update_session_name(session_id, new_name)

    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[SessionMetadata]:
        """Get all sessions for a user"""
        return await self.postgresql_manager.get_user_sessions(user_id, limit)

    async def list_user_sessions(self, user_id: str, limit: int = 50):
        """List all sessions for a user (compatibility method)"""
        sessions = await self.postgresql_manager.get_user_sessions(user_id, limit)
        return {"sessions": sessions, "total_count": len(sessions)}

    async def get_session_with_queries(self, session_id: str):
        """Get session metadata with all query details"""
        return await self.postgresql_manager.get_session_with_queries(session_id)

    # ============================================================================
    # ANALYTICS - Delegating to PostgreSQL Manager
    # ============================================================================

    # async def get_agent_performance_metrics(self, agent_name: Optional[str] = None,
    #                                       days: int = 30) -> List[AgentPerformanceMetrics]:
    #     """Get agent performance metrics"""
    #     return await self.postgresql_manager.get_agent_performance_metrics(agent_name, days)

    # ============================================================================
    # LEGACY COMPATIBILITY METHODS (for backward compatibility)
    # ============================================================================

    async def get_vote(self, query_id: str) -> Optional[VotingData]:
        """Retrieve vote for a specific query (legacy compatibility)"""
        # For now, return None as votes are stored as feedback in PostgreSQL
        # This method is kept for backward compatibility
        return None

    async def get_session_feedback(self, session_id: str) -> List[FeedbackData]:
        """Get all feedback for a session (legacy compatibility)"""
        # This method is kept for backward compatibility
        # In PostgreSQL implementation, feedback is retrieved differently
        return []



