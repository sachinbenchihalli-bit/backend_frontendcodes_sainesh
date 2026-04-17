"""
Search planner agent for Qdrant search.
"""
import json
import logging
from typing import List, Optional
from model import ConversationPayload, SearchPlannerOutput, SearchStep, PreviousSearchContext
from prompts.prompts import SystemPrompts
from search_tools import get_available_brands, get_available_industries, get_available_seasons
from llm_utils import generate_response

# Configure logging
logger = logging.getLogger(__name__)

async def search_planner_agent(
    user_query: str,
    conversation_history: List[ConversationPayload],
    previous_search_failed: bool = False,
    previous_search_context: Optional[PreviousSearchContext] = None,
    query_id: Optional[str] = None
) -> SearchPlannerOutput:
    """
    Analyzes the user query and conversation history to create a search plan.

    Args:
        user_query (str): The user's query text
        conversation_history (List[ConversationPayload]): Previous conversation messages
        previous_search_failed (bool): Whether a previous search with this query returned zero results
        previous_search_context (Optional[PreviousSearchContext]): Detailed context about the previous failed search

    Returns:
        SearchPlannerOutput: A structured search plan
    """
    # Handle empty query
    if not user_query or user_query.strip() == "":
        logger.warning("Empty query provided to search_planner_agent")
        return create_default_search_plan("")

    try:
        # Get available data for the tools
        brands = await get_available_brands()
        industries = await get_available_industries()
        seasons = await get_available_seasons()

        # Add tool information to the system prompt
        system_prompt = SystemPrompts.get_prompt("search_planner")
        system_prompt += f"\n\nAvailable Brands: {', '.join(brands.brands)}"
        system_prompt += f"\nAvailable Industries: {', '.join(industries.industries)}"
        system_prompt += f"\nAvailable Seasons: {', '.join(seasons.seasons)}"

        # Add information about previous search failure if applicable
        if previous_search_failed:
            logger.info(f"Previous search failed flag is True. Previous context provided: {previous_search_context is not None}")
            if previous_search_context:
                logger.info(f"Previous search context details: search_type={previous_search_context.search_type}, applied_filters={len(previous_search_context.applied_filters)}, retry_count={previous_search_context.retry_count}")
            system_prompt += "\n\nIMPORTANT: A previous search plan for this query returned zero results. Please create a broader search plan that is more likely to return results. Consider using semantic search instead of filtering, or using more general filter criteria."

            # Add detailed context about the previous search if available
            if previous_search_context:
                logger.info(f"Adding detailed previous search context: {previous_search_context.model_dump_json()}")
                system_prompt += f"\n\nDETAILED PREVIOUS SEARCH CONTEXT:"
                system_prompt += f"\n- Previous search type: {previous_search_context.search_type}"
                system_prompt += f"\n- Retry count: {previous_search_context.retry_count}"
                system_prompt += f"\n- Filter logic used: {previous_search_context.filter_logic} ({'AND' if previous_search_context.filter_logic == 'must' else 'OR'})"
                system_prompt += f"\n- Total candidates found: {previous_search_context.total_candidates_found}"
                system_prompt += f"\n- Final results count: {previous_search_context.final_results_count}"

                if previous_search_context.applied_filters:
                    system_prompt += f"\n- Applied filters:"
                    for filter_item in previous_search_context.applied_filters:
                        system_prompt += f"\n  * {filter_item.field}: {filter_item.value} (match type: {filter_item.match_type})"

                if previous_search_context.retry_history:
                    system_prompt += f"\n- Previous retry attempts:"
                    for i, retry in enumerate(previous_search_context.retry_history, 1):
                        system_prompt += f"\n  {i}. {retry}"

                if previous_search_context.search_explanation:
                    system_prompt += f"\n- Previous search explanation: {previous_search_context.search_explanation}"

                system_prompt += f"\n\nBased on this context, please create a different search strategy that avoids the same approach and is more likely to find relevant results."
            else:
                logger.warning("Previous search failed but no detailed context was provided")

        logger.info(f"SearchPlanner System prompt for planning: {system_prompt}")
        # Use the generate_response function with SearchPlannerOutput as response_class
        response_content = await generate_response(
            query=user_query,
            system_prompt=system_prompt,
            conversation_history=conversation_history,
            max_tokens=1000,
            response_class=SearchPlannerOutput,
            model="gpt-4o-mini",
            query_id=query_id,
            agent_name="search_planner_agent"
        )

        # Log the response for debugging
        logger.info(f"Search planner response: {response_content}")

        # Validate industry sectors if present in the response
        response_content = validate_industry_sectors(response_content)

        # If response_content is already a SearchPlannerOutput object, return it
        if isinstance(response_content, SearchPlannerOutput):
            logger.info(f"Search planner parameters: {response_content.model_dump_json(indent=2)}")
            return response_content

        # If we got a string response, try to parse it
        if isinstance(response_content, str):
            try:
                # Clean up the response
                clean_response = response_content.strip()
                if clean_response.startswith("```json"):
                    clean_response = clean_response[7:]
                if clean_response.endswith("```"):
                    clean_response = clean_response[:-3]

                # Parse the JSON
                clean_params = json.loads(clean_response)

                # Log the parsed parameters before validation
                logger.info(f"Parsed search parameters before validation: {json.dumps(clean_params, indent=2)}")

                # Check if required fields are present
                if 'steps' not in clean_params or 'search_type' not in clean_params:
                    logger.warning("Missing required fields in response, creating default SearchPlannerOutput")
                    return create_default_search_plan(user_query)

                # Log steps and their parameters
                for i, step in enumerate(clean_params['steps']):
                    logger.info(f"Step {i+1}: {step.get('step_type')} - {step.get('description')}")
                    logger.info(f"  Parameters: {step.get('parameters', {})}")

                # Validate the response
                validated_response = SearchPlannerOutput(**clean_params)
                logger.info(f"Search planner parameters after validation: {validated_response.model_dump_json(indent=2)}")
                return validated_response

            except json.JSONDecodeError as json_error:
                logger.error(f"JSON parsing error in search_planner_agent: {json_error}")
                logger.error(f"Raw response: {response_content}")
                # Return a default search plan
                return create_default_search_plan(user_query)

            except ValueError as validation_error:
                logger.error(f"Validation error in search_planner_agent: {validation_error}")
                # Return a default search plan
                return create_default_search_plan(user_query)

        # If we got here, something unexpected happened
        logger.error(f"Unexpected response type: {type(response_content)}")
        return create_default_search_plan(user_query)

    except Exception as e:
        logger.error(f"Error in search_planner_agent: {e}")
        logger.error(f"Query that led to error: {user_query}")
        # Return a default search plan
        return create_default_search_plan(user_query)

