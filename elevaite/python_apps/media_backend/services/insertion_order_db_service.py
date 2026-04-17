import os
import logging
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from contextlib import contextmanager

from db_connector import DatabaseConnector
from database_models import InsertionOrderModel, CampaignModel, PlacementModel, StatusChangeModel
from insertion_order_models import OrderGenerationRequest, PlacementModel as PlacementRequestModel

logger = logging.getLogger(__name__)

def parse_date_string(date_str):
    """
    Parse date string in multiple formats and return a date object

    Supported formats (in order of priority):
    - MM-DD-YYYY (US format) - Primary format based on your usage
    - YYYY-MM-DD (ISO format)
    - MM/DD/YYYY (US format with slashes)
    - YYYY/MM/DD (ISO format with slashes)
    - DD-MM-YYYY (European format)
    - DD/MM/YYYY (European format with slashes)
    """
    if not date_str or not isinstance(date_str, str):
        return None

    # List of date formats to try (prioritizing MM-DD-YYYY based on your usage)
    date_formats = [
        '%m-%d-%Y',    # 07-01-2025 (US format - your primary format)
        '%Y-%m-%d',    # 2025-07-01 (ISO format)
        '%m/%d/%Y',    # 07/01/2025 (US format with slashes)
        '%Y/%m/%d',    # 2025/07/01 (ISO format with slashes)
        '%d-%m-%Y',    # 01-07-2025 (European format)
        '%d/%m/%Y',    # 01/07/2025 (European format with slashes)
    ]

    for date_format in date_formats:
        try:
            return datetime.strptime(date_str, date_format).date()
        except ValueError:
            continue

    # If none of the formats work, raise an error with helpful message
    raise ValueError(f"Unable to parse date '{date_str}'. Supported formats: MM-DD-YYYY, YYYY-MM-DD, MM/DD/YYYY, YYYY/MM/DD, DD-MM-YYYY, DD/MM/YYYY")

