#!/usr/bin/env python
"""
Simple test script for the search planner agent.

This script provides a straightforward way to test the search planner agent
with specific queries and see the generated search plans.

Usage:
    python test_search_planner_simple.py [--query "your query here"]

If no query is provided, the script will run a set of predefined test queries.
"""

import os
import sys
import json
import logging
import argparse
import asyncio
from typing import List, Dict, Any, Optional

# Add the parent directory to the path so we can import from the parent module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the search planner agent and related models
from python_apps.media_backend.model import ConversationPayload, SearchPlannerOutput, SearchStep
from python_apps.media_backend.search_planner import search_planner_agent
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Predefined test queries
TEST_QUERIES = [
    "Show me Nike campaigns",
    "Find campaigns with high conversion rates",
    "Show me holiday ads for retail brands",
    "What are the best performing automotive campaigns?",
    "Show me campaigns from the Technology industry with high impressions"
]

async def test_search_planner(query: str, previous_search_failed: bool = False) -> None:
    """
    Test the search planner agent with a specific query.

    Args:
        query: The query to test
        previous_search_failed: Whether to simulate a previous search failure
    """
    print(f"\n{'='*80}")
    print(f"Testing query: {query}")
    print(f"Previous search failed: {previous_search_failed}")
    print(f"{'='*80}")

    # Create empty conversation history
    conversation_history = []

    try:
        # Call the search planner agent
        search_plan = await search_planner_agent(
            user_query=query,
            conversation_history=conversation_history,
            previous_search_failed=previous_search_failed
        )

        # Print the search plan
        print("\nSearch Plan:")
        print(f"  Search Type: {search_plan.search_type}")
        print(f"  Limit: {search_plan.limit}")
        print("\nSteps:")

        for i, step in enumerate(search_plan.steps):
            print(f"  Step {i+1}: {step.step_type}")
            print(f"    Description: {step.description}")
            print(f"    Parameters: {json.dumps(step.parameters, indent=4)}")

        # Print the raw JSON for reference
        print("\nRaw JSON:")
        print(json.dumps(search_plan.model_dump(), indent=2))

    except Exception as e:
        logger.error(f"Error testing search planner: {e}")

async def test_with_retry(query: str) -> None:
    """
    Test the search planner with a query, then retry with previous_search_failed=True.

    Args:
        query: The query to test
    """
    # First attempt
    await test_search_planner(query, previous_search_failed=False)

    # Retry with previous_search_failed=True
    await test_search_planner(query, previous_search_failed=True)

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the search planner agent.")
    parser.add_argument("--query", type=str, help="Query to test")
    parser.add_argument("--retry", action="store_true", help="Test with retry (previous_search_failed=True)")
    parser.add_argument("--api-key", type=str, help="OpenAI API key (overrides environment variable)")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Check for OpenAI API key
    if args.api_key:
        os.environ["OPENAI_API_KEY"] = args.api_key

    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable or use --api-key.")
        sys.exit(1)

    # Import and reinitialize the OpenAI client
    from llm_utils import client
    if client is None:
        from openai import OpenAI
        import llm_utils
        llm_utils.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        logger.info("Reinitialized OpenAI client")

    if args.query:
        # Test with the provided query
        if args.retry:
            await test_with_retry(args.query)
        else:
            await test_search_planner(args.query)
    else:
        # Test with predefined queries
        for query in TEST_QUERIES:
            await test_search_planner(query)
            # Add a small delay between queries
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
