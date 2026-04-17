#!/usr/bin/env python
"""
Test script for querying the Qdrant database and testing the search_qdrant function.
This script allows you to test different queries and visualize the results.

Usage:
    python test_qdrant_search.py --query "highest conversion"
    python test_qdrant_search.py --query "highest impressions"
    python test_qdrant_search.py --query "brand Nike"
    python test_qdrant_search.py --limit 10
"""

import os
import sys
import json
import argparse
from typing import Dict, Any, List, Optional
from dotenv import load_dotenv
import pandas as pd
from tabulate import tabulate
import matplotlib.pyplot as plt
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, Range, MatchValue, MatchAny

# Add the parent directory to the path so we can import from the parent module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Try to import the AdCreative model from the media_backend module
try:
    from python_apps.media_backend.model import AdCreative, SearchResult
except ImportError:
    # If the import fails, define a simple AdCreative class
    from pydantic import BaseModel, Field
    from typing import Optional as OptionalType

    class AdCreative(BaseModel):
        id: str
        file_name: str
        campaign_folder: str
        file_size: OptionalType[int] = None
        file_type: OptionalType[str] = None
        type: OptionalType[str] = None
        booked_measure_impressions: OptionalType[float] = None
        delivered_measure_impressions: OptionalType[float] = None
        duration_days: OptionalType[int] = Field(None, alias="duration(days)")
        duration_category: OptionalType[str] = None
        industry: OptionalType[str] = None
        brand: OptionalType[str] = None
        brand_type: OptionalType[str] = None
        season_holiday: OptionalType[str] = None
        product_service: OptionalType[str] = None
        ad_objective: OptionalType[str] = None
        targeting: OptionalType[str] = None
        tone_mood: OptionalType[str] = None
        clicks: OptionalType[int] = None
        conversion: OptionalType[float] = None
        creative_url: OptionalType[str] = None

        class Config:
            extra = "allow"
            populate_by_name = True
            str_strip_whitespace = True

    class SearchResult(BaseModel):
        results: List[AdCreative]
        total: int


def connect_to_qdrant():
    """Connect to the Qdrant database using environment variables."""
    try:
        qdrant_host = os.getenv("QDRANT_HOST", "http://3.101.65.253")
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))

        print(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}")
        client = QdrantClient(
            url=qdrant_host,
            port=qdrant_port
        )
        return client
    except Exception as e:
        print(f"Error connecting to Qdrant: {e}")
        sys.exit(1)


def search_by_numeric_field(client, field_name, min_value=None, max_value=None, limit=5, collection_name="media_data"):
    """Search for records based on a numeric field with optional min and max values."""
    filter_conditions = []

    if min_value is not None or max_value is not None:
        range_params = {}
        if min_value is not None:
            range_params["gte"] = float(min_value)
        if max_value is not None:
            range_params["lte"] = float(max_value)

        filter_conditions.append(
            FieldCondition(
                key=field_name,
                range=Range(**range_params)
            )
        )

    search_filter = Filter(must=filter_conditions) if filter_conditions else None

    try:
        search_result = client.scroll(
            collection_name=collection_name,
            limit=limit,
            filter=search_filter,
            with_payload=True,
            with_vectors=False
        )

        # Extract the points from the result
        points = search_result[0]

        # Convert to AdCreative objects
        ad_creatives = []
        for point in points:
            try:
                ad_creative = AdCreative.parse_obj(point.payload)
                ad_creatives.append(ad_creative)
            except Exception as e:
                print(f"Error parsing point: {e}")

        return SearchResult(results=ad_creatives, total=len(ad_creatives))
    except Exception as e:
        print(f"Error searching Qdrant: {e}")
        return SearchResult(results=[], total=0)


def search_by_text_field(client, field_name, value, limit=5, collection_name="media_data"):
    """Search for records based on a text field."""
    filter_conditions = []

    if value:
        filter_conditions.append(
            FieldCondition(
                key=field_name,
                match=MatchValue(value=value)
            )
        )

    search_filter = Filter(must=filter_conditions) if filter_conditions else None

    try:
        search_result = client.scroll(
            collection_name=collection_name,
            limit=limit,
            filter=search_filter,
            with_payload=True,
            with_vectors=False
        )

        # Extract the points from the result
        points = search_result[0]

        # Convert to AdCreative objects
        ad_creatives = []
        for point in points:
            try:
                ad_creative = AdCreative.parse_obj(point.payload)
                ad_creatives.append(ad_creative)
            except Exception as e:
                print(f"Error parsing point: {e}")

        return SearchResult(results=ad_creatives, total=len(ad_creatives))
    except Exception as e:
        print(f"Error searching Qdrant: {e}")
        return SearchResult(results=[], total=0)


