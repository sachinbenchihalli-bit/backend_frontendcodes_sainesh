from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date
import os
import logging
from simple_salesforce import Salesforce
from fastapi import HTTPException

# Configure logging
logger = logging.getLogger(__name__)

# Pydantic models matching your frontend structure
class MetricsModel(BaseModel):
    Impressions: Optional[int] = None
    Clicks: Optional[int] = None

class BidRateModel(BaseModel):
    CPM: Optional[float] = None
    CPC: Optional[float] = None

class BudgetModel(BaseModel):
    Amount: Optional[float] = None

class NewTargetingConfigurationModel(BaseModel):
    age_range: Optional[List[str]] = None
    gender: Optional[List[str]] = None
    income_level: Optional[List[str]] = None
    location: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    behavioral_data: Optional[List[str]] = None

class TargetingSuggestionsModel(BaseModel):
    Demographics: Optional[List[str]] = None
    Interests: Optional[List[str]] = None
    Keywords: Optional[List[str]] = None
    AudienceSegments: Optional[List[str]] = None
    DeviceTargeting: Optional[List[str]] = None
    age_range: Optional[List[str]] = None
    gender: Optional[List[str]] = None
    income_level: Optional[List[str]] = None
    interests: Optional[List[str]] = None
    location: Optional[List[str]] = None
    behavioral_data: Optional[List[str]] = None

class PlacementModel(BaseModel):
    Name: Optional[str] = None
    Destination: Optional[str] = None
    StartDate: Optional[str] = None
    EndDate: Optional[str] = None
    ConvertToCampaign: Optional[bool] = None
    Metrics: Optional[MetricsModel] = None
    BidRate: Optional[BidRateModel] = None
    Budget: Optional[BudgetModel] = None
    targeting_configuration_id: Optional[str] = None
    new_targeting_configuration: Optional[NewTargetingConfigurationModel] = None
    TargetingSuggestions: Optional[TargetingSuggestionsModel] = None

class ObjectiveDetailsModel(BaseModel):
    Description: Optional[str] = None

class OrderGenerationRequest(BaseModel):
    # Optional lookup fields (only include if you have real Salesforce IDs)
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    
    # Required frontend structure fields
    OrderNo: str
    Brand: str
    CampaignName: str
    CustomerApprover: str
    CustomerApproverEmail: EmailStr
    SalesOwner: str
    SalesOwnerEmail: EmailStr
    FulfillmentOwner: str
    FulfillmentOwnerEmail: EmailStr
    ObjectiveDetails: ObjectiveDetailsModel
    Placement: List[PlacementModel]
    PDF_View_Link_c: Optional[str] = None
    Media_Plan__c: Optional[str] = None
    Creative_Inspiration__c: Optional[str] = None
    
    class Config:
        schema_extra = {
            "example": {
                "OrderNo": "IO-340371-3439",
                "Brand": "Example Brand",
                "CampaignName": "Summer Campaign 2024",
                "CustomerApprover": "John Smith",
                "CustomerApproverEmail": "john.smith@company.com",
                "SalesOwner": "Sarah Johnson",
                "SalesOwnerEmail": "sarah.johnson@elevaite.com",
                "FulfillmentOwner": "Mike Davis",
                "FulfillmentOwnerEmail": "mike.davis@elevaite.com",
                "ObjectiveDetails": {
                    "Description": "Launch a new convenience store brand with a focus on summer sales and seasonal promotions."
                },
                "PDF_View_Link_c": "https://example.com/pdf/insertion-order-340371-3439.pdf",
                "Media_Plan__c": "https://example.com/pdf/media-plan-123-456.pdf",
                "Creative_Inspiration__c": "https://example.com/pdf/creative-inspiration-123-456.pdf",
                "Placement": [
                    {
                        "Name": "Social Media",
                        "Destination": "Instagram",
                        "StartDate": "06-01-2024",
                        "EndDate": "08-31-2024",
                        "ConvertToCampaign": True,
                        "Metrics": {
                            "Impressions": 500000,
                            "Clicks": 0
                        },
                        "BidRate": {
                            "CPM": 1.0,
                            "CPC": 0.0
                        },
                        "Budget": {
                            "Amount": 100000
                        },
                        "targeting_configuration_id": "config-123",
                        "new_targeting_configuration": {
                            "age_range": ["18-24"],
                            "gender": ["Male"],
                            "income_level": ["Low Income"],
                            "location": ["United States"],
                            "interests": ["Technology"],
                            "behavioral_data": ["Tech Enthusiasts"]
                        },
                        "TargetingSuggestions": {
                            "Demographics": ["Male", "18-24", "Low Income"],
                            "Interests": ["Technology"],
                            "Keywords": [],
                            "AudienceSegments": ["Tech Enthusiasts"],
                            "DeviceTargeting": ["United States"],
                            "age_range": ["18-24"],
                            "gender": ["Male"],
                            "income_level": ["Low Income"],
                            "interests": ["Technology"],
                            "location": ["United States"],
                            "behavioral_data": ["Tech Enthusiasts"]
                        }
                    }
                ]
            }
        }

