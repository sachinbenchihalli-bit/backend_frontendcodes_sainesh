from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any, Union, Literal
from datetime import datetime, date
from enum import Enum
import json

class AdCreative(BaseModel):
    id: str
    file_name: str
    campaign_folder: str
    file_size: Optional[int] = None
    file_type: Optional[str] = None
    type: Optional[str] = None
    booked_measure_impressions: Optional[float] = None
    delivered_measure_impressions: Optional[float] = None
    duration_days: Optional[int] = Field(None, alias="duration(days)")
    duration_category: Optional[str] = None
    industry_sectors: Optional[str] = None  # Changed from 'industry' to match Qdrant database field
    brand: Optional[str] = None
    brand_type: Optional[str] = None
    season_holiday: Optional[str] = None
    product_service: Optional[str] = None
    ad_objective: Optional[str] = None
    targeting: Optional[str] = None
    tone_mood: Optional[str] = None
    clicks: Optional[int] = None
    conversion: Optional[float] = None
    creative_url: Optional[str] = None
    md5_hash: Optional[str] = None
    full_data: Optional[Dict[str, Any]] = Field(default_factory=dict)
    product_category: Optional[str] = None
    creative_summary: Optional[str] = None

    @classmethod
    def parse_obj(cls, obj):
        try:
            # Handle the 'full_data' field parsing
            if 'full_data' in obj and isinstance(obj['full_data'], str):
                try:
                    obj['full_data'] = json.loads(obj['full_data'])
                except json.JSONDecodeError as e:
                    raise ValueError(f"Failed to decode 'full_data' as JSON: {e}. Input: {obj['full_data']}")

            # Normalize field names in 'full_data'
            if isinstance(obj.get('full_data'), dict):
                obj['full_data'] = {k.replace(' ', '_'): v for k, v in obj['full_data'].items()}

            return super().parse_obj(obj)

        except Exception as e:
            # Log or re-raise the error with context
            print(f"Error while parsing object: {e}. Input data: {obj}")
            # raise ValueError(f"Error while parsing object: {e}. Input data: {obj}")

    class Config:
        extra = "allow"
        populate_by_name = True
        str_strip_whitespace = True

class AppliedFilter(BaseModel):
    """Represents a filter that was applied during search."""
    field: str
    value: Union[str, List[str]]
    match_type: Literal["single", "multiple"]

class SearchStepResult(BaseModel):
    """Results from a specific search step."""
    step_type: str  # filter, semantic_search, etc.
    step_description: str
    results_count: int
    applied_filters: List[AppliedFilter] = Field(default_factory=list)
    brands_found: List[str] = Field(default_factory=list)
    industries_found: List[str] = Field(default_factory=list)

class SearchContext(BaseModel):
    """Context information about how the search was performed."""
    search_type: str  # semantic_only, filter_with_semantic, filter_without_semantic
    applied_filters: List[AppliedFilter] = Field(default_factory=list)
    sort_field: str = "conversion"
    sort_direction: str = "desc"
    retry_count: int = 0
    retry_history: List[str] = Field(default_factory=list)  # Descriptions of what was tried
    filter_logic: Literal["must", "should"] = "must"  # AND vs OR logic
    search_plan_steps: List[str] = Field(default_factory=list)  # Descriptions of executed steps
    fallback_used: bool = False
    total_candidates_found: int = 0
    final_results_count: int = 0
    search_explanation: str = ""  # Human-readable explanation of what was done
    step_results: List[SearchStepResult] = Field(default_factory=list)  # Detailed results from each step
    filter_relaxation_impact: Dict[str, int] = Field(default_factory=dict)  # Impact of filter relaxation

class SearchResult(BaseModel):
    results: List[AdCreative]
    total: int
    next_page_offset: Optional[str] = None  # For pagination with scroll
    search_context: Optional[SearchContext] = None  # Context about how search was performed
class ConversationPayload(BaseModel):
    actor: str
    content: str

