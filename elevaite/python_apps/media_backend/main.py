from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from model import (
    InferencePayload, MarkdownRequest,
    TargetingConfigurationCreate, TargetingConfigurationUpdate,
    TargetingConfigurationResponse, TargetingConfigurationListResponse,
    InsertionOrderUpdateRequest, InsertionOrderUpdateResponse,
    CampaignCreateRequest, CampaignPlacementRequest, CampaignUpdateRequest, CampaignResponse
)

from llm_rag_inference import perform_inference
from feedback_endpoints import (
    feedback_endpoints, session_endpoints, query_endpoints, analytics_endpoints,
    FeedbackRequest, VotingRequest, SessionCreateRequest, SessionUpdateRequest
)
from fastapi.responses import StreamingResponse
import json
import re
from datetime import datetime
from io import BytesIO
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
import httpx
import os
import asyncio
from typing import Dict, Any, List
import logging
import uuid
import json
from datetime import datetime, timezone

# Setup logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

async def store_io_message_in_database(session_id: str, user_id: str, message: str):
    """
    Store IO success message directly in the database as a new query and response
    """
    try:
        from db_connector import db_connector
        from database_models import SessionModel, QueryModel

        # Generate a unique query ID for this IO message
        query_id = "queryId_" + str(uuid.uuid4())

        # Get database session
        db = db_connector.get_session()

        try:
            # Check if session exists, create if it doesn't
            session = db.query(SessionModel).filter(SessionModel.session_id == session_id).first()
            if not session:
                session = SessionModel(
                    session_id=session_id,
                    user_id=user_id,
                    session_name="IO Generation Session",
                    creation_time=datetime.now(timezone.utc)
                )
                db.add(session)
                db.flush()  # Flush to get the session in the database

            # Create the query record
            query = QueryModel(
                query_id=query_id,
                session_id=session_id,
                user_id=user_id,
                original_query="Generate Insertion Order",
                start_time=datetime.now(timezone.utc),
                end_time=datetime.now(timezone.utc),
                total_duration_ms=0,  # Instant response
                final_response=message,
                intent_detected="insertion_order",
                agents_used=["insertion_order_generator"],
                success=True
            )

            db.add(query)
            db.commit()

            logger.info(f"Stored IO message directly in database for session {session_id}, query_id {query_id}")

            return query_id

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error storing IO message in database: {e}")
        raise

app = FastAPI()

origins = [
    origin.strip() for origin in os.getenv("ORIGINS_FRONT_END_URLS", "").split(",") if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Insertion Order Service at startup
insertion_order_service = None

try:
    # Add current directory to Python path to help with imports
    import sys
    current_dir = os.path.dirname(os.path.abspath(__file__))
    if current_dir not in sys.path:
        sys.path.insert(0, current_dir)

    from services.insertion_order_service import InsertionOrderService
    insertion_order_service = InsertionOrderService()
    logger.info("Insertion Order Service initialized successfully at startup")
except Exception as e:
    logger.error(f"Failed to initialize Insertion Order Service at startup: {str(e)}")
    logger.warning("Insertion Order Service will be unavailable until this is resolved")

async def download_image(url: str):
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(url, timeout=20.0)
            response.raise_for_status()  # Raise an error for bad responses
            return BytesIO(response.content)  # Return a BytesIO object
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None
async def parse_markdown_table(lines):
    table_data = []

    for line in lines:
        if line.strip() and not all(char in '-|' for char in line.strip()):
            row = [cell.strip() for cell in line.split('|') if cell.strip()]
            processed_row = []
            for cell in row:
                cleaned_cell = cell.replace('**', '').strip()

                # Regex to capture image URL correctly
                img_match = re.search(r'!\[(.*?)\]\((http[^\s)]+)(?:\s+"[^"]*")?\)', cleaned_cell)
                if img_match:
                    _, img_url = img_match.groups()
                    img_url = img_url.strip()  # Clean up the URL
                    logger.info(f"Processing image URL: {img_url}")  # Debug output
                    try:
                        img_data = await download_image(img_url)
                        if img_data:
                            processed_row.append(img_data)
                        else:
                            processed_row.append(Paragraph("Image not available", getSampleStyleSheet()['Normal']))
                    except Exception as e:
                        logger.error(f"Error downloading image: {e}")  # Log the error
                        processed_row.append(Paragraph("Error loading image", getSampleStyleSheet()['Normal']))
                else:
                    processed_row.append(Paragraph(cleaned_cell, getSampleStyleSheet()['Normal']))
            if processed_row:
                table_data.append(processed_row)
    return table_data


@app.post("/generate-pdf")
async def generate_pdf(request: MarkdownRequest):
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []
        styles = getSampleStyleSheet()
        normal_style = styles['Normal']
        heading_style = styles['Heading1']
        subheading_style = styles['Heading2']
        bold_style = styles['Normal'].clone('Bold')  # Clone for bold style

        table_width = doc.width * 0.9
        lines = request.markdown.splitlines()
        table_lines = []
        in_table = False

        for line in lines:
            if line.strip() == '---':
                story.append(Spacer(1, 12))
                continue
            if '|' in line:
                in_table = True
                table_lines.append(line)
            else:
                if in_table:
                    if table_lines:
                        story.append(Spacer(1, 12))
                        table_data = await parse_markdown_table(table_lines)
                        num_columns = len(table_data[0])
                        col_widths = [table_width / num_columns] * num_columns
                        wrapped_table_data = []

                        for row in table_data:
                            wrapped_row = []
                            for cell in row:
                                if isinstance(cell, BytesIO):  # Check if it's image data
                                    img = Image(cell, width=100, height=75)  # Use BytesIO directly
                                    wrapped_row.append(img)
                                elif isinstance(cell, Paragraph):
                                    wrapped_row.append(cell)
                                else:
                                    wrapped_row.append(Paragraph(str(cell), normal_style))
                            wrapped_table_data.append(wrapped_row)

                        table = Table(wrapped_table_data, colWidths=col_widths)
                        table.setStyle(TableStyle([
                            ('BACKGROUND', (0, 0), (-1, 0), "#F5F5F5"),
                            ('TEXTCOLOR', (0, 0), (-1, 0), "#FFFFFF"),
                            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                            ('BACKGROUND', (0, 1), (-1, -1), "#FFFFFF"),
                            ('GRID', (0, 0), (-1, -1), 1, "#EEEEEE"),
                            ('LEFTPADDING', (0, 0), (-1, -1), 5),
                            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                            ('BORDER', (0, 0), (-1, -1), 1, "#D9D9D9"),
                        ]))
                        story.append(table)
                        table_lines = []
                    in_table = False
                else:
                    # Process headings and bold text outside the table
                    formatted_line = line.strip()

                    if formatted_line.startswith('### '):
                        story.append(Paragraph(formatted_line[4:], subheading_style))
                    elif formatted_line.startswith('## '):
                        story.append(Paragraph(formatted_line[3:], heading_style))
                    elif formatted_line.startswith('# '):
                        story.append(Paragraph(formatted_line[2:], heading_style))
                    else:
                        # Handle bold text with ** if present
                        if '**' in formatted_line:
                            parts = formatted_line.split('**')
                            paragraphs = []
                            for i, part in enumerate(parts):
                                if i % 2 == 1:  # Bold part
                                    paragraphs.append(Paragraph(part.strip(), bold_style))
                                else:  # Normal part
                                    paragraphs.append(Paragraph(part.strip(), normal_style))
                            story.extend(paragraphs)
                        else:
                            story.append(Paragraph(formatted_line, normal_style))

        if table_lines:
            table_data = await parse_markdown_table(table_lines)
            max_column_width = (doc.width / len(table_data[0]) * 0.9) - 20
            col_widths = [max_column_width] * len(table_data[0])
            wrapped_table_data = []
            for row in table_data:
                wrapped_row = []
                for cell in row:
                    if isinstance(cell, BytesIO):  # Check if it's image data
                        img = Image(cell, width=100, height=75)  # Use BytesIO directly
                        wrapped_row.append(img)
                    else:
                        wrapped_row.append(cell)
                wrapped_table_data.append(wrapped_row)

            table = Table(wrapped_table_data, colWidths=col_widths)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), "#F5F5F5"),
                ('TEXTCOLOR', (0, 0), (-1, 0), "#FFFFFF"),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), "#FFFFFF"),
                ('GRID', (0, 0), (-1, -1), 1, "#EEEEEE"),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('BORDER', (0, 0), (-1, -1), 1, "#D9D9D9"),
            ]))
            story.append(table)

        doc.build(story)
        buffer.seek(0)
        return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "attachment; filename=chat_session.pdf"})

    except Exception as e:
        logger.error("Error generating PDF: %s" % str(e))
        raise HTTPException(status_code=500, detail=str(e))