# Keep original models for backwards compatibility
class TargetAudience(BaseModel):
    age_range: Optional[str] = None
    gender: Optional[str] = None
    income_level: Optional[str] = None
    interests: Optional[str] = None
    location: Optional[str] = None
    behavioral_data: Optional[str] = None

class Placement(BaseModel):
    name: Optional[str] = None
    destination: Optional[str] = None

class Metrics(BaseModel):
    impressions: Optional[int] = None
    clicks: Optional[int] = None

class BidRate(BaseModel):
    cpm: Optional[float] = None
    cpc: Optional[float] = None

class InsertionOrderRequest(BaseModel):
    # Required lookup fields
    account_id: Optional[str] = None
    campaign_id: Optional[str] = None
    opportunity_id: Optional[str] = None
    
    # Basic fields
    name: Optional[str] = None
    order_number: Optional[str] = None
    brand: Optional[str] = None
    campaign_name: Optional[str] = None
    
    # Approval fields
    customer_approver: Optional[str] = None
    customer_approver_email: Optional[EmailStr] = None
    customer_approval: Optional[str] = None
    sales_owner: Optional[str] = None
    sales_owner_email: Optional[EmailStr] = None
    sales_approval: Optional[str] = None
    fulfillment_owner: Optional[str] = None
    fulfillment_owner_email: Optional[EmailStr] = None
    
    # Date fields
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    
    # Nested objects
    placement: Optional[Placement] = None
    metrics: Optional[Metrics] = None
    bid_rate: Optional[BidRate] = None
    target_audience: Optional[TargetAudience] = None
    
    # Budget and description
    budget_amount: Optional[float] = None
    objective_description: Optional[str] = None

class InsertionOrderResponse(BaseModel):
    id: str
    order_number: str
    status: str
    message: str

