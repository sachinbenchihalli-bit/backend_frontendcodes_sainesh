"""
Execution Tracker for Agent Performance Monitoring

This module provides a context manager and utilities for tracking
agent execution during the inference process.
"""

import logging
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
from contextlib import asynccontextmanager

from model import AgentExecutionStep, QueryExecutionData
from session_feedback_manager import SessionFeedbackManager

logger = logging.getLogger(__name__)

class ExecutionTracker:
    """Tracks agent execution steps and performance metrics"""

    def __init__(self):
        self.manager = SessionFeedbackManager()
        self.current_query_data: Optional[QueryExecutionData] = None

    async def start_query_execution(self, query_id: str, user_id: str, session_id: str,
                                  original_query: str) -> QueryExecutionData:
        """Start tracking a new query execution"""
        try:
            self.current_query_data = await self.manager.start_query_tracking(
                query_id=query_id,
                user_id=user_id,
                session_id=session_id,
                original_query=original_query
            )

            logger.info(f"Started execution tracking for query {query_id}")
            return self.current_query_data

        except Exception as e:
            logger.error(f"Error starting query execution tracking: {e}")
            raise

    async def complete_query_execution(self, query_id: str, final_response: str,
                                     success: bool = True, error_details: Optional[str] = None,
                                     end_time: Optional[datetime] = None, intent_detected: Optional[str] = None):
        """Complete query execution tracking"""
        try:
            await self.manager.complete_query_tracking(
                query_id=query_id,
                final_response=final_response,
                success=success,
                error_details=error_details,
                end_time=end_time,
                intent_detected=intent_detected
            )

            logger.info(f"Completed execution tracking for query {query_id}")

        except Exception as e:
            logger.error(f"Error completing query execution tracking: {e}")

    @asynccontextmanager
    async def track_agent_step(self, query_id: str, agent_name: str, step_type: str,
                             input_prompt: str, model_used: str = "gpt-4o-mini"):
        """
        Context manager for tracking individual agent execution steps

        Usage:
            async with tracker.track_agent_step(query_id, "campaign_performance", "agent_processing", prompt) as step:
                # Agent execution code here
                result = await some_agent_function()
                step.set_output(result)
                step.set_tokens({"input": 100, "output": 200})
        """

        logger.info(f"Creating agent execution step for query {query_id}, agent {agent_name}, step_type {step_type}")

        step = AgentExecutionStep(
            agent_name=agent_name,
            step_type=step_type,
            start_time=datetime.now(),
            input_prompt=input_prompt,
            output_response="",
            model_used=model_used
        )

        step_tracker = AgentStepTracker(step, self.manager, query_id)

        try:
            yield step_tracker

            # Mark as successful if no exception occurred
            step.success = True
            step.end_time = datetime.now()

            # Calculate duration
            if step.start_time and step.end_time:
                duration_ms = int((step.end_time - step.start_time).total_seconds() * 1000)
                step.duration_ms = duration_ms
                logger.info(f"Agent step {agent_name} completed in {duration_ms}ms")

            # Save the step
            logger.info(f"Saving agent execution step for query {query_id}, agent {agent_name}")
            await self.manager.add_agent_execution_step(query_id, step)
            logger.info(f"Successfully saved agent execution step for query {query_id}, agent {agent_name}")

        except Exception as e:
            # Mark as failed and capture error
            step.success = False
            step.error_message = str(e)
            step.end_time = datetime.now()

            # Calculate duration for failed step
            if step.start_time and step.end_time:
                duration_ms = int((step.end_time - step.start_time).total_seconds() * 1000)
                step.duration_ms = duration_ms

            logger.error(f"Agent step {agent_name} failed: {e}")

            # Save the failed step
            try:
                await self.manager.add_agent_execution_step(query_id, step)
                logger.info(f"Saved failed agent execution step for query {query_id}, agent {agent_name}")
            except Exception as save_error:
                logger.error(f"Failed to save failed agent step: {save_error}")

            # Re-raise the exception
            raise

    async def track_intent_detection(self, query_id: str, input_query: str,
                                   detected_intent: str, model_used: str = "gpt-4o-mini"):
        """Track intent detection step"""
        async with self.track_agent_step(
            query_id=query_id,
            agent_name="intent_detector",
            step_type="intent_detection",
            input_prompt=input_query,
            model_used=model_used
        ) as step:
            step.set_output(f"Detected intent: {detected_intent}")
            step.set_metadata({"detected_intent": detected_intent})

    async def track_search_planning(self, query_id: str, input_query: str,
                                  search_plan: str, model_used: str = "gpt-4o-mini"):
        """Track search planning step"""
        async with self.track_agent_step(
            query_id=query_id,
            agent_name="search_planner",
            step_type="search_planning",
            input_prompt=input_query,
            model_used=model_used
        ) as step:
            step.set_output(search_plan)

    async def track_search_execution(self, query_id: str, search_query: str,
                                   results_count: int, search_type: str = "qdrant"):
        """Track search execution step"""
        async with self.track_agent_step(
            query_id=query_id,
            agent_name="search_executor",
            step_type="search_execution",
            input_prompt=search_query,
            model_used="N/A"
        ) as step:
            step.set_output(f"Retrieved {results_count} results")
            step.set_metadata({
                "results_count": results_count,
                "search_type": search_type
            })