class InferencePayload(BaseModel):
    conversation_payload: List[ConversationPayload]
    query: str
    query_id: str
    skip_llm_call: bool
    creative: Optional[str] = None
    session_id: str
    user_id: str

class IntentOutput(BaseModel):
    required_outcomes: List[int]
    unrelated_query: bool
    vector_search:bool
    follow_up:Optional[str]

class ExecutiveSummary(BaseModel):
    objectives: str
    target_audience: str
    budget: str
    campaign_duration_in_days: int
    ctr: float  # CTR predicted by LLM (as percentage, e.g., 2.5 for 2.5%)
    start_date: Optional[str]
    end_date: Optional[str]
class TargetingOptionModel(BaseModel):
    """Model for individual targeting configuration options"""
    option_number: int
    is_primary: bool
    targeting_configuration_id: Optional[str] = None
    new_targeting_configuration: Optional["TargetingConfig"] = None
    new_targeting_configuration_name: Optional[str] = None
    new_targeting_configuration_description: Optional[str] = None

class TargetAudienceDemographic(BaseModel):
    age_range: str
    gender: str
    income_level: str
    interests: List[str]
    location: str
    behavioral_data: str
    targeting_configuration_id: Optional[str] = None  # ID of existing targeting configuration
    new_targeting_configuration: Optional["TargetingConfig"] = None  # New targeting configuration details
    targeting_options: Optional[List[TargetingOptionModel]] = None  # Multiple targeting options
class MediaMixStrategy(BaseModel):
    channel_products: str
    tactics: str
    budget_allocation_percentage: str
    expected_reach: str
    justification: str
    # Backend-calculated fields (populated by budget tool)
    impressions: Optional[int] = None  # Calculated: (budget * 1000) / cpm
    clicks: Optional[int] = None       # Calculated: (ctr * impressions) / 1000
    cpm: Optional[float] = None        # Hardcoded: Journey video ads: $40, Journey ads: $15
class CreativeStrategy(BaseModel):
    asset_type: str
    description: str
    purpose: str
    distribution_channels: List[str]
class MeasurementMetric(BaseModel):
    metric: str
    description: str
    target: str
    reporting_frequency: str
class MediaPlanOutput(BaseModel):

    media_mix_strategy: List[MediaMixStrategy]
    target_audience: TargetAudienceDemographic
    creative_strategy: List[CreativeStrategy]
    measurement_and_evaluation: List[MeasurementMetric]
    message: str
    executive_summary: ExecutiveSummary
    brand: Optional[str] = None

class InsightRecommendation(BaseModel):
    recommendation: str
    supporting_insight: str

class CampaignStrategy(BaseModel):
    objective: str
    insight_recommendation: InsightRecommendation

