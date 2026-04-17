import os
import logging
from datetime import datetime
from typing import Dict, Any
from fastapi import HTTPException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

from oauth_handler import get_oauth_credentials
from insertion_order_models import OrderGenerationRequest, OrderGenerationResponse, PDFFileDetails
from .google_drive import GoogleDriveService
from .pdf_generator import PDFGenerator
from .insertion_order_db_service import InsertionOrderDatabaseService

logger = logging.getLogger(__name__)

class InsertionOrderService:
    def __init__(self):
        """Initialize the service with OAuth credentials"""
        self.oauth_credentials = None
        self.drive_service = None
        self.pdf_generator = None
        self.db_service = None
        self._initialize_services()

    def _initialize_services(self):
        """Initialize Google services with OAuth credentials"""
        try:
            self.oauth_credentials = get_oauth_credentials()
            if not self.oauth_credentials:
                raise Exception("OAuth credentials not found. Please ensure token.pickle is available.")

            self.drive_service = GoogleDriveService(credentials=self.oauth_credentials)
            self.pdf_generator = PDFGenerator(credentials=self.oauth_credentials)
            self.db_service = InsertionOrderDatabaseService()
            logger.info("Insertion Order services initialized with OAuth credentials")
        except Exception as e:
            logger.error(f"Error initializing services with OAuth: {str(e)}")
            raise

    def refresh_credentials_if_needed(self):
        """Refresh OAuth credentials if they are expired or about to expire"""
        try:
            # Get fresh credentials
            fresh_credentials = get_oauth_credentials()
            if fresh_credentials and fresh_credentials != self.oauth_credentials:
                logger.info("Refreshing OAuth credentials for services")
                self.oauth_credentials = fresh_credentials

                # Update services with new credentials
                if self.drive_service:
                    self.drive_service.update_credentials(fresh_credentials)
                if self.pdf_generator:
                    self.pdf_generator.update_credentials(fresh_credentials)

                logger.info("OAuth credentials refreshed successfully")
                return True
            return False
        except Exception as e:
            logger.error(f"Error refreshing credentials: {str(e)}")
            return False

    def _validate_configuration(self):
        """Validate that all required configuration is present"""
        base_folder_id = os.getenv("BASE_GOOGLE_DRIVE_FOLDER_ID")
        sheet_template_id = os.getenv("GOOGLE_SHEET_TEMPLATE_ID")
        pdf_template_id = os.getenv("PDF_GENERATION_TEMPLATE_ID")

        if not base_folder_id:
            raise HTTPException(status_code=500, detail="BASE_GOOGLE_DRIVE_FOLDER_ID not configured")

        if not sheet_template_id:
            raise HTTPException(status_code=500, detail="GOOGLE_SHEET_TEMPLATE_ID not configured")

        if not pdf_template_id:
            raise HTTPException(status_code=500, detail="PDF_GENERATION_TEMPLATE_ID not configured")

    def _share_pdf_with_stakeholders(self, file_id: str, stakeholder_emails: list, file_type: str = "PDF"):
        """
        Share PDF with iopex.com domain and stakeholders

        Args:
            file_id: The Google Drive file ID to share
            stakeholder_emails: List of stakeholder email addresses
            file_type: Type of file being shared (for logging)
        """
        try:
            # Share with iopex.com domain (anyone with link from domain can view)
            self.drive_service.share_file_with_domain(
                file_id=file_id,
                domain="iopex.com",
                role="reader"
            )
            logger.info(f"{file_type} {file_id} shared with iopex.com domain (link required)")

            # Still share with stakeholders individually for writer access
            for email in stakeholder_emails:
                try:
                    self.drive_service.share_file(
                        file_id=file_id,
                        email=email,
                        role='writer'
                    )
                except Exception as share_error:
                    logger.warning(f"Failed to share {file_type} with {email}: {share_error}")
            logger.info(f"{file_type} shared with stakeholders: {', '.join(stakeholder_emails)}")

        except Exception as e:
            logger.error(f"Error sharing {file_type} {file_id}: {str(e)}")
            raise

    async def create_insertion_order(self, request: OrderGenerationRequest) -> OrderGenerationResponse:
        """
        Create a complete insertion order with folder, sheet, and PDF
        """
        try:
            # Refresh credentials if needed before processing
            self.refresh_credentials_if_needed()

            # Validate configuration
            self._validate_configuration()

            # Get environment variables
            base_folder_id = os.getenv("BASE_GOOGLE_DRIVE_FOLDER_ID")
            sheet_template_id = os.getenv("GOOGLE_SHEET_TEMPLATE_ID")
            pdf_template_id = os.getenv("PDF_GENERATION_TEMPLATE_ID")

            logger.info(f"Creating insertion order for campaign: {request.CampaignName}")
            logger.info(f"Using BASE_GOOGLE_DRIVE_FOLDER_ID: {base_folder_id}")
            logger.info(f"Using PDF_GENERATION_TEMPLATE_ID: {pdf_template_id}")
            logger.info(f"Using GOOGLE_SHEET_TEMPLATE_ID: {sheet_template_id}")

            # Create campaign folder in Google Drive
            campaign_folder = self.drive_service.create_folder(
                f"{request.CampaignName}_{datetime.now().strftime('%Y%m%d')}",
                base_folder_id
            )
            logger.info(f"Created campaign folder: {campaign_folder['id']}")

            # Share campaign folder with all stakeholders
            stakeholder_emails = [
                request.CustomerApproverEmail,
                request.SalesOwnerEmail,
                request.FulfillmentOwnerEmail
            ]
            
            for email in stakeholder_emails:
                self.drive_service.share_file(
                    file_id=campaign_folder['id'],
                    email=email,
                    role='writer'
                )
            logger.info(f"Shared campaign folder with: {', '.join(stakeholder_emails)}")

            # Validate placements
            if not request.Placement:
                raise HTTPException(status_code=400, detail="At least one placement is required")

            # Validate that each placement has either targeting configuration or targeting suggestions
            for i, placement in enumerate(request.Placement):
                if not placement.targeting_configuration_id and not placement.new_targeting_configuration and not placement.TargetingSuggestions:
                    logger.warning(f"Placement {i+1} ({placement.Name}) has no targeting information")

            # Create and populate sheet using template
            sheet_result = self.drive_service.create_sheet_from_template(
                folder_id=campaign_folder['id'],
                sheet_name=f"Order_{request.OrderNo}",
                template_id=sheet_template_id,
                data={
                    'order_number': request.OrderNo,
                    'brand': request.Brand,
                    'campaign_name': request.CampaignName,
                    'customer_approver': request.CustomerApprover,
                    'customer_approver_email': request.CustomerApproverEmail,
                    'sales_owner': request.SalesOwner,
                    'sales_owner_email': request.SalesOwnerEmail,
                    'fulfillment_owner': request.FulfillmentOwner,
                    'fulfillment_owner_email': request.FulfillmentOwnerEmail,
                    'placements': request.Placement,
                    'objective_description': request.ObjectiveDetails.Description
                }
            )
            logger.info(f"Sheet created successfully: {sheet_result['sheet_id']}")

            # Create PDF folder
            pdf_folder = self.drive_service.create_pdf_folder(campaign_folder['id'])
            logger.info(f"PDF folder created: {pdf_folder['id']}")

            # Generate initial PDF
            template_variables = self._prepare_pdf_template_variables(request)
            pdf_result = await self.pdf_generator.generate(
                template_variables=template_variables,
                output_folder_id=pdf_folder['id'],
                filename=f"{request.OrderNo}_v0"
            )
            logger.info(f"PDF generated successfully: {pdf_result['pdf_file_id']}")

            # Share insertion order PDF based on access control settings
            self._share_pdf_with_stakeholders(
                file_id=pdf_result['pdf_file_id'],
                stakeholder_emails=stakeholder_emails,
                file_type="Insertion Order PDF"
            )

            # Generate media plan PDF if content is provided
            media_plan_pdf_result = None
            if request.MediaPlanContent:
                try:
                    media_plan_pdf_result = await self.pdf_generator.generate_media_plan_pdf(
                        media_plan_content=request.MediaPlanContent,
                        output_folder_id=pdf_folder['id'],
                        filename=f"{request.OrderNo}_MediaPlan"
                    )
                    logger.info(f"Media plan PDF generated successfully: {media_plan_pdf_result['pdf_file_id']}")

                    # Share media plan PDF based on access control settings
                    self._share_pdf_with_stakeholders(
                        file_id=media_plan_pdf_result['pdf_file_id'],
                        stakeholder_emails=stakeholder_emails,
                        file_type="Media Plan PDF"
                    )

                except Exception as e:
                    logger.error(f"Failed to generate media plan PDF: {str(e)}")
                    # Don't fail the entire operation if media plan PDF generation fails

            # Prepare response
            response = OrderGenerationResponse(
                status="success",
                message="Order created with initial sheet and PDF",
                campaign_folder_id=campaign_folder['id'],
                campaign_folder_link=campaign_folder['link'],
                sheet_id=sheet_result['sheet_id'],
                sheet_link=sheet_result['sheet_web_view_link'],
                pdf_folder_id=pdf_folder['id'],
                pdf_folder_link=pdf_folder['link'],
                file_details=PDFFileDetails(
                    filename=f"{request.OrderNo}_v0.pdf",
                    pdf_file_id=pdf_result['pdf_file_id'],
                    pdf_web_view_link=pdf_result['pdf_web_view_link']
                ),
                media_plan_pdf_link=media_plan_pdf_result['pdf_web_view_link'] if media_plan_pdf_result else None
            )

            # Save to database
            try:
                response_data = {
                    'campaign_folder_id': campaign_folder['id'],
                    'sheet_id': sheet_result['sheet_id'],
                    'pdf_file_id': pdf_result['pdf_file_id'],
                    'pdf_folder_id': pdf_folder['id'],
                    'media_plan_pdf_id': media_plan_pdf_result['pdf_file_id'] if media_plan_pdf_result else None
                }
                insertion_order_id = self.db_service.create_insertion_order_record(request, response_data)
                logger.info(f"Insertion order saved to database with ID: {insertion_order_id}")
            except Exception as db_error:
                logger.error(f"Failed to save insertion order to database: {db_error}")
                # Don't fail the entire operation if database save fails
                # The insertion order was still created successfully in Google Drive

            logger.info(f"Insertion order created successfully for {request.CampaignName}")
            return response

        except Exception as e:
            logger.error(f"Error creating insertion order: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_salesforce_documentation(self, request: OrderGenerationRequest) -> OrderGenerationResponse:
        """
        Create simplified Google Drive documentation for Salesforce submissions
        - Creates campaign folder
        - Generates PDF only (no spreadsheet)
        - Shares with stakeholders
        """
        try:
            # Refresh credentials if needed before processing
            self.refresh_credentials_if_needed()

            # Validate minimal configuration (no sheet template needed)
            base_folder_id = os.getenv("BASE_GOOGLE_DRIVE_FOLDER_ID")
            pdf_template_id = os.getenv("PDF_GENERATION_TEMPLATE_ID")

            if not base_folder_id:
                raise HTTPException(status_code=500, detail="BASE_GOOGLE_DRIVE_FOLDER_ID not configured")
            if not pdf_template_id:
                raise HTTPException(status_code=500, detail="PDF_GENERATION_TEMPLATE_ID not configured")

            logger.info(f"Creating Salesforce documentation for campaign: {request.CampaignName}")
            logger.info(f"Using BASE_GOOGLE_DRIVE_FOLDER_ID: {base_folder_id}")
            logger.info(f"Using PDF_GENERATION_TEMPLATE_ID: {pdf_template_id}")

            # Create campaign folder in Google Drive
            campaign_folder = self.drive_service.create_folder(
                f"{request.CampaignName}_{datetime.now().strftime('%Y%m%d')}_Salesforce",
                base_folder_id
            )
            logger.info(f"Created Salesforce campaign folder: {campaign_folder['id']}")

            # Share campaign folder with all stakeholders
            stakeholder_emails = [
                request.CustomerApproverEmail,
                request.SalesOwnerEmail,
                request.FulfillmentOwnerEmail
            ]

            for email in stakeholder_emails:
                self.drive_service.share_file(
                    file_id=campaign_folder['id'],
                    email=email,
                    role='writer'
                )
            logger.info(f"Shared Salesforce campaign folder with: {', '.join(stakeholder_emails)}")

            # Validate placements
            if not request.Placement:
                raise HTTPException(status_code=400, detail="At least one placement is required")

            # Create PDF folder
            pdf_folder = self.drive_service.create_pdf_folder(campaign_folder['id'])
            logger.info(f"PDF folder created: {pdf_folder['id']}")

            # Generate PDF (no spreadsheet)
            template_variables = self._prepare_pdf_template_variables(request)
            pdf_result = await self.pdf_generator.generate(
                template_variables=template_variables,
                output_folder_id=pdf_folder['id'],
                filename=f"{request.OrderNo}_Salesforce_v0"
            )
            logger.info(f"Salesforce PDF generated successfully: {pdf_result['pdf_file_id']}")

            # Share Salesforce insertion order PDF based on access control settings
            self._share_pdf_with_stakeholders(
                file_id=pdf_result['pdf_file_id'],
                stakeholder_emails=stakeholder_emails,
                file_type="Salesforce Insertion Order PDF"
            )

            # Generate media plan PDF if content is provided
            media_plan_pdf_result = None
            if request.MediaPlanContent:
                try:
                    media_plan_pdf_result = await self.pdf_generator.generate_media_plan_pdf(
                        media_plan_content=request.MediaPlanContent,
                        output_folder_id=pdf_folder['id'],
                        filename=f"{request.OrderNo}_Salesforce_MediaPlan"
                    )
                    logger.info(f"Salesforce media plan PDF generated successfully: {media_plan_pdf_result['pdf_file_id']}")

                    # Share Salesforce media plan PDF based on access control settings
                    self._share_pdf_with_stakeholders(
                        file_id=media_plan_pdf_result['pdf_file_id'],
                        stakeholder_emails=stakeholder_emails,
                        file_type="Salesforce Media Plan PDF"
                    )

                except Exception as e:
                    logger.error(f"Failed to generate Salesforce media plan PDF: {str(e)}")
                    # Don't fail the entire operation if media plan PDF generation fails

            # Prepare simplified response (no sheet data)
            response = OrderGenerationResponse(
                status="success",
                message="Salesforce documentation created with PDF only",
                campaign_folder_id=campaign_folder['id'],
                campaign_folder_link=campaign_folder['link'],
                sheet_id="salesforce_record",  # Placeholder since no sheet created
                sheet_link="",  # Will be filled with Salesforce URL by caller
                pdf_folder_id=pdf_folder['id'],
                pdf_folder_link=pdf_folder['link'],
                file_details=PDFFileDetails(
                    filename=f"{request.OrderNo}_Salesforce_v0.pdf",
                    pdf_file_id=pdf_result['pdf_file_id'],
                    pdf_web_view_link=pdf_result['pdf_web_view_link']
                ),
                media_plan_pdf_link=media_plan_pdf_result['pdf_web_view_link'] if media_plan_pdf_result else None
            )

            # Save to database
            try:
                response_data = {
                    'campaign_folder_id': campaign_folder['id'],
                    'sheet_id': "salesforce_record",
                    'pdf_file_id': pdf_result['pdf_file_id'],
                    'pdf_folder_id': pdf_folder['id'],
                    'media_plan_pdf_id': media_plan_pdf_result['pdf_file_id'] if media_plan_pdf_result else None
                }
                insertion_order_id = self.db_service.create_insertion_order_record(request, response_data)
                logger.info(f"Salesforce insertion order saved to database with ID: {insertion_order_id}")
            except Exception as db_error:
                logger.error(f"Failed to save Salesforce insertion order to database: {db_error}")
                # Don't fail the entire operation if database save fails

            logger.info(f"Salesforce documentation created successfully for {request.CampaignName}")
            return response

        except Exception as e:
            logger.error(f"Error creating Salesforce documentation: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error creating Salesforce documentation: {str(e)}")

    def _extract_targeting_info(self, placement) -> Dict[str, str]:
        """Extract targeting information from placement using new targeting configuration data"""
        # Default values
        targeting_info = {
            'age_range': 'Not specified',
            'gender': 'Not specified',
            'income_level': 'Not specified',
            'interests': 'Not specified',
            'location': 'Not specified',
            'behavioral_data': 'Not specified'
        }

        # Use targeting configuration data sent from frontend
        if placement.new_targeting_configuration:
            config = placement.new_targeting_configuration
            targeting_info.update({
                'age_range': ', '.join(config.age_range) if config.age_range else 'Not specified',
                'gender': ', '.join(config.gender) if config.gender else 'Not specified',
                'income_level': ', '.join(config.income_level) if config.income_level else 'Not specified',
                'interests': ', '.join(config.interests) if config.interests else 'Not specified',
                'location': ', '.join(config.location) if config.location else 'Not specified',
                'behavioral_data': ', '.join(config.behavioral_data) if config.behavioral_data else 'Not specified'
            })
            logger.info(f"Using targeting configuration data for placement {placement.Name}: {targeting_info}")
        else:
            logger.warning(f"No targeting configuration data found for placement {placement.Name}")

        return targeting_info

    def _prepare_pdf_template_variables(self, request: OrderGenerationRequest) -> Dict[str, Any]:
        """Prepare template variables for PDF generation"""
        # Create detailed placement information for PDF
        placement_details = []
        media_plan_table_rows = []
        total_impressions = 0
        total_clicks = 0
        total_budget = 0

        for i, placement in enumerate(request.Placement, 1):
            # Add to totals
            total_impressions += placement.Metrics.Impressions
            total_clicks += placement.Metrics.Clicks
            total_budget += placement.Budget.Amount

            # Extract targeting information using helper function
            targeting_info = self._extract_targeting_info(placement)

            # Create detailed placement description
            placement_detail = f"""
Placement {i}: {placement.Name}
  Destination: {placement.Destination}
  Duration: {placement.StartDate} - {placement.EndDate}
  Metrics: {placement.Metrics.Impressions:,} impressions, {placement.Metrics.Clicks:,} clicks
  Bid Rate: ${placement.BidRate.CPM} CPM
  CPC: ${placement.BidRate.CPC}
  Budget: ${placement.Budget.Amount:,.2f}
  Target Audience:
    - Age Range: {targeting_info['age_range']}
    - Gender: {targeting_info['gender']}
    - Income Level: {targeting_info['income_level']}
    - Interests: {targeting_info['interests']}
    - Location: {targeting_info['location']}
    - Behavioral Data: {targeting_info['behavioral_data']}
            """.strip()
            placement_details.append(placement_detail)

            # Create table row for media plan table
            targeting_summary = f"{targeting_info['age_range']}, {targeting_info['gender']}, {targeting_info['income_level']}, {targeting_info['location']}, {targeting_info['interests']}, {targeting_info['behavioral_data']}"

            table_row = [
                f"${placement.Budget.Amount:,.2f}",  # budget
                placement.StartDate,  # start date
                placement.EndDate,  # end date
                placement.Name,  # placement name
                placement.Destination,  # placement destination
                targeting_summary,  # targeting
                request.ObjectiveDetails.Description,  # objective description
                f"{placement.Metrics.Impressions:,}",  # target impressions
                f"{placement.Metrics.Clicks:,}",  # target clicks
                f"${placement.BidRate.CPM}",  # cpm
                f"${placement.BidRate.CPC}"  # cpc
            ]
            media_plan_table_rows.append(table_row)

        # Get overall date range
        start_dates = [p.StartDate for p in request.Placement]
        end_dates = [p.EndDate for p in request.Placement]
        earliest_start = min(start_dates) if start_dates else ""
        latest_end = max(end_dates) if end_dates else ""

        # Create media plan table data structure
        media_plan_table = {
            'headers': [
                'Budget', 'Start Date', 'End Date', 'Placement Name', 'Placement Destination',
                'Targeting', 'Objective Description', 'Target Impressions', 'Target Clicks', 'CPM', 'CPC'
            ],
            'rows': media_plan_table_rows
        }

        return {
            'order_number': request.OrderNo,
            'brand': request.Brand,
            'campaign_name': request.CampaignName,
            'customer_approver': request.CustomerApprover,
            'customer_approver_email': request.CustomerApproverEmail,
            'sales_owner': request.SalesOwner,
            'sales_owner_email': request.SalesOwnerEmail,
            'fulfillment_owner': request.FulfillmentOwner,
            'fulfillment_owner_email': request.FulfillmentOwnerEmail,
            'start_date': earliest_start,
            'end_date': latest_end,
            'placement_details': "\n\n".join(placement_details),
            'media_plan_table': media_plan_table,
            'impressions': str(total_impressions),
            'clicks': str(total_clicks),
            'cpm': "Multiple CPM rates (see placement details)",
            'cpc': "Multiple CPC rates (see placement details)",
            'budget_amount': str(total_budget),
            'age_range': "Multiple (see placement details)",
            'gender': "Multiple (see placement details)",
            'income_level': "Multiple (see placement details)",
            'interests': "Multiple (see placement details)",
            'location': "Multiple (see placement details)",
            'audience_segments': "Multiple (see placement details)",
            'device_targeting': "All Devices",
            'objective_description': request.ObjectiveDetails.Description,
            'creative_inspiration_link': request.CreativeInspirationLink or "",
            'generation_date': datetime.now().strftime("%Y-%m-%d")
        }
