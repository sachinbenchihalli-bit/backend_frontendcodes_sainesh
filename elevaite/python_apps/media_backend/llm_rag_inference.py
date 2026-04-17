from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range, MatchValue, MatchAny
from fastapi import HTTPException
import io
from typing import Dict, Any, List, Callable
from openai import OpenAI
from model import ImageModelDecider, AdCreative, CampaignPerformanceReport, CampaignPerformanceAgentOutput, SearchResult, InferencePayload, ConversationPayload, IntentOutput, MediaPlanOutput, CreativeInsightsReport, Related_Queries, QdrantSearchParams , PreviousSearchContext, SearchStepResult # Commented out unused imports: ImageAgentOutputV2, ImageAgentOutput, MessageData, AnalysisOfTrends, PerformanceSummary, MediaPlanSearchResult, MediaPlanCreative
import os
import sys
from database_services import CampaignService
import re
from dotenv import load_dotenv
import json
from typing import List, Type, Dict, Any, Optional, AsyncGenerator
from pydantic import BaseModel
import base64
import time
import requests
import asyncio
import uuid
from prompts.prompts import SystemPrompts
from sentence_transformers import CrossEncoder
from collections import OrderedDict
from cache_control import CacheControl
from sqlalchemy.orm import Session  # Import Session
# from postgresreader import read_campaigns
from db_connector import db_connector
# from validators.output_validators import media_plan_validator
from tools.budget_tool import Budget_tool
from tools.store_s3 import upload_to_s3
from datetime import date, datetime, timezone
from google import genai
from google.genai import types
from vertexai.generative_models import GenerativeModel, Image as VertexImage
import vertexai
from io import BytesIO
# from PIL import Image
from PIL import Image as PIL_Image
from google.genai.types import (
    RawReferenceImage,
    MaskReferenceImage,
    Image,
    EditImageConfig,
    MaskReferenceConfig
)
from google.oauth2 import service_account
from google.auth.transport.requests import Request
import logging
from iab_size_generator import BlackforestIABGenerator
PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")
SERVICE_ACCOUNT_KEY_PATH = os.getenv("SERVICE_ACCOUNT_KEY_PATH")
vertexai.init(project=PROJECT_ID, location=LOCATION)

# Timer and logging
def setup_logging(log_level=logging.INFO):
    """
    Configure logging with the specified log level.
    Default level is INFO to reduce verbosity while still showing important information.

    Args:
        log_level: The logging level to use (default: logging.INFO)

    Returns:
        A configured logger instance
    """
    # Remove any existing handlers from root logger
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Configure root logger
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )

    # Get the module logger
    logger = logging.getLogger(__name__)

    # Set a specific level for this module's logger
    logger.setLevel(log_level)

    return logger

# Initialize logger with INFO level by default
# To enable DEBUG logging, change this to setup_logging(logging.DEBUG)
# logger = setup_logging()
logger = setup_logging()
try:
    cache_control = CacheControl()
except Exception as e:
    logger.error(f"Error initializing Redis Cache: {e}")
try:
    reranker = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2",tokenizer_args={'clean_up_tokenization_spaces': True})
except Exception as e:
    logger.error(f"Error initializing reranker: {e}")