class ToneAndMood(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class CallToAction(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class SeasonHoliday(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class CampaignDuration(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class BookedImpressions(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class TargetingOptions(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class Conversion(BaseModel):
    insight_recommendation: InsightRecommendation

class CreativeInsights(BaseModel):
    key_trends: List[str]

class CreativeStrategy(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class CreativeContentType(BaseModel):
    description: str
    insight_recommendation: InsightRecommendation

class CampaignPerformanceReport(BaseModel):
    campaign_folders: List[str]
    message: Optional[str]

class CampaignOrderingCriteria(BaseModel):
    primary_metric: str  # e.g., "conversion", "clicks", "impressions", "duration", "budget_efficiency"
    secondary_metric: Optional[str] = None  # fallback ordering metric
    order_direction: Literal["ascending", "descending"] = "descending"
    reasoning: str  # explanation of why this ordering was chosen

class CampaignPerformanceAgentOutput(BaseModel):
    response_type: Literal["data_response", "search_retry", "user_response"]
    message: str
    selected_campaigns: Optional[List[str]] = None
    ordering_criteria: Optional[CampaignOrderingCriteria] = None

# Creative Insights
class CreativeElements(BaseModel):
    creative_thumbnail: str
    brand_elements: str
    seasonal_holiday_elements: Optional[str]
    visual_elements: str
    color_tone: str
    cinematography: Optional[str]
    # audio_elements: str
    narrative_structure: Optional[str]

class CreativeInsight(BaseModel):
    brand: str
    product: str
    creative_snapshot: str
    creative_elements: CreativeElements

class CreativeInsightsReport(BaseModel):
    creatives: Optional[List[CreativeInsight]]
    message: Optional[str] = None  # Message about relevance of results to user query


# Performance Summary
class PerformanceSummary(BaseModel):
    ad_objective: str
    call_to_action: str
    tone_and_mood: str
    duration_category: str
    unique_selling_proposition: str
    event_context: Optional[str]
    creative_performance: str
    overall_performance: str

class MediaPlanCreative(BaseModel):
    id: str
    file_name: str
    campaign_folder: str
    ad_objective: Optional[str] = None
    duration_days: Optional[int] = None
    duration_category: Optional[str] = None
    target_market: Optional[str] = None
    target_audience: Optional[str] = None
    tone_mood: Optional[str] = None
    weekends: Optional[int] = None
    holidays: Optional[str] = None
    national_events: Optional[str] = None
    sport_events: Optional[str] = None
    strategy: Optional[str] = None
    visual_elements: Optional[Dict[str, Any]] = None
    imagery: Optional[str] = None
    targeting: Optional[str] = None
    industry_sectors: Optional[str] = None  # Changed from 'industry' to match Qdrant database field
    conversion: Optional[float] = None
    booked_measure_impressions: Optional[float] = None
    delivered_measure_impressions: Optional[float] = None


class MediaPlanSearchResult(BaseModel):
    results: List[MediaPlanCreative]
    total: int

class MarkdownRequest(BaseModel):
    markdown: str


class MessageData(BaseModel):
    topic: Optional[str] = None
    message_query: str
    enhanced_query: str
    vector_data: List[dict]
    creative_data: List[str] = []
    media_plan_output: str = ""
    creative_insights_output: str = ""
    campaign_performance_output: str = ""
    general_response_string: str = ""

class ErrorResponse(BaseModel):
    error: str

class InferenceResponse(BaseModel):
    response: str

class Related_Queries(BaseModel):
    related_queries: List[str]

class FilterFields(BaseModel):
    """Specific fields for filtering Qdrant search results."""
    brand: Optional[str]
    industry_sectors: Optional[str]
    season: Optional[str]
    campaign_folder: Optional[str]

class QdrantSearchParams(BaseModel):
    """Parameters for Qdrant search operations."""
    filter_fields: FilterFields = Field(default_factory=FilterFields)  # Fields to filter on with strict schema
    sort_by: Optional[str]
    sort_order: Optional[Literal["asc", "desc"]]
    limit: Optional[int]   # Number of results to return
    use_vector_search: bool   # Whether to use vector search
    scroll_parameter: Optional[str]  # For pagination
    allow_duplicates: bool  # Whether to allow duplicates

class AvailableBrands(BaseModel):
    """List of available brands in the database."""
    brands: List[str]

class AvailableIndustries(BaseModel):
    """List of available industries in the database."""
    industries: List[str]

class AvailableSeasons(BaseModel):
    """List of available seasons in the database."""
    seasons: List[str]

class SearchStep(BaseModel):
    """A single step in the search plan."""
    step_type: Literal["filter", "semantic_search", "sort", "rerank"]
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)

class PreviousSearchContext(BaseModel):
    """Context information about a previous search that failed."""
    search_type: str  # The type of search that was attempted
    applied_filters: List[AppliedFilter] = Field(default_factory=list)  # Filters that were applied
    filter_logic: Literal["must", "should"] = "must"  # AND vs OR logic used
    total_candidates_found: int = 0  # Number of candidates found before final filtering
    final_results_count: int = 0  # Final number of results returned
    retry_count: int = 0  # How many retries have been attempted
    retry_history: List[str] = Field(default_factory=list)  # What was tried in previous attempts
    search_explanation: str = ""  # Human-readable explanation of what was attempted
    excluded_ids: List[str] = Field(default_factory=list)  # IDs to exclude from search results to avoid duplicates

class SearchPlannerOutput(BaseModel):
    """Output from the search planner agent."""
    steps: List[SearchStep]
    search_type: Literal["filter_with_semantic", "filter_without_semantic", "semantic_only"]
    limit: Optional[int] = 10

class ImageClass(BaseModel):
    width:int
    height:int

class ImageAgentOutput(BaseModel):
    image_specs: ImageClass

class ImageSpecs(BaseModel):
    width:int
    height:int
    use_uploaded_reference:Optional[bool] =False
    url:Optional[str] = None

class ImageAgentOutputV2(BaseModel):
    image_specifications: List[ImageSpecs]


# class ImageModelDecider(BaseModel):
#     reference_type: Optional[str]
#     url:Optional[str]
#     title: str
class ImageModelDecider(BaseModel):
    operation: Literal["resize", "generate", "multi_generate", "resize_to_iab"] = "generate"
    reference_type: Literal["url", "creative input", "None"] = "None"
    target_dimensions: Optional[str] = None  # For resize operations (e.g., "1024x1024")
    reference_url: Optional[str] = None
    title: str
    explanation: str  # Detailed user-friendly explanation of what the agent will do and why
    description: Optional[str] = None  # Additional technical context about the decision
    iab_sizes: Optional[List[str]] = None  # For resize_to_iab operations, specific sizes to generate (e.g., ["970x250", "300x250"])

# ============================================================================
# FEEDBACK AND SESSION MANAGEMENT MODELS
# ============================================================================

class FeedbackType(str, Enum):
    THUMBS_UP = "thumbs_up"
    THUMBS_DOWN = "thumbs_down"
    DETAILED = "detailed"

class VotingData(BaseModel):
    """Separate voting data model (following Arlo pattern)"""
    query_id: str
    user_id: str
    session_id: str
    vote: int = Field(ge=-1, le=1)  # -1 (down), 0 (neutral), 1 (up)
    timestamp: datetime

class FeedbackData(BaseModel):
    """Comprehensive feedback data model"""
    query_id: str
    user_id: str
    session_id: str
    feedback_type: FeedbackType
    feedback_text: str  
    vote: int = Field(0, ge=-1, le=1)  # -1 (down), 0 (neutral), 1 (up)
    timestamp: datetime

class AgentExecutionStep(BaseModel):
    """Individual agent execution step details"""
    agent_name: str
    step_type: Literal["intent_detection", "search_planning", "search_execution", "agent_processing", "response_generation"]
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_ms: Optional[int] = None
    input_prompt: str
    output_response: str
    model_used: str
    tokens_used: Optional[Dict[str, int]] = Field(default_factory=dict)  # {"input": 100, "output": 200, "total": 300}
    success: bool = True
    error_message: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict)

class QueryExecutionData(BaseModel):
    """Complete execution data for a single query"""
    query_id: str
    user_id: str
    session_id: str
    original_query: str
    enhanced_query: Optional[str] = None
    intent_detected: Optional[str] = None
    start_time: datetime
    end_time: Optional[datetime] = None
    total_duration_ms: Optional[int] = None
    execution_steps: List[AgentExecutionStep] = Field(default_factory=list)
    final_response: str
    agents_used: List[str] = Field(default_factory=list)
    total_tokens_used: Optional[Dict[str, int]] = Field(default_factory=dict)
    search_results_count: Optional[int] = None
    creative_data_used: Optional[List[str]] = Field(default_factory=list)  # MD5 hashes of creatives used
    success: bool = True
    error_details: Optional[str] = None
    related_queries: Optional[List[str]] = Field(default_factory=list)  # Related queries for session continuity

class SessionMetadata(BaseModel):
    """Session-level metadata and management"""
    session_id: str
    user_id: str
    session_name: str  # Auto-generated or user-defined
    creation_time: datetime
    last_activity_time: datetime
    total_queries: int = 0
    query_ids: List[str] = Field(default_factory=list)
    session_summary: Optional[str] = None  # AI-generated summary
    total_tokens_used: Optional[Dict[str, int]] = Field(default_factory=dict)
    feedback_count: int = 0
    positive_feedback_count: int = 0
    negative_feedback_count: int = 0

class SessionTopicAnalysis(BaseModel):
    """Analysis of session topics for auto-naming"""
    primary_topics: List[str] = Field(default_factory=list)
    secondary_topics: List[str] = Field(default_factory=list)
    suggested_name: str
    confidence_score: float = Field(ge=0.0, le=1.0)
    reasoning: str


# Targeting Configuration Models
class TargetingConfig(BaseModel):
    """Targeting configuration data structure"""
    age_range: List[str] = Field(default_factory=list)
    gender: List[str] = Field(default_factory=list)
    income_level: List[str] = Field(default_factory=list)
    location: List[str] = Field(default_factory=list)
    interests: List[str] = Field(default_factory=list)
    behavioral_data: List[str] = Field(default_factory=list)

class TargetingConfigurationCreate(BaseModel):
    """Request model for creating a targeting configuration"""
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    targeting_config: TargetingConfig

class TargetingConfigurationUpdate(BaseModel):
    """Request model for updating a targeting configuration"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    targeting_config: Optional[TargetingConfig] = None

class TargetingConfigurationResponse(BaseModel):
    """Response model for targeting configuration"""
    id: str
    name: str
    description: Optional[str] = None
    targeting_config: TargetingConfig
    user_id: str
    created_at: datetime
    updated_at: datetime


# New models for enhanced insertion order and campaign management

class PlacementUpdateRequest(BaseModel):
    """Request model for updating placements"""
    id: Optional[str] = Field(None, description="Placement ID (for updates)")
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    convert_to_campaign: Optional[bool] = Field(None, description="Flag to convert placement into individual campaign")
    impressions_booked: Optional[int] = Field(None, ge=0)
    impressions_delivered: Optional[int] = Field(None, ge=0)
    clicks: Optional[int] = Field(None, ge=0)
    ctr: Optional[float] = Field(None, ge=0.0)
    budget: Optional[float] = Field(None, ge=0.0)
    cpm: Optional[float] = Field(None, ge=0.0)
    cpc: Optional[float] = Field(None, ge=0.0)
    targeting_config: Optional[dict] = None
    status: Optional[str] = Field(None, description="Placement status")

class InsertionOrderUpdateRequest(BaseModel):
    """Request model for updating insertion orders"""
    # Insertion order fields (matching database schema)
    order_no: Optional[str] = Field(None, min_length=1, max_length=255)
    brand: Optional[str] = Field(None, max_length=255)
    campaign_name: Optional[str] = Field(None, min_length=1, max_length=255)
    customer_approver: Optional[str] = Field(None, max_length=255)
    customer_approver_email: Optional[str] = Field(None, max_length=255)
    sales_owner: Optional[str] = Field(None, max_length=255)
    sales_owner_email: Optional[str] = Field(None, max_length=255)
    fulfillment_owner: Optional[str] = Field(None, max_length=255)
    fulfillment_owner_email: Optional[str] = Field(None, max_length=255)
    objective_description: Optional[str] = None
    status: Optional[str] = Field(None, description="Status: draft, created, pending_approval, approved, rejected, in_flight, completed")
    workspace_type: Optional[str] = Field(None, description="Workspace type: google_drive or salesforce")
    creative_inspiration_id: Optional[str] = Field(None, max_length=255)
    io_pdf_id: Optional[str] = Field(None, max_length=255)
    media_plan_id: Optional[str] = Field(None, max_length=255)

    # Placement updates
    placements: Optional[List[PlacementUpdateRequest]] = Field(None, description="List of placement updates")

    # Metadata (not stored in insertion_orders table)
    update_reason: Optional[str] = Field(None, description="Reason for the update")
    updated_by: Optional[str] = Field(None, description="Who is making the update")


class CampaignPlacementCreateRequest(BaseModel):
    """Request model for creating campaign placements (matches campaign_placements table)"""
    flight_id: str = Field(..., description="Flight ID for this placement")
    start_date: date
    end_date: date
    impressions_booked: int = Field(0, ge=0)
    impressions_delivered: int = Field(0, ge=0)
    booked_clicks: int = Field(0, ge=0)
    delivered_clicks: int = Field(0, ge=0)
    ctr: float = Field(0.0, ge=0)
    budget: float = Field(..., gt=0)
    cpm: float = Field(0.0, ge=0)
    cpc: float = Field(0.0, ge=0)

class PlacementCreateRequest(BaseModel):
    """Request model for creating placements (matches placements table)"""
    name: str = Field(..., min_length=1, max_length=255)
    destination: str = Field(..., min_length=1, max_length=255)
    start_date: date
    end_date: date
    convert_to_campaign: Optional[bool] = Field(False, description="Flag to convert placement into individual campaign")
    impressions_booked: int = Field(..., ge=0)
    clicks: int = Field(..., ge=0)
    budget: float = Field(..., gt=0)
    cpm: Optional[float] = Field(None, ge=0)
    cpc: Optional[float] = Field(None, ge=0)
    targeting_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    status: Optional[str] = Field("draft", description="Placement status")


class CampaignPlacementRequest(BaseModel):
    """Request model for creating campaign placements (body only)"""
    placements: List[CampaignPlacementCreateRequest] = Field(..., min_items=1, description="List of campaign placements")

class CampaignCreateRequest(BaseModel):
    """Request model for creating campaigns with placements (legacy)"""
    name: str = Field(..., min_length=1, max_length=255)
    insertion_order_id: str = Field(..., description="Insertion order ID to associate with this campaign")
    status: Optional[str] = Field("shell_created", description="Campaign status: shell_created, live, paused, completed")
    placements: List[PlacementCreateRequest] = Field(..., min_items=1, description="List of placements for the campaign")


class PlacementUpdateRequest(BaseModel):
    """Request model for updating placements"""
    id: Optional[str] = Field(None, description="Placement ID for updates")
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    destination: Optional[str] = Field(None, min_length=1, max_length=255)
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    convert_to_campaign: Optional[bool] = Field(None, description="Flag to convert placement into individual campaign")
    impressions_booked: Optional[int] = Field(None, ge=0)
    clicks: Optional[int] = Field(None, ge=0)
    budget: Optional[float] = Field(None, gt=0)
    cpm: Optional[float] = Field(None, ge=0)
    cpc: Optional[float] = Field(None, ge=0)
    targeting_config: Optional[Dict[str, Any]] = None
    status: Optional[str] = Field(None, description="Placement status")


class CampaignUpdateRequest(BaseModel):
    """Request model for updating campaigns"""
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    status: Optional[str] = Field(None, description="Campaign status: shell_created, live, paused, completed")
    placements: Optional[List[PlacementUpdateRequest]] = Field(None, description="List of placement updates")
    update_reason: Optional[str] = Field(None, description="Reason for the update")
    updated_by: Optional[str] = Field(None, description="Who is making the update")


class CampaignResponse(BaseModel):
    """Response model for campaign operations"""
    id: str
    name: str
    status: str
    created_at: datetime
    updated_at: datetime
    placement_count: int
    total_budget: float


class InsertionOrderUpdateResponse(BaseModel):
    """Response model for insertion order updates"""
    id: str
    order_number: str
    previous_status: Optional[str]
    new_status: str
    updated_fields: List[str]
    success: bool
    message: str
    salesforce_io_id: Optional[str] = Field(None, description="Salesforce IO ID if source is salesforce")
    updated_at: datetime

class TargetingConfigurationListResponse(BaseModel):
    """Response model for listing targeting configurations"""
    configurations: List[TargetingConfigurationResponse]
    total_count: int
