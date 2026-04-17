#!/usr/bin/env python
"""
Interactive test script for the search_qdrant function.

This script provides an interactive way to test the search_qdrant function
with custom queries, conversation history, and parameters.

Usage:
    python test_search_qdrant_interactive.py
"""

import os
import sys
import json
import logging
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

# Sample queries
SAMPLE_QUERIES = [
    "Show me Nike campaigns",
    "Find campaigns with high conversion rates",
    "Show me campaigns in the Finance sector",
    "Find FanDuel ads",
    "Compare Nike and Adidas campaigns",
    "Show me holiday campaigns",
    "Find campaigns similar to successful sports apparel ads"
]

def print_header(text):
    """Print a header with the given text."""
    print(f"\n{'='*80}")
    print(f"{text}")
    print(f"{'='*80}")

def print_section(text):
    """Print a section header with the given text."""
    print(f"\n{'-'*40}")
    print(f"{text}")
    print(f"{'-'*40}")

def get_user_input(prompt, default=None):
    """Get user input with a default value."""
    if default:
        user_input = input(f"{prompt} [{default}]: ")
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ")

def select_conversation():
    """Let the user select a conversation history."""
    print_section("Select Conversation History")

    for i, (key, convo) in enumerate(SAMPLE_CONVERSATIONS.items()):
        print(f"{i+1}. {key} ({len(convo)} messages)")

    selection = get_user_input("Enter selection number (or 'empty' for no history)", "empty")

    if selection.isdigit() and 1 <= int(selection) <= len(SAMPLE_CONVERSATIONS):
        key = list(SAMPLE_CONVERSATIONS.keys())[int(selection) - 1]
        return SAMPLE_CONVERSATIONS[key]
    elif selection in SAMPLE_CONVERSATIONS:
        return SAMPLE_CONVERSATIONS[selection]
    else:
        return []

def select_sample_query():
    """Let the user select a sample query."""
    print_section("Select Sample Query")

    for i, query in enumerate(SAMPLE_QUERIES):
        print(f"{i+1}. {query}")

    selection = get_user_input("Enter selection number (or 'custom' for custom query)", "custom")

    if selection.isdigit() and 1 <= int(selection) <= len(SAMPLE_QUERIES):
        return SAMPLE_QUERIES[int(selection) - 1]
    else:
        return get_user_input("Enter your custom query")

async def test_search_qdrant(
    query: str,
    conversation_history: List[Dict[str, str]],
    use_vector_search: bool = None,
    number_of_results: int = None
) -> None:
    """
    Test the search_qdrant function with a specific query and conversation history.

    Args:
        query: The query to test
        conversation_history: The conversation history
        use_vector_search: Whether to force vector search mode
        number_of_results: Number of results to return
    """
    print_header("Testing Search Qdrant Function")

    print_section("Query")
    print(query)

    print_section("Conversation History")
    if conversation_history:
        for msg in conversation_history:
            print(f"{msg['actor']}: {msg['content']}")
    else:
        print("No conversation history")

    print_section("Parameters")
    print(f"Vector Search: {use_vector_search}")
    print(f"Number of Results: {number_of_results}")

    # Convert conversation history to ConversationPayload objects
    conversation_payload = [ConversationPayload(**msg) for msg in conversation_history]

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
        print_section(f"Search Results: {len(result.results)} items found")

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

        # Ask if user wants to see detailed results
        show_details = get_user_input("Show detailed results? (y/n)", "n").lower() in ["y", "yes"]

        if show_details:
            print_section("Detailed Results")
            for i, creative in enumerate(result.results):
                print(f"\nResult {i+1}:")
                print(f"  ID: {creative.id}")
                print(f"  Brand: {creative.brand}")
                print(f"  Industry: {creative.industry_sectors}")  # Updated field name
                print(f"  Campaign: {creative.campaign_folder}")
                print(f"  Conversion: {creative.conversion}")
                print(f"  File Name: {creative.file_name}")

    except Exception as e:
        logger.error(f"Error testing search_qdrant: {e}")
        print(f"\nError: {e}")

async def main():
    """Main function."""
    print_header("Search Qdrant Interactive Test")

    # Load environment variables
    load_dotenv()

    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)

    while True:
        # Get query
        query = select_sample_query()

        # Get conversation history
        conversation_history = select_conversation()

        # Get vector search parameter
        vector_search_input = get_user_input("Use vector search? (y/n/auto)", "auto").lower()
        use_vector_search = None
        if vector_search_input in ["y", "yes"]:
            use_vector_search = True
        elif vector_search_input in ["n", "no"]:
            use_vector_search = False

        # Get number of results
        limit_input = get_user_input("Number of results (or 'auto' for default)", "auto")
        number_of_results = None
        if limit_input.isdigit():
            number_of_results = int(limit_input)

        # Test the search_qdrant function
        await test_search_qdrant(
            query=query,
            conversation_history=conversation_history,
            use_vector_search=use_vector_search,
            number_of_results=number_of_results
        )

        # Ask to continue
        continue_input = get_user_input("Continue? (y/n)", "y").lower()
        if continue_input not in ["y", "yes"]:
            print("Exiting...")
            break

if __name__ == "__main__":
    asyncio.run(main())