# Serves the static files
# app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get('/hc')
async def health_check():
    """Enhanced health check including insertion order service status"""
    try:
        status = {
            "status": "live",
            "insertion_order_service": "available" if insertion_order_service else "unavailable"
        }

        # If service is available, check if credentials are valid
        if insertion_order_service:
            try:
                # Try to refresh credentials to verify they're working
                insertion_order_service.refresh_credentials_if_needed()
                status["oauth_credentials"] = "valid"
            except Exception as e:
                status["oauth_credentials"] = f"error: {str(e)}"

        return status
    except Exception as e:
        return {"status": "error", "detail": str(e)}

# async def post_message(inference_payload: InferencePayload, db: Session = Depends(get_db)):
@app.post("/")
async def post_message(inference_payload: InferencePayload):
    try:
        async def event_generator():
            # async for chunk in perform_inference(inference_payload,db):

                # return "Error: Database connection is not available"
            async for chunk in perform_inference(inference_payload):
                # Ensure each chunk is immediately flushed to the client
                yield f"data: {json.dumps(chunk)}\n\n"
                # Add explicit flush to ensure data is sent immediately
                await asyncio.sleep(0)  # Allow event loop to process the data

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache", "Connection": "keep-alive"}
        )
    except Exception as e:
        logger.error(e)
        raise HTTPException(status_code=500, detail=str(e))