# Salesforce connection manager
class SalesforceManager:
    def __init__(self):
        self.sf = None
        self.connect()
    
    def connect(self):
        """Establish connection to Salesforce"""
        try:
            self.sf = Salesforce(
                username=os.getenv('SALESFORCE_USERNAME'),
                password=os.getenv('SALESFORCE_PASSWORD'),
                security_token=os.getenv('SALESFORCE_SECURITY_TOKEN'),
                domain=os.getenv('SALESFORCE_DOMAIN', 'test')
            )
            logger.info("Successfully connected to Salesforce")
        except Exception as e:
            logger.error(f"Failed to connect to Salesforce: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to connect to Salesforce")
    
    def test_connection(self):
        """Test Salesforce connection"""
        try:
            result = self.sf.query("SELECT Id FROM User LIMIT 1")
            return True
        except Exception as e:
            logger.error(f"Salesforce connection test failed: {str(e)}")
            return False
    
    def is_valid_salesforce_id(self, id_value: str) -> bool:
        """Check if a string is a valid Salesforce ID (15 or 18 characters)"""
        if not id_value or id_value.lower() == "string" or len(id_value) < 15:
            return False
        return len(id_value) in [15, 18] and id_value.isalnum()
    
    def parse_date_string(self, date_str: str) -> Optional[str]:
        """Parse various date formats and return ISO format string"""
        from datetime import datetime
        
        if not date_str or date_str.lower() == "string":
            return None
            
        # Try different date formats
        date_formats = [
            "%m-%d-%Y",      # MM-DD-YYYY
            "%Y-%m-%d",      # YYYY-MM-DD
            "%m/%d/%Y",      # MM/DD/YYYY
            "%Y/%m/%d",      # YYYY/MM/DD
            "%d-%m-%Y",      # DD-MM-YYYY
            "%d/%m/%Y",      # DD/MM/YYYY
        ]
        
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt).date()
                return parsed_date.isoformat()
            except ValueError:
                continue
        
        logger.warning(f"Could not parse date: {date_str}")
        return None

    def create_insertion_order_from_frontend(self, order_data: OrderGenerationRequest):
        """Create an Insertion Order from frontend structure"""
        from datetime import datetime
        
        try:
            # Convert frontend structure to Salesforce format
            sf_data = {}
            
            # Basic required fields
            sf_data['Name'] = f"{order_data.Brand} - {order_data.CampaignName}"
            sf_data['Order_Number__c'] = order_data.OrderNo
            sf_data['Brand__c'] = order_data.Brand
            sf_data['Campaign_Name__c'] = order_data.CampaignName
            
            # Approval fields
            sf_data['Customer_Approver__c'] = order_data.CustomerApprover
            sf_data['Customer_Approver_Email__c'] = order_data.CustomerApproverEmail
            sf_data['Sales_Owner__c'] = order_data.SalesOwner
            sf_data['Sales_Owner_Email__c'] = order_data.SalesOwnerEmail
            sf_data['Fulfillment_Owner__c'] = order_data.FulfillmentOwner
            sf_data['Fulfillment_Owner_Email__c'] = order_data.FulfillmentOwnerEmail
            
            # Set default approvals
            sf_data['Customer_Approval__c'] = "Pending"
            sf_data['Sales_Approval__c'] = "Pending"
            
            # Objective description
            if order_data.ObjectiveDetails and order_data.ObjectiveDetails.Description:
                sf_data['objective_description__c'] = order_data.ObjectiveDetails.Description
            if order_data.PDF_View_Link_c:
                sf_data['PDF_View_Link__c'] = order_data.PDF_View_Link_c
            if order_data.Media_Plan__c:
                sf_data['Media_Plan__c'] = order_data.Media_Plan__c
            if order_data.Creative_Inspiration__c:
                sf_data['Creative_Inspiration__c'] = order_data.Creative_Inspiration__c
                
            # Lookup fields - only add if valid Salesforce IDs
            if order_data.account_id and self.is_valid_salesforce_id(order_data.account_id):
                sf_data['Account__c'] = order_data.account_id
            if order_data.campaign_id and self.is_valid_salesforce_id(order_data.campaign_id):
                sf_data['Campaign__c'] = order_data.campaign_id
            if order_data.opportunity_id and self.is_valid_salesforce_id(order_data.opportunity_id):
                sf_data['Opportunity__c'] = order_data.opportunity_id
            
            result = self.sf.Insertion_Order__c.create(sf_data)
            io_id = result['id']
            logger.info(f"Successfully created Insertion Order: {io_id}")

            for placement in order_data.Placement:
                placement_data = {}

                # Required lookup to parent Insertion Order
                placement_data['Insertion_Order__c'] = io_id

                # Placement fields
                if placement.Name:
                    placement_data['Name'] = placement.Name
                if placement.Destination:
                    placement_data['Destination__c'] = placement.Destination
                if placement.ConvertToCampaign is not None:
                    print("Convert to campaign: ", placement.ConvertToCampaign)
                    placement_data['Convert_to_Campaign__c'] = placement.ConvertToCampaign

                # Dates
                if placement.StartDate:
                    parsed_start = self.parse_date_string(placement.StartDate)
                    if parsed_start:
                        placement_data['Start_Date__c'] = parsed_start

                if placement.EndDate:
                    parsed_end = self.parse_date_string(placement.EndDate)
                    if parsed_end:
                        placement_data['End_Date__c'] = parsed_end

                # Metrics
                if placement.Metrics:
                    if placement.Metrics.Impressions is not None:
                        placement_data['Metrics_Impression__c'] = placement.Metrics.Impressions
                    if placement.Metrics.Clicks is not None:
                        placement_data['Metrics_Clicks__c'] = placement.Metrics.Clicks

                # Bid rates
                if placement.BidRate:
                    if placement.BidRate.CPM is not None:
                        placement_data['bid_rate_cpm__c'] = placement.BidRate.CPM
                    if placement.BidRate.CPC is not None:
                        placement_data['bid_rate_cpc__c'] = placement.BidRate.CPC

                # Budget
                if placement.Budget and placement.Budget.Amount is not None:
                    placement_data['Budget_Amount__c'] = placement.Budget.Amount

                # Targeting
                targeting_config = placement.new_targeting_configuration or placement.TargetingSuggestions
                if targeting_config:
                    if targeting_config.age_range:
                        placement_data['target_audience_age_range__c'] = ', '.join(targeting_config.age_range)
                    if targeting_config.gender:
                        placement_data['target_audience_gender__c'] = ', '.join(targeting_config.gender)
                    if targeting_config.income_level:
                        placement_data['target_audience_income_level__c'] = ', '.join(targeting_config.income_level)
                    if targeting_config.interests:
                        placement_data['target_audience_interests__c'] = ', '.join(targeting_config.interests)
                    if targeting_config.location:
                        placement_data['target_audience_location__c'] = ', '.join(targeting_config.location)
                    if targeting_config.behavioral_data:
                        placement_data['target_audience_behavioral_data__c'] = ', '.join(targeting_config.behavioral_data)

   
                self.sf.Placement__c.create(placement_data)

           
            return result
            
        except Exception as e:
            logger.error(f"Failed to create Insertion Order: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Failed to create Insertion Order: {str(e)}")
    

    
    def get_insertion_order(self, record_id: str):
        """Retrieve an Insertion Order from Salesforce"""
        try:
            result = self.sf.Insertion_Order__c.get(record_id)
            return result
        except Exception as e:
            logger.error(f"Failed to retrieve Insertion Order: {str(e)}")
            raise HTTPException(status_code=404, detail="Insertion Order not found")
    
    def list_insertion_orders(self, limit: int = 100):
        """List Insertion Orders from Salesforce"""
        try:
            query = f"""SELECT Id, Name, Brand__c, Campaign_Name__c, Start_Date__c, End_Date__c, 
                       Budget_Amount__c, Order_Number__c, Sales_Approval__c, Customer_Approval__c,
                       Account__r.Name, Opportunity__r.Name, PDF_View_Link__c, Media_Plan__c
                       FROM Insertion_Order__c 
                       ORDER BY CreatedDate DESC LIMIT {limit}"""
            result = self.sf.query(query)
            return result['records']
        except Exception as e:
            logger.error(f"Failed to list Insertion Orders: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to retrieve Insertion Orders")