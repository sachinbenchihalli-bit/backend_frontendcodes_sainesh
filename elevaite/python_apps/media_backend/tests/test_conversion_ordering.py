#!/usr/bin/env python
"""
Test script to verify Qdrant scroll ordering by conversion.
This script queries the Qdrant database and displays results ordered by conversion
to help diagnose why high-conversion campaigns like Fan Duel might not be appearing.
"""

import os
import sys
import logging
from dotenv import load_dotenv
from tabulate import tabulate
import pandas as pd

# Import the necessary components
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, MatchAny
# Add the parent directory to the path so we can import from the parent module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from model import AdCreative

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def main():
    # Load environment variables
    load_dotenv()

    # Initialize Qdrant client
    try:
        qdrant_host = os.getenv("QDRANT_HOST", "localhost")
        qdrant_port = int(os.getenv("QDRANT_PORT", 5333))
        collection_name = os.getenv("COLLECTION_NAME", "media_data_standardized")

        logger.info(f"Connecting to Qdrant at {qdrant_host}:{qdrant_port}, collection: {collection_name}")

        qclient = QdrantClient(
            qdrant_host,
            port=qdrant_port
        )
    except Exception as e:
        logger.error(f"Error initializing Qdrant client: {e}")
        return

    # Test 1: Simple scroll with ordering by conversion
    logger.info("Test 1: Simple scroll with ordering by conversion (desc)")
    try:
        scroll_result = qclient.scroll(
            collection_name=collection_name,
            limit=100,  # Get more results to sort manually
            with_payload=True,
            with_vectors=False,
            order_by={"key": "conversion", "direction": "desc"}  # Order by conversion in descending order
        )

        # Extract the points from the result
        points = scroll_result[0]
        logger.info(f"Found {len(points)} points")

        # Convert to AdCreative objects and display
        results = []
        for point in points:
            try:
                ad_creative = AdCreative.model_validate(point.payload)
                results.append({
                    "id": ad_creative.id,
                    "brand": ad_creative.brand,
                    "campaign": ad_creative.campaign_folder,
                    "conversion": ad_creative.conversion,
                    "industry": ad_creative.industry_sectors
                })
            except Exception as e:
                logger.error(f"Error parsing point: {e}")

        # Display results in a table
        df = pd.DataFrame(results)
        print("\nTop campaigns by conversion rate:")
        print(tabulate(df, headers="keys", tablefmt="grid", showindex=False))

        # Check specifically for Fan Duel
        fan_duel_results = [r for r in results if "fanduel" in str(r["brand"]).lower()]
        if fan_duel_results:
            print("\nFan Duel campaigns found:")
            fan_duel_df = pd.DataFrame(fan_duel_results)
            print(tabulate(fan_duel_df, headers="keys", tablefmt="grid", showindex=False))
        else:
            print("\nNo Fan Duel campaigns found in the top results.")

            # Try a specific search for Fan Duel
            logger.info("Searching specifically for Fan Duel")
            fan_duel_filter = Filter(
                must=[
                    FieldCondition(
                        key="brand",
                        match=MatchValue(value="fanduel")
                    )
                ]
            )

            fan_duel_scroll = qclient.scroll(
                collection_name=collection_name,
                limit=50,  # Get more results to sort manually
                scroll_filter=fan_duel_filter,
                with_payload=True,
                with_vectors=False,
                order_by={"key": "conversion", "direction": "desc"}  # Order by conversion in descending order
            )

            fan_duel_points = fan_duel_scroll[0]
            logger.info(f"Found {len(fan_duel_points)} Fan Duel points with exact match")

            # If no results, try with case-insensitive search
            if len(fan_duel_points) == 0:
                logger.info("Trying case variations of Fan Duel")
                variations = ["FanDuel", "Fan Duel", "FANDUEL", "Fanduel", "fanduel"]
                variation_filter = Filter(
                    must=[
                        FieldCondition(
                            key="brand",
                            match=MatchAny(any=variations)
                        )
                    ]
                )

                variation_scroll = qclient.scroll(
                    collection_name=collection_name,
                    limit=50,  # Get more results to sort manually
                    scroll_filter=variation_filter,
                    with_payload=True,
                    with_vectors=False,
                    order_by={"key": "conversion", "direction": "desc"}  # Order by conversion in descending order
                )

                variation_points = variation_scroll[0]
                logger.info(f"Found {len(variation_points)} Fan Duel points with variations")

                # Display results
                if len(variation_points) > 0:
                    variation_results = []
                    for point in variation_points:
                        try:
                            ad_creative = AdCreative.model_validate(point.payload)
                            variation_results.append({
                                "id": ad_creative.id,
                                "brand": ad_creative.brand,
                                "campaign": ad_creative.campaign_folder,
                                "conversion": ad_creative.conversion,
                                "industry": ad_creative.industry_sectors
                            })
                        except Exception as e:
                            logger.error(f"Error parsing point: {e}")

                    print("\nFan Duel campaigns found with name variations:")
                    variation_df = pd.DataFrame(variation_results)
                    print(tabulate(variation_df, headers="keys", tablefmt="grid", showindex=False))

    except Exception as e:
        logger.error(f"Error performing scroll query: {e}")

if __name__ == "__main__":
    main()