async def create_salesforce_insertion_order(order_request):
    """
    Create insertion order in Salesforce using the Salesforce connector service
    AND generate a PDF in Google Drive for documentation
    """
    try:
        logger.info("Creating Salesforce insertion order with PDF generation")
        salesforce_connector_url = os.getenv("SALESFORCE_CONNECTOR_URL", "http://localhost:8001")

        # Step 1: First generate the PDF and get the PDF link
        pdf_result = None
        pdf_view_link = None
        media_plan_pdf_link = None
        try:
            if insertion_order_service:
                # Create a temporary order request with Brand field for PDF generation
                temp_order_request = order_request.model_copy()
                if not temp_order_request.Brand:
                    temp_order_request.Brand = f"Salesforce Account {order_request.SalesforceAccount}"

                # Generate simplified documentation using the new Salesforce-specific method
                pdf_result = await insertion_order_service.create_salesforce_documentation(temp_order_request)
                pdf_view_link = pdf_result.file_details.pdf_web_view_link
                logger.info(f"Salesforce documentation created in Google Drive: {pdf_view_link}")

                # Check if media plan PDF was generated and get its link
                if pdf_result.media_plan_pdf_link:
                    media_plan_pdf_link = pdf_result.media_plan_pdf_link
                    logger.info(f"Media plan PDF created: {media_plan_pdf_link}")
        except Exception as e:
            logger.warning(f"Failed to generate Salesforce documentation (continuing without PDF): {e}")

        # Step 2: Prepare the request data for Salesforce connector (including PDF link)
        salesforce_data = {
            "account_id": order_request.SalesforceAccount,
            "opportunity_id": order_request.SalesforceOpportunityId,
            "OrderNo": order_request.OrderNo,
            "Brand": order_request.Brand or "Salesforce Account",  # Use Brand field or fallback
            "CampaignName": order_request.CampaignName,
            "CustomerApprover": order_request.CustomerApprover,
            "CustomerApproverEmail": order_request.CustomerApproverEmail,
            "SalesOwner": order_request.SalesOwner,
            "SalesOwnerEmail": order_request.SalesOwnerEmail,
            "FulfillmentOwner": order_request.FulfillmentOwner,
            "FulfillmentOwnerEmail": order_request.FulfillmentOwnerEmail,
            "ObjectiveDetails": order_request.ObjectiveDetails.model_dump(),
            "Placement": [placement.model_dump() for placement in order_request.Placement],
            "PDF_View_Link_c": pdf_view_link,  # Include the PDF link from media backend
            "Media_Plan__c": media_plan_pdf_link,  # Include the media plan PDF link
            "Creative_Inspiration__c": order_request.CreativeInspirationLink  # Include creative inspiration link
        }

        # Step 3: Call the Salesforce connector service
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{salesforce_connector_url}/generate-insertion-order",
                json=salesforce_data,
                timeout=40.0
            )
            response.raise_for_status()

            salesforce_response = response.json()
            logger.info(f"Salesforce insertion order created: {salesforce_response}")

        # Step 4: Create response with both Salesforce record and PDF links
        from insertion_order_models import OrderGenerationResponse, PDFFileDetails

        # Generate proper Salesforce Lightning URL
        salesforce_base_url = os.getenv("SALESFORCE_BASE_URL", "https://flow-business-5971.lightning.force.com")
        salesforce_record_id = salesforce_response.get('id', '')
        salesforce_record_url = f"{salesforce_base_url}/lightning/r/Insertion_Order__c/{salesforce_record_id}/view"

        logger.info(f"Generated Salesforce Lightning URL: {salesforce_record_url}")

        # Step 5: Create Salesforce mapping now that we have the Salesforce insertion order ID
        try:
            from services.insertion_order_db_service import InsertionOrderDatabaseService
            db_service = InsertionOrderDatabaseService()

            # We need to find the media backend insertion order ID that was created earlier
            # This should be stored in the response_data from the PDF creation
            if pdf_result and hasattr(pdf_result, 'insertion_order_id'):
                media_insertion_order_id = pdf_result.insertion_order_id
            else:
                # Fallback: find by order number
                with db_service.get_db_session() as session:
                    from database_models import InsertionOrderModel
                    insertion_order = session.query(InsertionOrderModel).filter(
                        InsertionOrderModel.order_no == order_request.OrderNo
                    ).first()
                    if insertion_order:
                        media_insertion_order_id = insertion_order.id
                    else:
                        raise Exception(f"Could not find media backend insertion order for {order_request.OrderNo}")

            # Create the Salesforce mapping
            db_service.create_salesforce_mapping_after_creation(
                insertion_order_id=media_insertion_order_id,
                salesforce_io_id=salesforce_record_id,
                request=order_request
            )
            logger.info(f"Created Salesforce mapping: {media_insertion_order_id} -> {salesforce_record_id}")

        except Exception as e:
            logger.error(f"Failed to create Salesforce mapping: {e}")
            # Don't fail the entire operation if mapping creation fails

        response_data = OrderGenerationResponse(
            status="success",
            message=f"Insertion Order created in Salesforce: {salesforce_record_id}",
            campaign_folder_id=pdf_result.campaign_folder_id if pdf_result else "salesforce_record",
            campaign_folder_link=pdf_result.campaign_folder_link if pdf_result else salesforce_record_url,
            sheet_id=salesforce_record_id,  # Use actual Salesforce record ID
            sheet_link=salesforce_record_url,  # Always use proper Salesforce Lightning URL
            pdf_folder_id=pdf_result.pdf_folder_id if pdf_result else "salesforce_record",
            pdf_folder_link=pdf_result.pdf_folder_link if pdf_result else salesforce_record_url,
            file_details=PDFFileDetails(
                filename=f"{order_request.OrderNo}_Salesforce.pdf",
                pdf_file_id=pdf_result.file_details.pdf_file_id if pdf_result else "salesforce_record",
                pdf_web_view_link=pdf_result.file_details.pdf_web_view_link if pdf_result else salesforce_record_url
            )
        )

        return response_data

    except httpx.HTTPError as e:
        logger.error(f"HTTP error calling Salesforce connector: {e}")
        raise HTTPException(status_code=503, detail="Salesforce service unavailable")
    except Exception as e:
        logger.error(f"Error creating Salesforce insertion order: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/create-insertion-order")
