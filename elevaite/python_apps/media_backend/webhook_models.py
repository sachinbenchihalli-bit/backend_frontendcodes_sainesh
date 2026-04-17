"""
Pydantic models for webhook endpoints
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum

class ApprovalStatus(str, Enum):
    """Enum for approval status types"""
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"

class SalesforceApproverInfo(BaseModel):
    """Information about the Salesforce approver"""
    name: str = Field(..., description="Full name of the approver")
    email: str = Field(..., description="Email address of the approver")
    salesforce_user_id: str = Field(..., description="Salesforce User ID")
    title: Optional[str] = Field(None, description="Job title of the approver")
    department: Optional[str] = Field(None, description="Department of the approver")

class SalesforceInsertionOrderApprovalRequest(BaseModel):
    """
    Webhook payload for Salesforce insertion order approval notifications
    """
    # Core insertion order identification
    order_number: str = Field(..., description="Insertion order number (e.g., IO-340371-3439)")
    salesforce_record_id: Optional[str] = Field(None, description="Salesforce record ID")
    
    # Approval information
    approval_status: ApprovalStatus = Field(..., description="Approval status")
    approver: SalesforceApproverInfo = Field(..., description="Information about the approver")
    approval_timestamp: datetime = Field(..., description="When the approval occurred")
    
    # Additional metadata
    approval_comments: Optional[str] = Field(None, description="Comments from the approver")
    approval_type: Optional[str] = Field("standard", description="Type of approval (standard, expedited, etc.)")
    workflow_step: Optional[str] = Field(None, description="Current workflow step in Salesforce")
    
    # Salesforce-specific metadata
    salesforce_metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="Additional Salesforce data")
    
    @validator('order_number')
    def validate_order_number(cls, v):
        """Validate order number format"""
        if not v or not v.strip():
            raise ValueError('Order number cannot be empty')
        return v.strip()
    
    @validator('approval_timestamp')
    def validate_approval_timestamp(cls, v):
        """Ensure approval timestamp is not in the future"""
        # Get current time in UTC for comparison
        now_utc = datetime.now(timezone.utc)

        # If the incoming datetime is timezone-naive, assume it's UTC
        if v.tzinfo is None:
            v = v.replace(tzinfo=timezone.utc)

        # Compare with current UTC time
        if v > now_utc:
            raise ValueError('Approval timestamp cannot be in the future')
        return v

class WebhookResponse(BaseModel):
    """Standard webhook response"""
    success: bool = Field(..., description="Whether the webhook was processed successfully")
    message: str = Field(..., description="Human-readable message about the result")
    insertion_order_id: Optional[str] = Field(None, description="Database ID of the updated insertion order")
    previous_status: Optional[str] = Field(None, description="Previous status of the insertion order")
    new_status: Optional[str] = Field(None, description="New status of the insertion order")
    processed_at: datetime = Field(default_factory=datetime.now, description="When the webhook was processed")

class WebhookErrorResponse(BaseModel):
    """Error response for webhook failures"""
    success: bool = Field(False, description="Always false for error responses")
    error: str = Field(..., description="Error type")
    message: str = Field(..., description="Detailed error message")
    order_number: Optional[str] = Field(None, description="Order number from the request if available")
    processed_at: datetime = Field(default_factory=datetime.now, description="When the error occurred")

# Example payload for documentation
EXAMPLE_SALESFORCE_APPROVAL_PAYLOAD = {
    "order_number": "IO-340371-3439",
    "salesforce_record_id": "a0X5g000001234567",
    "approval_status": "approved",
    "approver": {
        "name": "John Smith",
        "email": "john.smith@company.com",
        "salesforce_user_id": "0055g000001234567",
        "title": "Marketing Director",
        "department": "Marketing"
    },
    "approval_timestamp": "2025-06-30T14:30:00Z",
    "approval_comments": "Approved for Q3 campaign launch",
    "approval_type": "standard",
    "workflow_step": "final_approval",
    "salesforce_metadata": {
        "opportunity_id": "0065g000001234567",
        "account_id": "0015g000001234567",
        "campaign_id": "7015g000001234567"
    }
}
