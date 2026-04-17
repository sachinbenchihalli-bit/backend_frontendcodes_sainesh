from typing import Dict, Any, Optional, List, Union
import time
from datetime import datetime, timezone
import asyncio
import json
from execution_tracker import execution_tracker

class LLMTracker:
    """Wrapper to track all LLM API calls to the database"""

    @staticmethod
    async def track_llm_call(
        query_id: str,
        agent_name: str,
        messages: Union[List[Dict[str, str]], str],
        model_name: str,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        step_type: str = "response_generation"  # Changed from "llm_call" to "response_generation"
    ):
        """
        Creates a tracking context manager for LLM API calls

        Args:
            query_id: The query ID being processed
            agent_name: Name of the agent making the call
            messages: Either a list of message dicts (role/content) or a single string prompt
            model_name: The model being used
            session_id: Optional session ID
            user_id: Optional user ID
            step_type: Type of step being tracked

        Returns a context manager that will track the LLM call
        and automatically record the response and timing information
        """
        # Process messages to extract system prompt and user query
        system_prompt = ""
        user_query = ""

        # Format the input for storage
        if isinstance(messages, list):
            # Extract system prompt and user query from messages list
            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", "")
                elif msg.get("role") == "user":
                    user_query = msg.get("content", "")

            # Store the full messages as JSON for complete record
            formatted_input = json.dumps(messages)
        else:
            # If it's a single string, treat it as system prompt
            system_prompt = messages
            formatted_input = messages

        # Store metadata about the messages
        metadata = {
            "has_system_prompt": bool(system_prompt),
            "has_user_query": bool(user_query),
            "message_count": len(messages) if isinstance(messages, list) else 1
        }

        # Return the context manager to track this step
        return execution_tracker.track_agent_step(
            query_id=query_id,
            agent_name=agent_name,
            step_type=step_type,
            input_prompt=formatted_input,
            model_used=model_name
        )

    @staticmethod
    async def log_completion(
        query_id: str,
        agent_name: str,
        messages: Union[List[Dict[str, str]], str],
        response: str,
        model_name: str,
        tokens: Optional[Dict[str, int]] = None,
        session_id: Optional[str] = None,
        user_id: Optional[str] = None,
        step_type: str = "llm_call"
    ):
        """
        Log a completed LLM call (for cases where context manager isn't suitable)

        Args:
            query_id: The query ID being processed
            agent_name: Name of the agent making the call
            messages: Either a list of message dicts (role/content) or a single string prompt
            response: The response from the LLM
            model_name: The model being used
            tokens: Token usage information
            session_id: Optional session ID
            user_id: Optional user ID
            step_type: Type of step being tracked
        """
        async with LLMTracker.track_llm_call(
            query_id=query_id,
            agent_name=agent_name,
            messages=messages,
            model_name=model_name,
            session_id=session_id,
            user_id=user_id,
            step_type=step_type
        ) as step:
            step.set_output(response)
            if tokens:
                step.set_tokens(tokens)

# Create a singleton instance
llm_tracker = LLMTracker()