class AgentStepTracker:
    """Helper class for tracking individual agent steps"""

    def __init__(self, step: AgentExecutionStep, manager: SessionFeedbackManager, query_id: str):
        self.step = step
        self.manager = manager
        self.query_id = query_id
        logger.debug(f"Created AgentStepTracker for {step.agent_name} in query {query_id}")

    def set_output(self, output_response: str):
        """Set the output response for this step"""
        if output_response:
            truncated = output_response[:100] + "..." if len(output_response) > 100 else output_response
            logger.debug(f"Setting output for {self.step.agent_name}: {truncated}")
        else:
            logger.warning(f"Empty output for {self.step.agent_name}")
        self.step.output_response = output_response

    def set_tokens(self, tokens_used: Dict[str, int]):
        """Set token usage for this step"""
        logger.debug(f"Setting tokens for {self.step.agent_name}: {tokens_used}")
        self.step.tokens_used = tokens_used

    def set_metadata(self, metadata: Dict[str, Any]):
        """Set additional metadata for this step"""
        logger.debug(f"Setting metadata for {self.step.agent_name}")
        self.step.metadata = metadata

    def set_model(self, model_used: str):
        """Set the model used for this step"""
        logger.debug(f"Setting model for {self.step.agent_name}: {model_used}")
        self.step.model_used = model_used

    def set_error(self, error_message: str):
        """Set error message for this step"""
        logger.error(f"Setting error for {self.step.agent_name}: {error_message}")
        self.step.success = False
        self.step.error_message = error_message

# ============================================================================
# INTEGRATION HELPERS
# ============================================================================

class InferenceIntegration:
    """Integration helpers for the main inference pipeline"""

    def __init__(self):
        self.tracker = ExecutionTracker()

    async def wrap_agent_call(self, query_id: str, agent_name: str, agent_function,
                            input_prompt: str, *args, **kwargs):
        """
        Wrapper for agent function calls that automatically tracks execution

        Args:
            query_id: The query ID being processed
            agent_name: Name of the agent being called
            agent_function: The agent function to call
            input_prompt: The input prompt being sent to the agent
            *args, **kwargs: Arguments to pass to the agent function

        Returns:
            The result from the agent function
        """
        async with self.tracker.track_agent_step(
            query_id=query_id,
            agent_name=agent_name,
            step_type="agent_processing",
            input_prompt=input_prompt
        ) as step:

            # Call the agent function
            result = await agent_function(*args, **kwargs)

            # Set the output - store full response without truncation
            if isinstance(result, str):
                step.set_output(result)
            else:
                step.set_output(str(result))

            return result

    async def track_llm_call(self, query_id: str, agent_name: str, prompt: str,
                           response: str, tokens_used: Optional[Dict[str, int]] = None,
                           model_used: str = "gpt-4o-mini"):
        """
        Track a direct LLM call

        Args:
            query_id: The query ID being processed
            agent_name: Name of the agent making the call
            prompt: The prompt sent to the LLM
            response: The response from the LLM
            tokens_used: Token usage information
            model_used: The model that was used
        """
        async with self.tracker.track_agent_step(
            query_id=query_id,
            agent_name=agent_name,
            step_type="response_generation",
            input_prompt=prompt,
            model_used=model_used
        ) as step:

            step.set_output(response)  # Store full response without truncation

            if tokens_used:
                step.set_tokens(tokens_used)

# ============================================================================
# GLOBAL TRACKER INSTANCE
# ============================================================================

# Global tracker instance for use throughout the application
execution_tracker = ExecutionTracker()
inference_integration = InferenceIntegration()


