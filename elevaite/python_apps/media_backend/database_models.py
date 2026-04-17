import os
import sqlalchemy as sa
from sqlalchemy import Column, String, DateTime, Text, Integer, Float, Boolean, JSON, ForeignKey, Date, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from db_connector import Base
import uuid
from datetime import datetime, timezone

class CampaignData(Base):
    __tablename__ = os.getenv("DATABASE_CAMPAIGN_TABLE", "campaign_data")

    campaign_id = sa.Column(sa.String(255), primary_key=True)
    campaign_name = sa.Column(sa.String(255), nullable=False)
    booked_impressions = sa.Column(sa.Numeric(10, 2))
    clickable_impressions = sa.Column(sa.Numeric(10, 2))
    clicks = sa.Column(sa.Integer)
    conversion = sa.Column(sa.Numeric(10, 8))
    duration = sa.Column(sa.Integer)
    brand = sa.Column(sa.String(255))
    ad_surface = sa.Column(sa.String(255))
    ecpm = sa.Column(sa.Numeric(10, 2))
    budget = sa.Column(sa.Numeric(10, 2))
    insights = sa.Column(sa.Text)

    def __repr__(self):
        return f"<CampaignData(campaign_id='{self.campaign_id}', campaign_name='{self.campaign_name}')>"


# Session Management Tables
class SessionModel(Base):
    """SQLAlchemy model for session metadata"""
    __tablename__ = "sessions"

    session_id = Column(String(255), primary_key=True)
    user_id = Column(String(255), nullable=False, index=True)
    session_name = Column(String(500), nullable=False)
    creation_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    last_activity_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    total_queries = Column(Integer, default=0)
    session_summary = Column(Text)
    total_tokens_used = Column(JSON, default=dict)  # Dict with input/output/total
    feedback_count = Column(Integer, default=0)
    positive_feedback_count = Column(Integer, default=0)
    negative_feedback_count = Column(Integer, default=0)

    # Relationships
    queries = relationship("QueryModel", back_populates="session", cascade="all, delete-orphan")
    feedback = relationship("FeedbackModel", back_populates="session", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<SessionModel(session_id='{self.session_id}', user_id='{self.user_id}', name='{self.session_name}')>"


class QueryModel(Base):
    """SQLAlchemy model for query execution data"""
    __tablename__ = "queries"

    query_id = Column(String(255), primary_key=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    original_query = Column(Text, nullable=False)
    start_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime)
    total_duration_ms = Column(Integer)
    final_response = Column(Text)
    intent_detected = Column(String(100))
    agents_used = Column(JSON, default=list)  # List of agent names
    total_tokens_used = Column(JSON, default=dict)  # Dict with input/output/total
    success = Column(Boolean, default=True)
    error_details = Column(Text)

    # Relationships
    session = relationship("SessionModel", back_populates="queries")
    execution_steps = relationship("AgentExecutionStepModel", back_populates="query", cascade="all, delete-orphan")
    feedback = relationship("FeedbackModel", back_populates="query", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<QueryModel(query_id='{self.query_id}', session_id='{self.session_id}')>"


class AgentExecutionStepModel(Base):
    """SQLAlchemy model for individual agent execution steps"""
    __tablename__ = "agent_execution_steps"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(String(255), ForeignKey("queries.query_id"), nullable=False, index=True)
    agent_name = Column(String(100), nullable=False, index=True)
    step_type = Column(String(100), nullable=False)  # intent_detection, agent_processing, etc.
    start_time = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    end_time = Column(DateTime)
    duration_ms = Column(Integer)
    input_prompt = Column(Text)
    output_response = Column(Text)
    model_used = Column(String(100))
    tokens_used = Column(JSON, default=dict)  # Dict with input/output/total
    success = Column(Boolean, default=True)
    error_details = Column(Text)
    step_metadata = Column(JSON, default=dict)  # Additional context-specific data

    # Relationships
    query = relationship("QueryModel", back_populates="execution_steps")

    def __repr__(self):
        return f"<AgentExecutionStepModel(agent_name='{self.agent_name}', query_id='{self.query_id}')>"


class FeedbackModel(Base):
    """SQLAlchemy model for user feedback"""
    __tablename__ = "feedback"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(String(255), ForeignKey("queries.query_id"), nullable=False, index=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False, index=True)
    user_id = Column(String(255), nullable=False, index=True)
    feedback_type = Column(String(50), nullable=False)  # thumbs_up, thumbs_down, detailed
    feedback_text = Column(Text)
    vote = Column(Integer, default=0)  # 1=up, -1=down, 0=neutral
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    query = relationship("QueryModel", back_populates="feedback")
    session = relationship("SessionModel", back_populates="feedback")

    def __repr__(self):
        return f"<FeedbackModel(query_id='{self.query_id}', feedback_type='{self.feedback_type}')>"


class RelatedQueriesModel(Base):
    """SQLAlchemy model for storing final related queries for session continuity"""
    __tablename__ = "related_queries"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query_id = Column(String(255), ForeignKey("queries.query_id"), nullable=False, index=True)
    session_id = Column(String(255), ForeignKey("sessions.session_id"), nullable=False, index=True)
    related_queries = Column(JSON, default=list)  # List of related query strings
    timestamp = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))

    # Relationships
    query = relationship("QueryModel")
    session = relationship("SessionModel")

    def __repr__(self):
        return f"<RelatedQueriesModel(query_id='{self.query_id}', session_id='{self.session_id}')>"


