#!/usr/bin/env python3
"""
Script to upload modified intention examples to media_intention_prompt_examples_v3 collection.
This script reads the manually edited JSON file and creates embeddings for the user_query field,
then uploads all points to the new v3 collection.

Usage:
    python upload_intention_examples_v3.py [--input-file filename.json]
"""

import os
import sys
import json
import logging
import argparse
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http import models
from openai import OpenAI

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

def connect_to_qdrant() -> QdrantClient:
    """Connect to the Qdrant database using environment variables."""
    try:
        # Try environment variables first
        qdrant_host = os.getenv("QDRANT_HOST")
        qdrant_port = int(os.getenv("QDRANT_PORT", 6333))
        
        # If not found in env, use the provided URL
        if not qdrant_host:
            qdrant_host = "http://3.101.65.253"
            qdrant_port = 5333
            logger.info(f"Using provided Qdrant URL: {qdrant_host}:{qdrant_port}")
        else:
            logger.info(f"Using environment Qdrant URL: {qdrant_host}:{qdrant_port}")

        client = QdrantClient(
            url=qdrant_host,
            port=qdrant_port
        )
        
        # Test connection
        collections = client.get_collections()
        logger.info(f"Successfully connected to Qdrant. Found {len(collections.collections)} collections.")
        
        return client
    except Exception as e:
        logger.error(f"Error connecting to Qdrant: {e}")
        sys.exit(1)

def get_openai_client() -> OpenAI:
    """Initialize OpenAI client."""
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable not set")
        
        client = OpenAI(api_key=api_key)
        logger.info("OpenAI client initialized successfully")
        return client
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
        sys.exit(1)

def get_embedding(text: str, openai_client: OpenAI) -> Optional[List[float]]:
    """Get embedding for the given text using OpenAI."""
    try:
        response = openai_client.embeddings.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        logger.error(f"Error getting embedding for text: {e}")
        return None

def load_json_data(filepath: str) -> List[Dict[str, Any]]:
    """Load the JSON data from file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        logger.info(f"Loaded {len(data)} points from {filepath}")
        return data
    except Exception as e:
        logger.error(f"Error loading JSON file: {e}")
        sys.exit(1)

def create_collection(client: QdrantClient, collection_name: str, vector_size: int = 1536) -> None:
    """Create or recreate the collection."""
    try:
        # Check if collection exists
        try:
            existing_collection = client.get_collection(collection_name)
            logger.warning(f"Collection '{collection_name}' already exists with {existing_collection.points_count} points")
            
            response = input(f"Do you want to recreate the collection '{collection_name}'? This will delete all existing data. (y/N): ")
            if response.lower() != 'y':
                logger.info("Aborted by user")
                sys.exit(0)
        except:
            logger.info(f"Collection '{collection_name}' does not exist, creating new one")
        
        # Create/recreate collection
        client.recreate_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(
                size=vector_size,
                distance=models.Distance.COSINE
            )
        )
        logger.info(f"Collection '{collection_name}' created successfully")
        
    except Exception as e:
        logger.error(f"Error creating collection: {e}")
        sys.exit(1)

def upload_points(client: QdrantClient, collection_name: str, points_data: List[Dict[str, Any]], openai_client: OpenAI) -> None:
    """Upload points to the collection with embeddings."""
    try:
        logger.info(f"Starting upload of {len(points_data)} points...")
        
        points_to_upload = []
        failed_embeddings = 0
        
        for i, point_data in enumerate(points_data):
            try:
                # Extract user_query for embedding
                payload = point_data['payload']
                user_query = payload.get('user_query', '')
                
                if not user_query:
                    logger.warning(f"Point {point_data['id']} has no user_query, skipping")
                    continue
                
                # Get embedding
                embedding = get_embedding(user_query, openai_client)
                if embedding is None:
                    logger.warning(f"Failed to get embedding for point {point_data['id']}")
                    failed_embeddings += 1
                    continue
                
                # Create point
                point = models.PointStruct(
                    id=point_data['id'],
                    vector=embedding,
                    payload=payload
                )
                points_to_upload.append(point)
                
                if (i + 1) % 10 == 0:
                    logger.info(f"Processed {i + 1}/{len(points_data)} points")
                    
            except Exception as e:
                logger.error(f"Error processing point {point_data.get('id', 'unknown')}: {e}")
                failed_embeddings += 1
                continue
        
        if not points_to_upload:
            logger.error("No valid points to upload")
            return
        
        # Upload in batches
        batch_size = 50
        total_uploaded = 0
        
        for i in range(0, len(points_to_upload), batch_size):
            batch = points_to_upload[i:i + batch_size]
            
            try:
                client.upsert(
                    collection_name=collection_name,
                    points=batch
                )
                total_uploaded += len(batch)
                logger.info(f"Uploaded batch {i//batch_size + 1}: {len(batch)} points (Total: {total_uploaded})")
                
            except Exception as e:
                logger.error(f"Error uploading batch {i//batch_size + 1}: {e}")
                continue
        
        logger.info(f"Upload completed!")
        logger.info(f"Successfully uploaded: {total_uploaded} points")
        logger.info(f"Failed embeddings: {failed_embeddings}")
        
    except Exception as e:
        logger.error(f"Error during upload: {e}")

def main():
    """Main function to upload intention examples to v3 collection."""
    parser = argparse.ArgumentParser(description='Upload intention examples to v3 collection')
    parser.add_argument('--input-file', type=str, default='media_intention_examples_v2_export.json',
                       help='Input JSON file with modified examples')
    args = parser.parse_args()
    
    # Load environment variables
    load_dotenv()
    
    collection_name = "media_intention_prompt_examples_v3"
    
    # Get the full path to the input file
    script_dir = os.path.dirname(os.path.abspath(__file__))
    input_filepath = os.path.join(script_dir, args.input_file)
    
    if not os.path.exists(input_filepath):
        logger.error(f"Input file not found: {input_filepath}")
        sys.exit(1)
    
    logger.info("Starting upload of intention prompt examples to v3...")
    logger.info(f"Input file: {input_filepath}")
    logger.info(f"Target collection: {collection_name}")
    
    # Connect to services
    qdrant_client = connect_to_qdrant()
    openai_client = get_openai_client()
    
    # Load data
    points_data = load_json_data(input_filepath)
    
    # Create collection
    create_collection(qdrant_client, collection_name)
    
    # Upload points
    upload_points(qdrant_client, collection_name, points_data, openai_client)
    
    logger.info("Process completed successfully!")

if __name__ == "__main__":
    main()
