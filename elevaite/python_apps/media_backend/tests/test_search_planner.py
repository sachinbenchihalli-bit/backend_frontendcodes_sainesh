#!/usr/bin/env python
"""
Test script for the search planner agent.

This script tests the search planner agent with various types of queries and validates
the generated search plans. It helps ensure that the agent is creating appropriate
search plans for different types of queries.

Usage:
    python test_search_planner.py [--verbose] [--log-level=INFO]

Options:
    --verbose       Show detailed output for each test case
    --log-level     Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
"""

import os
import sys
import json
import logging
import argparse
import asyncio
from typing import List, Dict, Any, Optional
from tabulate import tabulate
import colorama
from colorama import Fore, Style

# Add the parent directory to the path so we can import from the parent module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Import the search planner agent and related models
from python_apps.media_backend.model import ConversationPayload, SearchPlannerOutput, SearchStep
from python_apps.media_backend.search_planner import search_planner_agent
from dotenv import load_dotenv

# Initialize colorama
colorama.init()

# Configure logging
logger = logging.getLogger(__name__)

# Test cases for the search planner agent
TEST_CASES = [
    {
        "id": "brand_query_simple",
        "description": "Simple brand query",
        "query": "Show me Nike campaigns",
        "conversation_history": [],
        "expected_search_type": "filter_without_semantic",
        "expected_steps": ["filter","sort"],
        "expected_parameters": {"brand": "nike"},
    },
    {
        "id": "brand_query_with_history",
        "description": "Brand query with conversation history",
        "query": "What about Adidas?",
        "conversation_history": [
            {"actor": "user", "content": "Show me Nike campaigns"},
            {"actor": "assistant", "content": "Here are some Nike campaigns..."}
        ],
        "expected_search_type": "filter_without_semantic",
        "expected_steps": ["filter","sort"],
        "expected_parameters": {"brand": "adidas"},
    },
    {
        "id": "industry_query",
        "description": "Industry-specific query",
        "query": "Show me campaigns in the Finance sector",
        "conversation_history": [],
        "expected_search_type": "filter_without_semantic",
        "expected_steps": ["filter","sort"],
        "expected_parameters": {"industry_sectors": "Finance"},
    },
    {
        "id": "performance_query",
        "description": "Performance-based query",
        "query": "Show me campaigns with highest conversion rates",
        "conversation_history": [],
        "expected_search_type": "filter_without_semantic",
        "expected_steps": ["sort"],
        "expected_parameters": {"sort_field": "conversion", "sort_order": "desc"},
    },
    {
        "id": "season_query",
        "description": "Season-specific query",
        "query": "Show me holiday campaigns",
        "conversation_history": [],
        "expected_search_type": "filter_without_semantic",
        "expected_steps": ["filter","sort"],
        "expected_parameters": {"season": "holiday"},
    },
    {
        "id": "complex_query",
        "description": "Complex query with multiple criteria",
        "query": "Show me Nike holiday campaigns with high conversion rates",
        "conversation_history": [],
        "expected_search_type": "filter_without_semantic",
        "expected_steps": ["filter", "sort"],
        "expected_parameters": {"brand": "nike", "season": "holiday", "sort_field": "conversion"},
    },
    {
        "id": "semantic_query",
        "description": "Query requiring semantic search",
        "query": "Find campaigns similar to successful sports apparel ads",
        "conversation_history": [],
        "expected_search_type": "semantic_only",
        "expected_steps": ["semantic_search"],
        "expected_parameters": {},
    },
    {
        "id": "empty_query",
        "description": "Empty query (edge case)",
        "query": "",
        "conversation_history": [],
        "expected_search_type": "semantic_only",  # Default behavior
        "expected_steps": ["semantic_search"],
        "expected_parameters": {},
        "expected_to_use_default": True,  # Expect to use default search plan
    },
    # {
    #     "id": "retry_query",
    #     "description": "Query with previous search failure",
    #     "query": "Show me Burberry winter campaigns",
    #     "conversation_history": [],
    #     "previous_search_failed": True,
    #     "expected_search_type": "semantic_only",  # Should fall back to semantic search
    #     "expected_steps": ["semantic_search"],
    #     "expected_parameters": {},
    #     "expected_to_use_default": False,  # We expect a real response, not the default
    # },
]

def setup_logging(log_level: str = "INFO") -> None:
    """Set up logging configuration."""
    numeric_level = getattr(logging, log_level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {log_level}")

    logging.basicConfig(
        level=numeric_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()]
    )