class InsertionOrderDatabaseService:
    """Service for managing insertion order database operations"""
    
    def __init__(self):
        """Initialize the database service"""
        self.db_connector = DatabaseConnector()
        
    @contextmanager
    def get_db_session(self):
        """Context manager for database sessions"""
        session = self.db_connector.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    def create_insertion_order_record(
        self,
        request: OrderGenerationRequest,
        response_data: Dict[str, Any]
    ) -> str:
        """
        Create insertion order record with proper mapping tables

        Args:
            request: The original insertion order request
            response_data: Response data from the insertion order creation

        Returns:
            str: The UUID of the created insertion order
        """
        try:
            with self.get_db_session() as session:
                # Determine workspace type based on request
                workspace_type = 'salesforce' if hasattr(request, 'SalesforceAccount') and request.SalesforceAccount else 'google_drive'

                # Create insertion order record
                insertion_order = InsertionOrderModel(
                    order_no=request.OrderNo,
                    brand=request.Brand,
                    campaign_name=request.CampaignName,
                    customer_approver=request.CustomerApprover,
                    customer_approver_email=request.CustomerApproverEmail,
                    sales_owner=request.SalesOwner,
                    sales_owner_email=request.SalesOwnerEmail,
                    fulfillment_owner=request.FulfillmentOwner,
                    fulfillment_owner_email=request.FulfillmentOwnerEmail,
                    objective_description=request.ObjectiveDetails.Description,
                    status='draft',
                    workspace_type=workspace_type,
                    # Store PDF and creative references in new fields
                    io_pdf_id=response_data.get('pdf_file_id'),
                    creative_inspiration_id=request.CreativeInspirationLink,
                    media_plan_id=response_data.get('media_plan_pdf_id'),
                    raw_data={
                        'request_data': request.dict(),
                        'response_data': response_data,
                        'workspace_type': workspace_type
                    }
                )

                session.add(insertion_order)
                session.flush()  # Get the ID

                # Create workspace-specific mapping records
                if workspace_type == 'google_drive':
                    self._create_google_drive_mapping(session, insertion_order.id, response_data)
                # Note: Salesforce mapping will be created later after we get the Salesforce IO ID

                # Create placement records (linked to insertion order)
                self._create_placement_records(session, insertion_order.id, request.Placement)

                # Create initial status change record
                self._create_status_change_record(
                    session,
                    insertion_order.id,
                    None,
                    'draft',
                    'System',
                    'Insertion order created'
                )

                session.commit()
                logger.info(f"Created insertion order record: {insertion_order.id} for order {request.OrderNo} with workspace type: {workspace_type}")
                return str(insertion_order.id)

        except SQLAlchemyError as e:
            logger.error(f"Database error creating insertion order record: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error creating insertion order record: {e}")
            raise
    
    def _create_campaign_record(
        self, 
        session: Session, 
        insertion_order_id: str, 
        request: OrderGenerationRequest
    ) -> CampaignModel:
        """Create campaign record from request data"""
        
        # Calculate campaign totals from placements
        total_budget = sum(p.Budget.Amount for p in request.Placement)
        total_impressions = sum(p.Metrics.Impressions for p in request.Placement)
        total_clicks = sum(p.Metrics.Clicks for p in request.Placement)
        
        # Get date range
        start_dates = [p.StartDate for p in request.Placement if p.StartDate]
        end_dates = [p.EndDate for p in request.Placement if p.EndDate]
        
        campaign_start = min(start_dates) if start_dates else None
        campaign_end = max(end_dates) if end_dates else None
        
        # Convert string dates to date objects if needed
        if campaign_start and isinstance(campaign_start, str):
            campaign_start = parse_date_string(campaign_start)
        if campaign_end and isinstance(campaign_end, str):
            campaign_end = parse_date_string(campaign_end)
        
        campaign = CampaignModel(
            insertion_order_id=insertion_order_id,
            name=request.CampaignName,
            start_date=campaign_start,
            end_date=campaign_end,
            impressions_booked=total_impressions,
            budget=total_budget,
            status='created'
        )
        
        session.add(campaign)
        session.flush()
        return campaign
    
    def _create_placement_records(
        self, 
        session: Session, 
        campaign_id: str, 
        placements: List[PlacementRequestModel]
    ):
        """Create placement records from request data"""
        
        for placement in placements:
            # Convert string dates to date objects if needed
            start_date = placement.StartDate
            end_date = placement.EndDate

            if isinstance(start_date, str):
                start_date = parse_date_string(start_date)
            if isinstance(end_date, str):
                end_date = parse_date_string(end_date)
            
            # Prepare targeting configuration
            targeting_config = {}
            
            # Handle new targeting configuration format
            if hasattr(placement, 'new_targeting_configuration') and placement.new_targeting_configuration:
                targeting_config = placement.new_targeting_configuration.dict()
            elif hasattr(placement, 'TargetingSuggestions') and placement.TargetingSuggestions:
                # Convert legacy format
                targeting_config = {
                    'demographics': placement.TargetingSuggestions.Demographics or [],
                    'interests': placement.TargetingSuggestions.Interests or [],
                    'keywords': placement.TargetingSuggestions.Keywords or [],
                    'audience_segments': placement.TargetingSuggestions.AudienceSegments or [],
                    'device_targeting': placement.TargetingSuggestions.DeviceTargeting or [],
                    'age_range': placement.TargetingSuggestions.age_range,
                    'gender': placement.TargetingSuggestions.gender,
                    'income_level': placement.TargetingSuggestions.income_level,
                    'location': placement.TargetingSuggestions.location,
                    'behavioral_data': placement.TargetingSuggestions.behavioral_data
                }
            
            placement_record = PlacementModel(
                campaign_id=campaign_id,
                name=placement.Name,
                destination=placement.Destination,
                start_date=start_date,
                end_date=end_date,
                impressions_booked=placement.Metrics.Impressions,
                clicks=placement.Metrics.Clicks,
                budget=placement.Budget.Amount,
                cpm=placement.BidRate.CPM,
                cpc=placement.BidRate.CPC,
                targeting_config=targeting_config,
                status='created'
            )
            
            session.add(placement_record)
    
    def _create_status_change_record(
        self, 
        session: Session, 
        insertion_order_id: str, 
        previous_status: Optional[str], 
        new_status: str,
        changed_by: str,
        reason: Optional[str] = None
    ):
        """Create a status change record"""
        
        status_change = StatusChangeModel(
            insertion_order_id=insertion_order_id,
            previous_status=previous_status,
            new_status=new_status,
            changed_by=changed_by,
            reason=reason
        )
        
        session.add(status_change)
    
    def update_insertion_order_status(
        self, 
        order_id: str, 
        new_status: str, 
        changed_by: str, 
        reason: Optional[str] = None
    ) -> bool:
        """
        Update insertion order status and create status change record
        
        Args:
            order_id: UUID of the insertion order
            new_status: New status value
            changed_by: Who made the change
            reason: Optional reason for the change
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            with self.get_db_session() as session:
                # Get current insertion order
                insertion_order = session.query(InsertionOrderModel).filter(
                    InsertionOrderModel.id == order_id
                ).first()
                
                if not insertion_order:
                    logger.error(f"Insertion order not found: {order_id}")
                    return False
                
                previous_status = insertion_order.status
                
                # Update status
                insertion_order.status = new_status
                
                # Status change timestamp is handled by the status_changes table
                # No need to set individual timestamp fields on the insertion order
                
                # Create status change record
                self._create_status_change_record(
                    session, order_id, previous_status, new_status, changed_by, reason
                )
                
                logger.info(f"Updated insertion order {order_id} status from {previous_status} to {new_status}")
                return True
                
        except SQLAlchemyError as e:
            logger.error(f"Database error updating insertion order status: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error updating insertion order status: {e}")
            return False
    
    def update_insertion_order_fields(
        self,
        order_id: str,
        update_data: Dict[str, Any],
        updated_by: str,
        reason: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update multiple fields of an insertion order

        Args:
            order_id: UUID of the insertion order
            update_data: Dictionary of fields to update
            updated_by: Who is making the update
            reason: Optional reason for the update

        Returns:
            Dict containing update results
        """
        try:
            with self.get_db_session() as session:
                # Get current insertion order
                insertion_order = session.query(InsertionOrderModel).filter(
                    InsertionOrderModel.id == order_id
                ).first()

                if not insertion_order:
                    logger.error(f"Insertion order not found: {order_id}")
                    return {"success": False, "error": "Insertion order not found"}

                previous_values = {}
                updated_fields = []

                # Track changes and update fields
                for field, value in update_data.items():
                    if hasattr(insertion_order, field) and value is not None:
                        previous_values[field] = getattr(insertion_order, field)
                        setattr(insertion_order, field, value)
                        updated_fields.append(field)

                # Handle special status updates
                if 'status' in update_data or 'approval_status' in update_data:
                    new_status = update_data.get('status') or update_data.get('approval_status')
                    if new_status:
                        previous_status = insertion_order.status
                        insertion_order.status = new_status

                        # Status change timestamp is handled by the status_changes table
                        # No need to set individual timestamp fields on the insertion order

                        # Create status change record
                        self._create_status_change_record(
                            session, order_id, previous_status, new_status, updated_by, reason
                        )

                session.commit()

                logger.info(f"Updated insertion order {order_id} fields: {updated_fields}")
                return {
                    "success": True,
                    "updated_fields": updated_fields,
                    "previous_values": previous_values,
                    "order_id": order_id
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error updating insertion order: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error updating insertion order: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def update_placement(
        self,
        placement_id: Optional[str],
        insertion_order_id: str,
        placement_data: Dict[str, Any],
        updated_by: str
    ) -> Dict[str, Any]:
        """
        Update an existing placement or create a new one if placement_id is None

        Args:
            placement_id: UUID of the placement to update (None for new placement)
            insertion_order_id: UUID of the insertion order
            placement_data: Dictionary of placement fields to update
            updated_by: Who is making the update

        Returns:
            Dict containing update results
        """
        try:
            with self.get_db_session() as session:
                if placement_id:
                    # Update existing placement
                    placement = session.query(PlacementModel).filter(
                        PlacementModel.id == placement_id
                    ).first()

                    if not placement:
                        logger.error(f"Placement not found: {placement_id}")
                        return {"success": False, "error": "Placement not found"}

                    updated_fields = []

                    # Update placement fields
                    for field, value in placement_data.items():
                        if hasattr(placement, field) and value is not None:
                            setattr(placement, field, value)
                            updated_fields.append(field)

                    session.commit()

                    logger.info(f"Updated placement {placement_id} fields: {updated_fields}")
                    return {
                        "success": True,
                        "placement_id": placement_id,
                        "updated_fields": updated_fields,
                        "action": "updated"
                    }
                else:
                    # Create new placement
                    placement = PlacementModel(
                        insertion_order_id=insertion_order_id,
                        **placement_data
                    )

                    session.add(placement)
                    session.flush()  # Get the ID

                    session.commit()

                    logger.info(f"Created new placement {placement.id} for insertion order {insertion_order_id}")
                    return {
                        "success": True,
                        "placement_id": str(placement.id),
                        "updated_fields": list(placement_data.keys()),
                        "action": "created"
                    }

        except SQLAlchemyError as e:
            logger.error(f"Database error updating placement: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error updating placement: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def get_insertion_order(self, order_id: str) -> Optional[Dict[str, Any]]:
        """
        Get insertion order with all related data

        Args:
            order_id: UUID of the insertion order
            
        Returns:
            Dict containing insertion order data or None if not found
        """
        try:
            with self.get_db_session() as session:
                insertion_order = session.query(InsertionOrderModel).filter(
                    InsertionOrderModel.id == order_id
                ).first()
                
                if not insertion_order:
                    return None
                
                # Convert to dictionary with relationships
                result = {
                    'id': str(insertion_order.id),
                    'order_no': insertion_order.order_no,
                    'brand': insertion_order.brand,
                    'campaign_name': insertion_order.campaign_name,
                    'customer_approver': insertion_order.customer_approver,
                    'customer_approver_email': insertion_order.customer_approver_email,
                    'sales_owner': insertion_order.sales_owner,
                    'sales_owner_email': insertion_order.sales_owner_email,
                    'fulfillment_owner': insertion_order.fulfillment_owner,
                    'fulfillment_owner_email': insertion_order.fulfillment_owner_email,
                    'objective_description': insertion_order.objective_description,
                    'status': insertion_order.status,
                    'created_at': insertion_order.created_at.isoformat() if insertion_order.created_at else None,
                    'workspace_type': insertion_order.workspace_type,
                    'creative_inspiration_id': insertion_order.creative_inspiration_id,
                    'io_pdf_id': insertion_order.io_pdf_id,
                    'media_plan_id': insertion_order.media_plan_id,
                    'raw_data': insertion_order.raw_data,
                    'campaigns': [],
                    'status_changes': []
                }
                
                # Add status changes
                for status_change in insertion_order.status_changes:
                    status_change_data = {
                        'id': str(status_change.id),
                        'previous_status': status_change.previous_status,
                        'new_status': status_change.new_status,
                        'changed_at': status_change.changed_at.isoformat() if status_change.changed_at else None,
                        'changed_by': status_change.changed_by,
                        'reason': status_change.reason
                    }
                    result['status_changes'].append(status_change_data)
                
                return result
                
        except SQLAlchemyError as e:
            logger.error(f"Database error getting insertion order: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting insertion order: {e}")
            return None

    def _create_salesforce_mapping(self, session: Session, insertion_order_id: str, request: OrderGenerationRequest, salesforce_io_id: str = None):
        """Create Salesforce mapping record"""
        from database_models import InsertionOrderSalesforceMapping

        mapping = InsertionOrderSalesforceMapping(
            insertion_order_id=insertion_order_id,
            salesforce_io_id=salesforce_io_id,  # The actual Salesforce insertion order ID
            salesforce_account_id=getattr(request, 'SalesforceAccount', None),
            salesforce_opportunity_id=getattr(request, 'SalesforceOpportunityId', None)
        )
        session.add(mapping)
        logger.info(f"Created Salesforce mapping for insertion order: {insertion_order_id} -> Salesforce IO: {salesforce_io_id}")

    def create_salesforce_mapping_after_creation(self, insertion_order_id: str, salesforce_io_id: str, request: OrderGenerationRequest):
        """Create Salesforce mapping after getting the Salesforce insertion order ID"""
        try:
            with self.get_db_session() as session:
                self._create_salesforce_mapping(session, insertion_order_id, request, salesforce_io_id)
                session.commit()
                logger.info(f"Successfully created Salesforce mapping: {insertion_order_id} -> {salesforce_io_id}")
        except Exception as e:
            logger.error(f"Error creating Salesforce mapping: {e}")
            raise

    def _create_google_drive_mapping(self, session: Session, insertion_order_id: str, response_data: Dict[str, Any]):
        """Create Google Drive mapping record"""
        from database_models import InsertionOrderGoogleDriveMapping

        mapping = InsertionOrderGoogleDriveMapping(
            insertion_order_id=insertion_order_id,
            drive_folder_id=response_data.get('campaign_folder_id'),
            sheet_id=response_data.get('sheet_id'),
            pdf_file_id=response_data.get('pdf_file_id')
        )
        session.add(mapping)
        logger.info(f"Created Google Drive mapping for insertion order: {insertion_order_id}")

    def _create_campaign_record_simplified(self, session: Session, insertion_order_id: str, request: OrderGenerationRequest):
        """Create campaign record using simplified schema"""
        from database_models import CampaignModel

        campaign = CampaignModel(
            name=request.CampaignName,
            status='created'
        )

        session.add(campaign)
        session.flush()
        logger.info(f"Created campaign record: {campaign.id} for insertion order: {insertion_order_id}")
        return campaign

    def _create_campaign_insertion_order_mapping(self, session: Session, campaign_id: str, insertion_order_id: str):
        """Create campaign-insertion order mapping"""
        from database_models import CampaignInsertionOrderMapping

        mapping = CampaignInsertionOrderMapping(
            campaign_id=campaign_id,
            insertion_order_id=insertion_order_id
        )
        session.add(mapping)
        logger.info(f"Created campaign-insertion order mapping: {campaign_id} -> {insertion_order_id}")

    def _create_placement_records(self, session: Session, insertion_order_id: str, placements: List):
        """Create placement records linked to insertion order"""
        from database_models import PlacementModel

        for placement in placements:
            # Convert string dates to date objects if needed
            start_date = placement.StartDate
            end_date = placement.EndDate

            if isinstance(start_date, str):
                start_date = parse_date_string(start_date)
            if isinstance(end_date, str):
                end_date = parse_date_string(end_date)

            # Prepare targeting configuration
            targeting_config = {}

            # Handle new targeting configuration format
            if hasattr(placement, 'new_targeting_configuration') and placement.new_targeting_configuration:
                targeting_config = placement.new_targeting_configuration.dict()
            elif hasattr(placement, 'TargetingSuggestions') and placement.TargetingSuggestions:
                # Convert legacy format
                targeting_config = {
                    'demographics': placement.TargetingSuggestions.Demographics or [],
                    'interests': placement.TargetingSuggestions.Interests or [],
                    'keywords': placement.TargetingSuggestions.Keywords or [],
                    'audience_segments': placement.TargetingSuggestions.AudienceSegments or [],
                    'device_targeting': placement.TargetingSuggestions.DeviceTargeting or [],
                    'age_range': placement.TargetingSuggestions.age_range,
                    'gender': placement.TargetingSuggestions.gender,
                    'income_level': placement.TargetingSuggestions.income_level,
                    'location': placement.TargetingSuggestions.location,
                    'behavioral_data': placement.TargetingSuggestions.behavioral_data
                }

            placement_record = PlacementModel(
                insertion_order_id=insertion_order_id,  # Linked to insertion order
                name=placement.Name,
                destination=placement.Destination,
                start_date=start_date,
                end_date=end_date,
                convert_to_campaign=getattr(placement, 'ConvertToCampaign', False),  # Handle placement-to-campaign conversion
                impressions_booked=placement.Metrics.Impressions,
                impressions_delivered=0,  # Default to 0 for new placements
                clicks=placement.Metrics.Clicks,
                ctr=0.0,  # Will be calculated later
                budget=placement.Budget.Amount,
                cpm=placement.BidRate.CPM,
                cpc=placement.BidRate.CPC,
                targeting_config=targeting_config,
                status='created'
            )

            session.add(placement_record)
            logger.info(f"Created placement record: {placement.Name} for insertion order: {insertion_order_id}")

    def create_campaign_with_placements(
        self,
        campaign_data: Dict[str, Any],
        placements_data: List[Dict[str, Any]],
        insertion_order_id: str
    ) -> Dict[str, Any]:
        """
        Create a new campaign with associated placements and insertion order mapping

        Args:
            campaign_data: Campaign information
            placements_data: List of placement information
            insertion_order_id: Insertion order ID to link to campaign

        Returns:
            Dict containing creation results
        """
        try:
            with self.get_db_session() as session:
                # Create campaign
                campaign = CampaignModel(
                    name=campaign_data['name'],
                    kevel_id=campaign_data.get('kevel_id'),
                    status=campaign_data.get('status', 'work_in_progress')
                )

                session.add(campaign)
                session.flush()  # Get the campaign ID

                # Create campaign-insertion order mapping
                from database_models import CampaignInsertionOrderMapping
                mapping = CampaignInsertionOrderMapping(
                    campaign_id=campaign.id,
                    insertion_order_id=insertion_order_id
                )
                session.add(mapping)

                # Create campaign placements
                created_placements = []
                total_budget = 0.0

                from database_models import CampaignPlacement
                for placement_data in placements_data:
                    placement = CampaignPlacement(
                        campaign_id=campaign.id,
                        flight_id=placement_data['flight_id'],
                        start_date=placement_data['start_date'],
                        end_date=placement_data['end_date'],
                        impressions_booked=placement_data.get('impressions_booked', 0),
                        impressions_delivered=placement_data.get('impressions_delivered', 0),
                        booked_clicks=placement_data.get('booked_clicks', 0),
                        delivered_clicks=placement_data.get('delivered_clicks', 0),
                        ctr=placement_data.get('ctr', 0.0),
                        budget=placement_data['budget'],
                        cpm=placement_data.get('cpm', 0.0),
                        cpc=placement_data.get('cpc', 0.0)
                    )

                    session.add(placement)
                    created_placements.append(placement)
                    total_budget += placement_data['budget']

                session.commit()

                logger.info(f"Created campaign {campaign.id} with {len(created_placements)} placements")
                return {
                    "success": True,
                    "campaign_id": str(campaign.id),
                    "campaign_name": campaign.name,
                    "placement_count": len(created_placements),
                    "total_budget": total_budget
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error creating campaign: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error creating campaign: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def update_campaign(
        self,
        campaign_id: str,
        update_data: Dict[str, Any],
        placements_updates: Optional[List[Dict[str, Any]]] = None,
        updated_by: str = "system"
    ) -> Dict[str, Any]:
        """
        Update campaign and optionally its placements

        Args:
            campaign_id: UUID of the campaign
            update_data: Campaign fields to update
            placements_updates: Optional list of placement updates
            updated_by: Who is making the update

        Returns:
            Dict containing update results
        """
        try:
            with self.get_db_session() as session:
                # Get campaign
                campaign = session.query(CampaignModel).filter(
                    CampaignModel.id == campaign_id
                ).first()

                if not campaign:
                    logger.error(f"Campaign not found: {campaign_id}")
                    return {"success": False, "error": "Campaign not found"}

                updated_fields = []

                # Update campaign fields
                for field, value in update_data.items():
                    if hasattr(campaign, field) and value is not None:
                        setattr(campaign, field, value)
                        updated_fields.append(field)

                # Update placements if provided
                placement_updates_count = 0
                if placements_updates:
                    for placement_update in placements_updates:
                        placement_id = placement_update.get('id')
                        if placement_id:
                            # Update existing placement
                            placement = session.query(PlacementModel).filter(
                                PlacementModel.id == placement_id
                            ).first()

                            if placement:
                                for field, value in placement_update.items():
                                    if field != 'id' and hasattr(placement, field) and value is not None:
                                        setattr(placement, field, value)
                                placement_updates_count += 1

                session.commit()

                logger.info(f"Updated campaign {campaign_id}, fields: {updated_fields}, placements: {placement_updates_count}")
                return {
                    "success": True,
                    "campaign_id": campaign_id,
                    "updated_fields": updated_fields,
                    "placement_updates": placement_updates_count
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error updating campaign: {e}")
            return {"success": False, "error": f"Database error: {str(e)}"}
        except Exception as e:
            logger.error(f"Unexpected error updating campaign: {e}")
            return {"success": False, "error": f"Unexpected error: {str(e)}"}

    def get_campaign(self, campaign_id: str) -> Optional[Dict[str, Any]]:
        """
        Get campaign with placement information

        Args:
            campaign_id: UUID of the campaign

        Returns:
            Campaign data with placements or None if not found
        """
        try:
            with self.get_db_session() as session:
                campaign = session.query(CampaignModel).filter(
                    CampaignModel.id == campaign_id
                ).first()

                if not campaign:
                    return None

                # Get associated placements (both insertion order linked and standalone)
                placements = session.query(PlacementModel).filter(
                    PlacementModel.insertion_order_id == None  # Campaign placements
                ).all()

                total_budget = sum(float(p.budget) for p in placements)

                return {
                    "id": str(campaign.id),
                    "name": campaign.name,
                    "status": campaign.status,
                    "created_at": campaign.created_at.isoformat(),
                    "updated_at": campaign.updated_at.isoformat(),
                    "placement_count": len(placements),
                    "total_budget": total_budget,
                    "placements": [
                        {
                            "id": str(p.id),
                            "name": p.name,
                            "destination": p.destination,
                            "start_date": p.start_date.isoformat() if p.start_date else None,
                            "end_date": p.end_date.isoformat() if p.end_date else None,
                            "budget": float(p.budget),
                            "status": p.status
                        } for p in placements
                    ]
                }

        except SQLAlchemyError as e:
            logger.error(f"Database error getting campaign: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting campaign: {e}")
            return None
