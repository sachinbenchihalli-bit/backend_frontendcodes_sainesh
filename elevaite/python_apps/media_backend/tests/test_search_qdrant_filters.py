#!/usr/bin/env python
"""
Test script for the search_qdrant function focusing on brand and industry filters.

This script specifically tests the brand and industry filtering functionality
of the search_qdrant function to help debug issues with these filters.

Usage:
    python test_search_qdrant_filters.py [--brand BRAND] [--industry INDUSTRY]

Options:
    --brand          Brand to filter by
    --industry       Industry to filter by
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

# Common brands and industries for testing
COMMON_BRANDS = [
    "Nike", "Adidas", "Apple", "Google", "Amazon", "Microsoft",
    "Coca-Cola", "Pepsi", "McDonald's", "Burger King", "FanDuel"
]

COMMON_INDUSTRIES = [
    "Technology", "Finance", "Retail", "Automotive", "Food & Beverage",
    "Healthcare", "Entertainment", "Sports", "Fashion", "Travel"
]

async def test_brand_filter(brand: str, limit: int = 5) -> None:
    """
    Test filtering by brand.

    Args:
        brand: The brand to filter by
        limit: Number of results to return
    """
    print(f"\n{'='*80}")
    print(f"Testing brand filter: {brand}")
    print(f"{'='*80}")

    # Create a query that explicitly asks for the brand
    query = f"Show me {brand} campaigns"

    try:
        # Call the search_qdrant function with filter_without_semantic search type
        result = await search_qdrant(
            query_text=query,
            conversation_payload=[],
            parameters={},
            use_vector_search=False,  # Force filter-only search
            number_of_results=limit
        )

        # Print the results
        print(f"\nSearch Results: {len(result.results)} items found")

        # Print detailed results
        for i, creative in enumerate(result.results):
            print(f"\nResult {i+1}:")
            print(f"  ID: {creative.id}")
            print(f"  Brand: {creative.brand}")
            print(f"  Industry: {creative.industry}")
            print(f"  Campaign: {creative.campaign_folder}")

        # Check if all results match the brand
        matching_results = [c for c in result.results if c.brand and c.brand.lower() == brand.lower()]
        match_percentage = (len(matching_results) / len(result.results) * 100) if result.results else 0

        print(f"\nFilter accuracy: {len(matching_results)}/{len(result.results)} results match the brand ({match_percentage:.1f}%)")

    except Exception as e:
        logger.error(f"Error testing brand filter: {e}")
        print(f"\nError: {e}")

async def test_industry_filter(industry: str, limit: int = 5) -> None:
    """
    Test filtering by industry.

    Args:
        industry: The industry to filter by
        limit: Number of results to return
    """
    print(f"\n{'='*80}")
    print(f"Testing industry filter: {industry}")
    print(f"{'='*80}")

    # Create a query that explicitly asks for the industry
    query = f"Show me campaigns in the {industry} sector"

    try:
        # Call the search_qdrant function with filter_without_semantic search type
        result = await search_qdrant(
            query_text=query,
            conversation_payload=[],
            parameters={},
            use_vector_search=False,  # Force filter-only search
            number_of_results=limit
        )

        # Print the results
        print(f"\nSearch Results: {len(result.results)} items found")

        # Print detailed results
        for i, creative in enumerate(result.results):
            print(f"\nResult {i+1}:")
            print(f"  ID: {creative.id}")
            print(f"  Brand: {creative.brand}")
            print(f"  Industry: {creative.industry_sectors}")  # Updated field name
            print(f"  Campaign: {creative.campaign_folder}")

        # Check if all results match the industry
        matching_results = [c for c in result.results if c.industry_sectors and c.industry_sectors.lower() == industry.lower()]
        match_percentage = (len(matching_results) / len(result.results) * 100) if result.results else 0

        print(f"\nFilter accuracy: {len(matching_results)}/{len(result.results)} results match the industry ({match_percentage:.1f}%)")

    except Exception as e:
        logger.error(f"Error testing industry filter: {e}")
        print(f"\nError: {e}")

async def test_combined_filter(brand: str, industry: str, limit: int = 5) -> None:
    """
    Test filtering by both brand and industry.

    Args:
        brand: The brand to filter by
        industry: The industry to filter by
        limit: Number of results to return
    """
    print(f"\n{'='*80}")
    print(f"Testing combined filter: Brand={brand}, Industry={industry}")
    print(f"{'='*80}")

    # Create a query that explicitly asks for both brand and industry
    query = f"Show me {brand} campaigns in the {industry} sector"

    try:
        # Call the search_qdrant function with filter_without_semantic search type
        result = await search_qdrant(
            query_text=query,
            conversation_payload=[],
            parameters={},
            use_vector_search=False,  # Force filter-only search
            number_of_results=limit
        )

        # Print the results
        print(f"\nSearch Results: {len(result.results)} items found")

        # Print detailed results
        for i, creative in enumerate(result.results):
            print(f"\nResult {i+1}:")
            print(f"  ID: {creative.id}")
            print(f"  Brand: {creative.brand}")
            print(f"  Industry: {creative.industry_sectors}")  # Updated field name
            print(f"  Campaign: {creative.campaign_folder}")

        # Check if all results match both brand and industry
        matching_results = [
            c for c in result.results
            if c.brand and c.brand.lower() == brand.lower() and
               c.industry_sectors and c.industry_sectors.lower() == industry.lower()  # Updated field name
        ]
        match_percentage = (len(matching_results) / len(result.results) * 100) if result.results else 0

        print(f"\nFilter accuracy: {len(matching_results)}/{len(result.results)} results match both criteria ({match_percentage:.1f}%)")

    except Exception as e:
        logger.error(f"Error testing combined filter: {e}")
        print(f"\nError: {e}")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the search_qdrant function's filtering capabilities.")
    parser.add_argument("--brand", type=str, help="Brand to filter by")
    parser.add_argument("--industry", type=str, help="Industry to filter by")
    parser.add_argument("--limit", type=int, default=5, help="Number of results to return")
    parser.add_argument("--list-options", action="store_true", help="List common brands and industries")
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Check for OpenAI API key
    if not os.environ.get("OPENAI_API_KEY"):
        logger.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
        sys.exit(1)

    if args.list_options:
        print("\nCommon Brands:")
        for brand in COMMON_BRANDS:
            print(f"  {brand}")

        print("\nCommon Industries:")
        for industry in COMMON_INDUSTRIES:
            print(f"  {industry}")
        return

    if args.brand and args.industry:
        # Test combined filter
        await test_combined_filter(args.brand, args.industry, args.limit)
    elif args.brand:
        # Test brand filter
        await test_brand_filter(args.brand, args.limit)
    elif args.industry:
        # Test industry filter
        await test_industry_filter(args.industry, args.limit)
    else:
        # Test a few common brands and industries
        for brand in COMMON_BRANDS[:3]:
            await test_brand_filter(brand, args.limit)
            await asyncio.sleep(1)

        for industry in COMMON_INDUSTRIES[:3]:
            await test_industry_filter(industry, args.limit)
            await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())