def validate_search_plan(
    search_plan: SearchPlannerOutput,
    expected_search_type: str,
    expected_steps: List[str],
    expected_parameters: Dict[str, Any],
    expected_to_use_default: bool = False
) -> Dict[str, bool]:
    """
    Validate the search plan against expected values.

    Args:
        search_plan: The generated search plan
        expected_search_type: The expected search type
        expected_steps: List of expected step types
        expected_parameters: Dictionary of expected parameters
        expected_to_use_default: Whether we expect the default search plan to be used

    Returns:
        Dictionary of validation results
    """
    results = {
        "search_type_valid": search_plan.search_type == expected_search_type,
        "steps_valid": True,
        "parameters_valid": True
    }

    # If we expect the default search plan, we just need to check the search type
    if expected_to_use_default:
        # Default search plan should have semantic_only search type and at least one semantic_search step
        has_semantic_search = any(step.step_type == "semantic_search" for step in search_plan.steps)
        results["steps_valid"] = has_semantic_search
        results["parameters_valid"] = True
        return results

    # Validate steps
    actual_steps = [step.step_type for step in search_plan.steps]
    if len(actual_steps) != len(expected_steps):
        results["steps_valid"] = False
    else:
        for expected_step in expected_steps:
            if expected_step not in actual_steps:
                results["steps_valid"] = False
                break

    # Validate parameters
    for key, value in expected_parameters.items():
        param_found = False
        for step in search_plan.steps:
            if key in step.parameters:
                # Handle string parameters
                if isinstance(step.parameters[key], str) and isinstance(value, str):
                    if step.parameters[key].lower() == value.lower():
                        param_found = True
                        break
                # Handle other parameter types
                elif step.parameters[key] == value:
                    param_found = True
                    break
        if not param_found:
            results["parameters_valid"] = False
            break

    return results

async def run_test_case(test_case: Dict[str, Any], verbose: bool = False) -> Dict[str, Any]:
    """
    Run a single test case.

    Args:
        test_case: The test case to run
        verbose: Whether to show detailed output

    Returns:
        Dictionary with test results
    """
    query = test_case["query"]
    conversation_history = [ConversationPayload(**msg) for msg in test_case["conversation_history"]]
    previous_search_failed = test_case.get("previous_search_failed", False)
    expected_to_use_default = test_case.get("expected_to_use_default", False)

    logger.info(f"Running test case: {test_case['id']} - {test_case['description']}")
    logger.info(f"Query: {query}")

    try:
        # Call the search planner agent
        search_plan = await search_planner_agent(
            user_query=query,
            conversation_history=conversation_history,
            previous_search_failed=previous_search_failed
        )

        # Validate the search plan
        validation_results = validate_search_plan(
            search_plan=search_plan,
            expected_search_type=test_case["expected_search_type"],
            expected_steps=test_case["expected_steps"],
            expected_parameters=test_case["expected_parameters"],
            expected_to_use_default=expected_to_use_default
        )

        # Determine overall result
        overall_result = all(validation_results.values())

        # Create result dictionary
        result = {
            "id": test_case["id"],
            "description": test_case["description"],
            "query": query,
            "search_plan": search_plan,
            "validation_results": validation_results,
            "overall_result": overall_result
        }

        if verbose:
            logger.info(f"Search plan: {search_plan.model_dump_json(indent=2)}")
            logger.info(f"Validation results: {validation_results}")
            logger.info(f"Overall result: {overall_result}")

        return result

    except Exception as e:
        logger.error(f"Error running test case {test_case['id']}: {e}")
        return {
            "id": test_case["id"],
            "description": test_case["description"],
            "query": query,
            "error": str(e),
            "overall_result": False
        }

async def run_tests(verbose: bool = False) -> List[Dict[str, Any]]:
    """
    Run all test cases.

    Args:
        verbose: Whether to show detailed output

    Returns:
        List of test results
    """
    results = []

    for test_case in TEST_CASES:
        result = await run_test_case(test_case, verbose)
        results.append(result)

    return results

def display_results(results: List[Dict[str, Any]]) -> None:
    """
    Display test results in a table.

    Args:
        results: List of test results
    """
    table_data = []

    for result in results:
        status = Fore.GREEN + "PASS" + Style.RESET_ALL if result.get("overall_result") else Fore.RED + "FAIL" + Style.RESET_ALL

        if "error" in result:
            details = f"Error: {result['error']}"
        else:
            validation = result["validation_results"]
            details = []
            for key, value in validation.items():
                color = Fore.GREEN if value else Fore.RED
                details.append(f"{key}: {color}{value}{Style.RESET_ALL}")
            details = ", ".join(details)

        table_data.append([
            result["id"],
            result["description"],
            result["query"],
            status,
            details
        ])

    headers = ["ID", "Description", "Query", "Status", "Details"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))

    # Print summary
    passed = sum(1 for r in results if r.get("overall_result"))
    total = len(results)
    print(f"\nSummary: {passed}/{total} tests passed ({passed/total*100:.1f}%)")

async def main():
    """Main function."""
    parser = argparse.ArgumentParser(description="Test the search planner agent.")
    parser.add_argument("--verbose", action="store_true", help="Show detailed output")
    parser.add_argument("--log-level", default="INFO", help="Set the logging level")
    parser.add_argument("--api-key", type=str, help="OpenAI API key (overrides environment variable)")
    args = parser.parse_args()

    # Set up logging
    setup_logging(args.log_level)

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

    # Run tests
    results = await run_tests(args.verbose)

    # Display results
    display_results(results)

if __name__ == "__main__":
    asyncio.run(main())