def create_default_search_plan(query: str) -> SearchPlannerOutput:
    """
    Creates a default search plan when the agent fails.

    Args:
        query (str): The user's query text

    Returns:
        SearchPlannerOutput: A default search plan
    """
    try:
        # Create a simple semantic search plan with sorting parameters included
        logger.info("Creating default search plan")
        semantic_step = SearchStep(
            step_type="semantic_search",
            description="Perform semantic search on the query and sort by conversion rate descending",
            parameters={
                "query": query,
                "sort_field": "conversion",
                "sort_order": "desc"
            }
        )

        # Return a default plan
        return SearchPlannerOutput(
            steps=[semantic_step],
            search_type="semantic_only",
            limit=10
        )
    except Exception as e:
        logger.error(f"Error creating default search plan: {e}")
        # Create a minimal valid search plan as a last resort
        return SearchPlannerOutput(
            steps=[
                SearchStep(
                    step_type="semantic_search",
                    description="Default semantic search with default sorting by conversion rate",
                    parameters={
                        "sort_field": "conversion",
                        "sort_order": "desc"
                    }
                )
            ],
            search_type="semantic_only",
            limit=10
        )

def validate_industry_sectors(response: SearchPlannerOutput) -> SearchPlannerOutput:
    """
    Validates and corrects industry_sectors parameter in search steps.

    Args:
        response (SearchPlannerOutput): The search planner response

    Returns:
        SearchPlannerOutput: The validated search planner response
    """
    # Define valid industry sectors
    VALID_INDUSTRIES = {
        "Automotive": ["car", "auto", "vehicle", "automotive"],
        "Entertainment & Media": ["entertainment", "media", "film", "tv", "television", "movie", "music", "streaming"],
        "Fashion & Retail": ["fashion", "retail", "clothing", "apparel", "shop", "store"],
        "Food & Beverage": ["food", "beverage", "restaurant", "dining", "drink"],
        "Healthcare": ["health", "medical", "hospital", "pharma", "healthcare"],
        "Technology & Telecommunications": ["tech", "technology", "software", "phone", "telecom", "telecommunications", "it"],
        "Travel & Tourism": ["travel", "tourism", "hotel", "vacation", "flight", "airline"],
        "Sports & Recreation": ["sport", "recreation", "fitness", "outdoor", "athletic"],
        "Beauty & Personal Care": ["beauty", "cosmetic", "skincare", "personal care"],
        "Business Services": ["business", "service", "consulting", "utility", "marketing", "finance"]
    }

    # Check if response is a SearchPlannerOutput object
    if not isinstance(response, SearchPlannerOutput):
        return response

    # Iterate through steps to find and validate industry_sectors
    for step in response.steps:
        if "industry_sectors" in step.parameters:
            industry_value = step.parameters["industry_sectors"]

            # Skip if already a valid industry
            if industry_value in VALID_INDUSTRIES:
                continue

            # Try to map to a valid industry
            matched = False
            for valid_industry, keywords in VALID_INDUSTRIES.items():
                # Check if the industry value contains any of the keywords
                if any(keyword.lower() in industry_value.lower() for keyword in keywords):
                    logger.info(f"Mapping industry '{industry_value}' to valid industry '{valid_industry}'")
                    step.parameters["industry_sectors"] = valid_industry
                    matched = True
                    break

            # If no match found, use a default or remove
            if not matched:
                logger.warning(f"Invalid industry sector '{industry_value}' could not be mapped to a valid industry")
                # Default to a general category or remove the parameter
                if "travel" in industry_value.lower():
                    step.parameters["industry_sectors"] = "Travel & Tourism"
                elif "tech" in industry_value.lower():
                    step.parameters["industry_sectors"] = "Technology & Telecommunications"
                else:
                    # Remove invalid industry parameter
                    logger.warning(f"Removing invalid industry_sectors parameter: {industry_value}")
                    step.parameters.pop("industry_sectors")

    return response