async def create_insertion_order(payload: Dict[str, Any]):
    """
    Create insertion order with Google Drive folder, sheet, and PDF generation
    """
    # Check if service is available
    if not insertion_order_service:
        raise HTTPException(
            status_code=503,
            detail="Insertion Order Service is not available. Please check server configuration."
        )

    # Extract session and user info from payload
    session_id = payload.get("session_id")
    user_id = payload.get("user_id")

    try:
        from insertion_order_models import OrderGenerationRequest

        # Remove session and user info from payload before processing
        order_data = {k: v for k, v in payload.items() if k not in ['session_id', 'user_id']}

        # Parse the payload into the OrderGenerationRequest model
        try:
            order_request = OrderGenerationRequest(**order_data)
            logger.info(f"Order request parsed successfully: {order_request.OrderNo}")

            # Debug: Log the raw request data for Salesforce fields
            logger.info(f"🔍 RAW REQUEST DATA:")
            logger.info(f"   SalesforceAccount (raw): {repr(order_data.get('SalesforceAccount'))}")
            logger.info(f"   SalesforceOpportunityId (raw): {repr(order_data.get('SalesforceOpportunityId'))}")
            logger.info(f"   Brand (raw): {repr(order_data.get('Brand'))}")
            logger.info(f"   SalesforceAccount (parsed): {repr(order_request.SalesforceAccount)}")
            logger.info(f"   SalesforceOpportunityId (parsed): {repr(order_request.SalesforceOpportunityId)}")

        except Exception as e:
            logger.error(f"Error parsing order request: {str(e)}")
            raise HTTPException(status_code=400, detail=f"Invalid order data: {str(e)}")

        # Check if this is a Salesforce destination
        # Check for both None and empty string cases
        salesforce_account_valid = (
            order_request.SalesforceAccount is not None and
            str(order_request.SalesforceAccount).strip() != "" and
            str(order_request.SalesforceAccount).strip().lower() != "none"
        )
        salesforce_opportunity_valid = (
            order_request.SalesforceOpportunityId is not None and
            str(order_request.SalesforceOpportunityId).strip() != "" and
            str(order_request.SalesforceOpportunityId).strip().lower() != "none"
        )

        is_salesforce_destination = salesforce_account_valid and salesforce_opportunity_valid

        logger.info(f"🔍 SALESFORCE DETECTION:")
        logger.info(f"   SalesforceAccount: '{order_request.SalesforceAccount}' -> Valid: {salesforce_account_valid}")
        logger.info(f"   SalesforceOpportunityId: '{order_request.SalesforceOpportunityId}' -> Valid: {salesforce_opportunity_valid}")
        logger.info(f"   Final is_salesforce_destination: {is_salesforce_destination}")

        # Store the destination type for consistent use throughout the function
        destination_type = "SALESFORCE" if is_salesforce_destination else "GOOGLE_WORKSPACE"
        logger.info(f"🎯 DESTINATION TYPE: {destination_type}")

        if is_salesforce_destination:
            # Handle Salesforce destination
            logger.info(f"🔄 Processing Salesforce insertion order for account: {order_request.SalesforceAccount}, opportunity: {order_request.SalesforceOpportunityId}")
            response_data = await create_salesforce_insertion_order(order_request)
            logger.info(f"✅ Salesforce insertion order completed successfully")
        else:
            # Handle Google Workspace destination (existing logic)
            logger.info(f"🔄 Processing Google Workspace insertion order for brand: {order_request.Brand}")
            response_data = await insertion_order_service.create_insertion_order(order_request)
            logger.info(f"✅ Google Workspace insertion order completed successfully")

        logger.info(f"Insertion order created successfully: {response_data.model_dump()}")

        # If successful, create and store the bot message
        if response_data and session_id:
            try:
                # Debug: Log the destination detection result and response data
                logger.info(f"🔍 SUCCESS MESSAGE GENERATION:")
                logger.info(f"   Destination Type: {destination_type}")
                logger.info(f"   is_salesforce_destination: {is_salesforce_destination}")
                logger.info(f"   Response sheet_link: {response_data.sheet_link}")
                logger.info(f"   Response pdf_web_view_link: {response_data.file_details.pdf_web_view_link}")
                logger.info(f"   Response campaign_folder_link: {response_data.campaign_folder_link}")

                # Create the success message markdown based on destination
                # Use multiple checks to ensure we detect Salesforce correctly
                is_salesforce_message = (
                    destination_type == "SALESFORCE" or
                    is_salesforce_destination or
                    'lightning.force.com' in str(response_data.sheet_link)
                )

                logger.info(f"🎯 MESSAGE TYPE DECISION: is_salesforce_message = {is_salesforce_message}")

                if is_salesforce_message:
                    # Enhanced Salesforce message with both Salesforce record and PDF links
                    salesforce_record_id = response_data.sheet_id  # This now contains the actual Salesforce record ID

                    bot_message = f"Your IO was created successfully in Salesforce! 🎉\n\n"

                    # Always show the real PDF document link (from Google Drive)
                    if (response_data.file_details.pdf_web_view_link and
                        'salesforce.com' not in response_data.file_details.pdf_web_view_link):
                        bot_message += f"📄 IO Document: {response_data.file_details.pdf_web_view_link}\n\n"

                    # Always show the Salesforce record link
                    bot_message += f"🔗 View in Salesforce: {response_data.sheet_link}"

                    # Add campaign folder link if PDF was generated
                    if (response_data.campaign_folder_link and
                        'salesforce.com' not in response_data.campaign_folder_link):
                        bot_message += f"\n\n📁 Campaign Folder: {response_data.campaign_folder_link}"

                    logger.info(f"Generated Salesforce success message for record: {salesforce_record_id}")
                    logger.info(f"📧 Salesforce Success Message Content:\n{bot_message}")
                else:
                    bot_message = f"Your IO was created successfully! 🎉\n\n" \
                                f"📄 IO Document: {response_data.file_details.pdf_web_view_link}\n\n" \
                                f"📊 Campaign Sheet: {response_data.sheet_link}\n\n" \
                                f"📁 Campaign Folder: {response_data.campaign_folder_link}"
                    logger.info(f"📧 Google Workspace Success Message Content:\n{bot_message}")

                # Store this as a bot message directly in the database
                await store_io_message_in_database(
                    session_id=session_id,
                    user_id=user_id,
                    message=bot_message
                )

                logger.info(f"Stored IO success message for session {session_id}")

            except Exception as e:
                logger.error(f"Failed to store IO success message: {e}")
                # Don't fail the entire request if message storage fails

        # Return the response data as a dictionary
        return response_data.model_dump()

    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"Error creating insertion order: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to create insertion order: {str(e)}")

# ============================================================================
# FEEDBACK AND SESSION MANAGEMENT ENDPOINTS
# ============================================================================

@app.post("/voting")
async def submit_vote(request: VotingRequest):
    """Submit user vote for a query (following Arlo pattern)"""
    return await feedback_endpoints.submit_vote(request)

@app.post("/feedback")
async def submit_feedback(request: FeedbackRequest):
    """Submit user feedback for a query"""
    return await feedback_endpoints.submit_feedback(request)