def get_all_records(client, limit=100, collection_name="media_data"):
    """Get all records from the collection."""
    try:
        search_result = client.scroll(
            collection_name=collection_name,
            limit=limit,
            with_payload=True,
            with_vectors=False
        )

        # Extract the points from the result
        points = search_result[0]

        # Convert to AdCreative objects
        ad_creatives = []
        for point in points:
            try:
                ad_creative = AdCreative.parse_obj(point.payload)
                ad_creatives.append(ad_creative)
            except Exception as e:
                print(f"Error parsing point: {e}")

        return SearchResult(results=ad_creatives, total=len(ad_creatives))
    except Exception as e:
        print(f"Error getting all records: {e}")
        return SearchResult(results=[], total=0)


def display_results(search_result, sort_by=None, ascending=True, limit=None):
    """Display the search results in a tabular format."""
    if not search_result.results:
        print("No results found.")
        return

    # Convert to DataFrame for easier manipulation
    data = []
    for result in search_result.results:
        data.append(result.dict())

    df = pd.DataFrame(data)

    # Sort if requested
    if sort_by and sort_by in df.columns:
        df = df.sort_values(by=sort_by, ascending=ascending)

    # Limit the number of rows if requested
    if limit and limit > 0:
        df = df.head(limit)

    # Select only the most relevant columns for display
    display_columns = [
        'id', 'brand', 'campaign_folder', 'conversion',
        'booked_measure_impressions', 'delivered_measure_impressions',
        'clicks', 'duration_days', 'industry'
    ]

    # Filter to only include columns that exist in the DataFrame
    display_columns = [col for col in display_columns if col in df.columns]

    # Display the results
    print(tabulate(df[display_columns], headers='keys', tablefmt='pretty', showindex=False))

    return df


def plot_results(df, x_column, y_column, title=None, limit=10):
    """Plot the results as a bar chart."""
    if x_column not in df.columns or y_column not in df.columns:
        print(f"Columns {x_column} or {y_column} not found in results.")
        return

    # Sort and limit
    df = df.sort_values(by=y_column, ascending=False).head(limit)

    plt.figure(figsize=(12, 6))
    plt.bar(df[x_column], df[y_column])
    plt.xlabel(x_column)
    plt.ylabel(y_column)
    plt.title(title or f"{y_column} by {x_column}")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()


def main():
    """Main function to parse arguments and execute the appropriate search."""
    parser = argparse.ArgumentParser(description='Test Qdrant search functionality.')
    parser.add_argument('--query', type=str, help='Query to search for (e.g., "highest conversion")')
    parser.add_argument('--limit', type=int, default=10, help='Maximum number of results to return')
    parser.add_argument('--collection', type=str, default='media_data_standardized', help='Collection name to search in')
    args = parser.parse_args()

    # Load environment variables
    load_dotenv()

    # Connect to Qdrant
    client = connect_to_qdrant()

    # Process the query
    if args.query:
        query = args.query.lower()

        if 'highest conversion' in query:
            print(f"Searching for campaigns with highest conversion rates (limit: {args.limit})...")
            results = get_all_records(client, limit=100, collection_name=args.collection)
            df = display_results(results, sort_by='conversion', ascending=False, limit=args.limit)
            if df is not None and not df.empty:
                plot_results(df, 'brand', 'conversion', 'Campaigns with Highest Conversion Rates', args.limit)

        elif 'highest impressions' in query:
            print(f"Searching for campaigns with highest impressions (limit: {args.limit})...")
            results = get_all_records(client, limit=100, collection_name=args.collection)
            df = display_results(results, sort_by='delivered_measure_impressions', ascending=False, limit=args.limit)
            if df is not None and not df.empty:
                plot_results(df, 'brand', 'delivered_measure_impressions', 'Campaigns with Highest Impressions', args.limit)

        elif 'highest clicks' in query:
            print(f"Searching for campaigns with highest clicks (limit: {args.limit})...")
            results = get_all_records(client, limit=100, collection_name=args.collection)
            df = display_results(results, sort_by='clicks', ascending=False, limit=args.limit)
            if df is not None and not df.empty:
                plot_results(df, 'brand', 'clicks', 'Campaigns with Highest Clicks', args.limit)

        elif query.startswith('brand '):
            brand_name = query.replace('brand ', '').strip()
            print(f"Searching for campaigns with brand '{brand_name}' (limit: {args.limit})...")
            results = search_by_text_field(client, 'brand', brand_name, limit=args.limit, collection_name=args.collection)
            df = display_results(results)

        elif query.startswith('industry '):
            industry_name = query.replace('industry ', '').strip()
            print(f"Searching for campaigns in industry '{industry_name}' (limit: {args.limit})...")
            results = search_by_text_field(client, 'industry', industry_name, limit=args.limit, collection_name=args.collection)
            df = display_results(results)

        else:
            print(f"Unrecognized query: {query}")
            print("Available queries: 'highest conversion', 'highest impressions', 'highest clicks', 'brand <name>', 'industry <name>'")
    else:
        # If no query is provided, just get all records
        print(f"Getting all records (limit: {args.limit})...")
        results = get_all_records(client, limit=args.limit, collection_name=args.collection)
        display_results(results)


if __name__ == "__main__":
    main()
