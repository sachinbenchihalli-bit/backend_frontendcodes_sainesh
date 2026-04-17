"""
Utility functions for working with LLMs.
"""
import json
import logging
import os
import asyncio
import uuid
from typing import List, Type, Dict, Any, Optional, TypeVar, Generic, Union
from pydantic import BaseModel, ValidationError
from openai import OpenAI
from model import ConversationPayload

# Configure logging
logger = logging.getLogger(__name__)

# Initialize OpenAI client
try:
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    client = None

# Type variable for the response class
T = TypeVar('T', bound=BaseModel)

async def generate_response(
    query: str,
    system_prompt: str,
    conversation_history: List[ConversationPayload] = None,
    max_tokens: int = 1000,
    response_class: Type[T] = None,
    model: str = "gpt-4o-mini",
    query_id: Optional[str] = None,
    agent_name: Optional[str] = None
) -> Union[str, T]:
    """
    Generate a response from the LLM.

    Args:
        query (str): The user's query
        system_prompt (str): The system prompt to use
        conversation_history (List[ConversationPayload], optional): Previous conversation messages
        max_tokens (int, optional): Maximum number of tokens to generate
        response_class (Type[T], optional): Pydantic model class for the response
        model (str, optional): The model to use
        query_id (Optional[str], optional): Query ID for tracking
        agent_name (Optional[str], optional): Agent name for tracking

    Returns:
        Union[str, T]: The generated response, either as a string or a Pydantic model
    """
    global client
    # Use provided query_id or get from current task or generate new one
    query_id = query_id or getattr(asyncio.current_task(), "query_id", str(uuid.uuid4()))
    logger.info(f"Query ID in generate_response: {query_id}")
    # Use provided agent_name or get from current task or use default
    agent_name = agent_name or getattr(asyncio.current_task(), "agent_name", "generate_response")

    # Handle empty query
    if not query or query.strip() == "":
        logger.warning("Empty query provided to generate_response")
        if response_class:
            # For SearchPlannerOutput, create a default instance
            if response_class.__name__ == "SearchPlannerOutput":
                from model import SearchStep
                return response_class(
                    steps=[
                        SearchStep(
                            step_type="semantic_search",
                            description="Default semantic search for empty query with default sorting by conversion rate",
                            parameters={
                                "sort_field": "conversion",
                                "sort_order": "desc"
                            }
                        )
                    ],
                    search_type="semantic_only",
                    limit=10
                )
            # For other response classes, return an empty instance
            return response_class()
        return "Error: Empty query provided"

    # Prepare messages for the LLM
    messages = [
        {"role": "system", "content": system_prompt}
    ]
    
    # Add conversation history if provided
    if conversation_history:
        for message in conversation_history:
            messages.append({"role": message.actor, "content": message.content})
    
    # Add the current query
    messages.append({"role": "user", "content": query})
    
    try:
        # Track the LLM call
        from llm_tracker import llm_tracker
        async with await llm_tracker.track_llm_call(
            query_id=query_id,
            agent_name=agent_name,
            messages=messages,
            model_name=model
        ) as step:
            # Make the API call
            response = client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens
            )
            
            # Extract the response text
            response_text = response.choices[0].message.content
            
            # Record token usage
            tokens = {
                "input": response.usage.prompt_tokens,
                "output": response.usage.completion_tokens,
                "total": response.usage.total_tokens
            }
            
            # Update the tracking step with results
            step.set_output(response_text)
            step.set_tokens(tokens)
            
            # Parse into response class if needed
            if response_class:
                try:
                    # Try to parse as JSON first
                    parsed_data = json.loads(response_text)
                    return response_class(**parsed_data)
                except (json.JSONDecodeError, ValidationError):
                    # If not valid JSON or doesn't match schema, try direct parsing
                    try:
                        return response_class.parse_raw(response_text)
                    except:
                        # Last resort: try to extract structured data from text
                        logger.warning(f"Failed to parse response as {response_class.__name__}, returning raw text")
                        return response_text
            
            return response_text
            
    except Exception as e:
        logger.error(f"Error in generate_response: {str(e)}")
        if response_class:
            try:
                return response_class()
            except:
                return f"Error: {str(e)}"
        return f"Error: {str(e)}"