def timer_decorator(func):
    """
    Decorator that logs the execution time of functions.
    For functions that take longer than 1 second, logs at INFO level.
    For faster functions, logs at DEBUG level to reduce noise.
    Always logs errors at ERROR level.
    """
    async def async_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = await func(*args, **kwargs)
            end = time.perf_counter()
            duration = end - start
            # Only log at INFO level if the function took more than 1 second
            if duration > 1.0:
                logger.info(f"{func.__name__} completed in {duration:.2f}s")
            else:
                logger.debug(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            end = time.perf_counter()
            logger.error(f"{func.__name__} failed after {end - start:.2f}s: {str(e)[:200]}")
            raise

    def sync_wrapper(*args, **kwargs):
        start = time.perf_counter()
        try:
            result = func(*args, **kwargs)
            end = time.perf_counter()
            duration = end - start
            # Only log at INFO level if the function took more than 1 second
            if duration > 1.0:
                logger.info(f"{func.__name__} completed in {duration:.2f}s")
            else:
                logger.debug(f"{func.__name__} completed in {duration:.2f}s")
            return result
        except Exception as e:
            end = time.perf_counter()
            logger.error(f"{func.__name__} failed after {end - start:.2f}s: {str(e)[:200]}")
            raise

    if asyncio.iscoroutinefunction(func):
        return async_wrapper
    else:
        return sync_wrapper


def load_prompt(prompt_name):
    """
    Fetches the prompt by name from the SystemPrompts class.
    Args:
        prompt_name (str): The name of the prompt to retrieve.
    Returns:
        str: The prompt text, or an error message if not found.
    """
    return SystemPrompts.get_prompt(prompt_name)

# Load environment variables
load_dotenv()

# Initialize Qdrant client
try:
    Qclient = QdrantClient(
        os.getenv("QDRANT_HOST", "localhost"),
        port=int(os.getenv("QDRANT_PORT", 5333))
    )
except Exception as e:
    logger.error(f"Error initializing Qdrant client: {e}")
    Qclient = None

# Initialize OpenAI client
try:
    client = OpenAI(
        api_key=os.environ.get("OPENAI_API_KEY"),
    )
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    client = None

try:
    Googleclient = genai.Client(api_key=os.environ.get("GEMINI_KEY"))
except Exception as e:
    logger.error(f"Error initializing OpenAI client: {e}")
    client = None

# @timer_decorator
def get_embedding(text, query_id: Optional[str] = None):
    try:
        # For synchronous functions, we'll track manually without context manager
        if query_id:
            from execution_tracker import execution_tracker
            from model import AgentExecutionStep
            from datetime import datetime
            import asyncio

            # Create step manually for synchronous tracking
            step_data = AgentExecutionStep(
                agent_name="embedding_generator",
                step_type="agent_processing",
                start_time=datetime.now(),
                input_prompt=f"Text: {text}",
                output_response="",
                model_used="text-embedding-ada-002"
            )

            try:
                response = client.embeddings.create(
                    input=text,
                    model="text-embedding-ada-002"
                )

                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    tokens = {
                        "input": response.usage.prompt_tokens,
                        "output": 0,  # Embeddings don't have completion tokens
                        "total": response.usage.total_tokens
                    }
                    step_data.tokens_used = tokens
                    logger.debug(f"Token usage tracked for get_embedding: {tokens}")

                # Set output for tracking
                step_data.output_response = f"Generated embedding with {len(response.data[0].embedding)} dimensions"
                step_data.success = True
                step_data.end_time = datetime.now()

                # Calculate duration
                if step_data.start_time and step_data.end_time:
                    duration_ms = int((step_data.end_time - step_data.start_time).total_seconds() * 1000)
                    step_data.duration_ms = duration_ms

                # Save step asynchronously (fire and forget)
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, schedule the save
                        asyncio.create_task(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                    else:
                        # If not in async context, run it
                        asyncio.run(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                except Exception as save_error:
                    logger.warning(f"Failed to save embedding step tracking: {save_error}")

                return response.data[0].embedding
            except Exception as e:
                step_data.success = False
                step_data.error_message = str(e)
                step_data.end_time = datetime.now()
                logger.error(f"Error in get_embedding with tracking: {e}")
                raise
        else:
            # Fallback without tracking
            response = client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return None

# Function to get access token using service account
def get_access_token():
    """Get access token using service account credentials"""
    if not os.path.exists(SERVICE_ACCOUNT_KEY_PATH):
        logger.error(f"Service account key file not found at: {SERVICE_ACCOUNT_KEY_PATH}")
        raise FileNotFoundError(f"Service account key file not found at: {SERVICE_ACCOUNT_KEY_PATH}")

    logger.debug(f"Using service account key from: {SERVICE_ACCOUNT_KEY_PATH}")
    try:
        credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_KEY_PATH,
            scopes=["https://www.googleapis.com/auth/cloud-platform"]
        )
        credentials.refresh(Request())
        return credentials.token
    except Exception as e:
        logger.error(f"Error getting access token: {e}")
        raise

@timer_decorator
def rerank_results(query_text: str, results: List[AdCreative], enriched_query_text: str) -> List[AdCreative]:
    """Rerank results based on query relevance, considering dynamic contextual terms from the enriched query."""
    # Process the enriched query to detect key contextual terms (e.g., industries, product categories, etc.)
    # This should capture the terms from the enriched query dynamically without hardcoding
    try:
        # Log initial results before reranking
        logger.info(f"Reranking {len(results)} results")

        # Log top 5 initial results
        initial_top = []
        for i, creative in enumerate(results[:5]):
            initial_top.append({
                "position": i+1,
                "brand": creative.brand,
                "campaign": creative.campaign_folder,
                "industry_sectors": creative.industry_sectors,  # Updated field name
                "conversion": creative.conversion
            })
        logger.info(f"Initial top results before reranking: {json.dumps(initial_top, indent=2)}")

        enriched_query_terms = set(enriched_query_text.lower().split())
        logger.debug(f"Enriched query terms: {enriched_query_terms}")

        reranker_input = []
        for ad_creative in results:
            brand = ad_creative.brand or ""
            business_category = ad_creative.industry_sectors or ""  # Using industry_sectors field
            # Concatenate the enriched query with brand and business_category for better contextual matching
            reranker_input.append((enriched_query_text, f"{brand} {business_category}"))

        scores = reranker.predict(reranker_input)
        reranked_results = []

        # Track score details for logging
        score_details = []

        for ad_creative, score in zip(results, scores):
            # Check if any of the enriched query terms match the brand or business category
            industry_terms = set(ad_creative.industry_sectors.lower().split()) if ad_creative.industry_sectors else set()
            brand_terms = set(ad_creative.brand.lower().split()) if ad_creative.brand else set()

            # Check for overlap between the enriched query terms and the ad's brand/industry terms
            term_intersection = enriched_query_terms.intersection(industry_terms.union(brand_terms))
            relevance_bonus = len(term_intersection)

            # Combine the Cross-Encoder score with the relevance bonus
            final_score = score + relevance_bonus

            # Store score details for logging
            score_details.append({
                "brand": ad_creative.brand,
                "campaign": ad_creative.campaign_folder,
                "industry_sectors": ad_creative.industry_sectors,  # Updated field name
                "base_score": float(score),
                "relevance_bonus": relevance_bonus,
                "final_score": float(final_score),
                "matching_terms": list(term_intersection)
            })

            reranked_results.append((ad_creative, final_score))

        # Sort by final score (higher is better)
        reranked_results = sorted(reranked_results, key=lambda x: x[1], reverse=True)

        # Log detailed score information for top results
        logger.info(f"Reranking score details (top 5): {json.dumps(score_details[:5], indent=2)}")

        # Log top 5 reranked results
        reranked_top = []
        for i, (creative, score) in enumerate(reranked_results[:5]):
            reranked_top.append({
                "position": i+1,
                "brand": creative.brand,
                "campaign": creative.campaign_folder,
                "industry_sectors": creative.industry_sectors,  # Updated field name
                "conversion": creative.conversion,
                "score": float(score)
            })
        logger.info(f"Top results after reranking: {json.dumps(reranked_top, indent=2)}")

        # Log position changes for top results
        position_changes = []
        for i, (creative, _) in enumerate(reranked_results[:5]):
            try:
                # Find original position - try using id if available, otherwise use brand+campaign as a fallback
                if hasattr(creative, 'id') and creative.id:
                    original_pos = next((idx for idx, c in enumerate(results) if c.id == creative.id), -1)
                else:
                    # Fallback to using brand+campaign as a composite key
                    original_pos = next((idx for idx, c in enumerate(results)
                                        if c.brand == creative.brand and c.campaign_folder == creative.campaign_folder), -1)

                if original_pos != -1:
                    change = original_pos - i
                    position_changes.append({
                        "brand": creative.brand,
                        "campaign": creative.campaign_folder,
                        "old_position": original_pos + 1,
                        "new_position": i + 1,
                        "change": change
                    })
            except Exception as e:
                logger.debug(f"Error tracking position change for {creative.brand}: {e}")

        if position_changes:
            logger.info(f"Position changes after reranking: {json.dumps(position_changes, indent=2)}")

        return [result[0] for result in reranked_results]
    except Exception as e:
        logger.error(f"Error reranking results: {e}")
        return results

def get_past_vectors_for_topic(existing_data: List[dict], current_topic: str) -> List[dict]:
    """
    Retrieves vector data from past sessions that match the current topic.
    Args:
        existing_data (List[dict]): The past session data containing topics and vector data.
        current_topic (str): The current topic to match against past session topics.

    Returns:
        List[dict]: A list of vector data associated with similar campaigns in the past.
    """
    past_vectors = []
    for session in existing_data:
        if 'topic' in session and session['topic'] == current_topic:
            if 'vector_data' in session:
                past_vectors.extend(session['vector_data'])
    return past_vectors

def get_past_creative_data_for_topic(existing_data: List[dict], current_topic: str) -> List[dict]:
    """
    Retrieves creative data from past sessions that match the current topic.
    If current_topic is provided, it will prioritize creative data from that topic,
    but will still include all creative data from other topics as well.

    Args:
        existing_data (List[dict]): The past session data containing topics and creative data.
        current_topic (str): The current topic to match against past session topics.

    Returns:
        List[dict]: A list of creative data from past sessions.
    """
    past_creative_data = []
    topic_specific_creative_data = []
    other_creative_data = []

    logger.info(f"Getting past creative data for topic: {current_topic}")
    logger.debug(f"Existing Data: {existing_data}")

    for session in existing_data:
        if 'creative_data' in session and session['creative_data']:
            # Check if this session matches the current topic
            if current_topic and 'topic' in session and session['topic'] == current_topic:
                # Add to topic-specific list first (higher priority)
                topic_specific_creative_data.extend(session['creative_data'])
                logger.info(f"Found {len(session['creative_data'])} creative items from matching topic: {current_topic}")
            else:
                # Add to general list
                other_creative_data.extend(session['creative_data'])
                if 'topic' in session:
                    logger.info(f"Found {len(session['creative_data'])} creative items from other topic: {session.get('topic', 'unknown')}")

    # Combine the lists, with topic-specific data first
    past_creative_data = topic_specific_creative_data + other_creative_data

    # Log the total number of creative items found
    logger.info(f"Total past creative data items found: {len(past_creative_data)}")

    return past_creative_data

def get_creative_by_query_id(existing_data: List[dict], query_id: str) -> Optional[dict]:
    """
    Retrieves creative information associated with a specific query ID.

    Args:
        existing_data (List[dict]): The past session data containing query IDs and creative data.
        query_id (str): The query ID to search for.

    Returns:
        Optional[dict]: Creative information if found, None otherwise.
    """
    for session in existing_data:
        if 'query_id' in session and session['query_id'] == query_id:
            if 'creative_data' in session and session['creative_data']:
                # Return the first creative associated with this query
                return session['creative_data'][0]
    return None

def get_all_creatives_from_existing_data(existing_data: List[dict]) -> List[dict]:
    """
    Retrieves all creative information from existing session data.

    Args:
        existing_data (List[dict]): The past session data containing creative data.

    Returns:
        List[dict]: List of all creative information from the session data.
    """
    all_creatives = []

    # Extract all creatives from existing data
    for session in existing_data:
        if 'creative_data' in session and session['creative_data']:
            all_creatives.extend(session['creative_data'])

    return all_creatives

def get_all_past_creative_data(existing_data: List[dict]) -> List[dict]:
    """
    Retrieves ALL creative data from past sessions without any topic filtering.
    This is useful for image operations where we want to consider all previous creatives.

    Args:
        existing_data (List[dict]): The past session data containing creative data.

    Returns:
        List[dict]: A list of all creative data from past sessions.
    """
    all_creative_data = []

    logger.info("Getting ALL past creative data without topic filtering")

    for session in existing_data:
        if 'creative_data' in session and session['creative_data']:
            all_creative_data.extend(session['creative_data'])
            if 'topic' in session:
                logger.info(f"Found {len(session['creative_data'])} creative items from topic: {session.get('topic', 'unknown')}")

    # Log the total number of creative items found
    logger.info(f"Total past creative data items found (no topic filtering): {len(all_creative_data)}")

    return all_creative_data


def get_final_response_text(media_plan_output: str, creative_insights_output: str,
                          campaign_performance_output: str, general_response_string: str,
                          creative_data: List = None, session_data: dict = None) -> str:
    """
    Combines all output responses into a single final response text in the same markdown format sent to frontend.
    This ensures that when chats are loaded, they display exactly as they were originally shown.
    Now includes generated images and creative content in markdown format.

    Args:
        media_plan_output: Media plan response (already in markdown format)
        creative_insights_output: Creative insights response (already in markdown format)
        campaign_performance_output: Campaign performance response (already in markdown format)
        general_response_string: General response (already in markdown format)
        creative_data: List of creative data/images generated (will be converted to markdown)
        session_data: Complete session data dictionary for additional context

    Returns:
        str: Combined final response text in original markdown format including images
    """
    responses = []

    # Store responses exactly as they were sent to frontend (already in markdown)
    if media_plan_output and media_plan_output.strip():
        responses.append(media_plan_output.strip())

    if creative_insights_output and creative_insights_output.strip():
        responses.append(creative_insights_output.strip())

    if campaign_performance_output and campaign_performance_output.strip():
        responses.append(campaign_performance_output.strip())

    if general_response_string and general_response_string.strip():
        responses.append(general_response_string.strip())

    # Include generated images and creative content in markdown format
    if creative_data and len(creative_data) > 0:
        images_markdown = "\n\n## Generated Images\n\n"
        for i, creative_item in enumerate(creative_data, 1):
            if isinstance(creative_item, dict):
                # Handle structured creative data with S3 keys
                if 's3_key' in creative_item:
                    title = creative_item.get('title', f'Generated Image {i}')
                    s3_key = creative_item.get('s3_key', '')
                    explanation = creative_item.get('explanation', '')
                    dimensions = creative_item.get('dimensions', '')
                    aspect_ratio = creative_item.get('aspect_ratio', '')

                    # Create markdown for the image using S3 key (will be converted to URL when loaded)
                    if dimensions and aspect_ratio:
                        images_markdown += f"### {title} - {aspect_ratio} ({dimensions})\n\n"
                    else:
                        images_markdown += f"### {title}\n\n"

                    images_markdown += f"![{title}]({s3_key})\n\n"

                    if explanation:
                        images_markdown += f"*{explanation}*\n\n"
                # Handle legacy URL format for backward compatibility
                elif 'url' in creative_item:
                    title = creative_item.get('title', f'Generated Image {i}')
                    url = creative_item.get('url', '')
                    explanation = creative_item.get('explanation', '')
                    dimensions = creative_item.get('dimensions', '')
                    aspect_ratio = creative_item.get('aspect_ratio', '')

                    # Create markdown for the image
                    if dimensions and aspect_ratio:
                        images_markdown += f"### {title} - {aspect_ratio} ({dimensions})\n\n"
                    else:
                        images_markdown += f"### {title}\n\n"

                    images_markdown += f"![{title}]({url})\n\n"

                    if explanation:
                        images_markdown += f"*{explanation}*\n\n"
                elif 'creative_id' in creative_item:
                    # Handle creative data with ID
                    creative_id = creative_item.get('creative_id', '')
                    features = creative_item.get('features', '')
                    images_markdown += f"### Creative {creative_id}\n\n"
                    if features:
                        images_markdown += f"*Features: {features}*\n\n"
            elif isinstance(creative_item, str):
                # Handle simple string URLs or S3 keys
                images_markdown += f"### Generated Image {i}\n\n![Generated Image {i}]({creative_item})\n\n"

        responses.append(images_markdown.strip())

    # Return combined response or fallback message
    if responses:
        return "\n\n".join(responses)
    else:
        # If no content was generated, provide a more helpful message
        return "I apologize, but I wasn't able to generate a complete response. Please try rephrasing your question or provide more specific details about what you're looking for."


async def handle_periodic_db_storage(user_id: str, session_id: str, query_id: str,
                                   user_query: str, final_response: str, end_time: Optional[datetime] = None,
                                   intent_detected: Optional[str] = None) -> None:
    """
    Handles database storage after every query.

    Previously handled periodic storage based on configurable criteria, but now simplified
    to store after every query for immediate persistence.

    Args:
        user_id: User identifier
        session_id: Session identifier
        query_id: Current query identifier
        user_query: Original user query (kept for compatibility, not currently used)
        final_response: Final response text
        end_time: Optional end time for accurate duration calculation
    """
    try:
        from execution_tracker import execution_tracker
        logger.info(f"[DB_STORAGE] Storing query {query_id} after every query, session {session_id}")

        # COMMENTED OUT: Previous periodic storage logic
        # Configuration for periodic storage
        # STORAGE_INTERVAL_MESSAGES = int(os.getenv("DB_STORAGE_INTERVAL_MESSAGES", "5"))
        # STORAGE_INTERVAL_MINUTES = int(os.getenv("DB_STORAGE_INTERVAL_MINUTES", "10"))

        # Get the number of messages in current session
        # message_count = len(existing_data)

        # Check if we should store based on message count
        # should_store_by_count = (message_count % STORAGE_INTERVAL_MESSAGES == 0)

        # Check if we should store based on time (check last storage time)
        # should_store_by_time = await should_store_by_time_interval(
        #     session_id, STORAGE_INTERVAL_MINUTES
        # )

        # Check if this is a significant event (complete workflow)
        # is_significant_event = is_complete_workflow(existing_data[-1] if existing_data else {})

        # SIMPLIFIED: Store after every query
        logger.info(f"[DB_STORAGE] Storing query {query_id} - Storing final response: {final_response[:100]}...")

        # Only complete query tracking (start was already called in perform_inference)
        await execution_tracker.complete_query_execution(
            query_id=query_id,
            final_response=final_response,
            success=True,
            end_time=end_time,
            intent_detected=intent_detected
        )

        logger.info(f"[DB_STORAGE] Successfully stored query {query_id}")

    except Exception as e:
        logger.error(f"[DB_STORAGE] Error in storage: {e}")
        # Don't raise exception - storage failure shouldn't break inference


# COMMENTED OUT: Helper functions for periodic storage - no longer needed since we store after every query

# async def should_store_by_time_interval(session_id: str, interval_minutes: int) -> bool:
#     """
#     Check if enough time has passed since last storage to warrant storing again.
#
#     Args:
#         session_id: Session identifier
#         interval_minutes: Minimum minutes between storage operations
#
#     Returns:
#         bool: True if enough time has passed
#     """
#     try:
#         cache_control = CacheControl()
#         last_storage_key = f"last_storage:{session_id}"
#         last_storage_time = cache_control.get(last_storage_key)
#
#         if not last_storage_time:
#             return True  # No previous storage, so store now
#
#         # Decode bytes to string if necessary (Redis returns bytes)
#         if isinstance(last_storage_time, bytes):
#             last_storage_time = last_storage_time.decode('utf-8')
#
#         last_time = datetime.fromisoformat(last_storage_time)
#         current_time = datetime.now()
#         time_diff = (current_time - last_time).total_seconds() / 60  # Convert to minutes
#
#         return time_diff >= interval_minutes
#
#     except Exception as e:
#         logger.error(f"Error checking time interval: {e}")
#         return True  # Default to storing on error


# async def update_last_storage_time(session_id: str) -> None:
#     """
#     Update the last storage time for a session.
#
#     Args:
#         session_id: Session identifier
#     """
#     try:
#         cache_control = CacheControl()
#         last_storage_key = f"last_storage:{session_id}"
#         current_time = datetime.now().isoformat()
#         cache_control.setex(last_storage_key, 3600, current_time)  # Store for 1 hour
#
#     except Exception as e:
#         logger.error(f"Error updating last storage time: {e}")


# def is_complete_workflow(session_data: dict) -> bool:
#     """
#     Determine if the current session data represents a complete workflow.
#
#     A complete workflow is defined as having significant outputs in multiple areas.
#
#     Args:
#         session_data: Current session data dictionary
#
#     Returns:
#         bool: True if this represents a complete workflow
#     """
#     if not session_data:
#         return False
#
#     # Check for significant outputs
#     has_media_plan = bool(session_data.get('media_plan_output', '').strip())
#     has_creative_insights = bool(session_data.get('creative_insights_output', '').strip())
#     has_campaign_performance = bool(session_data.get('campaign_performance_output', '').strip())
#     has_creative_data = bool(session_data.get('creative_data', []))
#
#     # Consider it a complete workflow if we have outputs in multiple areas
#     output_count = sum([has_media_plan, has_creative_insights, has_campaign_performance, has_creative_data])
#
#     return output_count >= 2  # At least 2 types of outputs


async def store_related_queries(query_id: str, session_id: str, related_queries: List[str]) -> bool:
    """
    Store related queries for session continuity.

    Args:
        query_id: Query identifier
        session_id: Session identifier
        related_queries: List of related query strings

    Returns:
        bool: True if stored successfully
    """
    try:
        from database_models import RelatedQueriesModel
        from db_connector import db_connector

        db_session = db_connector.get_session()

        # Check if related queries already exist for this query
        existing_related = db_session.query(RelatedQueriesModel).filter_by(query_id=query_id).first()

        if existing_related:
            # Update existing related queries
            existing_related.related_queries = related_queries
            existing_related.timestamp = datetime.now(timezone.utc)
            logger.info(f"Updated related queries for query {query_id}")
        else:
            # Create new related queries record
            related_queries_record = RelatedQueriesModel(
                query_id=query_id,
                session_id=session_id,
                related_queries=related_queries,
                timestamp=datetime.now(timezone.utc)
            )
            db_session.add(related_queries_record)
            logger.info(f"Created new related queries for query {query_id}")

        db_session.commit()
        db_session.close()

        logger.info(f"Successfully stored {len(related_queries)} related queries for query {query_id}")
        return True

    except Exception as e:
        logger.error(f"Error storing related queries for query {query_id}: {e}")
        if 'db_session' in locals():
            db_session.rollback()
            db_session.close()
        return False


async def get_latest_related_queries(session_id: str) -> List[str]:
    """
    Get the most recent related queries for a session to enable session continuity.

    Args:
        session_id: Session identifier

    Returns:
        List[str]: List of related query strings from the most recent query
    """
    try:
        from database_models import RelatedQueriesModel
        from db_connector import db_connector

        db_session = db_connector.get_session()

        # Get the most recent related queries for this session
        latest_related = db_session.query(RelatedQueriesModel)\
            .filter_by(session_id=session_id)\
            .order_by(RelatedQueriesModel.timestamp.desc())\
            .first()

        db_session.close()

        if latest_related and latest_related.related_queries:
            logger.info(f"Retrieved {len(latest_related.related_queries)} related queries for session {session_id}")
            return latest_related.related_queries
        else:
            logger.info(f"No related queries found for session {session_id}")
            return []

    except Exception as e:
        logger.error(f"Error retrieving related queries for session {session_id}: {e}")
        if 'db_session' in locals():
            db_session.close()
        return []


async def store_session_data_to_db(user_id: str, session_id: str, session_data_list: List[dict]) -> int:
    """
    Store all session data from cache to database.

    Args:
        user_id: User identifier
        session_id: Session identifier
        session_data_list: List of session data dictionaries from cache

    Returns:
        int: Number of queries stored
    """
    try:
        from execution_tracker import execution_tracker

        stored_count = 0

        for session_data in session_data_list:
            query_id = session_data.get('query_id')
            user_query = session_data.get('message_query', '')

            if not query_id or not user_query:
                logger.warning(f"Skipping session data with missing query_id or message_query: {session_data}")
                continue

            # Get final response including creative data (images)
            final_response = get_final_response_text(
                session_data.get('media_plan_output', ''),
                session_data.get('creative_insights_output', ''),
                session_data.get('campaign_performance_output', ''),
                session_data.get('general_response_string', ''),
                creative_data=session_data.get('creative_data', []),
                session_data=session_data
            )

            try:
                # Check if query already exists before attempting to start tracking
                from execution_tracker import execution_tracker

                # Try to start query tracking (will handle duplicates gracefully)
                try:
                    await execution_tracker.start_query_execution(
                        query_id=query_id,
                        user_id=user_id,
                        session_id=session_id,
                        original_query=user_query
                    )
                except Exception:
                    # If start fails due to duplicate, that's OK - query already exists
                    logger.info(f"Query {query_id} already exists in database, proceeding with completion")

                # Complete query tracking
                await execution_tracker.complete_query_execution(
                    query_id=query_id,
                    final_response=final_response,
                    success=True
                )

                stored_count += 1
                logger.info(f"[DB_STORAGE] Stored query {query_id} to database")

            except Exception as e:
                logger.error(f"[DB_STORAGE] Failed to store query {query_id}: {e}")
                continue

        logger.info(f"[DB_STORAGE] Successfully stored {stored_count} queries for session {session_id}")
        return stored_count

    except Exception as e:
        logger.error(f"[DB_STORAGE] Error storing session data to database: {e}")
        return 0


def check_url_type(url: str) -> str:
    """Determine if the given URL is a base64 URL or a normal URL."""
    base64_pattern = r'^data:image/\w+;base64,'
    if re.match(base64_pattern, url):
        return 'base64'
    return 'direct_link'

def check_non_empty_fields_for_topic(existing_data: List[dict], current_topic: str) -> List[str]:
    """
    Checks which fields have non-empty strings for the given topic in past session data.

    Args:
        existing_data (List[dict]): The past session data containing topics and fields to check.
        current_topic (str): The current topic to match against past session topics.

    Returns:
        List[str]: A list of field names that have non-empty strings for the given topic.
    """
    fields_to_check = ['media_plan_output', 'campaign_performance_output', 'creative_insights_output']
    non_empty_fields = []

    for session in existing_data:
        if session.get('topic') == current_topic:
            for field in fields_to_check:
                if field in session and isinstance(session[field], str) and session[field].strip():
                    non_empty_fields.append(field)

    return list(set(non_empty_fields))

@timer_decorator
async def topic_extractor(past_topics: List[str], user_query: str, query_id: Optional[str] = None) -> str:
    """
    Extracts the topic from the user's session history and compares it with the current user query using an LLM.
    For image generation and resizing operations, ensures a valid topic is always returned.

    Args:
        past_topics (List[str]): A list of topics from the user's previous session history.
        user_query (str): The current user query.

    Returns:
        str: The current topic determined by the LLM.
    """
    # Check if the query is related to image operations before calling the LLM
    image_operation_keywords = [
        "resize", "generate image", "create image", "make image",
        "iab", "standard size", "aspect ratio", "multi-generate",
        "1:1", "9:16", "16:9", "3:4", "4:3", "1024x1024", "768x1408",
        "1408x768", "896x1280", "1280x896", "970x250", "300x1050",
        "160x600", "300x250", "120x60"
    ]

    # Check if the query contains any image operation keywords
    is_image_operation = any(keyword.lower() in user_query.lower() for keyword in image_operation_keywords)

    # If it's clearly an image operation, return "image_generation" immediately
    if is_image_operation:
        logger.info(f"Query identified as image operation: '{user_query[:50]}...'")
        return "image_generation"

    # Prepare the prompt for the LLM for other cases
    prompt = load_prompt("topic_extractor").format(", ".join(past_topics), user_query)
    try:
        # Use the existing generate_response function to get the topic
        response_content = await generate_response(
            query=prompt,
            system_prompt="You are an AI that determines topics based on user queries.",
            max_tokens=150,
            query_id=query_id,
            agent_name="topic_extractor"
        )

        # Check if the response is "no topic" and provide a default
        if response_content.lower() == "no topic":
            logger.warning(f"LLM returned 'no topic' for query: '{user_query[:50]}...', using default topic")

            # Check if it might be related to creative generation
            creative_keywords = ["ad", "advertisement", "creative", "campaign", "marketing"]
            if any(keyword.lower() in user_query.lower() for keyword in creative_keywords):
                return "creative_generation"
            else:
                return "general_inquiry"

        # Return the response content as the current topic
        return response_content
    except Exception as e:
        logger.error(f"Error in topic extraction: {e}")
        # Provide a default topic instead of empty string on error
        return "general_inquiry"

# Import the search planner
from search_planner import search_planner_agent

# Searches Qdrant and returns search result object
async def search_qdrant(query_text: str, conversation_payload: list, parameters: Dict[str, Any] = None, use_vector_search: bool = None, number_of_results: int = None, retry_count: int = 0, unrelated_query: bool = False, previous_search_context: Optional[PreviousSearchContext] = None, query_id: Optional[str] = None) -> SearchResult:
    logger.info(f"SEARCH_QDRANT CALLED: retry_count={retry_count}, query='{query_text[:50]}...', use_vector_search={use_vector_search}")

    # Initialize search context tracking
    from model import SearchContext, AppliedFilter, PreviousSearchContext
    search_context = SearchContext(retry_count=retry_count, search_type="unknown")

    # Add a maximum retry count to prevent deep recursion
    MAX_RETRY_COUNT = 3
    if retry_count >= MAX_RETRY_COUNT:
        logger.warning(f"Maximum retry count ({MAX_RETRY_COUNT}) reached. Returning empty result.")
        search_context.search_explanation = f"Maximum retry count ({MAX_RETRY_COUNT}) reached. No results found after multiple search attempts."
        search_context.retry_history.append(f"Reached maximum retry limit of {MAX_RETRY_COUNT}")
        return SearchResult(results=[], total=0, search_context=search_context)

    try:
        # Check if we're retrying due to a previous failure
        previous_search_failed = retry_count > 0

        # Log what we're passing to the search planner
        logger.info(f"Calling search_planner_agent with: previous_search_failed={previous_search_failed}, previous_search_context={previous_search_context is not None}")
        if previous_search_context:
            logger.info(f"Previous search context being passed: {previous_search_context.model_dump_json()}")

        # Get search plan from the search planner agent
        search_plan = await search_planner_agent(
            query_text,
            conversation_payload,
            previous_search_failed=previous_search_failed,
            previous_search_context=previous_search_context,
            query_id=query_id
        )

        if number_of_results is not None:
            search_plan.limit = number_of_results
        elif search_plan.limit is None:
            search_plan.limit = 10

        logger.info(f"Search plan: {search_plan.model_dump_json()}")

        # Update search context with search plan information
        search_context.search_type = search_plan.search_type
        search_context.search_plan_steps = [f"{step.step_type}: {step.description}" for step in search_plan.steps]

        # Log the search context information for debugging
        logger.info(f"Search context initialized: search_type={search_context.search_type}, retry_count={search_context.retry_count}")

        # Debug: Log the search plan details
        logger.info(f"Search plan generated: {search_plan.search_type} with {len(search_plan.steps)} steps")
        for i, step in enumerate(search_plan.steps):
            logger.info(f"  Step {i+1}: {step.step_type} - {step.description}")
            logger.info(f"    Parameters: {step.parameters}")

        # Track retry history
        if retry_count > 0:
            if retry_count == 1:
                search_context.retry_history.append("Initial search returned no results, retrying with broader search plan")
            elif retry_count == 2:
                search_context.retry_history.append("Second attempt failed, trying with 'should' logic (OR instead of AND)")
            elif retry_count == 3:
                search_context.retry_history.append("Filter searches failed, falling back to semantic search")

        # Initialize variables
        ad_creatives = []
        filter_conditions = []
        collection_name = os.getenv("COLLECTION_NAME", "media_data_standardized")
        sort_field = "conversion"  # Default sort field - will be used if not specified in filter or semantic_search steps
        sort_direction = "desc"    # Default sort direction - will be used if not specified in filter or semantic_search steps

        # Update search context with sort information
        search_context.sort_field = sort_field
        search_context.sort_direction = sort_direction

        # Process each step in the search plan
        for step_index, step in enumerate(search_plan.steps):
            logger.info(f"Executing step {step_index+1}: {step.step_type} - {step.description}")

            # Process filter step
            if step.step_type == "filter":
                logger.info(f"Filter parameters: {step.parameters}")

                # Process brand filter
                if "brand" in step.parameters:
                    brand_value = step.parameters["brand"]
                    logger.info(f"Brand filter: {brand_value}")

                    if isinstance(brand_value, list):
                        # Convert all brand names to lowercase
                        lowercase_brands = [brand.lower() for brand in brand_value]
                        logger.info(f"Using multiple brand filter values (lowercase): {lowercase_brands}")
                        filter_conditions.append(FieldCondition(key="brand", match=MatchAny(any=lowercase_brands)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="brand",
                            value=lowercase_brands,
                            match_type="multiple"
                        ))
                    else:
                        lowercase_brand = brand_value.lower()
                        logger.info(f"Using single brand filter value (lowercase): {lowercase_brand}")
                        filter_conditions.append(FieldCondition(key="brand", match=MatchValue(value=lowercase_brand)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="brand",
                            value=lowercase_brand,
                            match_type="single"
                        ))

                # Process industry filter
                if "industry_sectors" in step.parameters:
                    industry_value = step.parameters["industry_sectors"]
                    logger.info(f"Industry filter: {industry_value}")

                    if isinstance(industry_value, list):
                        logger.info(f"Using multiple industry filter values: {industry_value}")
                        filter_conditions.append(FieldCondition(key="industry_sectors", match=MatchAny(any=industry_value)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="industry_sectors",
                            value=industry_value,
                            match_type="multiple"
                        ))
                    else:
                        logger.info(f"Using single industry filter value: {industry_value}")
                        filter_conditions.append(FieldCondition(key="industry_sectors", match=MatchValue(value=industry_value)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="industry_sectors",
                            value=industry_value,
                            match_type="single"
                        ))

                # Process season filter
                if "season" in step.parameters:
                    season_value = step.parameters["season"]
                    logger.info(f"Season filter: {season_value}")

                    if isinstance(season_value, list):
                        filter_conditions.append(FieldCondition(key="season", match=MatchAny(any=season_value)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="season",
                            value=season_value,
                            match_type="multiple"
                        ))
                    else:
                        filter_conditions.append(FieldCondition(key="season", match=MatchValue(value=season_value)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="season",
                            value=season_value,
                            match_type="single"
                        ))

                # Process campaign filter
                if "campaign" in step.parameters:
                    campaign_value = step.parameters["campaign"]
                    logger.info(f"Campaign filter: {campaign_value}")

                    if isinstance(campaign_value, list):
                        filter_conditions.append(FieldCondition(key="campaign_folder", match=MatchAny(any=campaign_value)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="campaign_folder",
                            value=campaign_value,
                            match_type="multiple"
                        ))
                    else:
                        filter_conditions.append(FieldCondition(key="campaign_folder", match=MatchValue(value=campaign_value)))
                        # Track applied filter
                        search_context.applied_filters.append(AppliedFilter(
                            field="campaign_folder",
                            value=campaign_value,
                            match_type="single"
                        ))

                # Process sort parameters in filter step
                if "sort_field" in step.parameters:
                    sort_field = step.parameters["sort_field"]
                    search_context.sort_field = sort_field
                    logger.info(f"Sort field from filter step: {sort_field}")
                if "sort_order" in step.parameters:
                    sort_direction = step.parameters["sort_order"]
                    search_context.sort_direction = sort_direction
                    logger.info(f"Sort order from filter step: {sort_direction}")

            # Process semantic search step
            elif step.step_type == "semantic_search":
                logger.info(f"Semantic search parameters: {step.parameters}")

                # Check for filter parameters in semantic search step
                for filter_key in ["brand", "industry", "season", "campaign"]:
                    if filter_key in step.parameters:
                        logger.info(f"Filter in semantic search step: {filter_key}={step.parameters[filter_key]}")
                        # Process these filters similar to the filter step
                        value = step.parameters[filter_key]
                        field_key = "industry_sectors" if filter_key == "industry" else \
                                   "campaign_folder" if filter_key == "campaign" else filter_key

                        if isinstance(value, list):
                            # For brand, convert to lowercase
                            if filter_key == "brand":
                                value = [brand.lower() for brand in value]
                                logger.info(f"Semantic search with multiple brand filter values (lowercase): {value}")
                            else:
                                logger.info(f"Semantic search with multiple {filter_key} filter values: {value}")
                            filter_conditions.append(FieldCondition(key=field_key, match=MatchAny(any=value)))
                            # Track applied filter
                            search_context.applied_filters.append(AppliedFilter(
                                field=field_key,
                                value=value,
                                match_type="multiple"
                            ))
                        else:
                            # For brand, convert to lowercase
                            if filter_key == "brand":
                                value = value.lower()
                                logger.info(f"Semantic search with single brand filter value (lowercase): {value}")
                            else:
                                logger.info(f"Semantic search with single {filter_key} filter value: {value}")
                            filter_conditions.append(FieldCondition(key=field_key, match=MatchValue(value=value)))
                            # Track applied filter
                            search_context.applied_filters.append(AppliedFilter(
                                field=field_key,
                                value=value,
                                match_type="single"
                            ))

                # Process sort parameters in semantic search step
                if "sort_field" in step.parameters:
                    sort_field = step.parameters["sort_field"]
                    search_context.sort_field = sort_field
                    logger.info(f"Sort field from semantic search step: {sort_field}")
                if "sort_order" in step.parameters:
                    sort_direction = step.parameters["sort_order"]
                    search_context.sort_direction = sort_direction
                    logger.info(f"Sort order from semantic search step: {sort_direction}")

            # Process rerank step (sort step is now handled in filter and semantic_search steps)

            # Process rerank step
            elif step.step_type == "rerank":
                logger.info(f"Rerank parameters: {step.parameters}")
                # We'll use this information later for reranking

        # Create search filter if we have conditions
        # Using 'must' instead of 'should' to require ALL conditions to match (AND logic)
        # rather than ANY condition to match (OR logic)
        search_filter = Filter(must=filter_conditions) if filter_conditions else None

        # Log detailed filter information
        if filter_conditions:
            filter_details = []
            for i, condition in enumerate(filter_conditions):
                filter_detail = {
                    "index": i + 1,
                    "field": getattr(condition, "key", "unknown"),
                    "match_type": type(getattr(condition, "match", None)).__name__,
                    "value": None
                }

                # Extract the actual value based on match type
                match_obj = getattr(condition, "match", None)
                if hasattr(match_obj, "value"):
                    filter_detail["value"] = match_obj.value
                elif hasattr(match_obj, "any"):
                    filter_detail["value"] = match_obj.any

                filter_details.append(filter_detail)

            logger.info(f"Final filter details: {json.dumps(filter_details, indent=2)}")
            logger.info(f"Filter logic: ALL conditions must match (AND logic)")
        else:
            logger.info("No filter conditions applied")

        # Prepare for search
        if unrelated_query:
            # If unrelated_query is True, don't include conversation history
            logger.info("Unrelated query flag is set to True. Not including conversation history in the query.")
            enriched_query_text = f"User Query: {query_text}"
        else:
            # Otherwise, include conversation history as usual
            formatted_history = format_conversation_payload(conversation_payload)
            enriched_query_text = f"{formatted_history}\nUser Query: {query_text}"

        query_vector = get_embedding(enriched_query_text)

        if not query_vector or len(query_vector) == 0:
            logger.error("No valid query vector obtained from the text.")
            return SearchResult(results=[], total=0)

        # Log the final sort parameters that will be used
        logger.info(f"Will sort results by {sort_field} in {sort_direction} order")

        # Initialize search variables
        candidate_ids = []
        next_page_offset = None
        search_result = []

        # Execute search based on the search plan type
        logger.info(f"Executing search with type: {search_plan.search_type}")

        if search_plan.search_type == "semantic_only":
            # Perform semantic search without filtering first
            try:
                logger.info("Performing semantic-only search")
                search_result = Qclient.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=search_plan.limit * 3,  # Get more results for processing
                    with_payload=True,
                    with_vectors=False,
                    # order_by={"key": sort_field, "direction": sort_direction}  # Order by sort_field in sort_direction
                )

                logger.info(f"Semantic-only search found {len(search_result)} results")

                # Track step result
                step_result = _create_step_result(
                    step_type="semantic_search",
                    step_description="Semantic search based on content similarity",
                    search_results=search_result,
                    applied_filters=[]
                )
                search_context.step_results.append(step_result)

            except Exception as e:
                logger.error(f"Error performing semantic-only search: {e}")
                return SearchResult(results=[], total=0)

        elif search_plan.search_type == "filter_without_semantic":
            # Perform filtering without semantic search
            try:
                # Log detailed filter information for debugging
                if search_filter and hasattr(search_filter, "must"):
                    filter_fields = [getattr(c, "key", "unknown") for c in search_filter.must]
                    filter_values = []
                    for condition in search_filter.must:
                        match_obj = getattr(condition, "match", None)
                        if hasattr(match_obj, "value"):
                            filter_values.append(match_obj.value)
                        elif hasattr(match_obj, "any"):
                            filter_values.append(match_obj.any)
                        else:
                            filter_values.append("unknown")

                    logger.info(f"Performing filter-only search with ALL of these conditions (AND logic):")
                    for field, value in zip(filter_fields, filter_values):
                        logger.info(f"  - Field: {field}, Value: {value}")
                else:
                    logger.info(f"Performing filter-only search with the filter: {search_filter}")

                scroll_result = Qclient.scroll(
                    collection_name=collection_name,
                    # limit=search_plan.limit * 3,  # Get more results for processing
                    limit=520,  # Get more results for processing
                    scroll_filter=search_filter,  # Changed from 'filter' to 'scroll_filter'
                    with_payload=True,
                    with_vectors=False,
                    offset=next_page_offset
                    # Note: order_by removed due to compatibility issues - sorting will be done in Python
                )

                # Extract the points from the result
                search_result = scroll_result[0]
                next_page_offset = scroll_result[1]

                logger.info(f"Filter-only search found {len(search_result)} results")

                # Track step result
                step_result = _create_step_result(
                    step_type="filter_search",
                    step_description="Filter search with specific criteria",
                    search_results=search_result,
                    applied_filters=search_context.applied_filters
                )
                search_context.step_results.append(step_result)

            except Exception as e:
                logger.error(f"Error performing filter-only search: {e}")
                return SearchResult(results=[], total=0)

        elif search_plan.search_type == "filter_with_semantic":
            # First filter, then perform semantic search on filtered results
            try:
                # Step 1: Use scroll to get candidate point IDs based on filter
                logger.info("Step 1: Scrolling to get candidate point IDs based on filter")
                scroll_result = Qclient.scroll(
                    collection_name=collection_name,
                    limit=520,  # Get a large number of candidates
                    scroll_filter=search_filter,  # Changed from 'filter' to 'scroll_filter'
                    with_payload=False,  # Don't need payload for this step
                    with_vectors=False  # Don't need vectors for this step
                    # Note: order_by removed due to compatibility issues - sorting will be done in Python
                )

                # Extract the points and next page offset from the result
                scrolled_points = scroll_result[0]
                next_page_offset = scroll_result[1]

                # Extract IDs from the points
                candidate_ids = [point.id for point in scrolled_points]
                logger.info(f"Found {len(candidate_ids)} candidate points from filter")

                # Step 2: Perform vector search on candidate IDs
                if candidate_ids:
                    logger.info(f"Step 2: Performing vector search on {len(candidate_ids)} candidate IDs")
                    search_result = Qclient.search(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        limit=search_plan.limit * 3,  # Get more results for processing
                        query_filter=Filter(must=[FieldCondition(key="id", match=MatchAny(any=candidate_ids))]),  # Changed from 'filter' to 'query_filter'
                        with_payload=True,
                        with_vectors=False,
                        # order_by={"key": sort_field, "direction": sort_direction}  # Order by sort_field in sort_direction
                    )

                    logger.info(f"Filter-with-semantic search found {len(search_result)} results")

                    # Track step result for filter + semantic
                    step_result = _create_step_result(
                        step_type="filter_with_semantic",
                        step_description=f"Filter search ({len(candidate_ids)} candidates) + semantic search",
                        search_results=search_result,
                        applied_filters=search_context.applied_filters
                    )
                    search_context.step_results.append(step_result)
                else:
                    logger.warning("No candidate IDs found from filter, falling back to filter-only search")
                    scroll_result = Qclient.scroll(
                        collection_name=collection_name,
                        limit=520,
                        scroll_filter=search_filter,  # Changed from 'filter' to 'scroll_filter'
                        with_payload=True,
                        with_vectors=False
                        # Note: order_by removed due to compatibility issues - sorting will be done in Python
                    )

                    # Extract the points from the result
                    search_result = scroll_result[0]

                    logger.info(f"Fallback filter-only search found {len(search_result)} results")

                    # Track step result for fallback filter search
                    step_result = _create_step_result(
                        step_type="fallback_filter_search",
                        step_description="Fallback filter search (no candidates found for semantic)",
                        search_results=search_result,
                        applied_filters=search_context.applied_filters
                    )
                    search_context.step_results.append(step_result)
            except Exception as e:
                logger.error(f"Error performing filter-with-semantic search: {e}")
                return SearchResult(results=[], total=0)
        else:
            # Default to semantic search if search type is not recognized
            logger.warning(f"Unrecognized search type: {search_plan.search_type}, defaulting to semantic search")
            try:
                search_result = Qclient.search(
                    collection_name=collection_name,
                    query_vector=query_vector,
                    limit=search_plan.limit * 3,
                    with_payload=True,
                    with_vectors=False,
                    # order_by={"key": sort_field, "direction": sort_direction}  # Order by sort_field in sort_direction
                )

                logger.info(f"Default semantic search found {len(search_result)} results")
            except Exception as e:
                logger.error(f"Error performing default semantic search: {e}")
                return SearchResult(results=[], total=0)

        # Process search results
        logger.info(f"Found {len(search_result)} search results to process")

        # Filter out excluded IDs if previous search context is provided
        if previous_search_context and previous_search_context.excluded_ids:
            logger.info(f"Filtering out {len(previous_search_context.excluded_ids)} excluded IDs from previous search")
            original_count = len(search_result)
            search_result = [hit for hit in search_result if hit.id not in previous_search_context.excluded_ids]
            filtered_count = len(search_result)
            logger.info(f"After excluding previous IDs: {filtered_count} results (removed {original_count - filtered_count})")

            # Update search context to track exclusion
            search_context.retry_history.append(f"Excluded {original_count - filtered_count} duplicate IDs from previous search")

        # Update search context with candidates found
        search_context.total_candidates_found = len(search_result)

        # Log search context state for debugging
        logger.info(f"Search context before retry check: search_type={search_context.search_type}, applied_filters={len(search_context.applied_filters)}, total_candidates={search_context.total_candidates_found}")
        if search_context.applied_filters:
            for i, filter_item in enumerate(search_context.applied_filters):
                logger.info(f"  Applied filter {i+1}: {filter_item.field}={filter_item.value} ({filter_item.match_type})")

        # Check if we got zero results and should retry
        if len(search_result) == 0:
            logger.warning(f"Search returned zero results (retry_count={retry_count})")

            # First retry: Try with a new search plan that knows the previous one failed
            if retry_count == 0:
                logger.info("Retrying with a new search plan that knows the previous one failed")

                # Create previous search context for the next attempt
                current_context = PreviousSearchContext(
                    search_type=search_context.search_type,
                    applied_filters=search_context.applied_filters,
                    filter_logic=search_context.filter_logic,
                    total_candidates_found=search_context.total_candidates_found,
                    final_results_count=0,  # Zero results is why we're retrying
                    retry_count=retry_count,
                    retry_history=search_context.retry_history.copy(),
                    search_explanation=f"Initial {search_context.search_type} search with {len(search_context.applied_filters)} filters returned zero results"
                )

                # Log the context being passed to the next search attempt
                logger.info(f"Creating previous search context for retry: {current_context.model_dump_json()}")

                return await search_qdrant(
                    query_text=query_text,
                    conversation_payload=conversation_payload,
                    parameters=parameters,
                    use_vector_search=use_vector_search,
                    number_of_results=number_of_results,
                    retry_count=1,  # Explicitly set to 1 for the next retry
                    unrelated_query=unrelated_query,
                    previous_search_context=current_context,
                    query_id=query_id
                )

            # Second retry: Use 'should' instead of 'must' to match ANY condition rather than ALL
            elif retry_count == 1:
                logger.info("Second retry: Using 'should' logic to match ANY condition rather than ALL")

                # Update search context to track filter logic change
                search_context.filter_logic = "should"
                search_context.retry_history.append("Changed filter logic from 'must' (AND) to 'should' (OR) to find more results")

                # Create a new filter with 'should' logic if we have filter conditions
                retry_filter = Filter(should=filter_conditions) if filter_conditions else None

                if retry_filter and filter_conditions:
                    logger.info("Performing filter search with 'should' logic (ANY condition matches)")
                    try:
                        scroll_result = Qclient.scroll(
                            collection_name=collection_name,
                            limit=520,
                            scroll_filter=retry_filter,
                            with_payload=True,
                            with_vectors=False
                            # Note: order_by removed due to compatibility issues - sorting will be done in Python
                        )

                        # Extract the points from the result
                        retry_result = scroll_result[0]

                        if len(retry_result) > 0:
                            logger.info(f"'Should' logic search found {len(retry_result)} results")
                            search_result = retry_result
                            # Update search context with successful retry
                            search_context.total_candidates_found = len(retry_result)
                            search_context.retry_history.append(f"'Should' logic search successful: found {len(retry_result)} results")

                            # Track step result for should logic retry
                            step_result = _create_step_result(
                                step_type="retry_should_logic",
                                step_description="Retry with 'should' logic (OR instead of AND)",
                                search_results=retry_result,
                                applied_filters=search_context.applied_filters
                            )
                            search_context.step_results.append(step_result)

                            # Track filter relaxation impact
                            search_context.filter_relaxation_impact["changed_to_OR_logic"] = len(retry_result)
                        else:
                            # Fall back to pure semantic search if 'should' logic still returns no results
                            logger.info("'Should' logic search returned zero results, falling back to pure semantic search")

                            # Create previous search context for the next attempt
                            current_context = PreviousSearchContext(
                                search_type=search_context.search_type,
                                applied_filters=search_context.applied_filters,
                                filter_logic="should",  # We tried 'should' logic
                                total_candidates_found=0,
                                final_results_count=0,
                                retry_count=retry_count,
                                retry_history=search_context.retry_history.copy(),
                                search_explanation=f"Second attempt with 'should' logic (OR) on {len(search_context.applied_filters)} filters also returned zero results"
                            )

                            # Call with retry_count=2 to ensure we move to the third retry if this fails
                            return await search_qdrant(
                                query_text=query_text,
                                conversation_payload=conversation_payload,
                                parameters=parameters,
                                use_vector_search=use_vector_search,
                                number_of_results=number_of_results,
                                retry_count=2,  # Explicitly set to 2 for the next retry
                                unrelated_query=unrelated_query,
                                previous_search_context=current_context,
                                query_id=query_id
                            )
                    except Exception as e:
                        logger.error(f"Error performing 'should' logic search: {e}")

                        # Create previous search context for the next attempt
                        current_context = PreviousSearchContext(
                            search_type=search_context.search_type,
                            applied_filters=search_context.applied_filters,
                            filter_logic="should",
                            total_candidates_found=0,
                            final_results_count=0,
                            retry_count=retry_count,
                            retry_history=search_context.retry_history + [f"'Should' logic search failed with error: {str(e)}"],
                            search_explanation=f"Second attempt with 'should' logic failed due to error: {str(e)}"
                        )

                        # Call with retry_count=2 to ensure we move to the third retry if this fails
                        return await search_qdrant(
                            query_text=query_text,
                            conversation_payload=conversation_payload,
                            parameters=parameters,
                            use_vector_search=use_vector_search,
                            number_of_results=number_of_results,
                            retry_count=2,  # Explicitly set to 2 for the next retry
                            unrelated_query=unrelated_query,
                            previous_search_context=current_context,
                            query_id=query_id
                        )
                else:
                    # If no filter conditions, fall back to semantic search

                    # Create previous search context for the next attempt
                    current_context = PreviousSearchContext(
                        search_type=search_context.search_type,
                        applied_filters=[],  # No filter conditions
                        filter_logic="should",
                        total_candidates_found=0,
                        final_results_count=0,
                        retry_count=retry_count,
                        retry_history=search_context.retry_history + ["No filter conditions available for 'should' logic, falling back to semantic search"],
                        search_explanation="Second attempt had no filter conditions to apply 'should' logic to"
                    )

                    # Call with retry_count=2 to ensure we move to the third retry if this fails
                    return await search_qdrant(
                        query_text=query_text,
                        conversation_payload=conversation_payload,
                        parameters=parameters,
                        use_vector_search=use_vector_search,
                        number_of_results=number_of_results,
                        retry_count=2,  # Explicitly set to 2 for the next retry
                        unrelated_query=unrelated_query,
                        previous_search_context=current_context,
                        query_id=query_id
                    )

            # Third retry: Fall back to pure semantic search with reranking
            elif retry_count == 2:
                logger.info("Third retry: Falling back to pure semantic search with reranking")
                search_context.fallback_used = True
                search_context.retry_history.append("Falling back to semantic search after filter attempts failed")

                # Create a semantic search with reranking
                try:
                    logger.info("Performing fallback semantic search")
                    semantic_result = Qclient.search(
                        collection_name=collection_name,
                        query_vector=query_vector,
                        limit=search_plan.limit * 3,
                        with_payload=True,
                        with_vectors=False,
                    )

                    logger.info(f"Fallback semantic search found {len(semantic_result)} results")

                    # Process semantic search results
                    fallback_creatives = []
                    for hit in semantic_result:
                        try:
                            ad_creative = AdCreative.parse_obj(hit.payload)
                            fallback_creatives.append(ad_creative)
                        except Exception as e:
                            logger.error(f"Error parsing fallback search result: {e}")

                    # Rerank the results
                    if fallback_creatives:
                        logger.info("Reranking fallback search results")
                        # Use query_text for reranking, respecting unrelated_query flag
                        if unrelated_query:
                            logger.info("Unrelated query flag is set to True. Not including conversation history in reranking.")
                            fallback_query_text = f"User Query: {query_text}"
                        else:
                            formatted_history = format_conversation_payload(conversation_payload)
                            fallback_query_text = f"{formatted_history}\nUser Query: {query_text}"

                        fallback_creatives = rerank_results(query_text, fallback_creatives, fallback_query_text)

                        # Limit to requested number of results
                        # final_results = fallback_creatives[:search_plan.limit]
                        final_results = fallback_creatives
                        logger.info(f"Returning {len(final_results)} fallback results")

                        # Track step result for fallback semantic search
                        step_result = _create_step_result(
                            step_type="fallback_semantic_search",
                            step_description="Fallback semantic search after filter attempts failed",
                            search_results=semantic_result,
                            applied_filters=[]
                        )
                        search_context.step_results.append(step_result)

                        # Track filter relaxation impact
                        search_context.filter_relaxation_impact["removed_all_filters"] = len(semantic_result)

                        # Update search context
                        search_context.final_results_count = len(final_results)
                        search_context.search_explanation = _generate_search_explanation(search_context)

                        return SearchResult(results=final_results, total=len(final_results), search_context=search_context)
                except Exception as e:
                    logger.error(f"Error in fallback semantic search: {e}")

                # If semantic search fails, return empty result with context
                search_context.search_explanation = "All search attempts failed, including semantic search fallback"
                return SearchResult(results=[], total=0, search_context=search_context)

            # If all retries failed, return empty result
            logger.error("All search attempts failed, returning empty result")
            return SearchResult(results=[], total=0)

        logger.info("Step: Converting search results to AdCreative objects")

        # Convert search results to AdCreative objects
        for hit in search_result:
            try:
                ad_creative = AdCreative.parse_obj(hit.payload)
                ad_creatives.append(ad_creative)
                # Log each result's industry and brand for debugging
                # logger.info(f"Search result: ID={ad_creative.id}, Brand={ad_creative.brand}, Industry={ad_creative.industry_sectors}")
            except Exception as e:
                logger.error(f"Error parsing search result: {e}")

        # Log summary of industries and brands found
        industries = {}
        brands = {}
        for creative in ad_creatives:
            industry = creative.industry_sectors or "Unknown"  # Updated field name
            brand = creative.brand or "Unknown"
            industries[industry] = industries.get(industry, 0) + 1
            brands[brand] = brands.get(brand, 0) + 1

        logger.info(f"Industries found after filtering: {json.dumps(industries, indent=2)}")
        logger.info(f"Brands found after filtering: {json.dumps(brands, indent=2)}")

        # Deduplicate results
        logger.info("Step: Deduplicating results")
        # Track brands and campaigns to avoid duplicates
        brand_campaign_seen = {}
        unique_creatives = []

        for creative in ad_creatives:
            brand = creative.brand or "Unknown"
            campaign = creative.campaign_folder or "Unknown"
            key = f"{brand}_{campaign}"

            if key not in brand_campaign_seen:
                brand_campaign_seen[key] = True
                unique_creatives.append(creative)

        logger.info(f"After deduplication: {len(unique_creatives)} results from {len(ad_creatives)}")
        ad_creatives = unique_creatives

        # Apply Python-based sorting since order_by was removed from Qdrant calls
        logger.info(f"Step: Sorting results by {sort_field} in {sort_direction} order using Python")
        try:
            def sort_key(creative):
                value = getattr(creative, sort_field, 0)
                # Handle None values and convert to float for sorting
                try:
                    return float(value) if value is not None else 0
                except (ValueError, TypeError):
                    return 0

            ad_creatives.sort(key=sort_key, reverse=(sort_direction == "desc"))
            logger.info(f"Successfully sorted {len(ad_creatives)} results by {sort_field} ({sort_direction})")

            # Log top 5 results after sorting for debugging
            for i, creative in enumerate(ad_creatives[:5]):
                sort_value = getattr(creative, sort_field, 'N/A')
                logger.info(f"  Position {i+1}: {creative.campaign_folder} - {sort_field}: {sort_value}")

        except Exception as e:
            logger.error(f"Error sorting results by {sort_field}: {e}")
            # Continue without sorting if there's an error

        # Check for rerank step
        should_rerank = any(step.step_type == "rerank" for step in search_plan.steps)
        if should_rerank:
            # Apply reranking only for semantic search types
            if search_plan.search_type != "filter_without_semantic":
                logger.info("Step: Reranking search results")
                # Use query_text directly for reranking
                ad_creatives = rerank_results(query_text, ad_creatives, query_text)
                logger.info(f"Reranked {len(ad_creatives)} results")
            else:
                logger.warning("Rerank step found but search type is filter_without_semantic. Skipping reranking.")

        # Limit to requested number of results
        # logger.info(f"Step: Limiting to {search_plan.limit} results")
        final_results = ad_creatives  # No limit applied, return all results
        logger.info(f"Returning {len(final_results)} results out of {len(ad_creatives)}")

        # Log final results with detailed information
        final_industries = {}
        final_brands = {}
        final_details = []

        for idx, creative in enumerate(final_results):
            industry = creative.industry_sectors or "Unknown"  # Updated field name
            brand = creative.brand or "Unknown"
            final_industries[industry] = final_industries.get(industry, 0) + 1
            final_brands[brand] = final_brands.get(brand, 0) + 1

            # Add detailed info for each result
            final_details.append({
                "position": idx + 1,
                "id": creative.id,
                "brand": brand,
                "industry_sectors": industry,  # Updated field name
                "campaign_folder": creative.campaign_folder,
                "conversion": creative.conversion
            })

        logger.info(f"Final industries in results: {json.dumps(final_industries, indent=2)}")
        logger.info(f"Final brands in results: {json.dumps(final_brands, indent=2)}")
        # logger.info(f"Final result details: {json.dumps(final_details, indent=2)}")

        # Update search context with final results
        search_context.final_results_count = len(final_results)

        # Generate search explanation
        search_context.search_explanation = _generate_search_explanation(search_context)

        # Debug: Log search context before returning
        logger.info(f"SEARCH CONTEXT BEING RETURNED: search_type={search_context.search_type}, applied_filters={len(search_context.applied_filters)}, final_results_count={search_context.final_results_count}")
        logger.info(f"Search explanation: {search_context.search_explanation}")

        # Create result with pagination info if available
        result = SearchResult(results=final_results, total=len(final_results), search_context=search_context)

        # Add pagination info if available
        if next_page_offset:
            result.next_page_offset = next_page_offset

        return result
    except Exception as e:
        logger.error(f"Error With Qdrant Search: {e}")
        # Create a basic search context for error cases
        error_search_context = SearchContext(
            search_type="error",
            retry_count=retry_count,
            search_explanation=f"Search failed due to error: {str(e)}"
        )
        return SearchResult(results=[], total=0, search_context=error_search_context)

def _create_step_result(step_type: str, step_description: str, search_results: List, applied_filters: List = None) -> SearchStepResult:
    """Create a SearchStepResult object from search results."""
    brands_found = []
    industries_found = []

    # Extract brands and industries from search results
    for hit in search_results:
        try:
            if hasattr(hit, 'payload'):
                payload = hit.payload
            else:
                payload = hit

            if 'brand' in payload and payload['brand']:
                brands_found.append(payload['brand'])
            if 'industry_sectors' in payload and payload['industry_sectors']:
                industries_found.append(payload['industry_sectors'])
        except Exception as e:
            logger.debug(f"Error extracting brand/industry from search result: {e}")

    return SearchStepResult(
        step_type=step_type,
        step_description=step_description,
        results_count=len(search_results),
        applied_filters=applied_filters or [],
        brands_found=brands_found,
        industries_found=industries_found
    )

def _generate_search_explanation(search_context) -> str:
    """Generate a human-readable explanation of the search process with detailed metrics."""
    explanation_parts = []

    # Describe search type
    if search_context.search_type == "semantic_only":
        explanation_parts.append("Performed semantic search to find relevant creatives based on content similarity")
    elif search_context.search_type == "filter_with_semantic":
        explanation_parts.append("Applied filters first, then performed semantic search on filtered results")
    elif search_context.search_type == "filter_without_semantic":
        explanation_parts.append("Applied filters to find creatives matching specific criteria")

    # Describe applied filters with detailed results
    if search_context.applied_filters:
        filter_descriptions = []
        for filter_item in search_context.applied_filters:
            if filter_item.match_type == "multiple":
                filter_descriptions.append(f"{filter_item.field}: {', '.join(filter_item.value)}")
            else:
                filter_descriptions.append(f"{filter_item.field}: {filter_item.value}")

        if search_context.filter_logic == "must":
            explanation_parts.append(f"Applied filters (ALL must match): {'; '.join(filter_descriptions)}")
        else:
            explanation_parts.append(f"Applied filters (ANY can match): {'; '.join(filter_descriptions)}")

    # Add detailed step-by-step results if available
    if search_context.step_results:
        step_details = []
        for i, step in enumerate(search_context.step_results):
            step_detail = f"Step {i+1} ({step.step_type}): Found {step.results_count} results"

            # Add brand and industry details if available
            if step.brands_found:
                unique_brands = list(set(step.brands_found))
                if len(unique_brands) <= 5:
                    step_detail += f" from brands: {', '.join(unique_brands)}"
                else:
                    step_detail += f" from {len(unique_brands)} different brands"

            if step.industries_found:
                unique_industries = list(set(step.industries_found))
                if len(unique_industries) <= 3:
                    step_detail += f" in industries: {', '.join(unique_industries)}"
                else:
                    step_detail += f" across {len(unique_industries)} industries"

            step_details.append(step_detail)

        if step_details:
            explanation_parts.append("Search progression: " + "; ".join(step_details))

    # Describe filter relaxation impact
    if search_context.filter_relaxation_impact:
        relaxation_details = []
        for filter_change, count in search_context.filter_relaxation_impact.items():
            relaxation_details.append(f"{filter_change}: {count} additional results")

        if relaxation_details:
            explanation_parts.append("Filter relaxation impact: " + "; ".join(relaxation_details))

    # Describe sorting
    explanation_parts.append(f"Results sorted by {search_context.sort_field} in {search_context.sort_direction}ending order")

    # Describe retry attempts with specific details
    if search_context.retry_count > 0:
        explanation_parts.append(f"Search required {search_context.retry_count} retry attempt(s)")
        if search_context.retry_history:
            retry_details = []
            for i, retry in enumerate(search_context.retry_history):
                retry_details.append(f"Attempt {i+1}: {retry}")
            explanation_parts.append("Retry progression: " + "; ".join(retry_details))

    # Describe final results with context
    if search_context.final_results_count > 0:
        result_description = f"Found {search_context.final_results_count} relevant creatives"
        if search_context.total_candidates_found > search_context.final_results_count:
            result_description += f" (filtered from {search_context.total_candidates_found} candidates)"
        explanation_parts.append(result_description)
    else:
        explanation_parts.append("No relevant creatives found matching the criteria")

    return ". ".join(explanation_parts) + "."

# Identifies the intent and enhances the query
@timer_decorator
def determine_intent(user_query: str, conversation_history: List[ConversationPayload], prompt_file: str, creative_provided: bool = False, creative_features: Optional[str] = None, existing_data: Optional[List[dict]] = None, query_id: Optional[str] = None) -> dict:
    try:
        system_prompt = load_prompt(prompt_file)

        # Handle current creative if provided
        if creative_provided:
            system_prompt += "\ncreative provided: true\n A new creative has been uploaded and provided by the user along with his message. Prioritize recent image uploads.\n"
            if creative_features:
                system_prompt += f"The creative features were: {creative_features}\n"
        else:
            system_prompt += "creative provided: false\n"

        # Add information about previous creatives from session data
        logger.info(f"Existing data is {existing_data}")
        if existing_data:
            logger.info("Adding previous creatives from session data to determine_intent")
            # Use get_all_past_creative_data to get ALL creatives without topic filtering
            previous_creatives = get_all_past_creative_data(existing_data)
            if previous_creatives:
                system_prompt += "\nPrevious creatives from session history:\n"
                # Limit to the 5 most recent creatives to avoid overwhelming the prompt but provide more context
                for i, creative in enumerate(previous_creatives[-10:]):
                    if 'features' in creative and creative['features']:
                        system_prompt += f"Creative {i+1} features: {creative['features']}\n"
                    if 'role' in creative and creative['role']:
                        system_prompt += f"Creative {i+1} role: {creative['role']}\n"
                    if 'url' in creative and creative['url']:
                        system_prompt += f"Creative {i+1} URL: {creative['url']}\n"


        query_embedding= get_embedding(user_query, query_id)
        search_results = Qclient.search(
                    collection_name=os.getenv("INTENT_EXAMPLE_COLLECTION_NAME"),  # Use the correct collection name
                    query_vector=query_embedding,
                    limit=3  # Number of examples to retrieve
                )
        example_context = ""
        logger.debug(f"Found {len(search_results)} intent examples")
        for hit in search_results:
            example = hit.payload
            if example['conversation_history']:
                example_context += f"\nUser: {example['user_query']}\n Conversation History:{example['conversation_history']} \nResponse: {example['response']}\n"
            else:
                example_context += f"\nUser: {example['user_query']}\nResponse: {example['response']}\n"
        # Append the examples to the system prompt
        system_prompt += "\nHere are some examples:\n" + example_context
        logger.info(f"System prompt for intent determination: {system_prompt}")
        messages = [{"role": "system", "content": system_prompt}]
        for message in conversation_history:
            messages.append({"role": message.actor, "content": message.content})
        messages.append({"role": "user", "content": user_query})

        # Log only the number of messages, not their full content
        logger.debug(f"Determine Intent: Processing {len(messages)} messages")

        # For synchronous functions, we'll track manually without context manager
        if query_id:
            from execution_tracker import execution_tracker
            from model import AgentExecutionStep
            from datetime import datetime
            import asyncio

            # Format input prompt for tracking - store full data without truncation
            formatted_input = f"System: {system_prompt}\nQuery: {user_query}"

            # Create step manually for synchronous tracking
            step_data = AgentExecutionStep(
                agent_name="determine_intent_agent",
                step_type="intent_detection",
                start_time=datetime.now(),
                input_prompt=formatted_input,
                output_response="",
                model_used="gpt-4o-mini"
            )

            try:
                response = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=messages,
                    response_format=IntentOutput,
                    max_tokens=500
                )

                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    tokens = {
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    }
                    step_data.tokens_used = tokens
                    logger.debug(f"Token usage tracked for determine_intent: {tokens}")

                # Set output for tracking - store full response without truncation
                response_content = response.choices[0].message.content.strip()
                step_data.output_response = response_content
                step_data.success = True
                step_data.end_time = datetime.now()

                # Calculate duration
                if step_data.start_time and step_data.end_time:
                    duration_ms = int((step_data.end_time - step_data.start_time).total_seconds() * 1000)
                    step_data.duration_ms = duration_ms

                # Save step asynchronously (fire and forget)
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, schedule the save
                        asyncio.create_task(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                    else:
                        # If not in async context, run it
                        asyncio.run(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                except Exception as save_error:
                    logger.warning(f"Failed to save determine_intent step tracking: {save_error}")

            except Exception as e:
                step_data.success = False
                step_data.error_message = str(e)
                step_data.end_time = datetime.now()
                logger.error(f"Error in determine_intent with tracking: {e}")
                raise
        else:
            # Fallback without tracking
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=messages,
                response_format=IntentOutput,
                max_tokens=500
            )
        response_content = response.choices[0].message.content
        try:
            parsed_response = json.loads(response_content)
            validated_response = IntentOutput(**parsed_response)
            return validated_response.model_dump()
        except json.JSONDecodeError as json_error:
            logger.error(f"JSON parsing error: {json_error}")
            return {"error": "Failed to parse JSON response"}
        except ValueError as validation_error:
            logger.error(f"Validation error: {validation_error}")
            return {"error": "Response did not match expected format"}

    except Exception as e:
        logger.error(f"Error determining intent: {e}")
        logger.error(f"Query that led to error:{user_query}")
        return {"error": "Error determining intent"}

# async def generate_response_streaming(
#     query: str,
#     system_prompt: str,
#     search_result: str = None,
#     conversation_history: List[ConversationPayload] = None,
#     combined_output: str = None,
#     output_parts: Dict[str, str] = None,
#     max_tokens: int = 2400,
# ) -> AsyncGenerator[str, None]:
#     messages = [{"role": "system", "content": system_prompt}]
#     if search_result:
#         messages.append({"role": "system", "content": f"Search Results: {search_result}"})
#     if conversation_history:
#         for message in conversation_history:
#             messages.append({"role": message.actor, "content": message.content})

#     messages.append({"role": "user", "content": f"Query: {query}"})
#     if output_parts:
#         for key, value in output_parts.items():
#             messages.append({"role": "user", "content": f"{key.capitalize()}: {value}"})

#     if combined_output:
#         messages.append({"role": "user", "content": f"Combined Output: {combined_output}"})

#     try:
#         request_params = {
#             "model": "gpt-4o",
#             "messages": messages,
#             "max_tokens": max_tokens,
#             "n": 1,
#             "temperature": 0.1,
#             "stream": True  # Enable streaming
#         }
#         response_stream = client.chat.completions.create(**request_params)
#         for chunk in response_stream:
#             content = chunk.choices[0].delta.content
#             # print("streamed content:",content)
#             if content:
#                 yield content
#     except Exception as e:
#         logger.error(f"Error in generating response: {e}")
#         yield f"Error: {str(e)}"

@timer_decorator
async def generate_response(
    query: str,
    system_prompt: str,
    search_result: str = None,
    conversation_history: List[ConversationPayload] = None,
    combined_output: str = None,
    output_parts: Dict[str, str] = None,
    max_tokens: int = 2400,
    response_class: Optional[Type[BaseModel]] = None,
    validator: Optional[Callable] = None,
    max_retries: int = 0,
    model: str = "gpt-4o-mini",
    query_id: Optional[str] = None,
    agent_name: Optional[str] = None
) -> str:
    messages = [{"role": "system", "content": system_prompt}]
    if search_result:
        messages.append({"role": "system", "content": f"Search Results: {search_result}"})
    # Log only the number of conversation history entries, not their content
    if conversation_history:
        logger.debug(f"Processing {len(conversation_history)} conversation history entries")
        for message in conversation_history:
            messages.append({"role": message.actor, "content": message.content})

    messages.append({"role": "user", "content": f"Query: {query}"})
    if output_parts:
        for key, value in output_parts.items():
            messages.append({"role": "user", "content": f"{key.capitalize()}: {value}"})

    if combined_output:
        messages.append({"role": "user", "content": f"Combined Output: {combined_output}"})

    # Log only the number of messages, not their full content
    logger.debug(f"Generate Response: Processing {len(messages)} messages with model {model}")

    # Set up tracking if query_id and agent_name are provided
    if query_id and agent_name:
        from execution_tracker import execution_tracker

        # Format input prompt for tracking
        formatted_input = f"System: {system_prompt} \nQuery: {query}"
        if search_result:
            formatted_input += f"\nSearch Results: {search_result}"

        async with execution_tracker.track_agent_step(
            query_id=query_id,
            agent_name=agent_name,
            step_type="response_generation",
            input_prompt=formatted_input,
            model_used=model
        ) as step:
            retries = 0
            while True:
                try:
                    request_params = {
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "n": 1,
                        "temperature": 0.1
                    }
                    if response_class:
                        request_params["response_format"] = response_class

                    response = await asyncio.to_thread(client.beta.chat.completions.parse, **request_params)
                    response_content = response.choices[0].message.content.strip()

                    # Track token usage
                    if hasattr(response, 'usage') and response.usage:
                        tokens = {
                            "input": response.usage.prompt_tokens,
                            "output": response.usage.completion_tokens,
                            "total": response.usage.total_tokens
                        }
                        step.set_tokens(tokens)
                        logger.info(f"Token usage tracked for {agent_name}: {tokens}")

                    # Set output for tracking - store full response without truncation
                    step.set_output(response_content)

                    if response_class:
                        try:
                            validated_response = response_class.model_validate_json(response_content)

                            # If validator is provided, check if the response is valid
                            if validator and not validator(validated_response):
                                print("Validation is occuring.")
                                if retries < max_retries:
                                    retries += 1
                                    logger.warning(f"Validation failed. Retrying ({retries}/{max_retries})...")
                                    # Add a message to guide the model to fix the issue
                                    messages.append({"role": "system", "content": "The previous response had inconsistent budget values. Please ensure the budget in executive_summary matches the sum of budget allocations in media_mix_strategy."})
                                    continue
                                else:
                                    logger.warning(f"Max retries reached. Returning last response despite validation failure.")

                        except Exception as validation_error:
                            logger.error(f"Warning: Response validation failed: {validation_error}")

                    return response_content

                except Exception as e:
                    logger.error(f"Error in generating response: {e}")
                    step.set_output(f"Error: {str(e)}")
                    step.set_metadata({"error": str(e), "success": False})
                    return "I apologize, but I couldn't generate a response at this time."
    else:
        # Fallback to original logic without tracking
        retries = 0
        while True:
            try:
                request_params = {
                    "model": model,
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "n": 1,
                    "temperature": 0.1
                }
                if response_class:
                    request_params["response_format"] = response_class

                response = await asyncio.to_thread(client.beta.chat.completions.parse, **request_params)
                response_content = response.choices[0].message.content.strip()

                if response_class:
                    try:
                        validated_response = response_class.model_validate_json(response_content)

                        # If validator is provided, check if the response is valid
                        if validator and not validator(validated_response):
                            print("Validation is occuring.")
                            if retries < max_retries:
                                retries += 1
                                logger.warning(f"Validation failed. Retrying ({retries}/{max_retries})...")
                                # Add a message to guide the model to fix the issue
                                messages.append({"role": "system", "content": "The previous response had inconsistent budget values. Please ensure the budget in executive_summary matches the sum of budget allocations in media_mix_strategy."})
                                continue
                            else:
                                logger.warning(f"Max retries reached. Returning last response despite validation failure.")

                    except Exception as validation_error:
                        logger.error(f"Warning: Response validation failed: {validation_error}")

                return response_content

            except Exception as e:
                logger.error(f"Error in generating response: {e}")
                return "I apologize, but I couldn't generate a response at this time."

# @timer_decorator
def generate_response_with_creatives(
    creative :str, # Base 64 encoded image/video/gif
    query: str,
    system_prompt: str,
    search_result: str = None,
    conversation_history: List[ConversationPayload] = None,
    combined_output: str = None,
    output_parts: Dict[str, str] = None,
    max_tokens: int = 2400,
    response_class: Optional[Type[BaseModel]] = None,
    query_id: Optional[str] = None,
    agent_name: Optional[str] = None):

    messages = [{"role": "system", "content": system_prompt}]

    if search_result:
        messages.append({"role": "system", "content": f"Search Results: {search_result}"})

    if conversation_history:
        for message in conversation_history:
            messages.append({"role": message.actor, "content": message.content})

    messages.append({"role": "user", "content": f"Query: {query}"})

    if output_parts:
        for key, value in output_parts.items():
            messages.append({"role": "user", "content": f"{key.capitalize()}: {value}"})

    if combined_output:
        messages.append({"role": "user", "content": f"Combined Output: {combined_output}"})

    if creative:
        messages.append({
            "role": "user",
            "content": [
                {"type": "text", "text": "Here is the creative content."},
                {"type": "image_url", "image_url": {"url": f"{creative}"}}
            ]
        })
    try:
        # For synchronous functions, we'll track manually without context manager
        if query_id and agent_name:
            from execution_tracker import execution_tracker
            from model import AgentExecutionStep
            from datetime import datetime
            import asyncio

            # Format input prompt for tracking - store full data without truncation
            formatted_input = f"System: {system_prompt}\nQuery: {query}\nCreative: [Image provided]"
            if search_result:
                formatted_input += f"\nSearch Results: {str(search_result)}"

            # Create step manually for synchronous tracking
            step_data = AgentExecutionStep(
                agent_name=agent_name,
                step_type="response_generation",
                start_time=datetime.now(),
                input_prompt=formatted_input,
                output_response="",
                model_used="gpt-4o-mini"
            )

            try:
                request_params = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": max_tokens,
                    "n": 1,
                    "temperature": 0.1,
                }
                if response_class:
                    request_params["response_format"] = response_class
                response = client.chat.completions.create(**request_params)
                response_content = response.choices[0].message.content.strip()

                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    tokens = {
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    }
                    step_data.tokens_used = tokens
                    logger.debug(f"Token usage tracked for {agent_name}: {tokens}")

                # Set output for tracking - store full response without truncation
                step_data.output_response = response_content
                step_data.success = True
                step_data.end_time = datetime.now()

                # Calculate duration
                if step_data.start_time and step_data.end_time:
                    duration_ms = int((step_data.end_time - step_data.start_time).total_seconds() * 1000)
                    step_data.duration_ms = duration_ms

                # Save step asynchronously (fire and forget)
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, schedule the save
                        asyncio.create_task(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                    else:
                        # If not in async context, run it
                        asyncio.run(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                except Exception as save_error:
                    logger.warning(f"Failed to save {agent_name} step tracking: {save_error}")

                if response_class:
                    try:
                        response_class.model_validate_json(response_content)
                    except Exception as validation_error:
                        logger.error(f"Warning: Response validation failed: {validation_error}")
                return response_content
            except Exception as e:
                step_data.success = False
                step_data.error_message = str(e)
                step_data.end_time = datetime.now()
                logger.error(f"Error in {agent_name} with tracking: {e}")
                raise
        else:
            # Fallback without tracking
            request_params = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "max_tokens": max_tokens,
                "n": 1,
                "temperature": 0.1,
            }
            if response_class:
                request_params["response_format"] = response_class
            response = client.chat.completions.create(**request_params)
            response_content = response.choices[0].message.content.strip()
            if response_class:
                try:
                    response_class.model_validate_json(response_content)
                except Exception as validation_error:
                    logger.error(f"Warning: Response validation failed: {validation_error}")
            return response_content
    except Exception as e:
            logger.error(f"Error in generating response: {e} during the process with the system prompt: {system_prompt}")
    return

@timer_decorator
def creative_to_features(creative: str, query_id: Optional[str] = None)-> str:
    prompt = load_prompt("creative_feature_extractor")
    messages = [{"role": "system", "content": prompt}]
    messages.append({"role":"user","content":[{
                        "type": "image_url",
                        "image_url": {"url": creative}}]})
    try:
        # For synchronous functions, we'll track manually without context manager
        if query_id:
            from execution_tracker import execution_tracker
            from model import AgentExecutionStep
            from datetime import datetime
            import asyncio

            # Create step manually for synchronous tracking - store full prompt without truncation
            step_data = AgentExecutionStep(
                agent_name="creative_feature_extractor",
                step_type="agent_processing",
                start_time=datetime.now(),
                input_prompt=f"System: {prompt}\nCreative: [Image provided]",
                output_response="",
                model_used="gpt-4o-mini"
            )

            try:
                request_params = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": 300,
                    "n": 1,
                    "temperature": 0.1,
                }
                response = client.chat.completions.create(**request_params)
                response_content = response.choices[0].message.content.strip()

                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    tokens = {
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    }
                    step_data.tokens_used = tokens
                    logger.debug(f"Token usage tracked for creative_to_features: {tokens}")

                # Set output for tracking - store full response without truncation
                step_data.output_response = response_content
                step_data.success = True
                step_data.end_time = datetime.now()

                # Calculate duration
                if step_data.start_time and step_data.end_time:
                    duration_ms = int((step_data.end_time - step_data.start_time).total_seconds() * 1000)
                    step_data.duration_ms = duration_ms

                # Save step asynchronously (fire and forget)
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, schedule the save
                        asyncio.create_task(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                    else:
                        # If not in async context, run it
                        asyncio.run(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                except Exception as save_error:
                    logger.warning(f"Failed to save creative_to_features step tracking: {save_error}")

                return response_content
            except Exception as e:
                step_data.success = False
                step_data.error_message = str(e)
                step_data.end_time = datetime.now()
                logger.error(f"Error in creative_to_features with tracking: {e}")
                raise
        else:
            # Fallback without tracking
            request_params = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "max_tokens": 300,
                "n": 1,
                "temperature": 0.1,
            }
            response = client.chat.completions.create(**request_params)
            response_content = response.choices[0].message.content.strip()
            return response_content
    except Exception as e:
            logger.error(f"Error in generating response: {e} during the process with the prompt: {prompt}")
    return

@timer_decorator
def determine_creative_role(creative: str, features: str, user_query: str, query_id: Optional[str] = None) -> str:
    """
    Determines the role or purpose of a creative based on its features and the user's query.

    Args:
        creative (str): URL of the creative image
        features (str): Extracted features from the creative
        user_query (str): The user's query or message

    Returns:
        str: A concise description of the creative's role in marketing context
    """
    prompt = load_prompt("creative_role_analyzer")
    # Prepare the message with both the image and text context
    messages = [{"role": "system", "content": prompt}]
    messages.append({
        "role": "user",
        "content": [
            {
                "type": "image_url",
                "image_url": {"url": creative}
            },
            {
                "type": "text",
                "text": f"User Query: {user_query}\n\nExtracted Features: {features}"
            }
        ]
    })
    try:
        # For synchronous functions, we'll track manually without context manager
        if query_id:
            from execution_tracker import execution_tracker
            from model import AgentExecutionStep
            from datetime import datetime
            import asyncio

            # Create step manually for synchronous tracking
            step_data = AgentExecutionStep(
                agent_name="creative_role_determiner",
                step_type="agent_processing",
                start_time=datetime.now(),
                input_prompt=f"System: {prompt[:500]}...\nFeatures: {features[:200]}...\nQuery: {user_query[:200]}...",
                output_response="",
                model_used="gpt-4o-mini"
            )

            try:
                request_params = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "max_tokens": 200,
                    "n": 1,
                    "temperature": 0.2,
                }
                response = client.chat.completions.create(**request_params)
                response_content = response.choices[0].message.content.strip()

                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    tokens = {
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    }
                    step_data.tokens_used = tokens
                    logger.debug(f"Token usage tracked for determine_creative_role: {tokens}")

                # Set output for tracking
                step_data.output_response = response_content[:1000]  # Truncate long responses
                step_data.success = True
                step_data.end_time = datetime.now()

                # Calculate duration
                if step_data.start_time and step_data.end_time:
                    duration_ms = int((step_data.end_time - step_data.start_time).total_seconds() * 1000)
                    step_data.duration_ms = duration_ms

                # Save step asynchronously (fire and forget)
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        # If we're in an async context, schedule the save
                        asyncio.create_task(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                    else:
                        # If not in async context, run it
                        asyncio.run(execution_tracker.manager.add_agent_execution_step(query_id, step_data))
                except Exception as save_error:
                    logger.warning(f"Failed to save determine_creative_role step tracking: {save_error}")

                return response_content
            except Exception as e:
                step_data.success = False
                step_data.error_message = str(e)
                step_data.end_time = datetime.now()
                logger.error(f"Error in determine_creative_role with tracking: {e}")
                raise
        else:
            # Fallback without tracking
            request_params = {
                "model": "gpt-4o-mini",
                "messages": messages,
                "max_tokens": 200,
                "n": 1,
                "temperature": 0.2,
            }
            response = client.chat.completions.create(**request_params)
            response_content = response.choices[0].message.content.strip()
            return response_content
    except Exception as e:
        logger.error(f"Error determining creative role: {e} during the process with the prompt: {prompt}")
        return "Unable to determine creative role due to an error."


@timer_decorator
async def creative_inspiration_with_gemini_and_imagen(
    user_query: str,
    creative: str = "",
    conversation_history: List[ConversationPayload] = None,
    vector_search: bool = False,
    existing_data: List[dict] = None,
    extracted_features: str = "",
    query_id: Optional[str] = None,
):
    """
    Generate creative inspirations with Gemini and Imagen, with streaming support.
    This function now yields progress updates and partial results as they become available.

    Args:
        user_query: The user's query
        creative: URL or base64 of the creative image
        conversation_history: List of conversation messages
        vector_search: Whether to perform vector search
        existing_data: List of existing creative data
        extracted_features: Pre-extracted features from the creative image
    """
    try:
        # Format conversation history for logging instead of directly logging the objects
        formatted_history = format_conversation_payload(conversation_history) if conversation_history else "[]"
        logger.info(f"Conversation History in the beginning of creative inspiration: {formatted_history}")
        search_results = ""
        result = {}

        # Yield initial progress update
        yield {"status": "starting", "message": "Starting image generation process..."}

        # Add tracking dictionary for model usage
        model_usage = {
            "operation": None,
            "primary_model": None,
            "fallback_model": None,
            "steps": []
        }

        # Perform vector search if required
        search_context_info = ""
        if creative and vector_search:
            yield {"status": "searching", "message": "Searching for relevant creatives..."}
            # Use the pre-extracted features if available
            if extracted_features:
                search_results = await search_qdrant(f"{user_query} Creative: {extracted_features}", conversation_history, use_vector_search=True, number_of_results=3, parameters={}, query_id=query_id)
            else:
                search_results = await search_qdrant(f"{user_query}", conversation_history, use_vector_search=True, number_of_results=3, parameters={}, query_id=query_id)

            # Extract search context information
            if hasattr(search_results, 'search_context') and search_results.search_context:
                search_context_info = f"Search context: {search_results.search_context.search_explanation}"

        elif vector_search:
            yield {"status": "searching", "message": "Searching for relevant creatives..."}
            search_results = await search_qdrant(f"{user_query}", conversation_history, use_vector_search=True, number_of_results=3, parameters={},query_id=query_id)

            # Extract search context information
            if hasattr(search_results, 'search_context') and search_results.search_context:
                search_context_info = f"Search context: {search_results.search_context.search_explanation}"

        # Step 1: Generate a response to decide URL, dimensions, and model
        yield {"status": "deciding", "message": "Analyzing your request to determine the best approach..."}
        decision_system_prompt = load_prompt("creative_decision_prompt_v2")

        decision_query = f"Query: {user_query}\n"
        if creative:
            # Use the pre-extracted features if available
            if extracted_features:
                decision_query += f"The Creative Input was provided. Extracted Features from the input: {extracted_features}\n"
            else:
                decision_query += f"The Creative Input was provided.\n"

            # Get creative role if available
            try:
                creative_role = determine_creative_role(creative, extracted_features or "", user_query, query_id)
                if creative_role:
                    decision_query += f"Creative Role: {creative_role}\n"
                    logger.info(f"Added creative role to decision query: {creative_role}")
            except Exception as e:
                logger.error(f"Error determining creative role for decision: {e}")

        # Add search context information if available
        if search_context_info:
            decision_query += f"{search_context_info}\n"

        if existing_data:
            decision_query += f"Previously Generated Creatives are:"
            for data in existing_data:
                # Add creative role information if available
                if 'role' in data:
                    decision_query += f"{data} (Role: {data['role']})\n"
                else:
                    decision_query += f"{data}\n"

        # log the entire input to the decision prompt
        logger.info(f"Inputs submitted to the decision prompt:\nuserquery:{user_query}\nsystemprompt:{decision_system_prompt}\nconversationhistory:{formatted_history}")

        decision_response = await generate_response(
            query=decision_query,
            system_prompt=decision_system_prompt,
            conversation_history=conversation_history,
            max_tokens=256,
            model="gpt-4o-mini",
            response_class=ImageModelDecider,
            query_id=query_id,
            agent_name="creative_decision_agent")

        decision_response_json = json.loads(decision_response)

        logger.info(f"Decision response:\n{decision_response_json}")
        reference_image = None

        # Extract decision data from the structured response
        operation = decision_response_json["operation"]
        target_dimensions = decision_response_json.get("target_dimensions")
        reference_type = decision_response_json["reference_type"]
        selected_url = decision_response_json["reference_url"]
        image_title = decision_response_json["title"]

        # Log operation type
        model_usage["operation"] = operation
        logger.info(f"[MODEL TRACKING] Operation selected: {operation}")

        logger.info(f"Decision: Operation={operation}, Type={reference_type}, URL={selected_url}, Title={image_title}, Dimensions={target_dimensions}")

        # Get the explanation from the decision agent
        explanation_message = decision_response_json.get("explanation", "")
        if not explanation_message:
            # Fallback in case the explanation is missing
            logger.warning("Decision agent did not provide an explanation, using default message")
            if operation == "resize":
                explanation_message = f"I'll resize your image to {target_dimensions}."
            elif operation == "multi_generate":
                explanation_message = f"I'll create multiple versions of your image in different aspect ratios."
            elif operation == "resize_to_iab":
                explanation_message = f"I'll generate your image in standard IAB ad sizes."
            elif operation == "generate":
                explanation_message = f"I'll create a new image based on your description."

        # Store the explanation for later use
        # This is important as we'll need to include it in the final response

        # Update frontend with decision and explanation
        yield {"status": "decided", "message": f"{explanation_message}\n\nCreating {image_title}...", "operation": operation}

        # Send the explanation as a separate response that the frontend can handle
        # This ensures the explanation appears in the chat
        yield {"response": explanation_message, "partial": True}

        if reference_type == "url" and selected_url:
            yield {"status": "loading_reference", "message": "Loading reference image..."}
            try:
                response = requests.get(selected_url)
                response.raise_for_status()
                reference_image = PIL_Image.open(BytesIO(response.content))
                logger.info(f"Successfully loaded image from URL: {selected_url}")
            except Exception as e:
                logger.error(f"Error fetching image from URL: {str(e)}")
                yield {"status": "warning", "message": f"Warning: Could not load reference image: {str(e)}"}

        elif reference_type == "creative input" and creative:
            yield {"status": "loading_reference", "message": "Processing your uploaded creative..."}
            # Use the original creative input
            url_type = check_url_type(creative)
            if url_type == 'base64':
                try:
                    # Split the base64 string to get the data part
                    _, base64_data = creative.split(",", 1)
                    missing_padding = len(base64_data) % 4
                    if missing_padding:
                        base64_data += "=" * (4 - missing_padding)
                    image_data = base64.b64decode(base64_data)
                    reference_image = PIL_Image.open(BytesIO(image_data))
                    logger.info("Successfully loaded image from creative input (base64)")
                except Exception as e:
                    logger.error(f"Error decoding base64 creative: {str(e)}")
                    yield {"status": "warning", "message": f"Warning: Could not process creative: {str(e)}"}
            elif url_type == 'direct_link':
                try:
                    response = requests.get(creative)
                    response.raise_for_status()
                    reference_image = PIL_Image.open(BytesIO(response.content))
                    logger.info("Successfully loaded image from creative input (URL)")
                except Exception as e:
                    logger.error(f"Error fetching image from creative URL: {str(e)}")
                    yield {"status": "warning", "message": f"Warning: Could not load creative from URL: {str(e)}"}
        elif reference_type == "None":
            logger.info("No reference image will be used as per decision")
        system_prompt = load_prompt("creative_agent_generation")
        # Handle resize operation
        if operation == "resize" and reference_image:
            yield {"status": "resizing", "message": f"Resizing image to {target_dimensions}..."}
            model_usage["primary_model"] = "Imagen 3.0 API"
            model_usage["steps"].append("Starting resize with Imagen 3.0 API")
            logger.info(f"[MODEL TRACKING] Attempting resize with Imagen 3.0 API to dimensions {target_dimensions}")
            # Calculate target size from aspect ratio/dimensions
            original_size = reference_image.size
            logger.debug("Trying to Resize")
            target_dimensions = decision_response_json.get("target_dimensions")
            upscale_factor = 1
            try:
                logger.debug("Attempting to use Imagen 3.0 API for resizing")
                yield {"status": "processing", "message": "Applying resizing ..."}

                # Use the new resize_image_with_imagen function
                upscaled_image = resize_image_with_imagen(
                    image_path=reference_image,
                    target_dimensions=target_dimensions,
                    upscale_factor=upscale_factor
                )

                if upscaled_image:
                    # Convert the resized image to bytes
                    response_data = get_bytes_from_pil(upscaled_image)
                    logger.debug(f"Resized image dimensions: {upscaled_image.size}")
                else:
                    raise ValueError("No image returned from resize_image_with_imagen")

                logger.debug("Image resizing completed successfully with Imagen API")
                logger.info(f"[MODEL TRACKING] Successfully used Imagen 3.0 API for resizing to {target_dimensions}")
                model_usage["steps"].append("Imagen 3.0 API resize successful")

            except Exception as e:
                logger.warning(f"Imagen API resizing failed: {str(e)}")
                logger.info("Falling back to standard Gemini image generation")
                logger.info(f"[MODEL TRACKING] Falling back to Gemini 2.0 Flash for resizing after Imagen failure")
                model_usage["fallback_model"] = "Gemini 2.0 Flash"
                model_usage["steps"].append("Fallback to Gemini 2.0 Flash after Imagen failure")

                # Calculate target size for fallback method
                target_size = calculate_target_size(
                    original_size,
                    dimensions=target_dimensions
                )
                logger.debug(f"Target size for fallback: {target_size}")

                # Fallback using standard Gemini (existing code)
                generation_config = types.GenerateContentConfig(
                    response_modalities=['Text', 'Image']
                )

                resize_prompt = f"Expand this image to {target_dimensions} dimensions. {user_query}"

                yield {"status": "generating", "message": "Generating resized image..."}

                # Add retry logic for Gemini API calls
                max_retries = 3
                retry_count = 0
                retry_delay = 1  # Initial delay in seconds

                while retry_count <= max_retries:
                    try:
                        if retry_count > 0:
                            yield {"status": "retrying", "message": f"Retrying image generation (attempt {retry_count} of {max_retries})..."}
                            logger.warning(f"Retrying Gemini image generation for resize (attempt {retry_count} of {max_retries})")

                        response = Googleclient.models.generate_content(
                            model='gemini-2.0-flash-exp-image-generation',
                            contents=[resize_prompt, reference_image],
                            config=generation_config
                        )
                        # If we get here, the call succeeded
                        break
                    except Exception as e:
                        retry_count += 1
                        error_message = str(e)
                        logger.error(f"Gemini API error during resize (attempt {retry_count} of {max_retries}): {error_message}")

                        # Check if it's a 500 internal server error or other retryable error
                        if "500" in error_message or "internal server error" in error_message.lower() or "timeout" in error_message.lower():
                            if retry_count <= max_retries:
                                # Use exponential backoff
                                wait_time = retry_delay * (2 ** (retry_count - 1))
                                logger.info(f"Waiting {wait_time} seconds before retry...")
                                yield {"status": "waiting", "message": f"Server error occurred. Waiting {wait_time} seconds before retry..."}
                                await asyncio.sleep(wait_time)
                            else:
                                logger.error(f"Max retries reached. Giving up on Gemini image resize.")
                                yield {"status": "error", "message": "Failed to resize image after multiple attempts. Please try again later."}
                                raise
                        else:
                            # Not a retryable error
                            logger.error(f"Non-retryable error during resize: {error_message}")
                            yield {"status": "error", "message": f"Error resizing image: {error_message}"}
                            raise

                response_data = None
                for part in response.candidates[0].content.parts:
                    if part.inline_data:
                        response_data = part.inline_data.data
                        break

                if not response_data:
                    raise ValueError("Failed to generate image with fallback method")
                logger.info(f"[MODEL TRACKING] Successfully used Gemini 2.0 Flash for resizing fallback")
                model_usage["steps"].append("Gemini 2.0 Flash resize successful")

            yield {"status": "uploading", "message": "Uploading resized image..."}
            logger.debug("Uploading resized image to S3")
            uploaded_result = upload_to_s3(response_data)

            # Store S3 key instead of URL for persistent storage
            result["S3Key"] = uploaded_result["key"]
            result["Title"] = image_title

            # Create markdown with S3 key for database storage
            markdown_with_s3_key = f"{image_title} ![{image_title}]({uploaded_result['key']})"
            result["MarkdownOutput"] = markdown_with_s3_key

            # Convert S3 key to URL for frontend display
            from tools.store_s3 import process_s3_keys_to_urls
            markdown_with_url = process_s3_keys_to_urls(markdown_with_s3_key, expires_in=7200)

            # Include the explanation in the result
            result["Explanation"] = explanation_message
            logger.info(f"Explanation added to the result object: {result['Explanation']}")
            logger.debug(f"Result S3 Key: {result['S3Key']}")

            # Final result with the image (send URL version to frontend)
            frontend_result = result.copy()
            frontend_result["MarkdownOutput"] = markdown_with_url
            yield {"status": "complete", "message": "Image resizing complete!", "result": frontend_result}
            # Return early to avoid continuing with native Gemini generation
            return

        # Handle IAB standard sizes generation
        elif operation == "resize_to_iab":
            yield {"status": "resize_to_iab", "message": "Preparing to generate IAB standard ad sizes..."}
            logger.debug("Starting resize_to_iab operation")
            logger.info(f"[MODEL TRACKING] Using Blackforest Labs API (flux-pro-1.1) for IAB standard sizes")
            model_usage["primary_model"] = "Blackforest Labs (flux-pro-1.1)"
            model_usage["steps"].append("Starting IAB size generation with Blackforest Labs")

            # Initialize the Blackforest IAB size generator
            iab_generator = BlackforestIABGenerator()

            # Generate a prompt for the IAB images
            system_prompt = load_prompt("creative_agent_generation_iab")

            # Check if we need to extract features
            features_to_use = extracted_features
            if not features_to_use and reference_image:
                yield {"status": "extracting_features", "message": "Analyzing reference image..."}
                logger.debug("Reference image found, extracting features")

                # If it's a URL, use it directly with creative_to_features
                if reference_type == "url" and selected_url:
                    try:
                        features_to_use = creative_to_features(selected_url, query_id)
                        logger.info("Successfully extracted features from reference URL")
                    except Exception as e:
                        logger.error(f"Error extracting features from URL: {str(e)}")
                        yield {"status": "warning", "message": f"Warning: Could not extract features from reference image: {str(e)}"}

                # If it's from creative input
                elif reference_type == "creative input" and creative:
                    url_type = check_url_type(creative)
                    if url_type == 'direct_link':
                        try:
                            features_to_use = creative_to_features(creative, query_id)
                            logger.info("Successfully extracted features from creative URL")
                        except Exception as e:
                            logger.error(f"Error extracting features from creative URL: {str(e)}")
                            yield {"status": "warning", "message": f"Warning: Could not extract features from creative: {str(e)}"}
                    elif url_type == 'base64':
                        # For base64 images, we already have the reference_image loaded as PIL Image
                        # We need to upload it to S3 to get a URL for creative_to_features
                        try:
                            image_data = get_bytes_from_pil(reference_image)
                            uploaded_result = upload_to_s3(image_data)
                            temp_url = uploaded_result["url"]
                            features_to_use = creative_to_features(temp_url, query_id)
                            logger.info("Successfully extracted features from uploaded image")
                        except Exception as e:
                            logger.error(f"Error extracting features from uploaded image: {str(e)}")
                            yield {"status": "warning", "message": f"Warning: Could not extract features from uploaded image: {str(e)}"}

                # If features were extracted or provided, append them to the system prompt
                if features_to_use:
                    # Limit the extracted features to 500 words if it's too long
                    words = features_to_use.split()
                    if len(words) > 500:
                        features_to_use = " ".join(words[:500])
                        logger.info("Features truncated to 500 words")

                    system_prompt += f"\n\nReference Image Features: {features_to_use}"
                    logger.info("Added features to system prompt")

            # Generate the prompt with the enhanced system prompt
            # Convert search_results to string if it's a SearchResult object
            search_results_str = None
            if search_results and hasattr(search_results, 'results'):
                search_results_str = json.dumps([result.model_dump() for result in search_results.results])
            elif search_results:
                search_results_str = search_results

            generated_prompt = await generate_response(
                query=user_query,
                system_prompt=system_prompt,
                search_result=search_results_str,
                conversation_history=conversation_history,
                max_tokens=500,
                query_id=query_id,
                agent_name="creative_prompt_generator"
            )

            logger.info(f"Generated prompt for IAB sizes:\n{generated_prompt}")
            result["PromptUsed"] = generated_prompt

            # Check if specific IAB sizes were requested in the decision
            specific_sizes = None
            if hasattr(decision_response_json, "iab_sizes") and decision_response_json.get("iab_sizes"):
                specific_sizes = decision_response_json.get("iab_sizes")
                logger.info(f"Specific IAB sizes requested: {specific_sizes}")

            # Generate IAB sizes (all or specific ones) with proper reference image handling
            async for chunk in iab_generator.generate_all_iab_sizes(generated_prompt, image_title, specific_sizes, reference_image):
                # If this is the final result, add the explanation to it
                if chunk.get("status") == "complete" and chunk.get("is_resize_to_iab"):
                    # Don't add explanation to the message, just to the result
                    if "result" not in chunk:
                        chunk["result"] = {}
                    chunk["result"]["Explanation"] = explanation_message
                    logger.info(f"Explanation added to IAB result object: {explanation_message}")

                yield chunk

                # If this is the final result, store it and return
                if chunk.get("status") == "complete" and chunk.get("is_resize_to_iab"):
                    logger.debug("Blackforest IAB size generation completed")
                    return

            # If we get here, something went wrong
            logger.error("IAB size generation did not complete properly")
            yield {"status": "error", "message": "Failed to generate IAB standard ad sizes"}
            return

        # Handle multi_generate operation
        elif operation == "multi_generate":
            yield {"status": "multi_generate", "message": "Preparing to generate multiple aspect ratios..."}
            logger.debug("Starting multi_generate operation")
            logger.info(f"[MODEL TRACKING] Using Gemini 2.0 Flash to generate base image for multi_generate")
            model_usage["primary_model"] = "Gemini 2.0 Flash + Imagen 3.0"
            model_usage["steps"].append("Generating base image with Gemini 2.0 Flash")

            # Standard dimensions to generate
            standard_dimensions = ["1024x1024", "768x1408", "1408x768", "896x1280", "1280x896"]

            # Create a base reference image if none is provided
            base_reference_image = reference_image
            base_reference_data = None

            # If no reference image is provided, generate one first
            if not base_reference_image:
                yield {"status": "generating_base", "message": "Creating base image..."}
                logger.debug("No reference image provided, generating base image first")

                # Generate a prompt for the base image
                system_prompt = load_prompt("creative_agent_generation")

                # Convert search_results to string if it's a SearchResult object
                search_results_str = None
                if search_results and hasattr(search_results, 'results'):
                    search_results_str = json.dumps([result.model_dump() for result in search_results.results])
                elif search_results:
                    search_results_str = search_results

                generated_prompt = await generate_response(
                    query=user_query,
                    system_prompt=system_prompt,
                    search_result=search_results_str,
                    conversation_history=conversation_history,
                    max_tokens=500,
                    query_id=query_id,
                    agent_name="creative_base_prompt_generator"
                )

                try:
                    generation_config = types.GenerateContentConfig(
                        response_modalities=['Text', 'Image']
                    )

                    # Add retry logic for Gemini API calls
                    max_retries = 3
                    retry_count = 0
                    retry_delay = 1  # Initial delay in seconds

                    while retry_count <= max_retries:
                        try:
                            if retry_count > 0:
                                yield {"status": "retrying", "message": f"Retrying base image generation (attempt {retry_count} of {max_retries})..."}
                                logger.warning(f"Retrying Gemini base image generation (attempt {retry_count} of {max_retries})")

                            response = Googleclient.models.generate_content(
                                model="gemini-2.0-flash-exp-image-generation",
                                contents=[generated_prompt],
                                config=generation_config
                            )
                            # If we get here, the call succeeded
                            break
                        except Exception as e:
                            retry_count += 1
                            error_message = str(e)
                            logger.error(f"Gemini API error during base image generation (attempt {retry_count} of {max_retries}): {error_message}")

                            # Check if it's a 500 internal server error or other retryable error
                            if "500" in error_message or "internal server error" in error_message.lower() or "timeout" in error_message.lower():
                                if retry_count <= max_retries:
                                    # Use exponential backoff
                                    wait_time = retry_delay * (2 ** (retry_count - 1))
                                    logger.info(f"Waiting {wait_time} seconds before retry...")
                                    yield {"status": "waiting", "message": f"Server error occurred. Waiting {wait_time} seconds before retry..."}
                                    await asyncio.sleep(wait_time)
                                else:
                                    logger.error(f"Max retries reached. Giving up on Gemini base image generation.")
                                    yield {"status": "error", "message": "Failed to generate base image after multiple attempts. Please try again later."}
                                    raise
                            else:
                                # Not a retryable error
                                logger.error(f"Non-retryable error during base image generation: {error_message}")
                                yield {"status": "error", "message": f"Error generating base image: {error_message}"}
                                raise

                    base_reference_data = None

                    # Extract the base image with proper null checks
                    if response and hasattr(response, 'candidates') and response.candidates:
                        if len(response.candidates) > 0 and hasattr(response.candidates[0], 'content'):
                            if hasattr(response.candidates[0].content, 'parts'):
                                for part in response.candidates[0].content.parts:
                                    if part and hasattr(part, 'inline_data') and part.inline_data:
                                        base_reference_data = part.inline_data.data
                                        break
                            else:
                                logger.error("Base image response candidates[0].content has no 'parts' attribute")
                        else:
                            logger.error("Base image response has no valid candidates or content")
                    else:
                        logger.error("Base image response is None or has no 'candidates' attribute")

                    # Log the response structure for debugging
                    logger.debug(f"Base image response structure: {str(response)[:200]}...")

                    if base_reference_data:
                        # Convert to PIL Image for further processing
                        base_reference_image = PIL_Image.open(BytesIO(base_reference_data))
                        logger.debug(f"Base image generated with dimensions: {base_reference_image.size}")
                    else:
                        logger.error("Failed to generate base reference image - no image data found in response")
                        yield {"status": "error", "message": "Failed to generate base reference image"}
                        raise ValueError("Failed to generate base reference image - no image data found in response")
                except Exception as e:
                    logger.error(f"Error generating base reference image: {str(e)}")
                    yield {"status": "error", "message": f"Failed to generate base reference image: {str(e)}"}
                    raise ValueError(f"Failed to generate base reference image: {str(e)}")
                logger.info(f"[MODEL TRACKING] Successfully generated base image with Gemini 2.0 Flash")
                model_usage["steps"].append("Base image generation with Gemini 2.0 Flash successful")

            # Now generate images for all standard dimensions
            multi_results = []
            total_dimensions = len(standard_dimensions)

            for i, dimensions in enumerate(standard_dimensions):
                try:
                    yield {"status": "generating_variant", "message": f"Generating image {i+1} of {total_dimensions}: {dimensions}"}
                    logger.debug(f"Generating image for dimensions: {dimensions}")
                    logger.info(f"[MODEL TRACKING] Using Imagen 3.0 API for variant {i+1}/{len(standard_dimensions)}: {dimensions}")
                    model_usage["steps"].append(f"Generating variant for {dimensions} with Imagen 3.0")

                    # Parse dimensions to get width and height
                    width, height = map(int, dimensions.split('x'))

                    # Get aspect ratio for display purposes
                    aspect_ratio = get_aspect_ratio_from_dimensions(width, height)

                    try:
                        # Use Imagen 3 API for resizing/generating
                        variant_image = resize_image_with_imagen(
                            image_path=base_reference_image,
                            target_dimensions=dimensions,
                            upscale_factor=1
                        )

                        if variant_image:
                            # Convert the image to bytes and upload
                            variant_data = get_bytes_from_pil(variant_image)
                            if not variant_data:
                                raise ValueError("Failed to convert image to bytes")

                            uploaded_variant = upload_to_s3(variant_data)
                            if not uploaded_variant or "key" not in uploaded_variant:
                                raise ValueError("Failed to upload image to S3 or get key")

                            # Add to results
                            variant_result = {
                                "S3Key": uploaded_variant["key"],
                                "Title": f"{image_title} ({aspect_ratio})",
                                "AspectRatio": aspect_ratio,
                                "Dimensions": dimensions
                            }

                            multi_results.append(variant_result)
                            logger.debug(f"Successfully generated image for {dimensions}")
                            logger.info(f"[MODEL TRACKING] Successfully generated variant for {dimensions} with Imagen 3.0")
                            model_usage["steps"].append(f"Variant for {dimensions} with Imagen 3.0 successful")

                            # Stream each image as it's generated - immediately yield to frontend
                            # Create markdown with S3 key for database storage
                            markdown_with_s3_key = f" \n\n {image_title} -{aspect_ratio}({dimensions}))\n\n![{image_title} ({aspect_ratio})]({uploaded_variant['key']})"

                            # Convert S3 key to URL for frontend display
                            from tools.store_s3 import process_s3_keys_to_urls
                            markdown_with_url = process_s3_keys_to_urls(markdown_with_s3_key, expires_in=7200)

                            partial_result = {
                                "S3Key": uploaded_variant["key"],  # Store S3 key for database
                                "Title": f"{image_title} ({aspect_ratio})",
                                "AspectRatio": aspect_ratio,
                                "Dimensions": dimensions,
                                "MarkdownOutput": markdown_with_s3_key  # Store S3 key version for database
                            }

                            # Create frontend version with URL
                            frontend_partial_result = partial_result.copy()
                            frontend_partial_result["MarkdownOutput"] = markdown_with_url

                            # Yield the partial result immediately
                            await asyncio.sleep(0)  # Allow event loop to process before continuing
                            yield {"status": "partial_result", "message": f"Generated {aspect_ratio} variant", "result": frontend_partial_result, "index": i, "total": total_dimensions}
                        else:
                            logger.warning(f"Failed to generate image for dimensions {dimensions} - resize_image_with_imagen returned None")
                            yield {"status": "warning", "message": f"Could not generate image for {dimensions}"}
                    except Exception as e:
                        logger.error(f"Error processing variant for dimensions {dimensions}: {str(e)}")
                        yield {"status": "warning", "message": f"Error generating {dimensions} variant: {str(e)}"}

                except Exception as e:
                    logger.error(f"Error generating image for dimensions {dimensions}: {str(e)}")
                    yield {"status": "error", "message": f"Error generating {dimensions} variant: {str(e)}"}

            # Prepare the final result with all generated images
            if multi_results:
                # Create a markdown summary of all images using S3 keys for database storage
                markdown_output = f"### Native Aspect Ratios\n\n"
                for variant in multi_results:
                    markdown_output += f"\n\n **{variant['AspectRatio']} ({variant['Dimensions']}):**\n"
                    markdown_output += f"![{variant['Title']}]({variant['S3Key']})\n\n"

                result["MultiResults"] = multi_results
                result["Title"] = image_title
                result["MarkdownOutput"] = markdown_output  # Store S3 key version for database
                # Include the explanation in the result
                result["Explanation"] = explanation_message
                logger.info(f"Explanation added to the result object: {result['Explanation']}")
                logger.debug(f"Multi-generate operation completed with {len(multi_results)} images")
                logger.info(f"[MODEL TRACKING] Completed multi-generate operation with {len(multi_results)} images")

                # Send a completion status with a flag indicating this is a multi-generate result
                # This is just a status update, not containing the actual images (they were already sent)
                yield {"status": "complete", "message": f"Successfully generated {len(multi_results)} images!", "is_multi_generate": True, "result": result}
                # Return early to avoid continuing with native Gemini generation
                return
            else:
                logger.error("Multi-generate operation failed: No images were generated")
                yield {"status": "error", "message": "Failed to generate any images"}
                raise ValueError("Failed to generate any images in multi_generate operation")

        # Existing generation flow for non-resize cases
        yield {"status": "creating_prompt", "message": "Crafting the perfect prompt for your image..."}

        # Convert search_results to string if it's a SearchResult object
        search_results_str = None
        if search_results and hasattr(search_results, 'results'):
            search_results_str = json.dumps([result.model_dump() for result in search_results.results])
        elif search_results:
            search_results_str = search_results

        if reference_image:
            generated_prompt = await generate_response(
                query=f"{user_query} A reference Image has been attached. Use it for your generation.",
                system_prompt=system_prompt,
                search_result=search_results_str,
                conversation_history=conversation_history,
                max_tokens=500,
                query_id=query_id,
                agent_name="creative_prompt_generator_with_ref"
            )

            logger.info(f"Inputs submitted to the generated prompt:\nuserquery:{user_query} A reference Image has been attached. Use it for your generation. \nsystemprompt:{system_prompt}\nconversationhistory:{formatted_history}")
        else:
            generated_prompt = await generate_response(
                query=user_query,
                system_prompt=system_prompt,
                search_result=search_results_str,
                conversation_history=conversation_history,
                max_tokens=500,
                query_id=query_id,
                agent_name="creative_prompt_generator"
            )
            logger.info(f"Inputs submitted to the generated prompt:\nuserquery:{user_query}\nsystemprompt:{system_prompt}\nSearchresult: {search_results}\nconversationhistory:{formatted_history}")


        logger.info(f"Generated prompt:\n{generated_prompt}")
        result["PromptUsed"] = generated_prompt

        # Existing Gemini image generation
        yield {"status": "generating", "message": "Generating your image..."}
        response_data = None

        generation_config = types.GenerateContentConfig(
            response_modalities=['Text', 'Image']
        )

        if reference_image:
            generated_prompt = f"Make full use of the reference image attached. {generated_prompt}"
            # Add retry logic for Gemini API calls
            max_retries = 3
            retry_count = 0
            retry_delay = 1  # Initial delay in seconds

            while retry_count <= max_retries:
                try:
                    if retry_count > 0:
                        yield {"status": "retrying", "message": f"Retrying image generation (attempt {retry_count} of {max_retries})..."}
                        logger.warning(f"Retrying Gemini image generation (attempt {retry_count} of {max_retries})")

                    response = Googleclient.models.generate_content(
                        model='gemini-2.0-flash-exp-image-generation',
                        contents=[generated_prompt, reference_image],
                        config=generation_config
                    )
                    # If we get here, the call succeeded
                    break
                except Exception as e:
                    retry_count += 1
                    error_message = str(e)
                    logger.error(f"Gemini API error (attempt {retry_count} of {max_retries}): {error_message}")

                    # Check if it's a 500 internal server error or other retryable error
                    if "500" in error_message or "internal server error" in error_message.lower() or "timeout" in error_message.lower():
                        if retry_count <= max_retries:
                            # Use exponential backoff
                            wait_time = retry_delay * (2 ** (retry_count - 1))
                            logger.info(f"Waiting {wait_time} seconds before retry...")
                            yield {"status": "waiting", "message": f"Server error occurred. Waiting {wait_time} seconds before retry..."}
                            await asyncio.sleep(wait_time)
                        else:
                            logger.error(f"Max retries reached. Giving up on Gemini image generation.")
                            yield {"status": "error", "message": "Failed to generate image after multiple attempts. Please try again later."}
                            raise
                    else:
                        # Not a retryable error
                        logger.error(f"Non-retryable error: {error_message}")
                        yield {"status": "error", "message": f"Error generating image: {error_message}"}
                        raise
        else:
            # Add retry logic for Gemini API calls
            max_retries = 3
            retry_count = 0
            retry_delay = 1  # Initial delay in seconds

            while retry_count <= max_retries:
                try:
                    if retry_count > 0:
                        yield {"status": "retrying", "message": f"Retrying image generation (attempt {retry_count} of {max_retries})..."}
                        logger.warning(f"Retrying Gemini image generation (attempt {retry_count} of {max_retries})")

                    response = Googleclient.models.generate_content(
                        model='gemini-2.0-flash-exp-image-generation',
                        contents=[generated_prompt],
                        config=generation_config
                    )
                    # If we get here, the call succeeded
                    break
                except Exception as e:
                    retry_count += 1
                    error_message = str(e)
                    logger.error(f"Gemini API error (attempt {retry_count} of {max_retries}): {error_message}")

                    # Check if it's a 500 internal server error or other retryable error
                    if "500" in error_message or "internal server error" in error_message.lower() or "timeout" in error_message.lower():
                        if retry_count <= max_retries:
                            # Use exponential backoff
                            wait_time = retry_delay * (2 ** (retry_count - 1))
                            logger.info(f"Waiting {wait_time} seconds before retry...")
                            yield {"status": "waiting", "message": f"Server error occurred. Waiting {wait_time} seconds before retry..."}
                            await asyncio.sleep(wait_time)
                        else:
                            logger.error(f"Max retries reached. Giving up on Gemini image generation.")
                            yield {"status": "error", "message": "Failed to generate image after multiple attempts. Please try again later."}
                            raise
                    else:
                        # Not a retryable error
                        logger.error(f"Non-retryable error: {error_message}")
                        yield {"status": "error", "message": f"Error generating image: {error_message}"}
                        raise

        # Initialize response_data
        response_data = None

        # Extract and process image with proper null checks
        if response and hasattr(response, 'candidates') and response.candidates:
            if len(response.candidates) > 0 and hasattr(response.candidates[0], 'content'):
                if hasattr(response.candidates[0].content, 'parts'):
                    for part in response.candidates[0].content.parts:
                        if part and hasattr(part, 'inline_data') and part.inline_data:
                            response_data = part.inline_data.data
                            break
                else:
                    logger.error("Response candidates[0].content has no 'parts' attribute")
            else:
                logger.error("Response has no valid candidates or content")
        else:
            logger.error("Response is None or has no 'candidates' attribute")

        # Log the response structure for debugging
        logger.debug(f"Response structure: {str(response)[:200]}...")

        if response_data:
            yield {"status": "uploading", "message": "Uploading your generated image..."}
            uploaded_result = upload_to_s3(response_data)
            result["S3Key"] = uploaded_result["key"]
            result["Title"] = image_title

            # Create markdown with S3 key for database storage
            markdown_with_s3_key = f" {image_title} ![{image_title}]({uploaded_result['key']})"
            result["MarkdownOutput"] = markdown_with_s3_key

            # Convert S3 key to URL for frontend display
            from tools.store_s3 import process_s3_keys_to_urls
            markdown_with_url = process_s3_keys_to_urls(markdown_with_s3_key, expires_in=7200)

            # Include the explanation in the result
            result["Explanation"] = explanation_message
            logger.info(f"Explanation added to the result object: {result['Explanation']}")
            logger.info(f"[MODEL TRACKING] Successfully generated image with Gemini 2.0 Flash")
            model_usage["steps"].append("Gemini 2.0 Flash generation successful")
            # Add model usage to result for client-side tracking
            result["ModelUsage"] = model_usage

            # Final result with the image (send URL version to frontend)
            frontend_result = result.copy()
            frontend_result["MarkdownOutput"] = markdown_with_url
            yield {"status": "complete", "message": "Image generation complete!", "result": frontend_result}
        else:
            yield {"status": "error", "message": "Failed to generate image"}

    except Exception as e:
        logger.error(f"Image generation failed: {str(e)}")
        yield {"status": "error", "message": f"Image generation failed: {str(e)}"}
        raise HTTPException(status_code=500, detail="Image generation failed")

    # yield {"status": "error", "message": "Image generation failed with unknown error"}


def get_aspect_ratio_from_dimensions(width, height):
    """
    Calculate the aspect ratio from width and height.

    Args:
        width: Width in pixels
        height: Height in pixels

    Returns:
        String representation of the aspect ratio (e.g., "16:9")
    """
    # Standard dimensions and their aspect ratios
    if width == 1024 and height == 1024:
        return "1:1"
    elif width == 768 and height == 1408:
        return "9:16"
    elif width == 1408 and height == 768:
        return "16:9"
    elif width == 896 and height == 1280:
        return "3:4"
    elif width == 1280 and height == 896:
        return "4:3"

    # Calculate GCD for custom dimensions
    import math
    gcd = math.gcd(width, height)
    return f"{width//gcd}:{height//gcd}"

def calculate_target_size(original_size, aspect_ratio=None, dimensions=None):
    """
    Calculate the target size for an image based on aspect ratio or specific dimensions.

    Args:
        original_size: Tuple of (width, height) of the original image
        aspect_ratio: String in format "w:h" (e.g., "16:9")
        dimensions: String in format "widthxheight" (e.g., "1024x1024")

    Returns:
        Tuple of (width, height) for the target size
    """
    logger.debug(f"Calculating target size for original size: {original_size}, aspect ratio: {aspect_ratio}, dimensions: {dimensions}")

    # Standard target dimensions for specific aspect ratios
    standard_dimensions = {
        "1:1": (1024, 1024),
        "9:16": (768, 1408),
        "16:9": (1408, 768),
        "3:4": (896, 1280),
        "4:3": (1280, 896)
    }

    # If specific dimensions are provided, use them directly
    if dimensions:
        return tuple(map(int, dimensions.split('x')))

    # If aspect ratio is provided
    if aspect_ratio:
        # If it's a standard aspect ratio, use the predefined dimensions
        if aspect_ratio in standard_dimensions:
            logger.debug(f"Using standard dimensions for {aspect_ratio}: {standard_dimensions[aspect_ratio]}")
            return standard_dimensions[aspect_ratio]

        # Otherwise calculate based on the aspect ratio
        w, h = map(int, aspect_ratio.split(':'))
        target_ratio = w / h
        orig_w, orig_h = original_size
        current_ratio = orig_w / orig_h

        if target_ratio > current_ratio:
            new_w = int(orig_h * target_ratio)
            logger.debug(f"New width: {new_w}, original height: {orig_h}")
            return (new_w, orig_h)
        else:
            new_h = int(orig_w / target_ratio)
            logger.debug(f"New height: {new_h}, original width: {orig_w}")
            return (orig_w, new_h)

    # If no aspect ratio or dimensions provided, return original size
    return original_size

def get_bytes_from_pil(image: PIL_Image.Image) -> bytes:
    byte_io = io.BytesIO()
    image.save(byte_io, "PNG")
    return byte_io.getvalue()

def pad_to_target_size(
    source_image: PIL_Image.Image,
    target_size: tuple,
    mode: str = "RGB",
    vertical_offset_ratio: float = 0,
    horizontal_offset_ratio: float = 0,
    fill_val: int = 255
) -> PIL_Image.Image:
    """Helper function to pad images to target size"""
    orig_w, orig_h = source_image.size
    target_w, target_h = target_size

    insert_x = (target_w - orig_w) // 2 + int(horizontal_offset_ratio * target_w)
    insert_y = (target_h - orig_h) // 2 + int(vertical_offset_ratio * target_h)

    padded_image = PIL_Image.new(mode, target_size, color=fill_val)
    padded_image.paste(source_image, (insert_x, insert_y))
    return padded_image

def resize_image_with_imagen(image_path, target_dimensions=None, upscale_factor=2):
    """Resize image using Vertex AI Imagen 3 API -
        Supported target dimensions are:
        1:1 (Square): 1024x1024 pixels.
        3:4 (Portrait/Mobile Portrait): 896x1280 pixels.
        4:3 (Landscape/Fullscreen): 1280x896 pixels.
        9:16 (Portrait/Tall): 768x1408 pixels.
        16:9 (Landscape/Widescreen): 1408x768 pixels.

    Args:
        image_path: Either a file path string or a PIL Image object
        target_dimensions: Optional string in format "widthxheight" (e.g., "800x600")
        upscale_factor: Factor to upscale by if target_dimensions not provided

    Returns:
        PIL Image object of the resized image, or None if the operation failed
    """
    # Load the image
    if isinstance(image_path, str):
        # Load from file path
        image = PIL_Image.open(image_path)
    else:
        # Assume it's already a PIL Image
        image = image_path

    logger.debug(f"Original image dimensions: {image.size}")

    # If target dimensions are provided, calculate the target size
    if target_dimensions:
        target_size = calculate_target_size(image.size, dimensions=target_dimensions)
    else:
        # Default to upscaling by the specified factor
        orig_w, orig_h = image.size
        target_size = (orig_w * upscale_factor, orig_h * upscale_factor)

    logger.debug(f"Target dimensions: {target_size}")

    # For upscaling, we'll use the Imagen 3 API directly
    try:
        # Get authentication token
        auth_token = get_access_token()

        # Prepare the API request
        url = f"https://{LOCATION}-aiplatform.googleapis.com/v1/projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/imagen-3.0-capability-001:predict"

        headers = {
            "Authorization": f"Bearer {auth_token}",
            "Content-Type": "application/json"
        }

        # For upscaling using outpainting approach instead
        # Create a larger canvas with the target dimensions
        orig_w, orig_h = image.size
        target_w, target_h = target_size

        # Create padded image and mask for "upscaling"
        # We'll use outpainting to achieve upscaling since EDIT_MODE_UPSCALE is not supported
        padded_image = PIL_Image.new("RGB", target_size, color=(0, 0, 0))

        # Calculate position to place the original image (centered)
        insert_x = (target_w - orig_w) // 2
        insert_y = (target_h - orig_h) // 2

        # Paste the original image onto the canvas
        padded_image.paste(image, (insert_x, insert_y))

        # Create a mask where:
        # - Black (0) represents the original image area (to keep)
        # - White (255) represents the padding area (to fill with outpainting)
        padded_mask = PIL_Image.new("L", target_size, color=255)  # Start with all white

        # Create a temporary black rectangle the size of the original image
        temp_mask = PIL_Image.new("L", (orig_w, orig_h), color=0)

        # Paste the black rectangle onto the mask at the same position as the image
        padded_mask.paste(temp_mask, (insert_x, insert_y))

        # Convert images to base64
        padded_image_b64 = base64.b64encode(get_bytes_from_pil(padded_image)).decode('utf-8')
        mask_b64 = base64.b64encode(get_bytes_from_pil(padded_mask)).decode('utf-8')

        # For upscaling using outpainting
        payload = {
            "instances": [
                {
                    "prompt": "",  # Empty prompt for outpainting
                    "referenceImages": [
                        {
                            "referenceType": "REFERENCE_TYPE_RAW",
                            "referenceId": 1,
                            "referenceImage": {
                                "bytesBase64Encoded": padded_image_b64
                            }
                        },
                        {
                            "referenceType": "REFERENCE_TYPE_MASK",
                            "referenceId": 2,
                            "referenceImage": {
                                "bytesBase64Encoded": mask_b64
                            },
                            "maskImageConfig": {
                                "maskMode": "MASK_MODE_USER_PROVIDED",
                                "dilation": 0.03  # Recommended value for outpainting
                            }
                        }
                    ]
                }
            ],
            "parameters": {
                "editConfig": {
                    "baseSteps": 35  # Recommended starting value for outpainting
                },
                "editMode": "EDIT_MODE_OUTPAINT",
                "sampleCount": 1
            }
        }

        # Send the request
        response = requests.post(url, headers=headers, json=payload)

        if response.status_code == 200:
            result = response.json()
            # Extract the base64-encoded image from the response
            if "predictions" in result and len(result["predictions"]) > 0:
                upscaled_image_b64 = result["predictions"][0]["bytesBase64Encoded"]
                upscaled_image_bytes = base64.b64decode(upscaled_image_b64)
                upscaled_image = PIL_Image.open(io.BytesIO(upscaled_image_bytes))
                logger.debug(f"Upscaled image dimensions: {upscaled_image.size}")
                return upscaled_image
            else:
                logger.error("No predictions found in response")
                logger.debug(result)
        else:
            logger.error(f"Error: {response.status_code}")
            logger.debug(response.text)

    except Exception as e:
        logger.error(f"Error in resize_image_with_imagen: {e}")
    return None

@timer_decorator
async def ideate_to_create_with_rag(user_query: str,creative:str,conversation_history:List[ConversationPayload],parameters:Dict[str, Any], query_id: Optional[str] = None)-> str:
    extracted_features = creative_to_features(creative, query_id)
    search_result = await search_qdrant(query_text= f"{user_query} Creatives: {extracted_features}", conversation_payload=conversation_history,parameters=parameters,use_vector_search = True, number_of_results = 2, query_id=query_id)
    # print("Search Results :",search_result)

    # Convert search_result to string if it's a SearchResult object
    search_result_str = None
    if search_result and hasattr(search_result, 'results'):
        search_result_str = json.dumps([result.model_dump() for result in search_result.results])
    else:
        search_result_str = search_result

    prompt = load_prompt("creative_trends")
    return generate_response_with_creatives(creative=creative,query=user_query,search_result=search_result_str,system_prompt=prompt,conversation_history=conversation_history,query_id=query_id,agent_name="creative_trends_agent")

@timer_decorator
def ideate_to_create_without_rag(user_query:str,creative:str,conversation_history:List[ConversationPayload], query_id: Optional[str] = None)-> str:
    prompt = load_prompt("creative_feedback")
    return generate_response_with_creatives(creative=creative,query=user_query,system_prompt=prompt,conversation_history=conversation_history,query_id=query_id,agent_name="creative_feedback_agent")

@timer_decorator
async def formatter(final_output: str = None, prompt_file_name: str = "formatter",query_content:str=None, query_id: Optional[str] = None) -> str:
    system_prompt = load_prompt(prompt_file_name)
    query = f"Content to be formatted: {final_output}"
    if query_content:
        query += f"Original Query:{query_content}"
    formatted_output = await generate_response(
        query=query,
        system_prompt=system_prompt,
        max_tokens=4000,
        query_id=query_id,
        agent_name="formatter_agent"
    )
    return "\n"+formatted_output+"\n"

def generate_image_url(md5_hash):
    """Generate the image URL from the given MD5 hash."""
    base_url = os.getenv("BASE_URL_FOR_CREATIVES")
    return f"{base_url}{md5_hash[:2]}/{md5_hash[2:4]}/{md5_hash}.thumbnail.jpg"
@timer_decorator
def formatter_for_creative_insight(data, creative_summaries):
    """Convert JSON input to a Markdown formatted string."""
    markdown_output = ""
    # Add message about relevance if it exists
    if "message" in data and data["message"]:
        markdown_output = f"{data['message']}\n\n"

    markdown_output += "\n ## Creative Insights\n\n"
    for creative in data["creatives"]:
        brand = creative["brand"]
        product = creative["product"]
        snapshot = creative["creative_snapshot"]
        elements = creative["creative_elements"]

        # Extract and parse the MD5 hash for the image URL
        thumbnail, md5_hash = map(str.strip, elements["creative_thumbnail"].split(","))

        markdown_output += f"\n### Brand: {brand}, Product: {product}\n\n"
        markdown_output += f"![{thumbnail}]({md5_hash} \"{product}\")\n\n"
        markdown_output += f"| **Creative Snapshot** | {snapshot} |\n"
        markdown_output += f"|-----------------------|-----------------------------------------------------------------------------------------------------|\n"
        markdown_output += f"| **Brand Elements**    | {elements['brand_elements']} |\n"
        markdown_output += f"| **Visual Elements**   | {elements['visual_elements']} |\n"
        markdown_output += f"| **Color Tone**        | {elements['color_tone']} |\n"

        # Find the matching creative summary for this brand
        # print(creative_summaries)

        optional_elements = ["cinematography", "audio_elements", "narrative_structure", "seasonal_holiday_elements"]
        for opt_elem in optional_elements:
            if elements.get(opt_elem):  # Check if the key exists and is not empty
                formatted_key = opt_elem.replace("_", " ").capitalize()
                markdown_output += f"| **{formatted_key}**    | {elements[opt_elem]} |\n"

        matching_summary = next((item for item in creative_summaries if item["brand"].lower() == brand.lower()), None)
        if matching_summary:
            points = matching_summary["creative_summary"].split("\n")
            if len(points) == 3:
                markdown_output += f"| **Creative Summary**  | {points[0]}<br>{points[1]}<br>{points[2]} |\n"
            else:
                # Fallback if there aren't exactly 3 points
                formatted_summary = matching_summary["creative_summary"].replace("\n", "<br><br>")
                markdown_output += f"| **Creative Summary**  | {formatted_summary} |\n"

        markdown_output += "\n"

    return markdown_output

def formatter_for_media_plan(data):
    """Convert media plan JSON input to a Markdown formatted string."""

    markdown_output = ""
        # Add message about data source
    if "message" in data and data["message"]:
        markdown_output += f"{data['message']}\n\n"

    markdown_output += "\n\n # Media Plan\n\n"

    # Add brand information as HTML comment if available
    if "brand" in data and data["brand"]:
        markdown_output += f"<!-- BRAND: {data['brand']} -->\n"

    # Executive Summary Section
    markdown_output += "## Executive Summary\n\n"
    if "executive_summary" in data and data["executive_summary"]:
        exec_summary = data["executive_summary"]
        markdown_output += "| Component | Details |\n"
        markdown_output += "|----------|--------|\n"

        # Add each component that exists
        if "objectives" in exec_summary:
            markdown_output += f"| Objectives | {exec_summary['objectives']} |\n"
        if "target_audience" in exec_summary:
            markdown_output += f"| Target Audience | {exec_summary['target_audience']} |\n"
        if "budget" in exec_summary:
            markdown_output += f"| Budget | {exec_summary['budget']} |\n"
        if "ctr" in exec_summary:
            markdown_output += f"| Predicted CTR | {exec_summary['ctr']}% |\n"
        if "campaign_duration_in_days" in exec_summary:
            markdown_output += f"| Campaign Duration (Days) | {exec_summary['campaign_duration_in_days']}  Days|\n"
        if "start_date" in exec_summary:
            markdown_output += f"| Start Date | {exec_summary['start_date']} |\n"
        if "end_date" in exec_summary:
            markdown_output += f"| End Date | {exec_summary['end_date']} |\n"
    else:
        markdown_output += "Information not available.\n"

    markdown_output += "\n"

    # Target Audience Section
    markdown_output += "## Target Audience\n\n"

    # Add targeting configuration metadata as HTML comments (invisible in rendered markdown)
    if "target_audience" in data and data["target_audience"]:
        target = data["target_audience"]

        # Add targeting configuration metadata
        if "targeting_configuration_id" in target and target["targeting_configuration_id"] is not None:
            markdown_output += f"<!-- TARGETING_CONFIG_ID: {target['targeting_configuration_id']} -->\n"
        elif "new_targeting_configuration" in target and target["new_targeting_configuration"] is not None:
            import json
            config_json = json.dumps(target["new_targeting_configuration"])
            markdown_output += f"<!-- NEW_TARGETING_CONFIG: {config_json} -->\n"

            # Add name and description if available
            if "new_targeting_configuration_name" in target and target["new_targeting_configuration_name"] is not None:
                markdown_output += f"<!-- TARGETING_CONFIG_NAME: {target['new_targeting_configuration_name']} -->\n"
            if "new_targeting_configuration_description" in target and target["new_targeting_configuration_description"] is not None:
                markdown_output += f"<!-- TARGETING_CONFIG_DESCRIPTION: {target['new_targeting_configuration_description']} -->\n"

        markdown_output += "| Demographic | Details |\n"
        markdown_output += "|------------|--------|\n"

        # Add each demographic that exists
        if "age_range" in target:
            markdown_output += f"| Age Range | {target['age_range']} |\n"
        if "gender" in target:
            markdown_output += f"| Gender | {target['gender']} |\n"
        if "income_level" in target:
            markdown_output += f"| Income Level | {target['income_level']} |\n"
        if "location" in target:
            markdown_output += f"| Location | {target['location']} |\n"
        if "behavioral_data" in target:
            markdown_output += f"| Behavioral Data | {target['behavioral_data']} |\n"
        if "interests" in target and isinstance(target["interests"], list):
            interests = ", ".join(target["interests"])
            markdown_output += f"| Interests | {interests} |\n"
    else:
        markdown_output += "Information not available.\n"

    markdown_output += "\n"

    # Media Mix Strategy Section
    markdown_output += "## Media Mix Strategy\n\n"
    if "media_mix_strategy" in data and data["media_mix_strategy"]:
        media_mix = data["media_mix_strategy"]
        markdown_output += "| Channel | Tactics | Budget % | Allocated Budget | Target Impressions | Target Clicks | CPM | Expected Reach | Justification |\n"
        markdown_output += "|---------|---------|--------:|----------------:|-------------------:|--------------:|----:|---------------|---------------|\n"

        for channel in media_mix:
            logger.debug(f"Chanel:{channel}")
            budget_pct = channel.get("budget_allocation_percentage", "N/A")
            allocated = channel.get("allocated_budget", "N/A")
            cpm = f"${channel.get('cpm', 0):.2f}" if channel.get('cpm') is not None else "N/A"

            # Round impressions and clicks for better readability
            raw_impressions = channel.get('impressions', 0) or 0
            raw_clicks = channel.get('clicks', 0) or 0

            # Round to nearest thousand for large numbers, otherwise round to nearest hundred
            if raw_impressions >= 10000:
                rounded_impressions = round(raw_impressions / 1000) * 1000
            elif raw_impressions >= 1000:
                rounded_impressions = round(raw_impressions / 100) * 100
            else:
                rounded_impressions = raw_impressions

            if raw_clicks >= 1000:
                rounded_clicks = round(raw_clicks / 100) * 100
            elif raw_clicks >= 100:
                rounded_clicks = round(raw_clicks / 10) * 10
            else:
                rounded_clicks = raw_clicks

            impressions = f"{rounded_impressions:,}" if raw_impressions > 0 else "N/A"
            clicks = f"{rounded_clicks:,}" if raw_clicks > 0 else "N/A"

            markdown_output += f"| {channel.get('channel_products', 'N/A')} | "
            markdown_output += f"{channel.get('tactics', 'N/A')} | "
            markdown_output += f"{budget_pct} | "
            markdown_output += f"{allocated} | "
            markdown_output += f"{impressions} | "
            markdown_output += f"{clicks} | "
            markdown_output += f"{cpm} | "
            markdown_output += f"{channel.get('expected_reach', 'N/A')} | "
            markdown_output += f"{channel.get('justification', 'N/A')} |\n"
    else:
        markdown_output += "Information not available.\n"

    markdown_output += "\n"

    # Creative Strategy Section
    markdown_output += "## Creative Strategy\n\n"
    if "creative_strategy" in data and data["creative_strategy"]:
        creative = data["creative_strategy"]
        markdown_output += "| Asset Type | Description | Purpose | Distribution Channels |\n"
        markdown_output += "|-----------|------------|---------|----------------------|\n"

        for asset in creative:
            channels = ", ".join(asset.get("distribution_channels", [])) if "distribution_channels" in asset else "N/A"
            markdown_output += f"| {asset.get('asset_type', 'N/A')} | "
            markdown_output += f"{asset.get('description', 'N/A')} | "
            markdown_output += f"{asset.get('purpose', 'N/A')} | "
            markdown_output += f"{channels} |\n"
    else:
        markdown_output += "Information not available.\n"

    markdown_output += "\n"

    # Measurement and Evaluation Section
    markdown_output += "## Measurement and Evaluation\n\n"

    # Always show only the three consistent metrics: Impressions, CTR, and Conversion Rate
    markdown_output += "| Metric | Description | Target | Reporting Frequency |\n"
    markdown_output += "|--------|------------|--------|--------------------|\n"

    # Calculate total impressions from media mix strategy for targets
    total_impressions = 0
    if "media_mix_strategy" in data and data["media_mix_strategy"]:
        for channel in data["media_mix_strategy"]:
            total_impressions += channel.get('impressions', 0) or 0

    # Round total impressions for better readability
    if total_impressions >= 10000:
        rounded_total_impressions = round(total_impressions / 1000) * 1000
    elif total_impressions >= 1000:
        rounded_total_impressions = round(total_impressions / 100) * 100
    else:
        rounded_total_impressions = total_impressions

    # Get predicted CTR from executive summary
    predicted_ctr = data.get('executive_summary', {}).get('ctr', 'N/A')
    ctr_target = f"{predicted_ctr}%" if predicted_ctr != 'N/A' else 'N/A'

    # Only the three standard metrics - no custom metrics to avoid duplication
    markdown_output += f"| Impressions | Total number of ad impressions delivered | {rounded_total_impressions:,} | Weekly |\n"
    markdown_output += f"| Click-through Rate (CTR) | Percentage of impressions that result in clicks | {ctr_target} | Weekly |\n"
    markdown_output += f"| Conversion Rate | Percentage of clicks that result in desired actions | 2-5% | Weekly |\n"

    return markdown_output


# @timer_decorator
def extract_specific_fields(search_result: SearchResult, fields: List[str]) -> List:
    extracted_data = []
  ##  logger.debug(f"Search Results:\n\n{search_result}")
    for ad_creative in search_result.results:
        # print(ad_creative)
        item = {}
        # Extract specified fields from AdCreative
        for field in fields:
            if hasattr(ad_creative, field):
                item[field] = getattr(ad_creative, field)
        extracted_data.append(item)
    return extracted_data

async def get_targeting_configurations_for_prompt(user_id: str = "default_user") -> str:
    """
    Retrieve targeting configurations for inclusion in media plan prompt.

    Args:
        user_id: User ID to fetch configurations for

    Returns:
        Formatted string of targeting configurations for the prompt
    """
    try:
        from database_models import TargetingConfigurationModel

        db = db_connector.get_session()
        try:
            configurations = db.query(TargetingConfigurationModel).filter(
                TargetingConfigurationModel.user_id == user_id
            ).order_by(TargetingConfigurationModel.created_at.desc()).all()

            if not configurations:
                return "No targeting configurations available. You should provide targeting details for creating a new configuration."

            config_list = []
            for config in configurations:
                config_info = {
                    "id": str(config.id),
                    "name": config.name,
                    "description": config.description or "No description",
                    "targeting_config": config.targeting_config
                }
                config_list.append(config_info)

            # Format for prompt
            prompt_text = "Available Targeting Configurations:\n"
            for config in config_list:
                prompt_text += f"- ID: {config['id']}\n"
                prompt_text += f"  Name: {config['name']}\n"
                prompt_text += f"  Description: {config['description']}\n"
                prompt_text += f"  Targeting: {config['targeting_config']}\n\n"

            return prompt_text

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error fetching targeting configurations: {e}")
        return "Error retrieving targeting configurations. You should provide targeting details for creating a new configuration."

def generate_targeting_config_name(targeting_config: dict) -> str:
    """
    Generate a descriptive name for a targeting configuration based on its data.

    Args:
        targeting_config: Dictionary containing targeting configuration data

    Returns:
        A descriptive name for the targeting configuration
    """
    try:
        name_parts = []

        # Add age range if available
        age_range = targeting_config.get("age_range", [])
        if age_range:
            if len(age_range) == 1:
                name_parts.append(f"{age_range[0]}")
            else:
                # Get the youngest and oldest ages
                ages = []
                for age in age_range:
                    if "-" in age:
                        start_age = age.split("-")[0]
                        ages.append(int(start_age))
                if ages:
                    min_age = min(ages)
                    max_age = max(ages) + 10  # Assume 10-year ranges
                    name_parts.append(f"{min_age}-{max_age}")

        # Add interests if available
        interests = targeting_config.get("interests", [])
        if interests:
            # Take the first 2 interests to keep the name concise
            interest_part = " ".join(interests[:2])
            name_parts.append(interest_part)

        # Add behavioral data if available and no interests
        if not interests:
            behavioral_data = targeting_config.get("behavioral_data", [])
            if behavioral_data:
                # Take the first behavioral trait
                name_parts.append(behavioral_data[0])

        # Add gender if specific
        gender = targeting_config.get("gender", [])
        if gender and gender != ["All"] and len(gender) == 1:
            name_parts.append(gender[0])

        # Combine parts to create a name
        if name_parts:
            name = " ".join(name_parts)
            # Clean up and format
            name = name.replace("_", " ").title()
            return name
        else:
            return f"Generated {datetime.now().strftime('%m/%d/%Y')}"

    except Exception as e:
        logger.error(f"Error generating targeting config name: {e}")
        return f"AI Generated - {datetime.now().strftime('%m/%d/%Y')}"


def generate_targeting_config_description(targeting_config: dict) -> str:
    """
    Generate a descriptive description for a targeting configuration based on its data.

    Args:
        targeting_config: Dictionary containing targeting configuration data

    Returns:
        A descriptive description for the targeting configuration
    """
    try:
        description_parts = []

        # Add age and gender info
        age_range = targeting_config.get("age_range", [])
        gender = targeting_config.get("gender", [])

        if age_range and gender:
            if gender == ["All"] or len(gender) > 1:
                description_parts.append(f"Targeting individuals aged {', '.join(age_range)}")
            else:
                description_parts.append(f"Targeting {gender[0].lower()} individuals aged {', '.join(age_range)}")
        elif age_range:
            description_parts.append(f"Targeting individuals aged {', '.join(age_range)}")
        elif gender and gender != ["All"]:
            description_parts.append(f"Targeting {', '.join([g.lower() for g in gender])} audience")

        # Add interests
        interests = targeting_config.get("interests", [])
        if interests:
            description_parts.append(f"with interests in {', '.join(interests).lower()}")

        # Add location
        location = targeting_config.get("location", [])
        if location:
            description_parts.append(f"located in {', '.join(location)}")

        # Add income level
        income_level = targeting_config.get("income_level", [])
        if income_level:
            description_parts.append(f"with {', '.join([i.lower() for i in income_level])} income levels")

        # Combine parts
        if description_parts:
            description = " ".join(description_parts)
            # Ensure it ends with a period
            if not description.endswith('.'):
                description += '.'
            return f"{description} This targeting configuration was automatically generated based on campaign requirements."
        else:
            return "Targeting configuration automatically generated based on campaign requirements."

    except Exception as e:
        logger.error(f"Error generating targeting config description: {e}")
        return "Targeting configuration automatically generated based on campaign requirements."


def parse_multiple_targeting_options(response_text: str) -> List[dict]:
    """
    Parse multiple targeting configuration options from AI response.

    Args:
        response_text: The raw response text from the AI

    Returns:
        List of targeting option dictionaries
    """
    import re

    targeting_options = []

    try:
        # Look for the "Targeting Configuration Options:" section
        options_section_pattern = r"\*\*Targeting Configuration Options:\*\*(.*?)(?=\n\n##|\n\n\*\*[A-Z]|\Z)"
        options_section_match = re.search(options_section_pattern, response_text, re.IGNORECASE | re.DOTALL)

        if not options_section_match:
            logger.info("No 'Targeting Configuration Options:' section found")
            return []

        options_section = options_section_match.group(1)
        logger.info(f"Found targeting configuration options section: {options_section[:200]}...")

        # Find all option blocks (Option 1, Option 2, etc.)
        option_pattern = r"\*\*Option (\d+)(?:\s*\(([^)]+)\))?\*\*:(.*?)(?=\*\*Option \d+|\Z)"
        option_matches = re.findall(option_pattern, options_section, re.IGNORECASE | re.DOTALL)

        for option_num, option_label, option_content in option_matches:
            option_dict = {
                "option_number": int(option_num),
                "is_primary": "primary" in option_label.lower() if option_label else False,
                "targeting_configuration_id": None,
                "new_targeting_configuration": None,
                "new_targeting_configuration_name": None,
                "new_targeting_configuration_description": None
            }

            # Check if this option uses an existing configuration
            id_pattern = r"Recommended Targeting Configuration ID:\s*([a-f0-9-]{36})"
            id_match = re.search(id_pattern, option_content, re.IGNORECASE)
            if id_match:
                option_dict["targeting_configuration_id"] = id_match.group(1)
                logger.info(f"Option {option_num}: Found existing config ID {id_match.group(1)}")
            else:
                # Look for new targeting configuration
                new_config_pattern = r"New Targeting Configuration Needed:(.*?)(?=\*\*Option|\Z)"
                new_config_match = re.search(new_config_pattern, option_content, re.IGNORECASE | re.DOTALL)

                if new_config_match:
                    new_config_text = new_config_match.group(1).strip()

                    # Parse targeting configuration details
                    targeting_config = parse_targeting_config_details(new_config_text)
                    if targeting_config:
                        option_dict["new_targeting_configuration"] = targeting_config

                        # Extract name and description
                        name_match = re.search(r"Targeting Configuration Name:\s*(.+?)(?=\n|$)", new_config_text, re.IGNORECASE)
                        if name_match:
                            option_dict["new_targeting_configuration_name"] = name_match.group(1).strip()

                        desc_match = re.search(r"Targeting Configuration Description:\s*(.+?)(?=\n\n|\n[A-Z]|\Z)", new_config_text, re.IGNORECASE | re.DOTALL)
                        if desc_match:
                            option_dict["new_targeting_configuration_description"] = desc_match.group(1).strip()

                        logger.info(f"Option {option_num}: Parsed new targeting configuration")

            if option_dict["targeting_configuration_id"] or option_dict["new_targeting_configuration"]:
                targeting_options.append(option_dict)

        logger.info(f"Successfully parsed {len(targeting_options)} targeting configuration options")

    except Exception as e:
        logger.error(f"Error parsing multiple targeting options: {e}")

    return targeting_options


def parse_targeting_config_details(config_text: str) -> dict:
    """
    Parse targeting configuration details from text.

    Args:
        config_text: Text containing targeting configuration details

    Returns:
        Dictionary with targeting configuration fields
    """
    import re

    targeting_config = {
        "age_range": [],
        "gender": [],
        "income_level": [],
        "location": [],
        "interests": [],
        "behavioral_data": []
    }

    # Extract each field using patterns
    field_patterns = {
        "age_range": r"age_range:\s*\[(.*?)\]",
        "gender": r"gender:\s*\[(.*?)\]",
        "income_level": r"income_level:\s*\[(.*?)\]",
        "location": r"location:\s*\[(.*?)\]",
        "interests": r"interests:\s*\[(.*?)\]",
        "behavioral_data": r"behavioral_data:\s*\[(.*?)\]"
    }

    for field, pattern in field_patterns.items():
        field_match = re.search(pattern, config_text, re.IGNORECASE)
        if field_match:
            # Parse the list content
            list_content = field_match.group(1)
            # Split by comma and clean up quotes
            items = [item.strip().strip('"\'') for item in list_content.split(',') if item.strip()]
            targeting_config[field] = items

    # Return None if no fields were found
    if not any(targeting_config.values()):
        return None

    return targeting_config


def extract_targeting_info_from_response(response_text: str) -> dict:
    """
    Extract targeting configuration information from AI response.
    Now supports multiple targeting configuration options.

    Args:
        response_text: The raw response text from the AI

    Returns:
        Dictionary containing targeting options array or legacy single option for backward compatibility
    """
    targeting_info = {
        "targeting_options": [],  # New array structure for multiple options
        "brand": None,
        # Legacy fields for backward compatibility
        "targeting_configuration_id": None,
        "new_targeting_configuration": None,
        "new_targeting_configuration_name": None,
        "new_targeting_configuration_description": None
    }

    try:
        import re
        import json

        # Debug: Log the full response text to understand the format
        logger.info(f"DEBUG: Full AI response text for targeting extraction:\n{response_text}")

        # Extract brand information from HTML comments
        brand_comment_pattern = r"<!--\s*BRAND:\s*(.*?)\s*-->"
        brand_comment_match = re.search(brand_comment_pattern, response_text, re.IGNORECASE)
        if brand_comment_match:
            targeting_info["brand"] = brand_comment_match.group(1).strip()
            logger.info(f"Found brand from comment: {targeting_info['brand']}")

        # First, try to parse multiple targeting configuration options from markdown
        multiple_options = parse_multiple_targeting_options(response_text)
        if multiple_options:
            targeting_info["targeting_options"] = multiple_options
            # Set legacy fields for backward compatibility (use primary option)
            primary_option = next((opt for opt in multiple_options if opt.get("is_primary")), multiple_options[0] if multiple_options else None)
            if primary_option:
                targeting_info["targeting_configuration_id"] = primary_option.get("targeting_configuration_id")
                targeting_info["new_targeting_configuration"] = primary_option.get("new_targeting_configuration")
                targeting_info["new_targeting_configuration_name"] = primary_option.get("new_targeting_configuration_name")
                targeting_info["new_targeting_configuration_description"] = primary_option.get("new_targeting_configuration_description")
            logger.info(f"Found {len(multiple_options)} targeting configuration options")
            return targeting_info

        # Fallback: try to parse as JSON (which is what the AI is actually generating)
        try:
            response_json = json.loads(response_text)
            logger.info("Successfully parsed AI response as JSON")

            # Extract targeting configuration from JSON structure
            target_audience = response_json.get("target_audience", {})

            # Check for targeting configuration ID
            targeting_config_id = target_audience.get("targeting_configuration_id")
            if targeting_config_id:
                targeting_info["targeting_configuration_id"] = targeting_config_id
                logger.info(f"Found targeting configuration ID in JSON: {targeting_config_id}")

            # Check for new targeting configuration
            new_targeting_config = target_audience.get("new_targeting_configuration")
            if new_targeting_config:
                targeting_info["new_targeting_configuration"] = new_targeting_config
                logger.info(f"Found new targeting configuration in JSON: {new_targeting_config}")

                # Generate descriptive name and description based on the targeting data
                targeting_info["new_targeting_configuration_name"] = generate_targeting_config_name(new_targeting_config)
                targeting_info["new_targeting_configuration_description"] = generate_targeting_config_description(new_targeting_config)
                logger.info(f"Generated targeting config name: {targeting_info['new_targeting_configuration_name']}")
                logger.info(f"Generated targeting config description: {targeting_info['new_targeting_configuration_description']}")

                return targeting_info

            # If no new_targeting_configuration found in target_audience, check if there's targeting data directly
            # Sometimes the AI might structure the response differently
            targeting_fields = ["age_range", "gender", "income_level", "location", "interests", "behavioral_data"]
            if any(field in target_audience for field in targeting_fields):
                logger.info("Found targeting fields directly in target_audience, creating new_targeting_configuration")
                new_targeting_config = {}
                for field in targeting_fields:
                    if field in target_audience:
                        value = target_audience[field]
                        # Ensure the value is a list
                        if isinstance(value, str):
                            new_targeting_config[field] = [value]
                        elif isinstance(value, list):
                            new_targeting_config[field] = value
                        else:
                            new_targeting_config[field] = [str(value)]
                    else:
                        new_targeting_config[field] = []

                targeting_info["new_targeting_configuration"] = new_targeting_config
                targeting_info["new_targeting_configuration_name"] = generate_targeting_config_name(new_targeting_config)
                targeting_info["new_targeting_configuration_description"] = generate_targeting_config_description(new_targeting_config)
                logger.info(f"Created targeting config from direct fields: {new_targeting_config}")
                logger.info(f"Generated targeting config name: {targeting_info['new_targeting_configuration_name']}")
                logger.info(f"Generated targeting config description: {targeting_info['new_targeting_configuration_description']}")

                return targeting_info

        except json.JSONDecodeError:
            logger.info("AI response is not JSON, trying markdown parsing")

        # Fallback to original markdown parsing logic
        # Pattern to match "Recommended Targeting Configuration ID: [ID]"
        id_pattern = r"Recommended Targeting Configuration ID:\s*([a-f0-9-]{36})"
        id_match = re.search(id_pattern, response_text, re.IGNORECASE)
        if id_match:
            targeting_info["targeting_configuration_id"] = id_match.group(1)
            logger.info(f"Found targeting configuration ID: {targeting_info['targeting_configuration_id']}")
        else:
            # Look for new targeting configuration pattern
            new_config_pattern = r"New Targeting Configuration Needed:(.*?)(?=\n\n|\n#|\Z)"
            new_config_match = re.search(new_config_pattern, response_text, re.IGNORECASE | re.DOTALL)

            if new_config_match:
                new_config_text = new_config_match.group(1).strip()
                logger.info(f"Found new targeting configuration text: {new_config_text}")

                # Extract targeting configuration name - try multiple patterns
                name_patterns = [
                    r"Targeting Configuration Name:\s*(.+?)(?=\n|$)",
                    r"Name:\s*(.+?)(?=\n|$)",
                    r"Configuration Name:\s*(.+?)(?=\n|$)"
                ]

                for pattern in name_patterns:
                    name_match = re.search(pattern, new_config_text, re.IGNORECASE)
                    if name_match:
                        targeting_info["new_targeting_configuration_name"] = name_match.group(1).strip()
                        logger.info(f"Found targeting configuration name with pattern '{pattern}': {targeting_info['new_targeting_configuration_name']}")
                        break
                else:
                    logger.warning(f"No targeting configuration name found in text: {new_config_text}")

                # Extract targeting configuration description - try multiple patterns
                desc_patterns = [
                    r"Targeting Configuration Description:\s*(.+?)(?=\n\n|\n[A-Z]|\Z)",
                    r"Description:\s*(.+?)(?=\n\n|\n[A-Z]|\Z)",
                    r"Configuration Description:\s*(.+?)(?=\n\n|\n[A-Z]|\Z)"
                ]

                for pattern in desc_patterns:
                    desc_match = re.search(pattern, new_config_text, re.IGNORECASE | re.DOTALL)
                    if desc_match:
                        targeting_info["new_targeting_configuration_description"] = desc_match.group(1).strip()
                        logger.info(f"Found targeting configuration description with pattern '{pattern}': {targeting_info['new_targeting_configuration_description']}")
                        break
                else:
                    logger.warning(f"No targeting configuration description found in text: {new_config_text}")

                # Parse the targeting configuration details
                targeting_config = {
                    "age_range": [],
                    "gender": [],
                    "income_level": [],
                    "location": [],
                    "interests": [],
                    "behavioral_data": []
                }

                # Extract each field using patterns
                field_patterns = {
                    "age_range": r"age_range:\s*\[(.*?)\]",
                    "gender": r"gender:\s*\[(.*?)\]",
                    "income_level": r"income_level:\s*\[(.*?)\]",
                    "location": r"location:\s*\[(.*?)\]",
                    "interests": r"interests:\s*\[(.*?)\]",
                    "behavioral_data": r"behavioral_data:\s*\[(.*?)\]"
                }

                for field, pattern in field_patterns.items():
                    field_match = re.search(pattern, new_config_text, re.IGNORECASE)
                    if field_match:
                        # Parse the list content
                        list_content = field_match.group(1)
                        # Split by comma and clean up quotes
                        items = [item.strip().strip('"\'') for item in list_content.split(',') if item.strip()]
                        targeting_config[field] = items

                targeting_info["new_targeting_configuration"] = targeting_config
                logger.info(f"Parsed new targeting configuration: {targeting_config}")
            else:
                # If no "New Targeting Configuration Needed:" section found,
                # try to find name and description anywhere in the response
                logger.info("No 'New Targeting Configuration Needed:' section found, searching entire response for name/description")

                # Search for targeting configuration name anywhere in the response
                name_patterns = [
                    r"Targeting Configuration Name:\s*(.+?)(?=\n|$)",
                    r"Name:\s*(.+?)(?=\n|$)",
                    r"Configuration Name:\s*(.+?)(?=\n|$)"
                ]

                for pattern in name_patterns:
                    name_match = re.search(pattern, response_text, re.IGNORECASE)
                    if name_match:
                        targeting_info["new_targeting_configuration_name"] = name_match.group(1).strip()
                        logger.info(f"Found targeting configuration name in full response with pattern '{pattern}': {targeting_info['new_targeting_configuration_name']}")
                        break

                # Search for targeting configuration description anywhere in the response
                desc_patterns = [
                    r"Targeting Configuration Description:\s*(.+?)(?=\n\n|\n[A-Z]|\Z)",
                    r"Description:\s*(.+?)(?=\n\n|\n[A-Z]|\Z)",
                    r"Configuration Description:\s*(.+?)(?=\n\n|\n[A-Z]|\Z)"
                ]

                for pattern in desc_patterns:
                    desc_match = re.search(pattern, response_text, re.IGNORECASE | re.DOTALL)
                    if desc_match:
                        targeting_info["new_targeting_configuration_description"] = desc_match.group(1).strip()
                        logger.info(f"Found targeting configuration description in full response with pattern '{pattern}': {targeting_info['new_targeting_configuration_description']}")
                        break

    except Exception as e:
        logger.error(f"Error extracting targeting info from response: {e}")

    # Final debug log
    logger.info(f"Final targeting_info extracted: {targeting_info}")
    return targeting_info

@timer_decorator
async def media_plan(filtered_data: SearchResult, query: str, conversation_history: List[ConversationPayload], past_vector_names: Optional[List[str]] = None, query_id: Optional[str] = None) ->  AsyncGenerator[str, None]:
    # Media_plan Data filtered out
    fields_to_extract = [
    "ad_objective",
    "brand",
    "industry",
    "duration(days)",
    "duration_category",
    "tone_mood",
    "booked_measure_impressions",
    "delivered_measure_impressions",
    "budget",
    "conversion",
    "ad_surface",
    "campaign_folder"  # Add campaign_folder to enable database lookup
    ]
    # Fields below are kept for future reference but not currently used
    # full_data_fields_to_extract = [
    #     "target market",
    #     "target audience",
    #     "weekends",
    #     "holidays",
    #     "national events",
    #     "sport events",
    #     "strategy",
    #     "visual elements",
    #     "imagery",
    #     "targeting",
    #     "industry",
    # ]

    # Extract initial data from Qdrant
    initial_data = extract_specific_fields(filtered_data, fields_to_extract)
    logger.debug(f"Extracted initial data from Qdrant: {len(str(initial_data))} characters")

    # Enhance data with budget information from database
    enhanced_data = []
    try:
        # Get a database session
        db = db_connector.get_session()
        try:
            campaign_service = CampaignService(db)

            for item in initial_data:
                campaign_folder = item.get("campaign_folder")
                if campaign_folder:
                    # Get complete campaign details from database
                    campaign_details = campaign_service.get_campaign_details_by_campaign_name(campaign_folder)
                    logger.debug(f"Database lookup for {campaign_folder}: {campaign_details}")

                    if "error" not in campaign_details:
                        # Enhance the item with database budget and performance data
                        enhanced_item = item.copy()
                        enhanced_item.update({
                            "budget": campaign_details.get("budget", item.get("budget", 0)),
                            "booked_impressions": campaign_details.get("booked_impressions", item.get("booked_measure_impressions", 0)),
                            "clickable_impressions": campaign_details.get("clickable_impressions", item.get("delivered_measure_impressions", 0)),
                            "clicks": campaign_details.get("clicks", 0),
                            "conversion": campaign_details.get("conversion", item.get("conversion", 0)),
                            "ecpm": campaign_details.get("ecpm", 0),
                            "duration": campaign_details.get("duration", item.get("duration(days)", 0))
                        })
                        enhanced_data.append(enhanced_item)
                        logger.info(f"Enhanced {campaign_folder} with budget: ${enhanced_item.get('budget', 0)}")
                    else:
                        # If database lookup fails, use original data
                        enhanced_data.append(item)
                        logger.warning(f"Database lookup failed for {campaign_folder}, using Qdrant data only")
                else:
                    # If no campaign_folder, use original data
                    enhanced_data.append(item)

            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Database error in media_plan budget enhancement: {e}")
            # Fallback to original data if database fails
            enhanced_data = initial_data
        finally:
            db.close()
    except Exception as e:
        logger.error(f"Error connecting to database for budget enhancement: {e}")
        # Fallback to original data if database connection fails
        enhanced_data = initial_data

    # Convert enhanced data to string for the LLM
    essential_data = str(enhanced_data)
    logger.debug(f"Enhanced essential data with budget info: {len(essential_data)} characters")
    logger.info(f"Media plan using enhanced data with {len(enhanced_data)} campaigns including budget information")

    system_prompt = load_prompt("media_plan_v7")

    # Add current date as reference
    from datetime import datetime
    current_date = datetime.now().strftime('%m-%d-%Y')
    system_prompt += f"\n\nCurrent Date Reference: {current_date}\nUse this current date as reference when generating media plans, especially for calculating campaign start dates, end dates, and seasonal relevance."

    # Add targeting configurations to the prompt
    targeting_configs = await get_targeting_configurations_for_prompt()
    system_prompt += f"\n\nTARGETING CONFIGURATIONS:\n{targeting_configs}"
    system_prompt += "\nIf you find a suitable targeting configuration from the list above, include its ID in your response. If none are suitable, provide targeting details for creating a new configuration."

    # Add search context information if available
    if filtered_data.search_context:
        logger.info(f"MEDIA PLAN: Search context available: {filtered_data.search_context}")
        search_context = filtered_data.search_context
        system_prompt += f"\n\nSEARCH CONTEXT:\n{search_context.search_explanation}"
        # Add detailed filter information
        if search_context.applied_filters:
            filter_info = []
            for filter_item in search_context.applied_filters:
                if filter_item.match_type == "multiple":
                    filter_info.append(f"{filter_item.field}: {', '.join(filter_item.value)}")
                else:
                    filter_info.append(f"{filter_item.field}: {filter_item.value}")
            system_prompt += f"\nFilters applied: {'; '.join(filter_info)}"

        # Add retry information if applicable
        if search_context.retry_count > 0:
            system_prompt += f"\nSearch required {search_context.retry_count} retry attempts. "
            if search_context.retry_history:
                system_prompt += f"Retry details: {'; '.join(search_context.retry_history)}"
    else:
        logger.warning("MEDIA PLAN: No search context available in filtered_data")

    if past_vector_names:
        system_prompt += f"\nPrioritize past vectors that were used for the previous queries which are listed as follows:{', '.join(past_vector_names)}"
    logger.info("Media Plan: Prompt used for media plan: %s",system_prompt)
    # logger.debug("media plan Input len: %d ",len(query)+len(system_prompt)+len(essential_data)+len(conversation_history))
    # logger.debug("Query, system, filtered, convo history: %d, %d, %d, %d",len(query),len(system_prompt),len(essential_data),len(conversation_history))
    logger.info(f"Media Plan: search result used for media plan:{essential_data}")
    logger.debug(f"Media Plan: conversation_history used for media plan:{conversation_history}")
    raw_response = await generate_response(
        query=query,
        system_prompt=system_prompt,
        search_result=essential_data,
        conversation_history=conversation_history,
        response_class=MediaPlanOutput,
        model="gpt-4o",
        max_tokens=4500,
        query_id=query_id,
        agent_name="media_plan_agent"
    )

    budgeted_plan = Budget_tool(raw_response)
    logger.info(f"Output from Media Plan Generator {raw_response}")
    logger.debug(f"Output from Budgetted tool {budgeted_plan}")

    # Extract targeting information from the raw response
    targeting_info = extract_targeting_info_from_response(raw_response)

    # Add targeting information to the budgeted plan
    if isinstance(budgeted_plan, dict):
        if "target_audience" not in budgeted_plan:
            budgeted_plan["target_audience"] = {}

        # Add multiple targeting options if available (enhanced system)
        if targeting_info.get("targeting_options"):
            budgeted_plan["target_audience"]["targeting_options"] = targeting_info["targeting_options"]
            logger.info(f"Added {len(targeting_info['targeting_options'])} targeting options to budgeted plan")

        # Add legacy targeting configuration information for backward compatibility
        if targeting_info["targeting_configuration_id"]:
            budgeted_plan["target_audience"]["targeting_configuration_id"] = targeting_info["targeting_configuration_id"]
        elif targeting_info["new_targeting_configuration"]:
            budgeted_plan["target_audience"]["new_targeting_configuration"] = targeting_info["new_targeting_configuration"]
            # Add name and description if available
            if targeting_info["new_targeting_configuration_name"]:
                budgeted_plan["target_audience"]["new_targeting_configuration_name"] = targeting_info["new_targeting_configuration_name"]
            if targeting_info["new_targeting_configuration_description"]:
                budgeted_plan["target_audience"]["new_targeting_configuration_description"] = targeting_info["new_targeting_configuration_description"]

        # Add brand information
        if targeting_info.get("brand"):
            budgeted_plan["brand"] = targeting_info.get("brand")

    # Safety check: ensure budgeted_plan is a dictionary before passing to formatter
    if not isinstance(budgeted_plan, dict):
        logger.error(f"Budget_tool returned unexpected type: {type(budgeted_plan)}, value: {budgeted_plan}")
        # Try to parse the original response as fallback
        try:
            budgeted_plan = json.loads(raw_response)
        except:
            # Create a minimal valid structure if all else fails
            budgeted_plan = {
                "executive_summary": {
                    "budget": "N/A",
                    "campaign_duration_in_days": "N/A",
                    "start_date": "N/A",
                    "end_date": "N/A"
                },
                "media_mix_strategy": [],
                "message": "Error processing budget information"
            }

    markdown_output = formatter_for_media_plan(budgeted_plan)
    logger.info(f"Media Plan: Final output after formatting: {markdown_output}")
    return markdown_output


def format_campaign_data_markdown(combined_campaign_data: list,message: str = None) -> str:
    """
    Format combined campaign data into a markdown table format.

    Args:
        combined_campaign_data: List of dictionaries containing all campaign information

    Returns:
        Formatted markdown string
    """
    if not combined_campaign_data:
        if message:
            return message
        return "No campaign data available."
    markdown_output = ""
    if message:
        markdown_output += f"{message}\n\n"
    markdown_output += "## Campaign Performance Report\n\n"
    logger.debug(f'Received campaign data:{combined_campaign_data}')
    for campaign in combined_campaign_data:
        # Extract basic campaign info
        brand = campaign.get("brand", "N/A")
        # campaign_name is extracted but not used in this function
        # keeping it commented for future reference
        # campaign_name = campaign.get("campaign_name", "N/A")
        product = campaign.get("product/service", "N/A")
        objective = campaign.get("ad_objective", "N/A")
        md5_hash = campaign.get("md5_hash", "placeholder")
        industry_sectors = campaign.get("industry_sectors", "N/A")
        creative_summary = campaign.get("creative_summary","")
        file_name = campaign.get("file_name","jpg")

        # Extract metrics
        days = campaign.get("duration", "N/A")
        duration_category = f"{days} days" if days else "N/A"
        budget = f"${campaign.get('budget', 0):,.2f}"
        booked_impressions = f"{int(campaign.get('booked_impressions', 0)):,}"
        delivered_impressions = f"{int(campaign.get('clickable_impressions', 0)):,}"
        clicks = f"{campaign.get('clicks', 0):,}"

        conversions = campaign.get("conversion", 0)
        ecpm = campaign.get("ecpm", "N/A")

        # If ecpm is not available, calculate it
        if ecpm == "N/A" and campaign.get("budget") and campaign.get("clickable_impressions"):
            ecpm = (float(campaign["budget"]) * 1000) / float(campaign["clickable_impressions"])
        ecpm = f"${ecpm:.2f}" if isinstance(ecpm, (int, float)) else ecpm

        # Format the campaign section
        markdown_output += f"**Brand and Product:** {brand} - {product if product != 'N/A' else industry_sectors}\n"
        markdown_output += f"**Campaign Objective:** {objective}\n\n"

        # Performance metrics table
        markdown_output += "| Campaign Duration | Budget | Booked Impressions | Delivered Impressions | Clicks/Actions | Value to Money (Conversions) | ECPM |\n"
        markdown_output += "|------------------:|-------:|------------------:|----------------------:|---------------:|------------------------------:|------:|\n"
        markdown_output += f"| {duration_category} | {budget} | {booked_impressions} | {delivered_impressions} | {clicks} | {round(conversions*100,3)}% | {ecpm} |\n\n"

        # Creative thumbnails table (if md5_hash is available)
        if md5_hash and md5_hash != "placeholder":
            creative_description = campaign.get("insights", f"Campaign for {brand} in the {industry_sectors} sector")
            creative_summary = campaign.get("creative_summary", "")

            def format_decimals(text):
                    """Format numbers with excessive decimals to 3 decimal places."""
                    return re.sub(r"(\d+\.\d{3})\d+", r"\1", text)

            if creative_summary:
                creative_summary = format_decimals(creative_summary)
                # Split by newlines and filter out empty lines
                raw_points = creative_summary.split('\n')
                creative_summary_points = [point.strip() for point in raw_points if point.strip()]
            # print(creative_summary)
            # print(creative_summary_points)
            if creative_description:
                creative_description = format_decimals(creative_description)

            points = creative_description.split("\n")
            markdown_output += "| Creative Thumbnail | Creative Snapshot | Campaign Summary |\n"
            markdown_output += "|-------------------|-------------------|-------------------|\n"
            markdown_output += f"| ![{file_name}]({md5_hash}.thumbnail.jpg \"{brand}\") |{creative_summary_points[0]} <br><br> {creative_summary_points[1]}| {points[0]}<br>{points[1]}<br>{points[2]}|\n\n"
            # else:
                # markdown_output += f"| ![{creative_filename}]({md5_hash}.thumbnail.jpg \"{brand}\") |{points[0]}<br>{points[1]}<br>{points[2]}|\n\n"
        markdown_output += "\n\n<br><br>"
    return markdown_output



def apply_agent_ordering(campaign_data: List[dict], ordering_criteria: dict, selected_campaigns: List[str]) -> List[dict]:
    """
    Apply the agent's ordering criteria to campaign data.

    Args:
        campaign_data: List of campaign dictionaries
        ordering_criteria: Agent's ordering criteria
        selected_campaigns: List of campaign folders in agent's preferred order

    Returns:
        Ordered list of campaign data
    """
    logger.info(f"=== DEBUGGING apply_agent_ordering ===")
    logger.info(f"Input campaign_data length: {campaign_data}")
    # logger.info(f"Input campaign_data length: {len(campaign_data)}")
    logger.info(f"Input selected_campaigns: {selected_campaigns}")
    logger.info(f"Input ordering_criteria: {ordering_criteria}")

    # Log the campaign_folder values in the input data
    campaign_folders_in_data = [item.get('campaign_folder') for item in campaign_data]
    logger.info(f"Campaign folders in data: {campaign_folders_in_data}")

    if not ordering_criteria or not selected_campaigns:
        logger.info("No ordering criteria or selected campaigns provided, returning original order")
        return campaign_data

    primary_metric = ordering_criteria.get('primary_metric', 'conversion')
    secondary_metric = ordering_criteria.get('secondary_metric')
    order_direction = ordering_criteria.get('order_direction', 'descending')

    logger.info(f"Applying agent ordering: {primary_metric} ({order_direction}), secondary: {secondary_metric}")

    # Filter campaign_data to only include campaigns that are in selected_campaigns
    # This ensures we only work with the campaigns the agent selected
    filtered_campaign_data = []
    missing_campaigns = []

    for campaign_folder in selected_campaigns:
        matching_item = next((item for item in campaign_data if item.get('campaign_folder') == campaign_folder), None)
        if matching_item:
            filtered_campaign_data.append(matching_item)
            logger.debug(f"Found selected campaign: {campaign_folder} -> {matching_item.get(primary_metric, 'N/A')}")
        else:
            missing_campaigns.append(campaign_folder)
            logger.warning(f"Selected campaign not found in data: {campaign_folder}")

    logger.info(f"Filtered to {len(filtered_campaign_data)} campaigns from selected list")
    logger.info(f"Missing campaigns: {missing_campaigns}")

    # Log the metric values for all campaigns before sorting
    logger.info(f"Campaign metrics before sorting by {primary_metric}:")
    for item in filtered_campaign_data:
        primary_val = item.get(primary_metric, 'N/A')
        secondary_val = item.get(secondary_metric, 'N/A') if secondary_metric else 'N/A'
        logger.info(f"  {item.get('campaign_folder')}: {primary_metric}={primary_val}, {secondary_metric}={secondary_val}")

    # Sort the filtered data by the specified metrics
    def sort_key(item):
        primary_value = item.get(primary_metric, 0)
        secondary_value = item.get(secondary_metric, 0) if secondary_metric else 0

        # Handle None values and convert to float for sorting
        try:
            primary_value = float(primary_value) if primary_value is not None else 0
            secondary_value = float(secondary_value) if secondary_value is not None else 0
        except (ValueError, TypeError):
            logger.warning(f"Could not convert to float: {primary_metric}={primary_value}, {secondary_metric}={secondary_value}")
            primary_value = 0
            secondary_value = 0

        return (primary_value, secondary_value)

    # Sort with detailed logging
    logger.info(f"Sorting campaigns by {primary_metric} ({order_direction})")
    filtered_campaign_data.sort(key=sort_key, reverse=(order_direction == 'descending'))

    # Log the sorted order with metric values
    logger.info(f"Campaigns after sorting by {primary_metric}:")
    for i, item in enumerate(filtered_campaign_data):
        primary_val = item.get(primary_metric, 'N/A')
        logger.info(f"  Position {i+1}: {item.get('campaign_folder')} - {primary_metric}: {primary_val}")

    ordered_data = filtered_campaign_data

    # Log final result
    final_order = [item.get('campaign_folder') for item in ordered_data]
    logger.info(f"Final ordered campaigns: {final_order}")
    logger.info(f"=== END DEBUGGING apply_agent_ordering ===")

    return ordered_data

@timer_decorator
async def campaign_performance(filtered_data: SearchResult, query: str, conversation_history: List[ConversationPayload], past_vector_names: Optional[List[str]] = None, retry_count: int = 0, query_id: Optional[str] = None)-> str:
    fields_to_extract = [
        "brand",
        "campaign_folder",
        "clicks",
        "conversion",
        "duration(days)",
        "start_date",
        "end_date",
        "booked_measure_impressions",
        "delivered_measure_impressions",
        "ad_objective",
        "md5_hash",
        "industry_sectors",
        "product_category",
        "creative_summary",
        "file_name"
    ]
    logger.debug(f"Received Data: {filtered_data}")
    essential_data = extract_specific_fields(filtered_data, fields_to_extract)
    # logger.info(f"Essential Data Extracted: {essential_data}")

    # Load the prompt for the new campaign performance agent
    system_prompt = load_prompt("campaign_performance_agent")

    # Add search context information if available
    if filtered_data.search_context:
        logger.info(f"CAMPAIGN PERFORMANCE: Search context available: {filtered_data.search_context}")
        search_context = filtered_data.search_context
        system_prompt += f"\n\nSEARCH CONTEXT:\n{search_context.search_explanation}"
        # Add detailed filter information
        if search_context.applied_filters:
            filter_info = []
            for filter_item in search_context.applied_filters:
                if filter_item.match_type == "multiple":
                    filter_info.append(f"{filter_item.field}: {', '.join(filter_item.value)}")
                else:
                    filter_info.append(f"{filter_item.field}: {filter_item.value}")
            system_prompt += f"\nFilters applied: {'; '.join(filter_info)}"

        # Add retry information if applicable
        if search_context.retry_count > 0:
            system_prompt += f"\nSearch required {search_context.retry_count} retry attempts. "
            if search_context.retry_history:
                system_prompt += f"Retry details: {'; '.join(search_context.retry_history)}"
    else:
        logger.warning("CAMPAIGN PERFORMANCE: No search context available in filtered_data")

    # Add past vector names if available
    if past_vector_names:
        system_prompt += f"\nThese are past vectors that were used for previous queries. Feel free to use them if necessary. They are listed as follows: {', '.join(past_vector_names)}"

    logger.info(f"CampaignPerformanceAgent System Prompt:{system_prompt}")
    # Call the new campaign performance agent
    agent_response = await generate_response(
        query=query,
        system_prompt=system_prompt,
        search_result=str(essential_data),  # Pass the formatted campaign data
        conversation_history=conversation_history,
        response_class=CampaignPerformanceAgentOutput,
        max_tokens=4000,
        query_id=query_id,
        agent_name="campaign_performance_agent"
    )

    logger.info(f"Output from campaign performance agent: {agent_response}")

    # Parse the agent response
    parsed_agent_response = json.loads(agent_response)
    response_type = parsed_agent_response.get('response_type')
    message = parsed_agent_response.get('message', '')
    selected_campaigns = parsed_agent_response.get('selected_campaigns', [])
    ordering_criteria = parsed_agent_response.get('ordering_criteria', {})

    # Handle different response types
    if response_type == "user_response":
        # Direct response to the user without using tools
        logger.info(f"Campaign performance agent providing direct response: {message}")
        return message

    elif response_type == "search_retry":
        # Agent wants to retry the search with different parameters
        logger.info(f"Campaign performance agent requesting search retry: {message}")

        # Perform a new search with vector search enabled to get more results
        retry_filtered_data = await search_qdrant(
            query_text=query,
            conversation_payload=conversation_history,
            parameters={},  # Empty parameters to get broader results
            use_vector_search=True,
            number_of_results=15,  # Increase number of results
            unrelated_query=False,
            retry_count=retry_count+1,
            query_id=query_id
        )

        logger.info(f"Search retry found {len(retry_filtered_data.results)} results")

        # If we still don't have enough results, return a message
        if not retry_filtered_data.results or len(retry_filtered_data.results) < 2:
            return f"I apologize, but I couldn't find any relevant campaign performance data for your query. {message}"

        # Extract essential data from the retry results
        retry_essential_data = extract_specific_fields(retry_filtered_data, fields_to_extract)
        # logger.info(f"Retry Essential Data Extracted: {retry_essential_data}")

        # Load the fallback prompt for campaign performance agent
        fallback_system_prompt = load_prompt("campaign_performance_agent_fallback")

        # Add search context information from retry search if available
        if retry_filtered_data.search_context:
            logger.info(f"Adding retry search context to fallback agent: {retry_filtered_data.search_context}")
            retry_search_context = retry_filtered_data.search_context
            fallback_system_prompt += f"\n\nSEARCH CONTEXT:\n{retry_search_context.search_explanation}"

            # Add detailed filter information
            if retry_search_context.applied_filters:
                filter_info = []
                for filter_item in retry_search_context.applied_filters:
                    if filter_item.match_type == "multiple":
                        filter_info.append(f"{filter_item.field}: {', '.join(filter_item.value)}")
                    else:
                        filter_info.append(f"{filter_item.field}: {filter_item.value}")
                fallback_system_prompt += f"\nFilters applied: {'; '.join(filter_info)}"

            # Add retry information if applicable
            if retry_search_context.retry_count > 0:
                fallback_system_prompt += f"\nSearch required {retry_search_context.retry_count} retry attempts. "
                if retry_search_context.retry_history:
                    fallback_system_prompt += f"Retry details: {'; '.join(retry_search_context.retry_history)}"
        else:
            logger.warning("No search context available from retry search")

        # Add past vector names if available
        if past_vector_names:
            fallback_system_prompt += f"\nThese are past vectors that were used for previous queries. Feel free to use them if necessary. They are listed as follows: {', '.join(past_vector_names)}"

        logger.info(f"Fallback CampaignPerformanceAgent System Prompt: {fallback_system_prompt}")

        # Call the campaign performance agent with the fallback prompt
        fallback_agent_response = await generate_response(
            query=query,
            system_prompt=fallback_system_prompt,
            search_result=str(retry_essential_data),
            conversation_history=conversation_history,
            response_class=CampaignPerformanceAgentOutput,
            max_tokens=4000,
            query_id=query_id,
            agent_name="campaign_performance_agent_fallback"
        )

        logger.info(f"Output from fallback campaign performance agent: {fallback_agent_response}")

        # Parse the fallback agent response
        parsed_fallback_response = json.loads(fallback_agent_response)
        fallback_message = parsed_fallback_response.get('message', '')
        fallback_selected_campaigns = parsed_fallback_response.get('selected_campaigns', [])

        # Process the selected campaigns from the fallback response
        combined_campaign_data = []

        try:
            # Get a database session
            db = db_connector.get_session()
            try:
                campaign_service = CampaignService(db)

                if not fallback_selected_campaigns:
                    logger.debug(f"No campaigns selected by the fallback agent")
                else:
                    # Create a mapping of campaign names to their positions in retry_essential_data
                    campaign_positions = {}
                    for idx, item in enumerate(retry_essential_data):
                        campaign_folder = item.get("campaign_folder")
                        if campaign_folder and campaign_folder in fallback_selected_campaigns:
                            campaign_positions[campaign_folder] = idx

                    # Sort fallback_selected_campaigns based on their order in retry_essential_data
                    # Campaigns not found in retry_essential_data will be placed at the end
                    sorted_campaigns = sorted(
                        fallback_selected_campaigns,
                        key=lambda campaign: campaign_positions.get(campaign, float('inf'))
                    )

                    logger.info(f"Original fallback campaign order: {fallback_selected_campaigns}")
                    logger.info(f"Sorted fallback campaign order based on essential data: {sorted_campaigns}")

                    # Process each selected campaign in the sorted order
                    for campaign_name in sorted_campaigns:
                        # Find the corresponding item in retry_essential_data
                        matching_item = next((item for item in retry_essential_data
                                            if item.get("campaign_folder") == campaign_name), {})

                        if campaign_name:
                            campaign_details = campaign_service.get_campaign_details_by_campaign_name(campaign_name)
                            logger.info(f"Campaign Details From DB: {campaign_details}")
                            if "error" not in campaign_details:
                                # Combine the data from both sources into a single object
                                combined_data = {
                                    # Data from essential_data
                                    "brand": matching_item.get("brand"),
                                    "campaign_folder": campaign_name,
                                    "ad_objective": matching_item.get("ad_objective"),
                                    "md5_hash": matching_item.get("md5_hash"),
                                    "industry_sectors": matching_item.get("industry_sectors"),
                                    "creative_summary": matching_item.get("creative_summary"),
                                    "file_name": matching_item.get("file_name"),

                                    # Data from campaign_details
                                    "campaign_name": campaign_details.get("campaign_name"),
                                    "booked_impressions": campaign_details.get("booked_impressions"),
                                    "clickable_impressions": campaign_details.get("clickable_impressions"),
                                    "clicks": campaign_details.get("clicks"),
                                    "conversion": campaign_details.get("conversion"),
                                    "duration": campaign_details.get("duration"),
                                    "ad_surface": campaign_details.get("ad_surface"),
                                    "ecpm": campaign_details.get("ecpm"),
                                    "budget": campaign_details.get("budget"),
                                    "insights": campaign_details.get("insights")
                                }
                                combined_campaign_data.append(combined_data)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Database error in campaign_performance fallback: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error retrieving campaign data from database in fallback: {e}")

        # Format the campaign data into markdown with the fallback message
        formatted_campaign_data = format_campaign_data_markdown(combined_campaign_data, fallback_message)
        logger.debug(f"Formatted Fallback Campaign Data: {formatted_campaign_data}")
        return formatted_campaign_data

    elif response_type == "data_response":
        # Agent wants to generate a performance report with the selected campaigns
        logger.debug(f"Campaign performance agent generating report with campaigns: {selected_campaigns}")

        combined_campaign_data = []

        try:
            # Get a database session
            db = db_connector.get_session()
            try:
                campaign_service = CampaignService(db)

                if not selected_campaigns:
                    logger.debug(f"No campaigns selected by the agent")
                else:
                    # Create a mapping of campaign names to their positions in essential_data
                    campaign_positions = {}
                    for idx, item in enumerate(essential_data):
                        campaign_folder = item.get("campaign_folder")
                        if campaign_folder and campaign_folder in selected_campaigns:
                            campaign_positions[campaign_folder] = idx

                    # Sort selected_campaigns based on their order in essential_data
                    # Campaigns not found in essential_data will be placed at the end
                    sorted_campaigns = sorted(
                        selected_campaigns,
                        key=lambda campaign: campaign_positions.get(campaign, float('inf'))
                    )

                    logger.info(f"Original campaign order: {selected_campaigns}")
                    logger.info(f"Sorted campaign order based on essential data: {sorted_campaigns}")

                    # Process each selected campaign in the sorted order
                    for campaign_name in sorted_campaigns:
                        # Find the corresponding item in essential_data
                        matching_item = next((item for item in essential_data
                                            if item.get("campaign_folder") == campaign_name), {})

                        if campaign_name:
                            campaign_details = campaign_service.get_campaign_details_by_campaign_name(campaign_name)
                            logger.info(f"Campaign Details From DB: {campaign_details}")
                            if "error" not in campaign_details:
                                # Combine the data from both sources into a single object
                                combined_data = {
                                    # Data from essential_data
                                    "brand": matching_item.get("brand"),
                                    "campaign_folder": campaign_name,
                                    "ad_objective": matching_item.get("ad_objective"),
                                    "md5_hash": matching_item.get("md5_hash"),
                                    "industry_sectors": matching_item.get("industry_sectors"),
                                    "creative_summary": matching_item.get("creative_summary"),
                                    "file_name": matching_item.get("file_name"),

                                    # Data from campaign_details
                                    "campaign_name": campaign_details.get("campaign_name"),
                                    "booked_impressions": campaign_details.get("booked_impressions"),
                                    "clickable_impressions": campaign_details.get("clickable_impressions"),
                                    "clicks": campaign_details.get("clicks"),
                                    "conversion": campaign_details.get("conversion"),
                                    "duration": campaign_details.get("duration"),
                                    "ad_surface": campaign_details.get("ad_surface"),
                                    "ecpm": campaign_details.get("ecpm"),
                                    "budget": campaign_details.get("budget"),
                                    "insights": campaign_details.get("insights")
                                }
                                combined_campaign_data.append(combined_data)
                db.commit()
            except Exception as e:
                db.rollback()
                logger.error(f"Database error in campaign_performance: {e}")
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Error retrieving campaign data from database: {e}")

        # Apply agent's ordering criteria to the campaign data
        if ordering_criteria and selected_campaigns:
            logger.info(f"Applying agent ordering criteria: {ordering_criteria}")
            logger.info(f"Selected campaigns: {selected_campaigns}")
            logger.info(f"Combined campaign data before ordering (length: {len(combined_campaign_data)}):")

            # Log detailed structure of each campaign data item
            for i, item in enumerate(combined_campaign_data):
                logger.info(f"  Campaign {i+1}: campaign_folder='{item.get('campaign_folder')}', "
                           f"conversion={item.get('conversion')}, clicks={item.get('clicks')}, "
                           f"keys={list(item.keys())}")

            combined_campaign_data = apply_agent_ordering(combined_campaign_data, ordering_criteria, selected_campaigns)

            logger.info(f"Combined campaign data after ordering (length: {len(combined_campaign_data)}):")
            for i, item in enumerate(combined_campaign_data):
                logger.info(f"  Campaign {i+1}: campaign_folder='{item.get('campaign_folder')}', "
                           f"conversion={item.get('conversion')}, clicks={item.get('clicks')}")
        else:
            logger.info("No ordering criteria provided by agent, using default order")
        # Format the campaign data into markdown
        formatted_campaign_data = format_campaign_data_markdown(combined_campaign_data, message)
        logger.info(f"Formatted Campaign Data: {formatted_campaign_data}")
        return formatted_campaign_data

    else:
        # Unknown response type
        logger.error(f"Unknown response type from campaign performance agent: {response_type}")
        return "I apologize, but I encountered an error processing the campaign performance data."


@timer_decorator
async def creative_insights(filtered_data: SearchResult, query: str, conversation_history: List[ConversationPayload], past_vector_names: Optional[List[str]] = None, query_id: Optional[str] = None) -> str:
    fields_to_extract = [
        "brand",
        "ad_objective",
        "tone_mood",
        "md5_hash",
        "colors",
        "duration(days)",
        "duration_category",
        "imagery",
        "file_name",
        "creative_summary",
        "clicks",
        "conversion",
        "industry_sectors",
        "file_name",
        "start_date",
        "end_date",
    ]
    logger.debug(f"Full Filtered Data:{filtered_data}")
    essential_data = extract_specific_fields(filtered_data, fields_to_extract)
    logger.debug(f"Extracted Data sent to creative insight agent:{essential_data}")

    creative_summaries = []
    for item in essential_data:
        creative_summary = item.pop('creative_summary', None)
        if creative_summary is not None:
            creative_summaries.append({"creative_summary":creative_summary,"brand":item["brand"]})

    essential_data = str(essential_data)
    system_prompt = load_prompt("creative_insights_v2")

    # Add search context information if available
    if filtered_data.search_context:
        search_context = filtered_data.search_context
        system_prompt += f"\n\nSEARCH CONTEXT:\n{search_context.search_explanation}"

        # Add detailed filter information
        if search_context.applied_filters:
            filter_info = []
            for filter_item in search_context.applied_filters:
                if filter_item.match_type == "multiple":
                    filter_info.append(f"{filter_item.field}: {', '.join(filter_item.value)}")
                else:
                    filter_info.append(f"{filter_item.field}: {filter_item.value}")
            system_prompt += f"\nFilters applied: {'; '.join(filter_info)}"

        # Add retry information if applicable
        if search_context.retry_count > 0:
            system_prompt += f"\nSearch required {search_context.retry_count} retry attempts. "
            if search_context.retry_history:
                system_prompt += f"Retry details: {'; '.join(search_context.retry_history)}"

        # Add instruction to explain search relevance in the message field
        system_prompt += "\n\nIMPORTANT: In the 'message' field of your response, explain how the search filters and context relate to the found creatives and their relevance to the user's query."

    if past_vector_names:
        system_prompt += f"\nPrioritize past vectors that were used for the previous queries which are listed as follows:{', '.join(past_vector_names)}"
    # print("Essential data:",essential_data)
    # Use the async version of generate_response
    logger.info(f"Creative Insights System Prompt: {system_prompt}")
    raw_response = await generate_response(
        query=query,
        system_prompt=system_prompt,
        search_result=essential_data,
        conversation_history=conversation_history,
        response_class=CreativeInsightsReport,
        query_id=query_id,
        agent_name="creative_insights_agent"
    )

  #  logger.debug(f"Creative Insights Raw: {raw_response}")
    # print(f"Creative insights raw_response: {raw_response}")

    parsed_response = json.loads(raw_response)
    if parsed_response.get("creatives") is None:
        response = await generate_response(query=query,system_prompt=load_prompt("no_creative_insight_data"),conversation_history=conversation_history,query_id=query_id,agent_name="creative_insights_fallback")
    else:
        response = formatter_for_creative_insight(parsed_response, creative_summaries)
    return response


@timer_decorator
async def performance_summary(query: str, output_parts: Dict[str, str], query_id: Optional[str] = None) -> str:
    # Assuming load_prompt is a quick operation, keep it synchronous
    system_prompt = load_prompt("performance_summary")
    # print("performance summary Input len:", len(query) + len(system_prompt) + len(str(output_parts)))
    # Use the async version of generate_response
    raw_response = await generate_response(
        query=query,
        system_prompt=system_prompt,
        output_parts=output_parts,
        # response_class=PerformanceSummary
        query_id=query_id,
        agent_name="performance_summary_agent"
    )
    # print("Performance summary len:", len(raw_response))
    # Use the async version of formatter
    # formatted_response = await formatter(raw_response, "formatter_performance_summary")
    return f"""\n\n{raw_response}"""

@timer_decorator
async def generic_without_creative(query: str, conversation_history: List[ConversationPayload],filtered_data: SearchResult=None, query_id: Optional[str] = None):
    system_prompt = load_prompt("generic_v2")
    if filtered_data:
        # Convert search_results to string if it's a SearchResult object
        search_results_str = None
        if filtered_data and hasattr(filtered_data, 'results'):
            search_results_str = json.dumps([result.model_dump() for result in filtered_data.results])
        else:
            search_results_str = filtered_data

        raw_response = await generate_response(query=query,system_prompt=system_prompt,conversation_history=conversation_history,search_result=search_results_str,query_id=query_id,agent_name="generic_with_search")
    else:
        raw_response = await generate_response(query=query,system_prompt=system_prompt,conversation_history=conversation_history,query_id=query_id,agent_name="generic_without_search")
    return raw_response

@timer_decorator
def generic_with_creative(user_query:str,conversation_history:List[ConversationPayload],creative:str,filtered_data: SearchResult=None, query_id: Optional[str] = None)-> str:
    prompt = "You are an AI assistant. Be Polite and answer in markdown. You can answer questions based on uploaded creatives."
    if filtered_data:
        # Convert search_results to string if it's a SearchResult object
        search_results_str = None
        if filtered_data and hasattr(filtered_data, 'results'):
            search_results_str = json.dumps([result.model_dump() for result in filtered_data.results])
        else:
            search_results_str = filtered_data

        result = generate_response_with_creatives(creative=creative,query=user_query,system_prompt=prompt,conversation_history=conversation_history,search_result=search_results_str,query_id=query_id,agent_name="generic_with_creative_and_search")
    else:
        result = generate_response_with_creatives(creative=creative,query=user_query,system_prompt=prompt,conversation_history=conversation_history,query_id=query_id,agent_name="generic_with_creative")
    return result

# @timer_decorator
def replace_hash_with_url(S):
    md5_pattern_thumbnail = r'\b([a-fA-F0-9]{32})(?:\.thumbnail\.jpg)?\b'
    def replace_thumbnail(match):
        hash_value = match.group(1)
        return get_url_for_hash(hash_value, "thumbnail.jpg")
    # Replace thumbnail URLs
    S = re.sub(md5_pattern_thumbnail, replace_thumbnail, S)

    return S
# @timer_decorator
def get_url_for_hash(hash, extension):
    base_url = os.getenv("BASE_URL_FOR_CREATIVES")
    directory_structure = f"{hash[:2]}/{hash[2:4]}/{hash}"
    return f"{base_url}/{directory_structure}.{extension}"

def remove_markdown_prefix(s):
    s = re.sub(r'```markdown', '', s)
    s = re.sub(r'```', '\n---', s)
    # s = re.sub(r'### (.*)\n', r'<h2><strong>\1</strong></h2><br>\n', s)
    # s = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', s)
    return s
# @timer_decorator
def format_conversation_payload(conversation_payload: List[ConversationPayload]) -> str:
    """
    Format the conversation history into a single string.

    Args:
        conversation_payload: List of conversation entries

    Returns:
        Formatted conversation history as a string
    """
    formatted_history = ""
    # Log only the length of conversation history, not the full content
    logger.debug(f"Formatting conversation history with {len(conversation_payload)} entries")
    for entry in conversation_payload:
        actor = entry.actor
        content = entry.content
        formatted_history += f"{actor}: {content}\n"
    return formatted_history.strip()

async def generate_related_queries(intent_data: dict, conversation_history: List[ConversationPayload],user_query:str,prompt_file:str,non_empty_fields:List[str]=None,past_vector_names:List[str]=None, query_id: Optional[str] = None, output_parts: Dict[str, str] = None) -> List[str]:
    """
    Generates related queries based on the intent data, previous user queries, and output context.

    Args:
        intent_data (dict): The intent data containing user query information.
        conversation_history (List[ConversationPayload]): The conversation history to extract previous queries.
        user_query (str): The current user query.
        prompt_file (str): The prompt file to use for generation.
        non_empty_fields (List[str], optional): List of non-empty fields for context.
        past_vector_names (List[str], optional): List of past vector names for context.
        query_id (str, optional): Query ID for tracking purposes.
        output_parts (Dict[str, str], optional): Dictionary containing previously generated outputs for context.

    Returns:
        List[str]: A list of related queries.
    """
    # Load the prompt for generating related queries
    if non_empty_fields and past_vector_names:
        prompt = load_prompt(prompt_file).format(str(non_empty_fields),str(past_vector_names))
    elif non_empty_fields:
        prompt = load_prompt(prompt_file).format(str(non_empty_fields),"")
    elif past_vector_names:
        prompt = load_prompt(prompt_file).format("",str(past_vector_names))
    else:
        prompt = load_prompt(prompt_file)

    # print("Related Queries Prompt:",prompt)
    OUTCOME_MAPPING = {
    1: "Media Plan - Can create/generate a media plan for a product",
    # 2: "Analysis of Trends",
    3: "Campaign Performance",
    4: "Existing Creative Insights",
    5: "Performance Summary - Summary of other outputs",
    6: "Creative Trends - if creative uploaded is true, then provide creative trends",
    7: "Creative Inspiration - generate creatives using an API.",
    8: "Creative Feedback - Constructive Feedback based on provided Creative",
    9: "Follow Up Question - Ask a follow up question. If it is for creatives, ask them if they want to generate a fresh creative or base their creative off another that performed well.",
    10: "Generic Media Chatbot Questions",
    11: "Irrelevant Questions"
}
    # Extract previous user queries from the conversation history
    previous_queries = [entry.content for entry in conversation_history if entry.actor == "user"]
    required_outcomes = intent_data.get('required_outcomes', [11])
    outcome_descriptions = [OUTCOME_MAPPING.get(outcome, "Unknown Outcome") for outcome in required_outcomes]
    # Prepare the input for the LLM call
    input_data = {
        "base_query": user_query,
        "previous_queries": str(previous_queries),
        "current_intents_chosen":str(outcome_descriptions)
    }
    # Build messages similar to generate_response
    messages = [{"role": "system", "content": prompt}]

    # Add conversation history
    if conversation_history:
        for message in conversation_history:
            messages.append({"role": message.actor, "content": message.content})

    # Add user query
    messages.append({"role": "user", "content": f"Query: {user_query}"})

    # Add output parts context (similar to generate_response)
    if output_parts:
        for key, value in output_parts.items():
            messages.append({"role": "user", "content": f"{key.capitalize()}: {value}"})

    # Add input data
    messages.append({"role": "user", "content": f"Intent Data: {str(input_data)}"})

    # Call the LLM with the prompt and input data
    try:
        # Track token usage if query_id is provided
        if query_id:
            from execution_tracker import execution_tracker

            # Format input prompt for tracking - store full data without truncation
            formatted_input = f"System: {prompt}\nQuery: {user_query}\nInput: {str(input_data)}"
            if output_parts:
                formatted_input += f"\nOutput Context: {str(output_parts)}"

            async with execution_tracker.track_agent_step(
                query_id=query_id,
                agent_name="related_queries_generator",
                step_type="response_generation",
                input_prompt=formatted_input,
                model_used="gpt-4o-mini"
            ) as step:
                response = client.beta.chat.completions.parse(
                    model="gpt-4o-mini",
                    messages=messages,
                    max_tokens=200,  # Adjust max tokens as needed
                    response_format= Related_Queries
                )

                # Track token usage
                if hasattr(response, 'usage') and response.usage:
                    tokens = {
                        "input": response.usage.prompt_tokens,
                        "output": response.usage.completion_tokens,
                        "total": response.usage.total_tokens
                    }
                    step.set_tokens(tokens)
                    logger.debug(f"Token usage tracked for generate_related_queries: {tokens}")

                # Set output for tracking - store full response without truncation
                response_content = response.choices[0].message.content
                step.set_output(response_content)
        else:
            # Fallback without tracking
            response = client.beta.chat.completions.parse(
                model="gpt-4o-mini",
                messages=messages,
                max_tokens=200,  # Adjust max tokens as needed
                response_format= Related_Queries
            )
        response_content = response.choices[0].message.content
        try:
            Related_Queries.model_validate_json(response_content)
        except Exception as validation_error:
            logger.error(f"Warning: Response validation failed: {validation_error}")
            return response_content
        response_json = json.loads(response_content)
        logger.debug(f"Generated Related Query Content: {response_json}")
        return response_json.get("related_queries")
    except Exception as e:
        logger.error(f"Error generating related queries: {e}")
        return []


async def perform_inference(inference_payload: InferencePayload):
    try:
        user_id = inference_payload.user_id
        session_id = inference_payload.session_id
        query_id = inference_payload.query_id
        user_query = inference_payload.query
        cache_key = f"{user_id}:{session_id}"

        # Import execution tracker for database storage
        from execution_tracker import execution_tracker

        # Start query tracking in database
        logger.info(f"[DB_STORAGE] Starting query tracking for query_id: {query_id}")
        try:
            await execution_tracker.start_query_execution(
                query_id=query_id,
                user_id=user_id,
                session_id=session_id,
                original_query=user_query
            )
            logger.info(f"[DB_STORAGE] Successfully started tracking query {query_id}")
        except Exception as e:
            logger.error(f"[DB_STORAGE] Failed to start query tracking: {e}")
            # Continue with inference even if database tracking fails

        try:
            cache_control = CacheControl()
        except Exception as e:
            yield{"response":"Error initializing cache control. Please try again later."}
            return
        media_plan_output = ""
        creative_insights_output = ""
        campaign_performance_output = ""
        general_response_string = ""
        creative_data = []
        vector_data = []
        retry_count = 0
        past_topics = []
        filtered_data = None
        related_prompt_file = "related_queries_general_v2"
        existing_data_json = cache_control.get(cache_key)
        existing_data = json.loads(existing_data_json) if existing_data_json else []
        logger.info(f"ExistingJSON from Cache: {existing_data_json}")
        threshold = 3
        conversation_history = inference_payload.conversation_payload or []

        logger.info(f"Conversation_history:{conversation_history}")
        logger.info(f"Query ID: {query_id}")
        user_query=inference_payload.query

        # Process creative (image) upload immediately if present
        creative_url = None
        creative_id = None
        extracted_features = None
        if inference_payload.creative:
            yield {"status": "processing_image", "message": "Processing your uploaded image..."}
            creative = inference_payload.creative
            url_type = check_url_type(creative)

            # Handle base64 image
            if url_type == 'base64':
                try:
                    # Split the base64 string to get the data part
                    _, base64_data = creative.split(",", 1)
                    missing_padding = len(base64_data) % 4
                    if missing_padding:
                        base64_data += "=" * (4 - missing_padding)
                    image_data = base64.b64decode(base64_data)
                    image = PIL_Image.open(BytesIO(image_data))
                    logger.info("Successfully loaded image from creative input (base64)")

                    # Convert PIL image to bytes and upload to S3
                    image_bytes = get_bytes_from_pil(image)
                    uploaded_result = upload_to_s3(image_bytes)
                    if uploaded_result and "key" in uploaded_result:
                        creative_s3_key = uploaded_result["key"]
                        creative_id = uploaded_result.get("creative_id")
                        logger.info(f"Successfully uploaded image to S3: {creative_s3_key} with ID: {creative_id}")

                        # For feature extraction, we need a temporary URL
                        try:
                            from tools.store_s3 import generate_secure_presigned_url
                            temp_url = generate_secure_presigned_url(creative_s3_key, expires_in=1800)  # 30 minutes
                            extracted_features = creative_to_features(temp_url, query_id)
                            logger.info("Successfully extracted features from uploaded image")
                        except Exception as e:
                            logger.error(f"Error extracting features from uploaded image: {str(e)}")
                            extracted_features = "Could not extract features"

                        # Determine the role of the creative using temp URL
                        try:
                            creative_role = determine_creative_role(temp_url, extracted_features, user_query, query_id)
                            logger.info(f"Determined creative role: {creative_role}")
                        except Exception as e:
                            logger.error(f"Error determining creative role: {str(e)}")
                            creative_role = "Unknown role"

                        # Store creative information in Redis with S3 key instead of URL
                        creative_info = {
                            "creative_id": creative_id,
                            "s3_key": creative_s3_key,  # Store S3 key instead of URL
                            "features": extracted_features,
                            "role": creative_role,
                            "query_id": query_id,
                            "timestamp": uploaded_result.get("upload_timestamp", datetime.now().isoformat())
                        }
                        creative_data.append(creative_info)
                        logger.info(f"Stored creative information for query ID: {query_id} with role: {creative_role}")
                    else:
                        logger.error("Failed to upload image to S3")
                except Exception as e:
                    logger.error(f"Error processing base64 creative: {str(e)}")
                    yield {"status": "warning", "message": f"Warning: Could not process creative: {str(e)}"}

            # Handle direct URL
            elif url_type == 'direct_link':
                try:
                    creative_url = creative
                    # Extract features from the URL
                    try:
                        extracted_features = creative_to_features(creative_url, query_id)
                        logger.info("Successfully extracted features from creative URL")
                    except Exception as e:
                        logger.error(f"Error extracting features from creative URL: {str(e)}")
                        extracted_features = "Could not extract features"

                    # Determine the role of the creative
                    try:
                        creative_role = determine_creative_role(creative_url, extracted_features, user_query, query_id)
                        logger.info(f"Determined creative role: {creative_role}")
                    except Exception as e:
                        logger.error(f"Error determining creative role for URL: {str(e)}")
                        creative_role = "Unknown role"

                    # Generate a creative ID for direct links
                    creative_id = f"creative_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}"

                    # Store creative information in Redis with query ID
                    creative_info = {
                        "creative_id": creative_id,
                        "url": creative_url,
                        "features": extracted_features,
                        "role": creative_role,
                        "query_id": query_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    creative_data.append(creative_info)
                    logger.info(f"Stored creative information for query ID: {query_id} from direct URL with role: {creative_role}")
                except Exception as e:
                    logger.error(f"Error extracting features from creative URL: {str(e)}")
                    yield {"status": "warning", "message": f"Warning: Could not extract features from creative URL: {str(e)}"}

        # Send a status update that we're thinking about the query
        yield {"status": "thinking", "message": "Thinking about your request..."}

        # Determine intent using the intent agent
        if inference_payload.creative:
            # Pass extracted features to the intent determination if available
            if extracted_features:
                intent_data = determine_intent(
                    user_query=user_query,
                    conversation_history=conversation_history,
                    prompt_file="intention_v6",
                    creative_provided=True,
                    creative_features=extracted_features,
                    existing_data=existing_data,
                    query_id=query_id
                )
            else:
                intent_data = determine_intent(
                    user_query=user_query,
                    conversation_history=conversation_history,
                    prompt_file="intention_v6",
                    creative_provided=True,
                    existing_data=existing_data,
                    query_id=query_id
                )
        else:
            intent_data = determine_intent(
                user_query=user_query,
                conversation_history=conversation_history,
                prompt_file="intention_v6",
                creative_provided=False,
                existing_data=existing_data,
                query_id=query_id
            )

        # Get required outcomes and other intent data
        required_outcomes = intent_data.get('required_outcomes', [11])
        unrelated_query = intent_data.get('unrelated_query', False)
        vector_search = intent_data.get('vector_search', False)

        # Get search parameters from the Qdrant search agent
        # Note: parameters are now handled by the qdrant_search_agent, not the intent agent
        parameters = {}

        if 11 not in required_outcomes:
            past_topics = [session['topic'] for session in existing_data if 'topic' in session]

        current_topic = await topic_extractor(past_topics, user_query, query_id)
        logger.debug(f"Current Topic:{current_topic}")
        non_empty_fields = check_non_empty_fields_for_topic(existing_data, current_topic)
        logger.debug(f"Non-empty fields for topic '{current_topic}': {non_empty_fields}")

        past_vectors = get_past_vectors_for_topic(existing_data, current_topic)
        past_vector_names = ["brand: "+vector['brand']+" industry: "+vector['industry_sectors'] for vector in past_vectors]
        past_vector_names = list(set(past_vector_names))

        # Convert ConversationPayload objects to serializable format
        logger.info(f"Current Topic: {current_topic}")

        logger.info(f"Intent Agent Output:{intent_data}")
        logger.debug(f"Intent Extracted:\n Query:{user_query}\nRequired Outcomes{required_outcomes}\nvector_search:{vector_search}")
        logger.debug(str(intent_data))

        # Note: We now handle unrelated_query in the search_qdrant function directly
        # This commented code is kept for referenceretru

        # Irrelevant Questions
        if 11 in required_outcomes:
            response_message = "I specialize in media marketing campaigns plan generation and historical data insights. Is there anything related to media campaigns that I can assist you with?"
            yield {"response":  response_message}
            # Generate related queries for irrelevant questions
            # Send a status update that we're wrapping up
            # yield {"status": "wrapping_up", "message": "Wrapping up and finding related topics..."}
            # Use general related queries prompt for irrelevant questions
            related_prompt_file = "related_queries_general_v2"
            # Create output_parts context from response_message
            irrelevant_output_parts = {"general_response": response_message} if response_message else None
            if past_vector_names and non_empty_fields:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, non_empty_fields=non_empty_fields, past_vector_names=past_vector_names, query_id=query_id, output_parts=irrelevant_output_parts)
            elif past_vector_names:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, past_vector_names=past_vector_names, query_id=query_id, output_parts=irrelevant_output_parts)
            elif non_empty_fields:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, non_empty_fields=non_empty_fields, query_id=query_id, output_parts=irrelevant_output_parts)
            else:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, query_id=query_id, output_parts=irrelevant_output_parts)
            yield {"related_queries": related_queries}

            # Store related queries for session continuity
            if related_queries:
                await store_related_queries(query_id, session_id, related_queries)

            session_data = {
                "topic": current_topic,
                "message_query": user_query,
                "query_id": query_id,
                "enhanced_query": user_query,
                "vector_data": vector_data,
                "creative_data": creative_data,
                "media_plan_output": "",
                "creative_insights_output": "",
                "campaign_performance_output": "",
                "general_response_string": response_message,
                "timestamp": datetime.now().isoformat()
            }
            existing_data.append(session_data)
            cache_control.setex(cache_key, 500, json.dumps(existing_data))
            await handle_periodic_db_storage(
                user_id=user_id,
                session_id=session_id,
                query_id=query_id,
                user_query=user_query,
                final_response=response_message,
                end_time=datetime.now(timezone.utc)
            )
            return

        # Follow up Questions
        if intent_data.get('follow_up'):
            follow_up_message = intent_data.get('follow_up', 'Could you explain your query further')

            # Create and save session data before returning
            session_data = {
                "topic": current_topic,
                "message_query": user_query,
                "query_id": query_id,
                "enhanced_query": user_query,
                "vector_data": vector_data,
                "creative_data": creative_data,
                "media_plan_output": "",
                "creative_insights_output": "",
                "campaign_performance_output": "",
                "general_response_string": follow_up_message,
                "timestamp": datetime.now().isoformat()
            }

            existing_data.append(session_data)
            cache_control.setex(cache_key, 500, json.dumps(existing_data))
            logger.debug(f"Current Session Data:{session_data}")
            yield {"response": follow_up_message}

            # Generate related queries for follow-up questions
            # Send a status update that we're wrapping up
            yield {"status": "wrapping_up", "message": "Wrapping up and finding related topics..."}

            # Use general related queries prompt for follow-up scenarios
            related_prompt_file = "related_queries_general_v2"

            # Create output_parts context from follow_up_message
            follow_up_output_parts = {"follow_up_response": follow_up_message} if follow_up_message else None

            if past_vector_names and non_empty_fields:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, non_empty_fields=non_empty_fields, past_vector_names=past_vector_names, query_id=query_id, output_parts=follow_up_output_parts)
            elif past_vector_names:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, past_vector_names=past_vector_names, query_id=query_id, output_parts=follow_up_output_parts)
            elif non_empty_fields:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, non_empty_fields=non_empty_fields, query_id=query_id, output_parts=follow_up_output_parts)
            else:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, query_id=query_id, output_parts=follow_up_output_parts)

            yield {"related_queries": related_queries}

            # Store related queries for session continuity
            if related_queries:
                await store_related_queries(query_id, session_id, related_queries)

            # Capture the end time for follow-up queries
            follow_up_end_time = datetime.now(timezone.utc)

            # Store follow-up message to database before returning
            await handle_periodic_db_storage(
                user_id=user_id,
                session_id=session_id,
                query_id=query_id,
                user_query=user_query,
                final_response=follow_up_message,  # Store the follow-up message as-is
                end_time=follow_up_end_time
            )

            return

        # Creative Feedback - Constructive Feedback based on provided Creative
        if 8 in required_outcomes:
            result = ideate_to_create_without_rag(user_query, inference_payload.creative, conversation_history, query_id)
            result = replace_hash_with_url(remove_markdown_prefix(result))
            yield {"response": result}
            general_response_string += result
            related_prompt_file = "related_queries_general_v2"

        # Uploaded Creative Trends analysis
        if 6 in required_outcomes:
            result = await ideate_to_create_with_rag(
                user_query=user_query,
                creative=inference_payload.creative,
                conversation_history=conversation_history,
                parameters=parameters,
                query_id=query_id
            )
            result = replace_hash_with_url(remove_markdown_prefix(result))
            yield {"response": result}
            general_response_string += result
            related_prompt_file = "related_queries_ideate_to_create_with_rag"

        # Generic queries
        if 10 in required_outcomes:
            # Send a status update that we're processing the query
            yield {"status": "processing", "message": "Processing your query..."}

            if inference_payload.creative:
                if vector_search:
                    filtered_data = await search_qdrant(user_query, conversation_history, parameters, use_vector_search=True, number_of_results=threshold, unrelated_query=unrelated_query, query_id=query_id)
                    result = generic_with_creative(user_query=user_query, creative=inference_payload.creative, conversation_history=conversation_history, filtered_data=filtered_data, query_id=query_id)
                    result = replace_hash_with_url(remove_markdown_prefix(result))
                    yield {"response": result}
                else:
                    result = generic_with_creative(user_query=user_query, creative=inference_payload.creative, conversation_history=conversation_history, query_id=query_id)
                    result = replace_hash_with_url(remove_markdown_prefix(result))
                    yield {"response": result}
            else:
                if vector_search:
                    filtered_data = await search_qdrant(user_query, conversation_history, parameters, use_vector_search=True, number_of_results=threshold, unrelated_query=unrelated_query, query_id=query_id)
                    result = await generic_without_creative(user_query, conversation_history, filtered_data=filtered_data, query_id=query_id)
                    yield {"response": f"{result}\n\n"}
                else:
                    result = await generic_without_creative(user_query, conversation_history, query_id=query_id)
                    yield {"response": f"{result}\n\n"}
            general_response_string += result
            related_prompt_file = "related_queries_general_v2"
            # Note: Related queries generation moved to end to avoid double calling

        if any(num in required_outcomes for num in [1, 3, 4, 5]):
            # Send a status update that we're searching for relevant data
            yield {"status": "searching", "message": "Searching for relevant campaign data..."}
            filtered_data = await search_qdrant(user_query, conversation_history, parameters, False, 10, unrelated_query=unrelated_query, query_id=query_id)

            if not filtered_data.results:
                logger.info("No results found, retrying with vector search")
                filtered_data = await search_qdrant(user_query, conversation_history, parameters, use_vector_search=True, number_of_results=threshold, unrelated_query=unrelated_query, query_id=query_id)
                if len(filtered_data.results) < 1:
                    yield {"response": "Media Campaign Information related to your query were not found. Please try a different query.\n"}
                    return
            elif len(filtered_data.results) < threshold:
                logger.info(f"Not enough results found, fetching additional {threshold - len(filtered_data.results)} results. Currently receieved: {len(filtered_data.results)}")
                currently_present_ids = [i.id for i in filtered_data.results]
                logger.info(f"Currently present IDS{currently_present_ids}")
                retry_count +=1
                # Create previous search context to pass to additional search
                from model import PreviousSearchContext
                previous_context = None
                if filtered_data.search_context:
                    previous_context = PreviousSearchContext(
                        search_type=filtered_data.search_context.search_type,
                        applied_filters=filtered_data.search_context.applied_filters,
                        excluded_ids=currently_present_ids,  # Exclude already found IDs
                        retry_count=filtered_data.search_context.retry_count,
                        search_explanation=filtered_data.search_context.search_explanation
                    )
                    logger.info(f"Passing previous search context to additional search: {len(currently_present_ids)} IDs to exclude")

                additional_data = await search_qdrant(
                    query_text=user_query,
                    conversation_payload=conversation_history,
                    parameters=parameters,
                    use_vector_search=True,
                    number_of_results=(threshold - len(filtered_data.results)),
                    unrelated_query=unrelated_query,
                    retry_count=retry_count,
                    previous_search_context=previous_context,
                    query_id=query_id
                )

                # DEBUG: Log search context status before merging
                logger.info(f"BEFORE MERGING - filtered_data.search_context: {filtered_data.search_context is not None}")
                logger.info(f"BEFORE MERGING - additional_data.search_context: {additional_data.search_context is not None}")
                if filtered_data.search_context:
                    logger.info(f"BEFORE MERGING - original search_type: {filtered_data.search_context.search_type}")
                if additional_data.search_context:
                    logger.info(f"BEFORE MERGING - additional search_type: {additional_data.search_context.search_type}")

                if len(additional_data.results) > 0:
                    for additional_result in additional_data.results:
                        if additional_result.id not in currently_present_ids:
                            filtered_data.results.append(additional_result)
                            filtered_data.total += 1

                    # Merge search context from additional search
                    if additional_data.search_context and filtered_data.search_context:
                        logger.info("Merging search context from additional search")
                        # Update the original search context with additional search information
                        filtered_data.search_context.final_results_count = len(filtered_data.results)

                        # Add retry information to the original search context
                        if additional_data.search_context.retry_count > filtered_data.search_context.retry_count:
                            filtered_data.search_context.retry_count = additional_data.search_context.retry_count

                        # Merge retry history
                        if additional_data.search_context.retry_history:
                            if not filtered_data.search_context.retry_history:
                                filtered_data.search_context.retry_history = []
                            filtered_data.search_context.retry_history.extend(additional_data.search_context.retry_history)

                        # Update search explanation to reflect the combined search
                        original_explanation = filtered_data.search_context.search_explanation
                        additional_explanation = additional_data.search_context.search_explanation
                        filtered_data.search_context.search_explanation = f"{original_explanation} Additional search performed to reach threshold: {additional_explanation}"

                        logger.info(f"Updated search context: final_results_count={filtered_data.search_context.final_results_count}, retry_count={filtered_data.search_context.retry_count}")
                    elif additional_data.search_context and not filtered_data.search_context:
                        # If original search had no context but additional search does, use the additional context
                        logger.info("Using search context from additional search (original had none)")
                        filtered_data.search_context = additional_data.search_context
                        filtered_data.search_context.final_results_count = len(filtered_data.results)
                    else:
                        logger.warning(f"SEARCH CONTEXT MERGE FAILED - filtered_data.search_context: {filtered_data.search_context is not None}, additional_data.search_context: {additional_data.search_context is not None}")

                # DEBUG: Log final search context status after merging
                logger.info(f"AFTER MERGING - filtered_data.search_context: {filtered_data.search_context is not None}")
                if filtered_data.search_context:
                    logger.info(f"AFTER MERGING - final search_type: {filtered_data.search_context.search_type}")
                    logger.info(f"AFTER MERGING - final_results_count: {filtered_data.search_context.final_results_count}")
                    logger.info(f"AFTER MERGING - retry_count: {filtered_data.search_context.retry_count}")

                logger.info(f"Added additional data: So Final results: {len(filtered_data.results)}")

            vector_data = {ad_creative.id: ad_creative.model_dump() for ad_creative in filtered_data.results}

            for past_vector in past_vectors:
                vector_data[past_vector['id']] = past_vector

            vector_data = list(vector_data.values())
            filtered_data_with_past_vectors = SearchResult(
                results=[AdCreative(**data) for data in vector_data],
                total=len(vector_data),
                search_context=filtered_data.search_context  # Preserve search context when adding past vectors
            )
            output_parts = OrderedDict()
            ordered_keys = ["media_plan", "analysis_of_trends", "campaign_performance", "creative_insights", "performance_summary"]

            for outcome in required_outcomes:
                if outcome == 1:  # Media plan
                    # Send a status update that we're creating a media plan
                    yield {"status": "media_plan", "message": "Creating your media plan..."}
                    result = await media_plan(filtered_data_with_past_vectors, user_query, conversation_history, past_vector_names, query_id)
                    media_plan_output += result  # Add result to media_plan_output
                    output_parts[ordered_keys[outcome - 1]] = result
                    yield {"response": result}
                # elif outcome == 2:  # Analysis of trends
                #     # Send a status update that we're analyzing trends
                #     yield {"status": "analyzing_trends", "message": "Analyzing market trends..."}
                #     result = await analysis_of_trends(filtered_data_with_past_vectors, user_query, conversation_history)
                #     result = replace_hash_with_url(remove_markdown_prefix(result))
                #     general_response_string += result
                #     output_parts[ordered_keys[outcome - 1]] = result
                #     yield {"response": result}
                elif outcome == 3:  # Campaign performance
                    # Send a status update that we're analyzing campaign performance
                    yield {"status": "campaign_performance", "message": "Analyzing campaign performance..."}

                    # DEBUG: Log what search context is being passed to campaign_performance
                    logger.info(f"CALLING CAMPAIGN_PERFORMANCE - search_context available: {filtered_data_with_past_vectors.search_context is not None}")
                    if filtered_data_with_past_vectors.search_context:
                        logger.info(f"CALLING CAMPAIGN_PERFORMANCE - search_type: {filtered_data_with_past_vectors.search_context.search_type}")
                        logger.info(f"CALLING CAMPAIGN_PERFORMANCE - final_results_count: {filtered_data_with_past_vectors.search_context.final_results_count}")
                        logger.info(f"CALLING CAMPAIGN_PERFORMANCE - retry_count: {filtered_data_with_past_vectors.search_context.retry_count}")
                        logger.info(f"CALLING CAMPAIGN_PERFORMANCE - search_explanation: {filtered_data_with_past_vectors.search_context.search_explanation}")

                    result = await campaign_performance(filtered_data_with_past_vectors, user_query, conversation_history,retry_count=retry_count, query_id=query_id)
                    result = replace_hash_with_url(remove_markdown_prefix(result))
                    campaign_performance_output += result
                    output_parts[ordered_keys[outcome - 1]] = result
                    yield {"response": result}
                elif outcome == 4:  # Creative insights
                    # Send a status update that we're analyzing creative insights
                    yield {"status": "creative_insights", "message": "Analyzing creative insights..."}
                    result = await creative_insights(filtered_data_with_past_vectors, user_query, conversation_history, query_id=query_id)
                    result = replace_hash_with_url(remove_markdown_prefix(result))
                    creative_insights_output += result
                    output_parts[ordered_keys[outcome - 1]] = result
                    yield {"response": result}
                elif outcome == 5:  # Performance summary
                    # Send a status update that we're creating a performance summary
                    yield {"status": "performance_summary", "message": "Creating performance summary..."}
                    performance_summary_result = await performance_summary(user_query, output_parts, query_id)
                    performance_summary_result = replace_hash_with_url(remove_markdown_prefix(performance_summary_result))
                    output_parts["performance_summary"] = performance_summary_result
                    general_response_string += performance_summary_result  # Add to general_response_string
                    yield {"response": f"{performance_summary_result}\n\n"}

        if 7 in required_outcomes:
            # For image operations, get ALL past creative data without topic filtering
            # This ensures we have access to all previous creatives regardless of topic
            past_creative_data = get_all_past_creative_data(existing_data)
            if past_creative_data:
                logger.info(f"Past creative Data (all topics): {len(past_creative_data)} items")

            # Prepare the generator function based on parameters
            image_generator = None
            if inference_payload.creative:
                # Use the temp URL for uploaded images or the original creative URL for direct links
                creative_url_to_use = temp_url if 'temp_url' in locals() else inference_payload.creative

                if past_creative_data:
                    image_generator = creative_inspiration_with_gemini_and_imagen(
                        user_query=user_query,
                        creative=creative_url_to_use,
                        conversation_history=conversation_history,
                        vector_search=vector_search,
                        existing_data=past_creative_data,
                        extracted_features=extracted_features,
                        query_id=query_id
                    )
                else:
                    image_generator = creative_inspiration_with_gemini_and_imagen(
                        user_query=user_query,
                        creative=creative_url_to_use,
                        conversation_history=conversation_history,
                        vector_search=vector_search,
                        extracted_features=extracted_features,
                        query_id=query_id
                    )
            else:
                if past_creative_data:
                    image_generator = creative_inspiration_with_gemini_and_imagen(
                        user_query=user_query,
                        conversation_history=conversation_history,
                        vector_search=vector_search,
                        existing_data=past_creative_data,
                        query_id=query_id
                    )
                else:
                    image_generator = creative_inspiration_with_gemini_and_imagen(
                        user_query=user_query,
                        conversation_history=conversation_history,
                        vector_search=vector_search,
                        query_id=query_id
                    )

            # Process the streaming responses
            final_result = None
            multi_results = []
            logger.info("Starting to process image generator chunks")
            async for chunk in image_generator:
                # Log each chunk type for debugging
                logger.info(f"Received chunk with status: {chunk.get('status')}")

                # Forward progress updates to the client
                if chunk.get("status") == "complete":
                    # This is the final result with the image
                    final_result = chunk.get("result")
                    logger.info(f"Received complete status with is_multi_generate={chunk.get('is_multi_generate', False)}")

                    # Check if this is a multi-generate completion
                    if chunk.get("is_multi_generate"):
                        # For multi-generate, we've already streamed each image individually
                        # Just send a completion status without duplicating content
                        logger.debug("Multi-generate operation completed - not sending duplicate content")
                        # Don't yield the final result again as it contains all images already sent
                    elif final_result and "MarkdownOutput" in final_result:
                        # For single image generation, send the result
                        logger.debug("Sending single image generation result")
                        # Convert S3 keys to URLs before sending to frontend
                        from tools.store_s3 import process_s3_keys_to_urls
                        processed_markdown = process_s3_keys_to_urls(final_result["MarkdownOutput"], expires_in=7200)
                        yield {"response": processed_markdown}
                    elif final_result and "explanation" in final_result:
                        yield {"response": final_result["explanation"]}
                elif chunk.get("status") == "partial_result":
                    # For multi-generate, stream each image as it's created
                    partial_result = chunk.get("result")
                    if partial_result and "MarkdownOutput" in partial_result:
                        logger.debug(f"Sending partial result {chunk.get('index', '?')}/{chunk.get('total', '?')}")
                        multi_results.append(partial_result)

                        # Add each partial result to creative_data to ensure it's stored in the session
                        if partial_result.get("S3Key"):
                            # Create a creative info object similar to what we do for uploaded images
                            partial_creative_info = {
                                "creative_id": f"generated_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}",
                                "s3_key": partial_result.get("S3Key"),
                                "title": partial_result.get("Title", "Generated Image"),
                                "dimensions": partial_result.get("Dimensions", ""),
                                "aspect_ratio": partial_result.get("AspectRatio", ""),
                                "role": f"Generated image in {partial_result.get('AspectRatio', '')} aspect ratio",
                                "query_id": query_id,
                                "timestamp": datetime.now().isoformat()
                            }
                            creative_data.append(partial_creative_info)
                            logger.info(f"Added partial result to creative_data: {partial_creative_info['s3_key']}")

                        # Add explicit yield for each partial result
                        await asyncio.sleep(0)  # Allow event loop to process
                        # Convert S3 keys to URLs before sending to frontend
                        from tools.store_s3 import process_s3_keys_to_urls
                        processed_markdown = process_s3_keys_to_urls(partial_result["MarkdownOutput"], expires_in=7200)
                        yield {"response": processed_markdown, "partial": True}
                else:
                    # Forward progress updates
                    logger.debug(f"Forwarding status update: {chunk.get('status')}")
                    yield {"status": chunk.get("status"), "message": chunk.get("message")}

            if final_result:
                # Ensure the final result has all the necessary information for the session
                if isinstance(final_result, dict) and "S3Key" in final_result:
                    # Create a properly structured creative info object
                    final_creative_info = {
                        "creative_id": f"generated_{datetime.now().strftime('%Y%m%d%H%M%S')}_{str(uuid.uuid4())[:8]}",
                        "s3_key": final_result.get("S3Key"),
                        "title": final_result.get("Title", "Generated Image"),
                        "features": final_result.get("PromptUsed", ""),  # Store the prompt as features
                        "explanation": final_result.get("Explanation", ""),
                        "role": "Generated image based on user request",  # Add a default role
                        "query_id": query_id,
                        "timestamp": datetime.now().isoformat()
                    }
                    creative_data.append(final_creative_info)
                    logger.info(f"Added final result to creative_data: {final_creative_info['s3_key']}")
                else:
                    # If the structure is unexpected, store the original result
                    creative_data.append(final_result)
                    logger.warning(f"Added raw final result to creative_data (unexpected structure)")

                related_prompt_file = "related_queries_generate_advertisement"

        # Set appropriate related prompt file based on outcomes
        if 1 in required_outcomes:
            related_prompt_file = "related_queries_media_plan_v3"
        # elif 2 in required_outcomes:
            # related_prompt_file = "related_queries_overall_trends"
        elif 3 in required_outcomes and 4 in required_outcomes:
            related_prompt_file = "related_queries_general_v2"
        elif 3 in required_outcomes:
            related_prompt_file = "related_queries_campaign_performance_v2"
        elif 4 in required_outcomes:
            related_prompt_file = "related_queries_creative_insights"

        # Generate related queries only if the outcome is not 9 or 11
        if 9 not in required_outcomes and 11 not in required_outcomes:
            # Send a status update that we're wrapping up
            yield {"status": "wrapping_up", "message": "Wrapping up and finding related topics..."}

            # Create comprehensive output_parts context from all available outputs
            comprehensive_output_parts = {}
            if 'output_parts' in locals() and output_parts:
                comprehensive_output_parts.update(output_parts)
            if general_response_string:
                comprehensive_output_parts["general_response"] = general_response_string
            if media_plan_output:
                comprehensive_output_parts["media_plan"] = media_plan_output
            if creative_insights_output:
                comprehensive_output_parts["creative_insights"] = creative_insights_output
            if campaign_performance_output:
                comprehensive_output_parts["campaign_performance"] = campaign_performance_output

            # Use comprehensive context if available, otherwise None
            context_to_use = comprehensive_output_parts if comprehensive_output_parts else None

            if past_vector_names and non_empty_fields:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, non_empty_fields=non_empty_fields, past_vector_names=past_vector_names, query_id=query_id, output_parts=context_to_use)
            elif past_vector_names:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, past_vector_names=past_vector_names, query_id=query_id, output_parts=context_to_use)
            elif non_empty_fields:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, non_empty_fields=non_empty_fields, query_id=query_id, output_parts=context_to_use)
            else:
                related_queries = await generate_related_queries(intent_data, conversation_history, user_query, prompt_file=related_prompt_file, query_id=query_id, output_parts=context_to_use)
            yield {"related_queries": related_queries}

            # Store related queries for session continuity
            if related_queries:
                await store_related_queries(query_id, session_id, related_queries)

        session_data = {
            "topic": current_topic,
            "message_query": user_query,
            "query_id": query_id,
            "enhanced_query": user_query,
            "vector_data": vector_data,
            "creative_data": creative_data,
            "media_plan_output": media_plan_output,
            "creative_insights_output": creative_insights_output,
            "campaign_performance_output": campaign_performance_output,
            "general_response_string": general_response_string,
            "timestamp": datetime.now().isoformat()
        }

        existing_data.append(session_data)

        logger.debug(f"Current Session Data:{session_data}")
        cache_control.setex(cache_key, 500, json.dumps(existing_data))

        # Capture the end time right after query processing finishes
        query_end_time = datetime.now(timezone.utc)

        # Database storage after every query
        await handle_periodic_db_storage(
            user_id=user_id,
            session_id=session_id,
            query_id=query_id,
            user_query=user_query,
            final_response=get_final_response_text(
                media_plan_output,
                creative_insights_output,
                campaign_performance_output,
                general_response_string,
                creative_data=creative_data,
                session_data=session_data
            ),
            end_time=query_end_time,
            intent_detected=str(intent_data.get("required_outcomes")) if 'intent_data' in locals() and intent_data else None
        )
        yield {"status": "complete", "message": ""}

    except Exception as e:
        logger.error(f"An error occurred: {e}")

        # Capture the end time for error tracking
        error_end_time = datetime.now(timezone.utc)

        # Complete query tracking with error details
        try:
            await execution_tracker.complete_query_execution(
                query_id=query_id,
                final_response=f"Error occurred during processing: {str(e)}",
                success=False,
                error_details=str(e),
                end_time=error_end_time,
                intent_detected=str(intent_data.get("required_outcomes")) if 'intent_data' in locals() and intent_data else None
            )
        except Exception as tracking_error:
            logger.error(f"Failed to track error in database: {tracking_error}")

        yield {"response": f"An error occurred: {e}\n"}
