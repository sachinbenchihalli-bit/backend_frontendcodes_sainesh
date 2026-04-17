"""
PostgreSQL Session and Feedback Management Service for Media Backend

This module provides comprehensive session tracking, feedback collection,
and agent performance monitoring capabilities using PostgreSQL instead of Redis.
"""

import logging
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc, func, case
from db_connector import db_connector
from database_models import (
    SessionModel, QueryModel, AgentExecutionStepModel,
    FeedbackModel
)
from model import (
    FeedbackData, VotingData, AgentExecutionStep, QueryExecutionData,
    SessionMetadata, FeedbackType
)

logger = logging.getLogger(__name__)

class PostgreSQLSessionManager:
    """Manages session data, feedback collection, and agent performance tracking using PostgreSQL"""

    def __init__(self):
        self.db_connector = db_connector

    def get_db_session(self) -> Session:
        """Get a database session"""
        return self.db_connector.get_session()

    # ============================================================================
    # VOTING AND FEEDBACK METHODS
    # ============================================================================

    async def save_vote(self, voting_data: VotingData) -> str:
        """Save user vote (thumbs up/down) for a specific query"""
        try:
            db_session = self.get_db_session()

            # Check if feedback already exists
            existing_feedback = db_session.query(FeedbackModel).filter_by(
                query_id=voting_data.query_id
            ).first()

            feedback_type = FeedbackType.THUMBS_UP if voting_data.vote > 0 else FeedbackType.THUMBS_DOWN

            if existing_feedback:
                # Update existing feedback with new vote
                logger.info(f"Updating existing feedback for query {voting_data.query_id} with new vote: {voting_data.vote}")
                existing_feedback.vote = voting_data.vote
                existing_feedback.feedback_type = feedback_type.value
                existing_feedback.timestamp = datetime.now(timezone.utc)
            else:
                # Create new feedback record for voting
                feedback_record = FeedbackModel(
                    query_id=voting_data.query_id,
                    session_id=voting_data.session_id,
                    user_id=voting_data.user_id,
                    feedback_type=feedback_type.value,
                    vote=voting_data.vote,
                    timestamp=datetime.now(timezone.utc)
                )
                db_session.add(feedback_record)

            # Update session feedback counts
            await self._update_session_feedback_counts(db_session, voting_data.session_id)

            db_session.commit()
            db_session.close()

            if existing_feedback:
                logger.info(f"Vote updated for query {voting_data.query_id}")
                return "Vote Updated"
            else:
                logger.info(f"Vote saved for query {voting_data.query_id}")
                return "Vote Saved"

        except Exception as e:
            logger.error(f"Error saving vote: {e}")
            if 'db_session' in locals():
                db_session.rollback()
                db_session.close()
            return "Vote Failed"

    async def save_feedback(self, feedback_data: FeedbackData) -> str:
        """Save user feedback for a specific query"""
        try:
            db_session = self.get_db_session()

            # Check if feedback already exists
            existing_feedback = db_session.query(FeedbackModel).filter_by(
                query_id=feedback_data.query_id
            ).first()

            if existing_feedback:
                # Update existing feedback with new data
                logger.info(f"Updating existing feedback for query {feedback_data.query_id}, Received feedback data: {feedback_data}")
                existing_feedback.feedback_type = feedback_data.feedback_type.value
                existing_feedback.feedback_text = feedback_data.feedback_text
                existing_feedback.vote = feedback_data.vote
                existing_feedback.timestamp = datetime.now(timezone.utc)
                # existing_feedback.agent_specific_feedback = feedback_data.agent_specific_feedback or {}
            else:
                # Create new feedback record
                feedback_record = FeedbackModel(
                    query_id=feedback_data.query_id,
                    session_id=feedback_data.session_id,
                    user_id=feedback_data.user_id,
                    feedback_type=feedback_data.feedback_type.value,
                    feedback_text=feedback_data.feedback_text,
                    vote=feedback_data.vote,
                    timestamp=datetime.now(timezone.utc),
                    # agent_specific_feedback=feedback_data.agent_specific_feedback or {}
                )
                db_session.add(feedback_record)

            # Update session feedback counts
            await self._update_session_feedback_counts(db_session, feedback_data.session_id)

            db_session.commit()
            db_session.close()

            if existing_feedback:
                logger.info(f"Feedback updated for query {feedback_data.query_id}")
                return "Feedback Updated"
            else:
                logger.info(f"Feedback saved for query {feedback_data.query_id}")
                return "Feedback Saved"

        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            if 'db_session' in locals():
                db_session.rollback()
                db_session.close()
            return "Feedback Failed"

    async def get_feedback(self, query_id: str) -> Optional[FeedbackData]:
        """Retrieve feedback for a specific query"""
        try:
            db_session = self.get_db_session()

            feedback_record = db_session.query(FeedbackModel).filter_by(
                query_id=query_id
            ).first()

            db_session.close()

            if feedback_record:
                return FeedbackData(
                    query_id=feedback_record.query_id,
                    user_id=feedback_record.user_id,
                    session_id=feedback_record.session_id,
                    feedback_type=FeedbackType(feedback_record.feedback_type),
                    feedback_text=feedback_record.feedback_text,
                    vote=feedback_record.vote,
                    timestamp=feedback_record.timestamp,
                    agent_specific_feedback=feedback_record.agent_specific_feedback
                )
            return None

        except Exception as e:
            logger.error(f"Error retrieving feedback: {e}")
            if 'db_session' in locals():
                db_session.close()
            return None

    # ============================================================================
    # QUERY EXECUTION TRACKING METHODS
    # ============================================================================

    async def start_query_tracking(self, query_id: str, user_id: str, session_id: str,
                                 original_query: str) -> QueryExecutionData:
        """Initialize query execution tracking"""
        try:
            db_session = self.get_db_session()

            # Check if query already exists
            existing_query = db_session.query(QueryModel).filter_by(query_id=query_id).first()

            if existing_query:
                logger.info(f"Query {query_id} already exists, returning existing data")

                # Return existing QueryExecutionData
                query_data = QueryExecutionData(
                    query_id=existing_query.query_id,
                    user_id=existing_query.user_id,
                    session_id=existing_query.session_id,
                    original_query=existing_query.original_query,
                    start_time=existing_query.start_time,
                    final_response=existing_query.final_response or ""
                )

                db_session.close()
                return query_data

            # Create new query record
            query_record = QueryModel(
                query_id=query_id,
                session_id=session_id,
                user_id=user_id,
                original_query=original_query,
                start_time=datetime.now(timezone.utc)
            )

            db_session.add(query_record)

            # Update session with new query
            await self._update_session_activity(db_session, session_id)

            try:
                db_session.commit()
            except Exception as commit_error:
                # Handle potential race condition where another process inserted the same query_id
                db_session.rollback()

                # Check if the query now exists (race condition)
                existing_query = db_session.query(QueryModel).filter_by(query_id=query_id).first()
                if existing_query:
                    logger.info(f"Query {query_id} was created by another process during commit, returning existing data")

                    # Return existing QueryExecutionData
                    query_data = QueryExecutionData(
                        query_id=existing_query.query_id,
                        user_id=existing_query.user_id,
                        session_id=existing_query.session_id,
                        original_query=existing_query.original_query,
                        start_time=existing_query.start_time,
                        final_response=existing_query.final_response or ""
                    )

                    db_session.close()
                    return query_data
                else:
                    # Re-raise the original error if it's not a duplicate key issue
                    raise commit_error

            # Return QueryExecutionData object before closing session
            query_data = QueryExecutionData(
                query_id=query_id,
                user_id=user_id,
                session_id=session_id,
                original_query=original_query,
                start_time=query_record.start_time,
                final_response=""
            )

            db_session.close()

            logger.info(f"Started tracking query {query_id}")
            return query_data

        except Exception as e:
            logger.error(f"Error starting query tracking: {e}")
            if 'db_session' in locals():
                db_session.rollback()
                db_session.close()
            raise

    async def add_agent_execution_step(self, query_id: str, step: AgentExecutionStep) -> bool:
        """Add an agent execution step to a query"""
        try:
            db_session = self.get_db_session()

            step_record = AgentExecutionStepModel(
                query_id=query_id,
                agent_name=step.agent_name,
                step_type=step.step_type,
                start_time=step.start_time,
                end_time=step.end_time,
                duration_ms=step.duration_ms,
                input_prompt=step.input_prompt,
                output_response=step.output_response,
                model_used=step.model_used,
                tokens_used=step.tokens_used or {},
                success=step.success,
                error_details=step.error_message,
                step_metadata=step.metadata or {}
            )

            db_session.add(step_record)
            db_session.commit()
            db_session.close()

            logger.info(f"Added execution step for query {query_id}, agent {step.agent_name}, step_type {step.step_type}")
            return True

        except Exception as e:
            logger.error(f"Error adding agent execution step: {e}")
            if 'db_session' in locals():
                db_session.rollback()
                db_session.close()
            return False

    async def complete_query_tracking(self, query_id: str, final_response: str,
                                    success: bool = True, error_details: Optional[str] = None,
                                    end_time: Optional[datetime] = None, intent_detected: Optional[str] = None) -> bool:
        """Complete query execution tracking"""
        try:
            db_session = self.get_db_session()

            query_record = db_session.query(QueryModel).filter_by(query_id=query_id).first()
            if not query_record:
                db_session.close()
                return False

            # Update query record - use provided end_time or current time as fallback
            if end_time is None:
                end_time = datetime.now(timezone.utc)
            elif end_time.tzinfo is None:
                # Ensure end_time is timezone-aware
                end_time = end_time.replace(tzinfo=timezone.utc)

            query_record.end_time = end_time

            # Ensure start_time is timezone-aware for duration calculation
            start_time = query_record.start_time
            if start_time.tzinfo is None:
                start_time = start_time.replace(tzinfo=timezone.utc)

            query_record.total_duration_ms = int((end_time - start_time).total_seconds() * 1000)
            query_record.final_response = final_response
            query_record.success = success
            query_record.error_details = error_details

            # Set intent_detected if provided
            if intent_detected:
                query_record.intent_detected = intent_detected

            # Get agents used from execution steps
            agents_used = db_session.query(AgentExecutionStepModel.agent_name).filter_by(
                query_id=query_id
            ).distinct().all()
            query_record.agents_used = [agent[0] for agent in agents_used]

            # Calculate total tokens used by aggregating from execution steps
            execution_steps = db_session.query(AgentExecutionStepModel).filter_by(query_id=query_id).all()
            total_tokens = {"input": 0, "output": 0, "total": 0}

            for step in execution_steps:
                if step.tokens_used:
                    for key in ["input", "output", "total"]:
                        if key in step.tokens_used:
                            total_tokens[key] += step.tokens_used[key]

            query_record.total_tokens_used = total_tokens

            db_session.commit()
            db_session.close()

            logger.info(f"Completed tracking query {query_id}")
            return True

        except Exception as e:
            logger.error(f"Error completing query tracking: {e}")
            if 'db_session' in locals():
                db_session.rollback()
                db_session.close()
            return False

    async def get_query_execution_data(self, query_id: str) -> Optional[QueryExecutionData]:
        """Retrieve complete query execution data"""
        try:
            db_session = self.get_db_session()

            query_record = db_session.query(QueryModel).filter_by(query_id=query_id).first()
            if not query_record:
                db_session.close()
                return None

            # Get execution steps
            execution_steps = db_session.query(AgentExecutionStepModel).filter_by(
                query_id=query_id
            ).order_by(AgentExecutionStepModel.start_time).all()

            db_session.close()

            # Convert to AgentExecutionStep objects
            steps = []
            for step_record in execution_steps:
                step = AgentExecutionStep(
                    agent_name=step_record.agent_name,
                    step_type=step_record.step_type,
                    start_time=step_record.start_time,
                    end_time=step_record.end_time,
                    duration_ms=step_record.duration_ms,
                    input_prompt=step_record.input_prompt,
                    output_response=step_record.output_response,
                    model_used=step_record.model_used,
                    tokens_used=step_record.tokens_used,
                    success=step_record.success,
                    error_message=step_record.error_details,
                    metadata=step_record.step_metadata
                )
                steps.append(step)

            # Process final_response to convert S3 keys to URLs
            processed_final_response = query_record.final_response or ""
            if processed_final_response:
                try:
                    from tools.store_s3 import process_s3_keys_to_urls
                    processed_final_response = process_s3_keys_to_urls(processed_final_response, expires_in=7200)  # 2 hours
                    logger.info(f"Processed S3 keys in final_response for query {query_record.query_id}")
                except Exception as e:
                    logger.error(f"Error processing S3 keys in final_response: {e}")
                    # Keep original response if processing fails
                    processed_final_response = query_record.final_response or ""

            # Create QueryExecutionData object
            query_data = QueryExecutionData(
                query_id=query_record.query_id,
                user_id=query_record.user_id,
                session_id=query_record.session_id,
                original_query=query_record.original_query,
                start_time=query_record.start_time,
                end_time=query_record.end_time,
                total_duration_ms=query_record.total_duration_ms,
                final_response=processed_final_response,
                intent_detected=query_record.intent_detected,
                execution_steps=steps,
                agents_used=query_record.agents_used or [],
                total_tokens_used=query_record.total_tokens_used or {},
                success=query_record.success,
                error_details=query_record.error_details
            )

            return query_data

        except Exception as e:
            logger.error(f"Error retrieving query execution data: {e}")
            if 'db_session' in locals():
                db_session.close()
            return None

    # ============================================================================
    # SESSION MANAGEMENT METHODS
    # ============================================================================

    async def create_session(self, session_id: str, user_id: str,
                           session_name: Optional[str] = None) -> SessionMetadata:
        """Create a new session or return existing one if session_id already exists"""
        try:
            db_session = self.get_db_session()

            # First check if session already exists
            existing_session = db_session.query(SessionModel).filter_by(session_id=session_id).first()
            if existing_session:
                logger.info(f"Session {session_id} already exists, returning existing session")

                # Convert existing session to SessionMetadata
                session_metadata = SessionMetadata(
                    session_id=existing_session.session_id,
                    user_id=existing_session.user_id,
                    session_name=existing_session.session_name,
                    creation_time=existing_session.creation_time,
                    last_activity_time=existing_session.last_activity_time,
                    total_queries=existing_session.total_queries,
                    query_ids=[],
                    session_summary=existing_session.session_summary,
                    total_tokens_used=existing_session.total_tokens_used or {},
                    feedback_count=existing_session.feedback_count,
                    positive_feedback_count=existing_session.positive_feedback_count,
                    negative_feedback_count=existing_session.negative_feedback_count
                )

                db_session.close()
                return session_metadata

            # Create new session if it doesn't exist
            if not session_name:
                session_name = f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"

            session_record = SessionModel(
                session_id=session_id,
                user_id=user_id,
                session_name=session_name,
                creation_time=datetime.now(timezone.utc),
                last_activity_time=datetime.now(timezone.utc)
            )

            db_session.add(session_record)
            db_session.commit()

            # Convert to SessionMetadata object before closing session
            session_metadata = SessionMetadata(
                session_id=session_record.session_id,
                user_id=session_record.user_id,
                session_name=session_record.session_name,
                creation_time=session_record.creation_time,
                last_activity_time=session_record.last_activity_time,
                total_queries=session_record.total_queries,
                query_ids=[],
                session_summary=session_record.session_summary,
                total_tokens_used=session_record.total_tokens_used or {},
                feedback_count=session_record.feedback_count,
                positive_feedback_count=session_record.positive_feedback_count,
                negative_feedback_count=session_record.negative_feedback_count
            )

            db_session.close()

            logger.info(f"Created new session {session_id}")
            return session_metadata

        except Exception as e:
            logger.error(f"Error creating session: {e}")
            if 'db_session' in locals():
                db_session.rollback()
                db_session.close()
            raise

    async def get_session_metadata(self, session_id: str) -> Optional[SessionMetadata]:
        """Retrieve session metadata"""
        try:
            db_session = self.get_db_session()

            session_record = db_session.query(SessionModel).filter_by(session_id=session_id).first()
            if not session_record:
                db_session.close()
                return None

            # Get query IDs for this session
            query_ids = db_session.query(QueryModel.query_id).filter_by(
                session_id=session_id
            ).order_by(QueryModel.start_time).all()

            db_session.close()

            # Convert to SessionMetadata object
            session_metadata = SessionMetadata(
                session_id=session_record.session_id,
                user_id=session_record.user_id,
                session_name=session_record.session_name,
                creation_time=session_record.creation_time,
                last_activity_time=session_record.last_activity_time,
                total_queries=session_record.total_queries,
                query_ids=[query_id[0] for query_id in query_ids],
                session_summary=session_record.session_summary,
                total_tokens_used=session_record.total_tokens_used or {},
                feedback_count=session_record.feedback_count,
                positive_feedback_count=session_record.positive_feedback_count,
                negative_feedback_count=session_record.negative_feedback_count
            )

            return session_metadata

        except Exception as e:
            logger.error(f"Error retrieving session metadata: {e}")
            if 'db_session' in locals():
                db_session.close()
            return None

    async def update_session_name(self, session_id: str, new_name: str) -> bool:
        """Update session name"""
        try:
            db_session = self.get_db_session()

            session_record = db_session.query(SessionModel).filter_by(session_id=session_id).first()
            if not session_record:
                db_session.close()
                return False

            session_record.session_name = new_name
            db_session.commit()
            db_session.close()

            logger.info(f"Updated session name for {session_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating session name: {e}")
            if 'db_session' in locals():
                db_session.rollback()
                db_session.close()
            return False

    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[SessionMetadata]:
        """Get all sessions for a user"""
        try:
            db_session = self.get_db_session()

            session_records = db_session.query(SessionModel).filter_by(
                user_id=user_id
            ).order_by(desc(SessionModel.last_activity_time)).limit(limit).all()

            db_session.close()

            sessions = []
            for record in session_records:
                session_metadata = SessionMetadata(
                    session_id=record.session_id,
                    user_id=record.user_id,
                    session_name=record.session_name,
                    creation_time=record.creation_time,
                    last_activity_time=record.last_activity_time,
                    total_queries=record.total_queries,
                    query_ids=[],  # Don't load query IDs for list view
                    session_summary=record.session_summary,
                    total_tokens_used=record.total_tokens_used or {},
                    feedback_count=record.feedback_count,
                    positive_feedback_count=record.positive_feedback_count,
                    negative_feedback_count=record.negative_feedback_count
                )
                sessions.append(session_metadata)

            return sessions

        except Exception as e:
            logger.error(f"Error retrieving user sessions: {e}")
            if 'db_session' in locals():
                db_session.close()
            return []

    async def get_session_with_queries(self, session_id: str):
        """Get session metadata with all query details including related queries"""
        try:
            session_metadata = await self.get_session_metadata(session_id)
            if not session_metadata:
                return None

            db_session = self.get_db_session()

            # Get all queries for this session with their execution steps
            query_records = db_session.query(QueryModel).filter_by(
                session_id=session_id
            ).order_by(QueryModel.start_time).all()

            # Get all related queries for this session first
            from database_models import RelatedQueriesModel
            related_queries_records = db_session.query(RelatedQueriesModel).filter_by(
                session_id=session_id
            ).order_by(RelatedQueriesModel.timestamp.desc()).all()

            # Create a mapping of query_id to related queries
            related_queries_map = {}
            for related_record in related_queries_records:
                related_queries_map[related_record.query_id] = related_record.related_queries

            logger.info(f"Retrieved {len(related_queries_records)} related query records for session {session_id}")

            query_details = []
            for query_record in query_records:
                # Get execution steps for this query
                execution_steps = db_session.query(AgentExecutionStepModel).filter_by(
                    query_id=query_record.query_id
                ).order_by(AgentExecutionStepModel.start_time).all()

                # Convert to AgentExecutionStep objects
                steps = []
                for step_record in execution_steps:
                    step = AgentExecutionStep(
                        agent_name=step_record.agent_name,
                        step_type=step_record.step_type,
                        start_time=step_record.start_time,
                        end_time=step_record.end_time,
                        duration_ms=step_record.duration_ms,
                        input_prompt=step_record.input_prompt,
                        output_response=step_record.output_response,
                        model_used=step_record.model_used,
                        tokens_used=step_record.tokens_used,
                        success=step_record.success,
                        error_message=step_record.error_details,
                        metadata=step_record.step_metadata
                    )
                    steps.append(step)

                # Get related queries for this specific query
                query_related_queries = related_queries_map.get(query_record.query_id, [])
                logger.info(f"Query {query_record.query_id} has {len(query_related_queries)} related queries: {query_related_queries}")

                # Process final_response to convert S3 keys to URLs
                processed_final_response = query_record.final_response or ""
                if processed_final_response:
                    try:
                        from tools.store_s3 import process_s3_keys_to_urls
                        processed_final_response = process_s3_keys_to_urls(processed_final_response, expires_in=7200)  # 2 hours
                        logger.info(f"Processed S3 keys in final_response for query {query_record.query_id}")
                    except Exception as e:
                        logger.error(f"Error processing S3 keys in final_response: {e}")
                        # Keep original response if processing fails
                        processed_final_response = query_record.final_response or ""

                # Create QueryExecutionData object
                query_data = QueryExecutionData(
                    query_id=query_record.query_id,
                    user_id=query_record.user_id,
                    session_id=query_record.session_id,
                    original_query=query_record.original_query,
                    start_time=query_record.start_time,
                    end_time=query_record.end_time,
                    total_duration_ms=query_record.total_duration_ms,
                    final_response=processed_final_response,
                    intent_detected=query_record.intent_detected,
                    execution_steps=steps,
                    agents_used=query_record.agents_used or [],
                    total_tokens_used=query_record.total_tokens_used or {},
                    success=query_record.success,
                    error_details=query_record.error_details,
                    related_queries=query_related_queries  # Include related queries directly in the model
                )

                logger.info(f"Created QueryExecutionData for {query_record.query_id} with related_queries: {query_data.related_queries}")
                query_details.append(query_data)

            db_session.close()

            return {
                "session_metadata": session_metadata,
                "query_details": query_details
            }

        except Exception as e:
            logger.error(f"Error retrieving session with queries: {e}")
            if 'db_session' in locals():
                db_session.close()
            return None

    # ============================================================================
    # PRIVATE HELPER METHODS
    # ============================================================================

    async def _update_session_feedback_counts(self, db_session: Session, session_id: str):
        """Update session feedback counts"""
        try:
            # Count feedback for this session
            feedback_counts = db_session.query(
                func.count(FeedbackModel.id).label('total'),
                func.sum(case((FeedbackModel.vote > 0, 1), else_=0)).label('positive'),
                func.sum(case((FeedbackModel.vote < 0, 1), else_=0)).label('negative')
            ).filter_by(session_id=session_id).first()

            # Update session record
            session_record = db_session.query(SessionModel).filter_by(session_id=session_id).first()
            if session_record:
                session_record.feedback_count = feedback_counts.total or 0
                session_record.positive_feedback_count = feedback_counts.positive or 0
                session_record.negative_feedback_count = feedback_counts.negative or 0

        except Exception as e:
            logger.error(f"Error updating session feedback counts: {e}")

    async def _update_session_activity(self, db_session: Session, session_id: str):
        """Update session's last activity time and query count"""
        try:
            session_record = db_session.query(SessionModel).filter_by(session_id=session_id).first()
            if session_record:
                session_record.last_activity_time = datetime.now(timezone.utc)
                session_record.total_queries += 1

        except Exception as e:
            logger.error(f"Error updating session activity: {e}")

    # ============================================================================
    # ANALYTICS AND PERFORMANCE METHODS
    # ============================================================================

    # Agent performance metrics removed - can be calculated from AgentExecutionStepModel data when needed