# Media Backend Tests

This directory contains test scripts for the Media Backend application.

## Test Scripts

### Search Qdrant Tests

- **test_search_qdrant.py**: Basic test script for the `search_qdrant` function with various queries.
  ```
  python -m python_apps.media_backend.tests.test_search_qdrant [--query "your query here"] [--verbose] [--vector-search] [--limit 10]
  ```

- **test_search_qdrant_interactive.py**: Interactive test script for the `search_qdrant` function.
  ```
  python -m python_apps.media_backend.tests.test_search_qdrant_interactive
  ```

- **test_search_qdrant_filters.py**: Test script specifically for testing brand and industry filters.
  ```
  python -m python_apps.media_backend.tests.test_search_qdrant_filters [--brand "Nike"] [--industry "Technology"] [--limit 5]
  python -m python_apps.media_backend.tests.test_search_qdrant_filters --list-options  # Shows common brands and industries
  ```

### Search Planner Tests

- **test_search_planner.py**: Test script for the `search_planner_agent` function with predefined test cases.
  ```
  python -m python_apps.media_backend.tests.test_search_planner [--verbose] [--log-level INFO]
  ```

- **test_search_planner_interactive.py**: Interactive test script for the `search_planner_agent` function.
  ```
  python -m python_apps.media_backend.tests.test_search_planner_interactive
  ```

- **test_search_planner_simple.py**: Simple test script for the `search_planner_agent` function.
  ```
  python -m python_apps.media_backend.tests.test_search_planner_simple [--query "your query here"] [--retry]
  ```

### Qdrant Database Tests

- **test_qdrant_search.py**: Test script for direct Qdrant database queries.
  ```
  python -m python_apps.media_backend.tests.test_qdrant_search [--query "highest conversion"] [--limit 10]
  ```

## Running Tests

Make sure you have the required environment variables set:

- `OPENAI_API_KEY`: Your OpenAI API key
- `QDRANT_HOST`: Qdrant host URL (default: http://3.101.65.253)
- `QDRANT_PORT`: Qdrant port (default: 6333)
- `COLLECTION_NAME`: Qdrant collection name (default: media_data)

You can set these in a `.env` file in the project root directory.

## Common Test Queries

Here are some example queries to test with:

- "Show me Nike campaigns"
- "Find campaigns with high conversion rates"
- "Show me campaigns in the Finance sector"
- "Find FanDuel ads"
- "Compare Nike and Adidas campaigns"
- "Show me holiday campaigns"
- "Find campaigns similar to successful sports apparel ads"
