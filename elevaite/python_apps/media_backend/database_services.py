import logging
import uuid
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from typing import Dict, Any, Optional, List
from sqlalchemy import select

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CampaignService:
    """
    Service class for campaign-related database operations.
    """
    
    def __init__(self, db: Session):
        """
        Initialize the service with a database session.
        
        Args:
            db (Session): SQLAlchemy database session
        """
        self.db = db
    
    def generate_campaign_id(self, campaign_name: str) -> str:
        """
        Generates a campaign ID based on the campaign name.
        
        Args:
            campaign_name (str): Name of the campaign
            
        Returns:
            str: Generated UUID for the campaign
            
        Raises:
            ValueError: If campaign name is invalid
        """
        try:
            return str(uuid.uuid5(uuid.NAMESPACE_DNS, campaign_name))
        except TypeError as e:
            logger.error(f"TypeError in generate_campaign_id: {e}")
            raise ValueError(f"Invalid campaign name format: {campaign_name}")
        except Exception as e:
            logger.error(f"Unexpected error in generate_campaign_id: {e}")
            raise
    
    def get_campaign_details_by_campaign_name(self, campaign_name: str) -> Dict[str, Any]:
        """
        Retrieves campaign details by campaign name.
        
        Args:
            campaign_name (str): Name of the campaign
            
        Returns:
            Dict[str, Any]: Campaign details or error message
        """
        from database_models import CampaignData  # Import here to avoid circular imports
        
        try:
            campaign_id = self.generate_campaign_id(campaign_name)
            logger.info(f"Looking up campaign with ID: {campaign_id}")
            
            stmt = select(CampaignData).where(CampaignData.campaign_id == campaign_id)
            campaign = self.db.execute(stmt).scalar_one_or_none()
            
            if campaign:
                return {
                    "campaign_id": campaign.campaign_id, 
                    "campaign_name": campaign.campaign_name,
                    "insights": campaign.insights,
                    "booked_impressions": float(campaign.booked_impressions) if campaign.booked_impressions else 0,
                    "clickable_impressions": float(campaign.clickable_impressions) if campaign.clickable_impressions else 0,
                    "clicks": campaign.clicks,
                    "conversion": float(campaign.conversion) if campaign.conversion else 0,
                    "ecpm": float(campaign.ecpm) if campaign.ecpm else 0,
                    "budget": float(campaign.budget) if campaign.budget else 0,
                    "duration": campaign.duration,
                    "brand": campaign.brand,
                    "ad_surface": campaign.ad_surface
                }
            else:
                logger.warning(f"Campaign not found: {campaign_name}")
                return {"error": "Campaign not found"}
                
        except ValueError as e:
            logger.error(f"ValueError in get_campaign_details_by_campaign_name: {e}")
            return {"error": str(e)}
        except SQLAlchemyError as e:
            logger.error(f"Database error in get_campaign_details_by_campaign_name: {e}")
            return {"error": f"Database error: {str(e)}"}
        except Exception as e:
            logger.error(f"Error in get_campaign_details_by_campaign_name: {e}")
            return {"error": f"Failed to retrieve campaign details: {str(e)}"}
    
    def get_insights_by_campaign_name(self, campaign_name: str) -> Dict[str, Any]:
        """
        Retrieves campaign insights by campaign name.
        
        Args:
            campaign_name (str): Name of the campaign
            
        Returns:
            Dict[str, Any]: Campaign insights or error message
        """
        campaign_details = self.get_campaign_details_by_campaign_name(campaign_name)
        
        if "error" in campaign_details:
            return campaign_details
        
        # Extract just the insights and related performance metrics
        return {
            "campaign_id": campaign_details["campaign_id"],
            "campaign_name": campaign_details["campaign_name"],
            "insights": campaign_details["insights"],
            "performance_metrics": {
                "booked_impressions": campaign_details["booked_impressions"],
                "clickable_impressions": campaign_details["clickable_impressions"],
                "clicks": campaign_details["clicks"],
                "conversion": campaign_details["conversion"],
                "ecpm": campaign_details["ecpm"],
                "budget": campaign_details["budget"],
                "duration": campaign_details["duration"]
            }
        }
    
    def list_all_campaigns(self) -> List[Dict[str, Any]]:
        """
        Lists all campaigns in the database.
        
        Returns:
            List[Dict[str, Any]]: List of campaign data
        """
        from database_models import CampaignData  # Import here to avoid circular imports
        
        try:
            campaigns = self.db.query(CampaignData).all()
            return [
                {
                    "campaign_id": campaign.campaign_id,
                    "campaign_name": campaign.campaign_name,
                    "brand": campaign.brand,
                    "ad_surface": campaign.ad_surface
                }
                for campaign in campaigns
            ]
        except SQLAlchemyError as e:
            logger.error(f"Database error in list_all_campaigns: {e}")
            return [{"error": f"Database error: {str(e)}"}]
        except Exception as e:
            logger.error(f"Error in list_all_campaigns: {e}")
            return [{"error": f"Failed to list campaigns: {str(e)}"}]