class TargetingConfigurationModel(Base):
    """SQLAlchemy model for storing targeting configurations"""
    __tablename__ = "targeting_configurations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    targeting_config = Column(JSON, nullable=False)  # Contains age_range, gender, income_level, etc.
    user_id = Column(String(255), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<TargetingConfigurationModel(id='{self.id}', name='{self.name}', user_id='{self.user_id}')>"


# Insertion Order Management Tables
class InsertionOrderModel(Base):
    """SQLAlchemy model for insertion orders"""
    __tablename__ = "insertion_orders"

    id = Column(String(255), primary_key=True, default=lambda: str(uuid.uuid4()))
    order_no = Column(String(255), nullable=False, unique=True, index=True)
    brand = Column(String(255))
    campaign_name = Column(String(255), nullable=False, index=True)
    customer_approver = Column(String(255), nullable=False)
    customer_approver_email = Column(String(255), nullable=False)
    sales_owner = Column(String(255), nullable=False)
    sales_owner_email = Column(String(255), nullable=False)
    fulfillment_owner = Column(String(255), nullable=False)
    fulfillment_owner_email = Column(String(255), nullable=False)
    objective_description = Column(Text)
    status = Column(String(50), nullable=False, default='draft', index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    workspace_type = Column(String(50), index=True)  # 'google_drive' or 'salesforce'
    creative_inspiration_id = Column(String(255))  # External system ID (not UUID)
    io_pdf_id = Column(String(255))  # Google Drive file ID or other external ID
    media_plan_id = Column(String(255))  # External system ID (not UUID)
    raw_data = Column(JSONB, default=dict)

    # Relationships
    status_changes = relationship("StatusChangeModel", back_populates="insertion_order", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<InsertionOrderModel(id='{self.id}', order_no='{self.order_no}', campaign_name='{self.campaign_name}')>"


class CampaignModel(Base):
    """SQLAlchemy model for campaigns - simplified schema"""
    __tablename__ = "campaigns"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    kevel_id = Column(String(255), unique=True, index=True)
    status = Column(String(50), nullable=False, default='work_in_progress', index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<CampaignModel(id='{self.id}', name='{self.name}', status='{self.status}')>"


class CampaignPlacement(Base):
    """SQLAlchemy model for campaign placements - stores placement details for campaigns"""
    __tablename__ = "campaign_placements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    flight_id = Column(String(255), index=True)
    start_date = Column(Date, index=True)
    end_date = Column(Date, index=True)
    impressions_booked = Column(Integer, default=0)
    impressions_delivered = Column(Integer, default=0)
    booked_clicks = Column(Integer, default=0)
    delivered_clicks = Column(Integer, default=0)
    ctr = Column(Numeric(10, 6), default=0.0)
    budget = Column(Numeric(15, 2), default=0.0)
    cpm = Column(Numeric(10, 2), default=0.0)
    cpc = Column(Numeric(10, 2), default=0.0)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    campaign = relationship("CampaignModel", backref="campaign_placements")

    def __repr__(self):
        return f"<CampaignPlacement(id='{self.id}', campaign_id='{self.campaign_id}', budget='{self.budget}')>"


class PlacementModel(Base):
    """SQLAlchemy model for placements"""
    __tablename__ = "placements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insertion_order_id = Column(String(255), ForeignKey("insertion_orders.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False, index=True)
    destination = Column(String(255), index=True)
    start_date = Column(Date, index=True)
    end_date = Column(Date, index=True)
    convert_to_campaign = Column(Boolean, default=False)  # Flag to convert placement into individual campaign
    impressions_booked = Column(Integer, default=0)
    impressions_delivered = Column(Integer, default=0)
    clicks = Column(Integer, default=0)
    ctr = Column(Numeric(10, 6), default=0.0)
    budget = Column(Numeric(15, 2), default=0.0)
    cpm = Column(Numeric(10, 2), default=0.0)
    cpc = Column(Numeric(10, 2), default=0.0)
    targeting_config = Column(JSONB, default=dict)
    status = Column(String(50), nullable=False, default='draft', index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    insertion_order = relationship("InsertionOrderModel", backref="placements")

    def __repr__(self):
        return f"<PlacementModel(id='{self.id}', name='{self.name}', insertion_order_id='{self.insertion_order_id}')>"


class StatusChangeModel(Base):
    """SQLAlchemy model for status changes"""
    __tablename__ = "status_changes"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insertion_order_id = Column(String(255), ForeignKey("insertion_orders.id"), nullable=False, index=True)
    previous_status = Column(String(50))
    new_status = Column(String(50), nullable=False, index=True)
    changed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    changed_by = Column(String(255), index=True)
    reason = Column(Text)

    # Relationships
    insertion_order = relationship("InsertionOrderModel", back_populates="status_changes")

    def __repr__(self):
        return f"<StatusChangeModel(id='{self.id}', insertion_order_id='{self.insertion_order_id}', new_status='{self.new_status}')>"


# New Mapping Tables for the updated schema

class InsertionOrderSalesforceMapping(Base):
    """SQLAlchemy model for insertion order to Salesforce mapping"""
    __tablename__ = "insertion_order_salesforce_mapping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insertion_order_id = Column(String(255), ForeignKey("insertion_orders.id"), nullable=False, index=True)
    salesforce_io_id = Column(String(255), nullable=False, index=True)  # Salesforce insertion order ID
    salesforce_account_id = Column(String(255), index=True)
    salesforce_opportunity_id = Column(String(255), index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    insertion_order = relationship("InsertionOrderModel", backref="salesforce_mapping")

    def __repr__(self):
        return f"<InsertionOrderSalesforceMapping(id='{self.id}', insertion_order_id='{self.insertion_order_id}', salesforce_io_id='{self.salesforce_io_id}')>"


class InsertionOrderGoogleDriveMapping(Base):
    """SQLAlchemy model for insertion order to Google Drive mapping"""
    __tablename__ = "insertion_order_google_drive_mapping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    insertion_order_id = Column(String(255), ForeignKey("insertion_orders.id"), nullable=False, index=True)
    drive_folder_id = Column(String(255), index=True)
    sheet_id = Column(String(255), index=True)
    pdf_file_id = Column(String(255), index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    insertion_order = relationship("InsertionOrderModel", backref="google_drive_mapping")

    def __repr__(self):
        return f"<InsertionOrderGoogleDriveMapping(id='{self.id}', insertion_order_id='{self.insertion_order_id}', folder_id='{self.drive_folder_id}')>"


class CampaignInsertionOrderMapping(Base):
    """SQLAlchemy model for campaign to insertion order mapping"""
    __tablename__ = "campaign_insertion_order_mapping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    insertion_order_id = Column(String(255), ForeignKey("insertion_orders.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)

    # Relationships
    campaign = relationship("CampaignModel", backref="insertion_order_mappings")
    insertion_order = relationship("InsertionOrderModel", backref="campaign_mappings")

    def __repr__(self):
        return f"<CampaignInsertionOrderMapping(id='{self.id}', campaign_id='{self.campaign_id}', insertion_order_id='{self.insertion_order_id}')>"


class CreativeAsset(Base):
    """SQLAlchemy model for creative assets"""
    __tablename__ = "creative_assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    file_url = Column(Text)
    file_type = Column(String(50), index=True)
    file_size = Column(Integer)
    width = Column(Integer)
    height = Column(Integer)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    def __repr__(self):
        return f"<CreativeAsset(id='{self.id}', name='{self.name}', file_type='{self.file_type}')>"


class CampaignCreativeMapping(Base):
    """SQLAlchemy model for campaign to creative asset mapping"""
    __tablename__ = "campaign_creative_mapping"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    creative_asset_id = Column(UUID(as_uuid=True), ForeignKey("creative_assets.id"), nullable=False, index=True)
    created_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    campaign = relationship("CampaignModel", backref="creative_mappings")
    creative_asset = relationship("CreativeAsset", backref="campaign_mappings")

    def __repr__(self):
        return f"<CampaignCreativeMapping(id='{self.id}', campaign_id='{self.campaign_id}', creative_asset_id='{self.creative_asset_id}')>"

class CampaignChangeTracking(Base):
    """SQLAlchemy model for tracking campaign changes over time"""
    __tablename__ = "campaign_change_tracking"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False, index=True)
    change_date = Column(Date, nullable=False, index=True)
    change_type = Column(String(50), nullable=False, index=True)  # 'targeting', 'budget_spend', 'creative'
    # Previous values (JSON for flexibility)
    previous_values = Column(JSONB, default=dict)
    # New values (JSON for flexibility)
    new_values = Column(JSONB, default=dict)
    # Change details
    change_description = Column(Text)
    variance_percentage = Column(Numeric(10, 2))  # For budget/spend changes
    # Metadata
    detected_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    data_source = Column(String(50), default='system')  # 'system', 'manual', 'api'
    # Relationships
    campaign = relationship("CampaignModel", backref="change_tracking")

    def __repr__(self):
        return f"<CampaignChangeTracking(id='{self.id}', campaign_id='{self.campaign_id}', change_type='{self.change_type}', change_date='{self.change_date}')>"
