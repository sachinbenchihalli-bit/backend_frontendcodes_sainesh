#!/usr/bin/env python
"""
Test script for the search_qdrant function.

This script tests the search_qdrant function with various types of queries and displays
the results. It helps debug issues with the search implementation by showing detailed
logging of the search process.

Usage:
    python test_search_qdrant.py [--query "your query here"] [--verbose] [--vector-search]

Options:
    --query          Specific query to test
    --verbose        Show detailed output
    --vector-search  Force vector search mode
    --limit          Number of results to return
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

# Import the search_qdrant function and related models
from python_apps.media_backend.model import ConversationPayload, SearchResult, AdCreative
from python_apps.media_backend.llm_rag_inference import search_qdrant
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Test queries based on the test_search_planner examples
TEST_QUERIES = [
    # Brand queries
    "Show me Nike campaigns",
    "Show me Adidas campaigns",
    "Find FanDuel ads",

    # Industry queries
    "Show me campaigns in the Finance sector",
    "Find Technology industry ads",
    "What are the best Automotive campaigns",

    # Performance queries
    "Show me campaigns with highest conversion rates",
    "Find ads with the most impressions",

    # Season queries
    "Show me holiday campaigns",
    "Find summer ads",

    # Complex queries
    "Show me Nike holiday campaigns with high conversion rates",
    "Find Technology industry campaigns with good performance",

    # Semantic queries
    "Find campaigns similar to successful sports apparel ads",
    "Show me ads that use humor effectively",

    # Queries with multiple brands or industries
    "Compare Nike and Adidas campaigns",
    "Show me campaigns from both Finance and Technology sectors"
]

# Sample conversation history
SAMPLE_CONVERSATIONS = {
    "empty": [],
    "brand_query": [
        {"actor": "user", "content": "Show me Nike campaigns"},
        {"actor": "assistant", "content": "Here are some Nike campaigns..."}
    ],
    "performance_query": [
        {"actor": "user", "content": "Which campaigns have the highest conversion rates?"},
        {"actor": "assistant", "content": "Here are campaigns with high conversion rates..."}
    ],
    "industry_query": [
        {"actor": "user", "content": "Show me campaigns in the Technology sector"},
        {"actor": "assistant", "content": "Here are some Technology sector campaigns..."}
    ]
}

async def test_search_qdrant(
    query: str,
    conversation_history: List[Dict[str, str]] = None,
    use_vector_search: bool = None,
    number_of_results: int = None,
    verbose: bool = False
) -> None:
    """
    Test the search_qdrant function with a specific query.

    Args:
        query: The query to test
        conversation_history: The conversation history
        use_vector_search: Whether to force vector search mode
        number_of_results: Number of results to return
        verbose: Whether to show detailed output
    """
    print(f"\n{'='*80}")
    print(f"Testing query: {query}")
    if use_vector_search is not None:
        print(f"Vector search: {use_vector_search}")
    if number_of_results is not None:
        print(f"Number of results: {number_of_results}")
    print(f"{'='*80}")

    # Convert conversation history to ConversationPayload objects
    conversation_payload = []
    if conversation_history:
        conversation_payload = [ConversationPayload(**msg) for msg in conversation_history]
        print("\nConversation History:")
        for msg in conversation_history:
            print(f"  {msg['actor']}: {msg['content']}")

    try:
        # Call the search_qdrant function
        result = await search_qdrant(
            query_text=query,
            conversation_payload=conversation_payload,
            parameters={},
            use_vector_search=use_vector_search,
            number_of_results=number_of_results
        )

        # Print the results
        print(f"\nSearch Results: {len(result.results)} items found")

        if verbose:
            # Print detailed results
            for i, creative in enumerate(result.results):
                print(f"\nResult {i+1}:")
                print(f"  ID: {creative.id}")
                print(f"  Brand: {creative.brand}")
                print(f"  Industry: {creative.industry_sectors}")  # Updated field name
                print(f"  Campaign: {creative.campaign_folder}")
                print(f"  Conversion: {creative.conversion}")
        else:
            # Print summary
            brands = {}
            industries = {}
            for creative in result.results:
                brand = creative.brand or "Unknown"
                industry = creative.industry_sectors or "Unknown"  # Updated field name
                brands[brand] = brands.get(brand, 0) + 1
                industries[industry] = industries.get(industry, 0) + 1

            print("\nBrands found:")
            for brand, count in brands.items():
                print(f"  {brand}: {count}")

            print("\nIndustries found:")
            for industry, count in industries.items():
                print(f"  {industry}: {count}")

    except Exception as e:
        logger.error(f"Error testing search_qdrant: {e}")
        print(f"\nError: {e}")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the search_qdrant function.")
    parser.add_argument("--query", type=str, help="Query to test")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--vector-search", action="store_true", help="Force vector search mode")
    parser.add_argument("--limit", type=int, help="Number of results to return")
    parser.add_argument("--conversation", type=str, choices=list(SAMPLE_CONVERSATIONS.keys()), default="empty", help="Conversation history to use")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)

    # Get conversation history
    conversation_history = SAMPLE_CONVERSATIONS[args.conversation]

    if args.query:
        # Test with the provided query
        await test_search_qdrant(
            query=args.query,
            conversation_history=conversation_history,
            use_vector_search=args.vector_search,
            number_of_results=args.limit,
            verbose=args.verbose
        )
    else:
        # Test with predefined queries
        for query in TEST_QUERIES:
            await test_search_qdrant(
                query=query,
                conversation_history=conversation_history,
                use_vector_search=args.vector_search,
                number_of_results=args.limit,
                verbose=args.verbose
            )
            # Add a small delay between queries
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
