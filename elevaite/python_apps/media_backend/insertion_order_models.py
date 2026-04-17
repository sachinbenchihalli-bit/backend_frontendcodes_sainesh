from pydantic import BaseModel
from typing import Dict, Any, Optional, List, Union

class PDFGenerationRequest(BaseModel):
    sheet_id: str
    drive_folder_id: str
    pdf_folder_id: str
    current_pdf_version: int

    class Config:
        schema_extra = {
            "example": {
                "sheet_id": "1234567890",
                "drive_folder_id": "folder_id_123",
                "pdf_folder_id": "pdf_folder_id_456",
                "current_pdf_version": 2
            }
        }

class MetricsModel(BaseModel):
    Impressions: int
    Clicks: int

class BidRateModel(BaseModel):
    CPM: float
    CPC: float

class BudgetModel(BaseModel):
    Amount: float

class TargetingConfig(BaseModel):
    """New targeting configuration structure"""
    age_range: List[str]
    gender: List[str]
    income_level: List[str]
    location: List[str]
    interests: List[str]
    behavioral_data: List[str]

class TargetingSuggestionsModel(BaseModel):
    """Legacy targeting suggestions model - supports both old and new formats"""
    Demographics: Optional[List[str]] = []
    Interests: Optional[List[str]] = []
    Keywords: Optional[List[str]] = []
    AudienceSegments: Optional[List[str]] = []
    DeviceTargeting: Optional[List[str]] = []
    # Support both string and array formats for backward compatibility
    age_range: Optional[Union[str, List[str]]] = None
    gender: Optional[Union[str, List[str]]] = None
    income_level: Optional[Union[str, List[str]]] = None
    interests: Optional[List[str]] = []
    location: Optional[Union[str, List[str]]] = None
    behavioral_data: Optional[Union[str, List[str]]] = None

class ObjectiveDetailsModel(BaseModel):
    Description: str

class TargetingOptionModel(BaseModel):
    """Model for individual targeting configuration options"""
    option_number: int
    is_primary: bool
    targeting_configuration_id: Optional[str] = None
    new_targeting_configuration: Optional[TargetingConfig] = None
    new_targeting_configuration_name: Optional[str] = None
    new_targeting_configuration_description: Optional[str] = None

class PlacementModel(BaseModel):
    Name: str
    Destination: str
    StartDate: str
    EndDate: str
    ConvertToCampaign: Optional[bool] = None  # Flag to convert placement into individual campaign
    Metrics: MetricsModel
    BidRate: BidRateModel
    Budget: BudgetModel
    # Support new targeting configuration fields
    targeting_configuration_id: Optional[str] = None
    new_targeting_configuration: Optional[TargetingConfig] = None
    new_targeting_configuration_name: Optional[str] = None
    new_targeting_configuration_description: Optional[str] = None
    targeting_options: Optional[List[TargetingOptionModel]] = None  # Multiple targeting options
    # Legacy targeting suggestions - now optional for backward compatibility
    TargetingSuggestions: Optional[TargetingSuggestionsModel] = None

class OrderGenerationRequest(BaseModel):
    OrderNo: str
    Brand: Optional[str] = None  # Optional for Salesforce destination
    CampaignName: str
    CustomerApprover: str
    CustomerApproverEmail: str
    SalesOwner: str
    SalesOwnerEmail: str
    FulfillmentOwner: str
    FulfillmentOwnerEmail: str
    ObjectiveDetails: ObjectiveDetailsModel
    Placement: List[PlacementModel]
    # Salesforce-specific fields
    SalesforceAccount: Optional[str] = None
    SalesforceOpportunityId: Optional[str] = None
    # Media plan content
    MediaPlanContent: Optional[str] = None
    # Creative inspiration link
    CreativeInspirationLink: Optional[str] = None

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
                "Placement": [
                    {
                        "Name": "Social Media",
                        "Destination": "Instagram",
                        "StartDate": "06-01-2024",
                        "EndDate": "08-31-2024",
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

class PDFFileDetails(BaseModel):
    filename: str
    pdf_file_id: str
    pdf_web_view_link: str

class PDFGenerationResponse(BaseModel):
    status: str
    message: str
    pdf_folder_id: str
    pdf_file_id: str
    pdf_web_view_link: str

class OrderGenerationResponse(BaseModel):
    status: str
    message: str
    campaign_folder_id: str
    campaign_folder_link: str
    sheet_id: str
    sheet_link: str
    pdf_folder_id: str
    pdf_folder_link: str
    file_details: PDFFileDetails
    media_plan_pdf_link: Optional[str] = None
