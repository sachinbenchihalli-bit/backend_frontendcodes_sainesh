"""
Tools for the search planner agent to get information about available data.
"""
from typing import List
import os
import logging
from model import AvailableBrands, AvailableIndustries, AvailableSeasons

# Configure logging
logger = logging.getLogger(__name__)

# Mock data for now - will be replaced with actual database queries later
MOCK_BRANDS = ['heaven hill', 'caffe nero', 'match.com', "mcdonald's all", 'diageo', 'accenture', 'espn', 'twingate', 'nba', 'fanduel', 'vh1', 'simon', 'usda', 'the north face',
                'toyota', 'warnerbros', 'xfinity', 'hallmark', 'ovo energy', 'labatt', 'jackpocket', 'campari', 'pernod ricard', 'hubspot', 'wow vegas', 'future foods', 'coca-cola',
                'balloon museum', 'beats', 'jagermeister', 'sony pictures', 'walmart', 'burberry', 'the iconic', 'disney', 'universal pictures', 'unilever', 'whataburger', 'get your guide',
                'hard rock hotel and casino', 'chick-fil-a', 'heineken', 'molson coors', 'kirin holdings company', 'supermicro', 'visit barbados', 'bloomingdales', 'genentech', "applebee's",
                'nissan', 'hulu', 'live nation', 'bojangles', 'dior', 'merck', 'netflix']

MOCK_INDUSTRIES = [
    "Entertainment & Media",
    "Food & Beverage", 
    "Technology & Telecommunications",
    "Fashion & Retail",
    "Automotive",
    "Travel & Tourism",
    "Healthcare",
    "Business Services",
    "Sports & Recreation",
    "Beauty & Personal Care"
]

MOCK_SEASONS =[ 
    "spring", "summer", "autumn", "winter", "fall", "winter", "holiday", "spring-summer", "fall-winter", "winter-spring", "summer-fall", "spring-fall", "year-round", "unknown", "other"
]               

async def get_available_brands() -> AvailableBrands:
    """
    Get a list of available brands in the database.
    
    Returns:
        AvailableBrands: A model containing the list of available brands.
    """
    logger.info("Getting available brands")
    return AvailableBrands(brands=MOCK_BRANDS)

async def get_available_industries() -> AvailableIndustries:
    """
    Get a list of available industries in the database.
    
    Returns:
        AvailableIndustries: A model containing the list of available industries.
    """
    logger.info("Getting available industries")
    return AvailableIndustries(industries=MOCK_INDUSTRIES)

async def get_available_seasons() -> AvailableSeasons:
    """
    Get a list of available seasons in the database.
    
    Returns:
        AvailableSeasons: A model containing the list of available seasons.
    """
    logger.info("Getting available seasons")
    return AvailableSeasons(seasons=MOCK_SEASONS)
