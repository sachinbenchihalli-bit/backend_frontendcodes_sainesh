#!/usr/bin/env python
"""
Interactive test script for the search planner agent.

This script provides an interactive way to test the search planner agent
with custom queries and conversation history.

Usage:
    python test_search_planner_interactive.py
"""

import os
import sys
import json
import logging
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

def print_colored(text: str, color: str = "white") -> None:
    """Print colored text."""
    colors = {
        "red": "\033[91m",
        "green": "\033[92m",
        "yellow": "\033[93m",
        "blue": "\033[94m",
        "magenta": "\033[95m",
        "cyan": "\033[96m",
        "white": "\033[97m",
        "reset": "\033[0m"
    }
    print(f"{colors.get(color, colors['white'])}{text}{colors['reset']}")

def print_header(text: str) -> None:
    """Print a header."""
    print("\n" + "=" * 80)
    print_colored(text, "cyan")
    print("=" * 80)

def print_section(text: str) -> None:
    """Print a section header."""
    print("\n" + "-" * 40)
    print_colored(text, "yellow")
    print("-" * 40)

def print_json(data: Dict[str, Any]) -> None:
    """Print JSON data."""
    print(json.dumps(data, indent=2))

def print_conversation(conversation: List[Dict[str, str]]) -> None:
    """Print conversation history."""
    for msg in conversation:
        actor = msg["actor"]
        content = msg["content"]
        color = "green" if actor == "assistant" else "blue"
        print_colored(f"{actor.capitalize()}: {content}", color)

async def test_search_planner(
    query: str,
    conversation_history: List[Dict[str, str]],
    previous_search_failed: bool = False
) -> None:
    """
    Test the search planner agent with a specific query and conversation history.

    Args:
        query: The query to test
        conversation_history: The conversation history
        previous_search_failed: Whether to simulate a previous search failure
    """
    print_header(f"Testing Search Planner Agent")

    print_section("Query")
    print_colored(query, "magenta")

    print_section("Conversation History")
    if conversation_history:
        print_conversation(conversation_history)
    else:
        print_colored("No conversation history", "yellow")

    print_section("Previous Search Failed")
    print_colored(str(previous_search_failed), "yellow")

    # Convert conversation history to ConversationPayload objects
    conversation_payload = [ConversationPayload(**msg) for msg in conversation_history]

    try:
        # Call the search planner agent
        search_plan = await search_planner_agent(
            user_query=query,
            conversation_history=conversation_payload,
            previous_search_failed=previous_search_failed
        )

        print_section("Search Plan")
        print_colored(f"Search Type: {search_plan.search_type}", "green")
        print_colored(f"Limit: {search_plan.limit}", "green")

        print_section("Steps")
        for i, step in enumerate(search_plan.steps):
            print_colored(f"Step {i+1}: {step.step_type}", "cyan")
            print(f"  Description: {step.description}")
            print(f"  Parameters: {json.dumps(step.parameters, indent=2)}")

        print_section("Raw JSON")
        print_json(search_plan.model_dump())

    except Exception as e:
        logger.error(f"Error testing search planner: {e}")
        print_colored(f"Error: {e}", "red")

def get_user_input(prompt: str, default: str = "") -> str:
    """Get user input with a default value."""
    if default:
        user_input = input(f"{prompt} [{default}]: ")
        return user_input if user_input else default
    else:
        return input(f"{prompt}: ")

def select_conversation() -> List[Dict[str, str]]:
    """Select a conversation history."""
    print_section("Select Conversation History")
    print("Available conversation histories:")

    for i, (name, _) in enumerate(SAMPLE_CONVERSATIONS.items()):
        print(f"{i+1}. {name}")

    print(f"{len(SAMPLE_CONVERSATIONS)+1}. Custom")

    while True:
        try:
            choice = int(get_user_input("Enter your choice", "1"))
            if 1 <= choice <= len(SAMPLE_CONVERSATIONS):
                # Return a selected sample conversation
                name = list(SAMPLE_CONVERSATIONS.keys())[choice-1]
                return SAMPLE_CONVERSATIONS[name]
            elif choice == len(SAMPLE_CONVERSATIONS)+1:
                # Create a custom conversation
                return create_custom_conversation()
            else:
                print_colored("Invalid choice. Please try again.", "red")
        except ValueError:
            print_colored("Please enter a number.", "red")

def create_custom_conversation() -> List[Dict[str, str]]:
    """Create a custom conversation history."""
    print_section("Create Custom Conversation")
    print("Enter conversation messages (leave empty to finish):")

    conversation = []
    i = 1

    while True:
        actor = get_user_input(f"Message {i} - Actor (user/assistant)", "user").lower()
        if actor not in ["user", "assistant"]:
            print_colored("Actor must be 'user' or 'assistant'. Please try again.", "red")
            continue

        content = get_user_input(f"Message {i} - Content")
        if not content:
            break

        conversation.append({"actor": actor, "content": content})
        i += 1

        if i > 10:
            print_colored("Maximum conversation length reached.", "yellow")
            break

    return conversation

async def main():
    """Main function."""
    # Load environment variables
    load_dotenv()

    # Check for OpenAI API key
    api_key = get_user_input("Enter your OpenAI API key (leave empty to use environment variable)")
    if api_key:
        os.environ["OPENAI_API_KEY"] = api_key

    if not os.environ.get("OPENAI_API_KEY"):
        print_colored("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable or enter it when prompted.", "red")
        return

    # Import and reinitialize the OpenAI client
    from llm_utils import client
    if client is None:
        from openai import OpenAI
        import llm_utils
        llm_utils.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
        print_colored("Reinitialized OpenAI client", "green")

    while True:
        print_header("Search Planner Agent Interactive Test")

        # Get query
        query = get_user_input("Enter your query", "Show me Nike campaigns")
        if not query:
            print_colored("Exiting...", "yellow")
            break

        # Get conversation history
        conversation_history = select_conversation()

        # Get previous search failed flag
        previous_search_failed_input = get_user_input("Previous search failed? (y/n)", "n").lower()
        previous_search_failed = previous_search_failed_input in ["y", "yes", "true"]

        # Test the search planner
        await test_search_planner(query, conversation_history, previous_search_failed)

        # Ask to continue
        continue_input = get_user_input("Continue? (y/n)", "y").lower()
        if continue_input not in ["y", "yes"]:
            print_colored("Exiting...", "yellow")
            break

if __name__ == "__main__":
    asyncio.run(main())