@app.get("/feedback/{query_id}")
async def get_feedback(query_id: str):
    """Get feedback for a specific query"""
    return await feedback_endpoints.get_feedback(query_id)

@app.get("/feedback/session/{session_id}")
async def get_session_feedback(session_id: str):
    """Get all feedback for a session"""
    return await feedback_endpoints.get_session_feedback(session_id)

@app.post("/session")
async def create_session(request: SessionCreateRequest):
    """Create a new session"""
    logger.info(f"[MAIN] POST /session called with: {request}")
    result = await session_endpoints.create_session(request)
    logger.info(f"[MAIN] POST /session returning: {result}")
    return result

@app.get("/session/{session_id}")
async def get_session(session_id: str):
    """Get session metadata"""
    return await session_endpoints.get_session(session_id)

@app.get("/session/{session_id}/full")
async def get_session_with_queries(session_id: str):
    """Get session with all query details"""
    logger.info(f"[MAIN] GET /session/{session_id}/full called")
    result = await session_endpoints.get_session_with_queries(session_id)
    logger.info(f"[MAIN] GET /session/{session_id}/full returning: {type(result)} with keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
    return result

@app.put("/session/name")
async def update_session_name(request: SessionUpdateRequest):
    """Update session name"""
    success = await session_endpoints.update_session_name(request)
    return {"success": success}

@app.get("/sessions/user/{user_id}")
async def list_user_sessions(user_id: str, limit: int = 50):
    """List all sessions for a user"""
    logger.info(f"[MAIN] GET /sessions/user/{user_id} called with limit: {limit}")
    result = await session_endpoints.list_user_sessions(user_id, limit)
    logger.info(f"[MAIN] GET /sessions/user/{user_id} returning: {type(result)} with keys: {result.keys() if isinstance(result, dict) else 'not a dict'}")
    return result

@app.post("/session/{session_id}/flush")
async def flush_session_to_database(session_id: str, user_id: str = Query(...)):
    """Flush all pending session data from cache to database"""
    logger.info(f"[MAIN] POST /session/{session_id}/flush called for user: {user_id}")
    result = await session_endpoints.flush_session_to_database(session_id, user_id)
    logger.info(f"[MAIN] POST /session/{session_id}/flush returning: {result}")
    return result



# @app.get("/query/{query_id}")
# async def get_query_details(query_id: str):
#     """Get detailed execution data for a query"""
#     return await query_endpoints.get_query_details(query_id)

# @app.get("/analytics/agents")
# async def get_agent_analytics(agent_name: str = None):
#     """Get agent performance analytics"""
#     return await analytics_endpoints.get_agent_analytics(agent_name)

# @app.get("/analytics/session/{session_id}")
# async def get_session_analytics(session_id: str):
#     """Get comprehensive session analytics"""
#     return await analytics_endpoints.get_session_analytics(session_id)


# ============================================================================
# TARGETING CONFIGURATION ENDPOINTS
# ============================================================================

@app.get("/targeting-configurations")
async def list_targeting_configurations(user_id: str = Query(...)):
    """List all targeting configurations for a user"""
    try:
        from db_connector import db_connector
        from database_models import TargetingConfigurationModel

        db = db_connector.get_session()
        try:
            configurations = db.query(TargetingConfigurationModel).filter(
                TargetingConfigurationModel.user_id == user_id
            ).order_by(TargetingConfigurationModel.created_at.desc()).all()

            response_configs = []
            for config in configurations:
                response_configs.append(TargetingConfigurationResponse(
                    id=str(config.id),
                    name=config.name,
                    description=config.description,
                    targeting_config=config.targeting_config,
                    user_id=config.user_id,
                    created_at=config.created_at,
                    updated_at=config.updated_at
                ))

            return TargetingConfigurationListResponse(
                configurations=response_configs,
                total_count=len(response_configs)
            )

        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error listing targeting configurations: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/targeting-configurations")
async def create_targeting_configuration(request: TargetingConfigurationCreate, user_id: str = Query(...)):
    """Create a new targeting configuration"""
    try:
        from db_connector import db_connector
        from database_models import TargetingConfigurationModel

        db = db_connector.get_session()
        try:
            # Create new configuration
            new_config = TargetingConfigurationModel(
                name=request.name,
                description=request.description,
                targeting_config=request.targeting_config.model_dump(),
                user_id=user_id
            )

            db.add(new_config)
            db.commit()
            db.refresh(new_config)

            return TargetingConfigurationResponse(
                id=str(new_config.id),
                name=new_config.name,
                description=new_config.description,
                targeting_config=new_config.targeting_config,
                user_id=new_config.user_id,
                created_at=new_config.created_at,
                updated_at=new_config.updated_at
            )

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except Exception as e:
        logger.error(f"Error creating targeting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/targeting-configurations/{config_id}")
async def get_targeting_configuration(config_id: str, user_id: str = Query(...)):
    """Get a specific targeting configuration"""
    try:
        from db_connector import db_connector
        from database_models import TargetingConfigurationModel

        db = db_connector.get_session()
        try:
            config = db.query(TargetingConfigurationModel).filter(
                TargetingConfigurationModel.id == config_id,
                TargetingConfigurationModel.user_id == user_id
            ).first()

            if not config:
                raise HTTPException(status_code=404, detail="Targeting configuration not found")

            return TargetingConfigurationResponse(
                id=str(config.id),
                name=config.name,
                description=config.description,
                targeting_config=config.targeting_config,
                user_id=config.user_id,
                created_at=config.created_at,
                updated_at=config.updated_at
            )

        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting targeting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.put("/targeting-configurations/{config_id}")
async def update_targeting_configuration(config_id: str, request: TargetingConfigurationUpdate, user_id: str = Query(...)):
    """Update a targeting configuration"""
    try:
        from db_connector import db_connector
        from database_models import TargetingConfigurationModel

        db = db_connector.get_session()
        try:
            config = db.query(TargetingConfigurationModel).filter(
                TargetingConfigurationModel.id == config_id,
                TargetingConfigurationModel.user_id == user_id
            ).first()

            if not config:
                raise HTTPException(status_code=404, detail="Targeting configuration not found")

            # Update fields if provided
            if request.name is not None:
                config.name = request.name
            if request.description is not None:
                config.description = request.description
            if request.targeting_config is not None:
                config.targeting_config = request.targeting_config.model_dump()

            config.updated_at = datetime.now(timezone.utc)

            db.commit()
            db.refresh(config)

            return TargetingConfigurationResponse(
                id=str(config.id),
                name=config.name,
                description=config.description,
                targeting_config=config.targeting_config,
                user_id=config.user_id,
                created_at=config.created_at,
                updated_at=config.updated_at
            )

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating targeting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/targeting-configurations/{config_id}")
async def delete_targeting_configuration(config_id: str, user_id: str = Query(...)):
    """Delete a targeting configuration"""
    try:
        from db_connector import db_connector
        from database_models import TargetingConfigurationModel

        db = db_connector.get_session()
        try:
            config = db.query(TargetingConfigurationModel).filter(
                TargetingConfigurationModel.id == config_id,
                TargetingConfigurationModel.user_id == user_id
            ).first()

            if not config:
                raise HTTPException(status_code=404, detail="Targeting configuration not found")

            db.delete(config)
            db.commit()

            return {"message": "Targeting configuration deleted successfully"}

        except Exception as e:
            db.rollback()
            raise e
        finally:
            db.close()

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting targeting configuration: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# SALESFORCE INTEGRATION ENDPOINTS
# ============================================================================

@app.get("/salesforce/accounts")
async def get_salesforce_accounts():
    """Get list of Salesforce Accounts for dropdown population"""
    try:
        # Get Salesforce connector service URL from environment
        salesforce_connector_url = os.getenv("SALESFORCE_CONNECTOR_URL", "http://localhost:8001")
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{salesforce_connector_url}/accounts", timeout=20.0)
            response.raise_for_status()

            accounts = response.json()
            logger.info(f"Retrieved {len(accounts)} Salesforce accounts")
            return accounts

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching Salesforce accounts: {e}")
        raise HTTPException(status_code=503, detail="Salesforce service unavailable")
    except Exception as e:
        logger.error(f"Error fetching Salesforce accounts: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/salesforce/opportunities-by-account/{account_id}")
async def get_salesforce_opportunities_by_account(account_id: str):
    """Get Salesforce Opportunities associated with a specific Account"""
    try:
        # Get Salesforce connector service URL from environment
        salesforce_connector_url = os.getenv("SALESFORCE_CONNECTOR_URL", "http://localhost:8001")

        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.get(f"{salesforce_connector_url}/opportunities-by-account/{account_id}", timeout=20.0)
            response.raise_for_status()

            opportunities = response.json()
            logger.info(f"Retrieved {len(opportunities)} Salesforce opportunities for account: {account_id}")
            return opportunities

    except httpx.HTTPError as e:
        logger.error(f"HTTP error fetching Salesforce leads by account: {e}")
        raise HTTPException(status_code=503, detail="Salesforce service unavailable")
    except Exception as e:
        logger.error(f"Error fetching Salesforce leads by account: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# WEBHOOK ENDPOINTS
# ============================================================================

@app.post("/insertion-orders/{order_id}/update", response_model=InsertionOrderUpdateResponse)
async def update_insertion_order(
    order_id: str,
    request: InsertionOrderUpdateRequest,
    source: str = Query(..., description="Source system: 'salesforce' or 'google_drive'")
):
    """
    Update insertion order fields including approval status and other properties

    This endpoint:
    1. Resolves order_id based on source query parameter (salesforce or google_drive)
    2. Updates insertion order fields based on the request
    3. Handles approval status changes (draft, pending_approval, approved, rejected)
    4. Updates fields like campaign_name, objective_description, customer details, etc.
    5. Updates placement data if provided
    6. Creates status change records for audit purposes

    Updatable fields include:
    - order_no, brand, campaign_name
    - customer_approver, customer_approver_email
    - sales_owner, sales_owner_email
    - fulfillment_owner, fulfillment_owner_email
    - objective_description (campaign objective/description)
    - status, workspace_type
    - creative_inspiration_id, io_pdf_id, media_plan_id
    - placements (list of placement updates including convert_to_campaign flag)

    Placement updates support:
    - Basic fields: name, destination, dates, budget, metrics
    - convert_to_campaign: Flag to convert individual placements into separate campaigns
    - targeting_config: Targeting configuration updates
    """
    # Validate source parameter
    if source not in ['salesforce', 'google_drive']:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid source: {source}. Must be 'salesforce' or 'google_drive'"
        )

    logger.info(f"Received insertion order update request for order: {order_id}, source: {source}")

    try:
        # Import the database service
        from services.insertion_order_db_service import InsertionOrderDatabaseService
        db_service = InsertionOrderDatabaseService()

        # Resolve the actual insertion order ID based on source
        actual_order_id = None
        salesforce_io_id = None

        if source == "salesforce":
            # Look up insertion order ID using Salesforce IO ID
            logger.info(f"Looking up Salesforce IO ID: {order_id}")
            with db_service.get_db_session() as session:
                from database_models import InsertionOrderSalesforceMapping

                mapping = session.query(InsertionOrderSalesforceMapping).filter(
                    InsertionOrderSalesforceMapping.salesforce_io_id == order_id
                ).first()

                if not mapping:
                    logger.warning(f"Salesforce IO ID not found in mapping: {order_id}")
                    raise HTTPException(
                        status_code=404,
                        detail=f"No insertion order mapping found for Salesforce IO ID: {order_id}"
                    )

                actual_order_id = mapping.insertion_order_id
                salesforce_io_id = order_id
                logger.info(f"Mapped Salesforce IO {order_id} to insertion order {actual_order_id}")

        elif source == "google_drive":
            # Use the order_id directly as it's already the insertion order ID
            actual_order_id = order_id
            logger.info(f"Using Google Drive insertion order ID directly: {order_id}")

        # Get current insertion order to check if it exists
        current_order = db_service.get_insertion_order(actual_order_id)
        if not current_order:
            raise HTTPException(
                status_code=404,
                detail=f"Insertion order not found: {actual_order_id}"
            )

        # Prepare update data for insertion order fields only
        update_data = {}
        updated_by = request.updated_by or "system"

        # Handle insertion order fields (matching database schema)
        if request.order_no:
            update_data['order_no'] = request.order_no
        if request.brand:
            update_data['brand'] = request.brand
        if request.campaign_name:
            update_data['campaign_name'] = request.campaign_name
        if request.customer_approver:
            update_data['customer_approver'] = request.customer_approver
        if request.customer_approver_email:
            update_data['customer_approver_email'] = request.customer_approver_email
        if request.sales_owner:
            update_data['sales_owner'] = request.sales_owner
        if request.sales_owner_email:
            update_data['sales_owner_email'] = request.sales_owner_email
        if request.fulfillment_owner:
            update_data['fulfillment_owner'] = request.fulfillment_owner
        if request.fulfillment_owner_email:
            update_data['fulfillment_owner_email'] = request.fulfillment_owner_email
        if request.objective_description:
            update_data['objective_description'] = request.objective_description
        if request.status:
            update_data['status'] = request.status
        if request.workspace_type:
            update_data['workspace_type'] = request.workspace_type
        if request.creative_inspiration_id:
            update_data['creative_inspiration_id'] = request.creative_inspiration_id
        if request.io_pdf_id:
            update_data['io_pdf_id'] = request.io_pdf_id
        if request.media_plan_id:
            update_data['media_plan_id'] = request.media_plan_id

        # Update insertion order if there are fields to update
        updated_fields = []
        if update_data:
            result = db_service.update_insertion_order_fields(
                order_id=actual_order_id,
                update_data=update_data,
                updated_by=updated_by,
                reason=request.update_reason
            )

            if not result.get('success'):
                logger.error(f"Failed to update insertion order {actual_order_id}: {result.get('error')}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Failed to update insertion order: {result.get('error')}"
                )

            updated_fields.extend(result.get('updated_fields', []))
            logger.info(f"Successfully updated insertion order {actual_order_id}: {result.get('updated_fields')}")

        # Update placements if provided
        if request.placements:
            logger.info(f"Updating {len(request.placements)} placements for insertion order {actual_order_id}")

            for placement_update in request.placements:
                placement_data = {}

                # Build placement update data
                if placement_update.name:
                    placement_data['name'] = placement_update.name
                if placement_update.destination:
                    placement_data['destination'] = placement_update.destination
                if placement_update.start_date:
                    placement_data['start_date'] = placement_update.start_date
                if placement_update.end_date:
                    placement_data['end_date'] = placement_update.end_date
                if placement_update.convert_to_campaign is not None:
                    placement_data['convert_to_campaign'] = placement_update.convert_to_campaign
                if placement_update.impressions_booked is not None:
                    placement_data['impressions_booked'] = placement_update.impressions_booked
                if placement_update.impressions_delivered is not None:
                    placement_data['impressions_delivered'] = placement_update.impressions_delivered
                if placement_update.clicks is not None:
                    placement_data['clicks'] = placement_update.clicks
                if placement_update.ctr is not None:
                    placement_data['ctr'] = placement_update.ctr
                if placement_update.budget is not None:
                    placement_data['budget'] = placement_update.budget
                if placement_update.cpm is not None:
                    placement_data['cpm'] = placement_update.cpm
                if placement_update.cpc is not None:
                    placement_data['cpc'] = placement_update.cpc
                if placement_update.targeting_config:
                    placement_data['targeting_config'] = placement_update.targeting_config
                if placement_update.status:
                    placement_data['status'] = placement_update.status

                if placement_data:
                    # Update existing placement or create new one
                    placement_result = db_service.update_placement(
                        placement_id=placement_update.id,
                        insertion_order_id=actual_order_id,
                        placement_data=placement_data,
                        updated_by=updated_by
                    )

                    if placement_result.get('success'):
                        updated_fields.append(f"placement_{placement_update.id or 'new'}")
                    else:
                        logger.error(f"Failed to update placement: {placement_result.get('error')}")

        return InsertionOrderUpdateResponse(
            id=actual_order_id,
            order_number=current_order.get('order_no', ''),
            previous_status=current_order.get('status'),
            new_status=update_data.get('status', current_order.get('status')),
            updated_fields=updated_fields,
            success=True,
            message="Insertion order updated successfully",
            salesforce_io_id=salesforce_io_id,
            updated_at=datetime.now()
        )

    except HTTPException:
        # Re-raise HTTP exceptions (404, etc.)
        raise
    except Exception as e:
        logger.error(f"Error updating insertion order: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Internal server error updating insertion order: {str(e)}"
        )






@app.post("/campaigns/{kevel_id}/{salesforce_io_id}", response_model=CampaignResponse)
async def create_campaign(
    kevel_id: str,
    salesforce_io_id: str,
    request: CampaignPlacementRequest,
    status: str = "work_in_progress"
):
    """
    Create a new campaign with placements using Kevel ID and Salesforce IO ID

    This endpoint:
    1. Looks up insertion order using Salesforce IO ID
    2. Creates a new campaign with kevel_id and status 'shell_created'
    3. Creates the campaign-insertion order mapping
    4. Creates associated campaign placements
    5. Returns campaign information with placement count and total budget

    Path parameters:
    - kevel_id: Kevel campaign ID
    - salesforce_io_id: Salesforce insertion order ID
    """
    logger.info(f"Creating new campaign with Kevel ID: {kevel_id} for Salesforce IO: {salesforce_io_id}")

    try:
        # Import the database service
        from services.insertion_order_db_service import InsertionOrderDatabaseService
        db_service = InsertionOrderDatabaseService()

        # Look up insertion order using Salesforce IO ID
        with db_service.get_db_session() as session:
            from database_models import InsertionOrderSalesforceMapping

            mapping = session.query(InsertionOrderSalesforceMapping).filter(
                InsertionOrderSalesforceMapping.salesforce_io_id == salesforce_io_id
            ).first()

            if not mapping:
                logger.warning(f"Salesforce IO ID not found in mapping: {salesforce_io_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No insertion order mapping found for Salesforce IO ID: {salesforce_io_id}"
                )

            insertion_order_id = mapping.insertion_order_id
            logger.info(f"Mapped Salesforce IO {salesforce_io_id} to insertion order {insertion_order_id}")

        # Validate insertion order exists
        insertion_order = db_service.get_insertion_order(insertion_order_id)
        if not insertion_order:
            raise HTTPException(
                status_code=404,
                detail=f"Insertion order not found: {insertion_order_id}"
            )

        # Prepare campaign data with kevel_id and status
        campaign_data = {
            'name': f"Campaign {kevel_id}",  # Generate name from kevel_id
            'kevel_id': kevel_id,
            'status': status  # Use provided status or default to work_in_progress
        }

        # Prepare campaign placements data (matches campaign_placements table)
        placements_data = []
        for placement in request.placements:
            placement_data = {
                'flight_id': placement.flight_id,
                'start_date': placement.start_date,
                'end_date': placement.end_date,
                'impressions_booked': placement.impressions_booked,
                'impressions_delivered': placement.impressions_delivered,
                'booked_clicks': placement.booked_clicks,
                'delivered_clicks': placement.delivered_clicks,
                'ctr': placement.ctr,
                'budget': placement.budget,
                'cpm': placement.cpm,
                'cpc': placement.cpc
            }
            placements_data.append(placement_data)

        # Create campaign with placements and insertion order mapping
        result = db_service.create_campaign_with_placements(
            campaign_data=campaign_data,
            placements_data=placements_data,
            insertion_order_id=insertion_order_id
        )

        if not result.get('success'):
            logger.error(f"Failed to create campaign: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create campaign: {result.get('error')}"
            )

        logger.info(f"Successfully created campaign {result.get('campaign_id')}")

        return CampaignResponse(
            id=result.get('campaign_id'),
            name=result.get('campaign_name'),
            status=status,  # Use the provided or default status
            created_at=datetime.now(),
            updated_at=datetime.now(),
            placement_count=result.get('placement_count'),
            total_budget=result.get('total_budget')
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error creating campaign: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Internal server error creating campaign: {str(e)}"
        )


@app.put("/campaigns/{campaign_id}", response_model=CampaignResponse)
async def update_campaign(
    campaign_id: str,
    request: CampaignUpdateRequest
):
    """
    Update campaign fields and optionally its placements

    This endpoint:
    1. Updates campaign fields like name and status
    2. Optionally updates associated placements
    3. Returns updated campaign information

    Campaign states: shell_created, live, paused, completed
    """
    logger.info(f"Updating campaign: {campaign_id}")

    try:
        # Import the database service
        from services.insertion_order_db_service import InsertionOrderDatabaseService
        db_service = InsertionOrderDatabaseService()

        # Check if campaign exists
        current_campaign = db_service.get_campaign(campaign_id)
        if not current_campaign:
            raise HTTPException(
                status_code=404,
                detail=f"Campaign not found: {campaign_id}"
            )

        # Prepare update data
        update_data = {}
        if request.name:
            update_data['name'] = request.name
        if request.status:
            update_data['status'] = request.status

        # Prepare placement updates
        placements_updates = None
        if request.placements:
            placements_updates = []
            for placement in request.placements:
                placement_update = {}
                if placement.id:
                    placement_update['id'] = placement.id
                if placement.name:
                    placement_update['name'] = placement.name
                if placement.destination:
                    placement_update['destination'] = placement.destination
                if placement.start_date:
                    placement_update['start_date'] = placement.start_date
                if placement.end_date:
                    placement_update['end_date'] = placement.end_date
                if placement.impressions_booked is not None:
                    placement_update['impressions_booked'] = placement.impressions_booked
                if placement.clicks is not None:
                    placement_update['clicks'] = placement.clicks
                if placement.budget:
                    placement_update['budget'] = placement.budget
                if placement.cpm:
                    placement_update['cpm'] = placement.cpm
                if placement.cpc:
                    placement_update['cpc'] = placement.cpc
                if placement.targeting_config:
                    placement_update['targeting_config'] = placement.targeting_config
                if placement.status:
                    placement_update['status'] = placement.status

                placements_updates.append(placement_update)

        # Update campaign
        result = db_service.update_campaign(
            campaign_id=campaign_id,
            update_data=update_data,
            placements_updates=placements_updates,
            updated_by=request.updated_by or "system"
        )

        if not result.get('success'):
            logger.error(f"Failed to update campaign {campaign_id}: {result.get('error')}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to update campaign: {result.get('error')}"
            )

        logger.info(f"Successfully updated campaign {campaign_id}: {result.get('updated_fields')}")

        # Get updated campaign details
        updated_campaign = db_service.get_campaign(campaign_id)

        return CampaignResponse(
            id=campaign_id,
            name=updated_campaign.get('name'),
            status=updated_campaign.get('status'),
            created_at=datetime.fromisoformat(updated_campaign.get('created_at')),
            updated_at=datetime.fromisoformat(updated_campaign.get('updated_at')),
            placement_count=updated_campaign.get('placement_count'),
            total_budget=updated_campaign.get('total_budget')
        )

    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error updating campaign: {e}")
        import traceback
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=f"Internal server error updating campaign: {str(e)}"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
