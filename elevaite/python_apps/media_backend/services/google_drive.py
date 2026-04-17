import logging
from datetime import datetime
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import Dict, Any

logger = logging.getLogger(__name__)

class GoogleDriveService:
    def __init__(self, credentials=None):
        """Initialize with OAuth credentials - REQUIRED"""
        if not credentials:
            raise ValueError("OAuth credentials are required for GoogleDriveService")

        self.credentials = credentials
        self.service = None
        self.sheets_service = None
        self._build_service()

    def update_credentials(self, credentials):
        """Update credentials and rebuild service"""
        self.credentials = credentials
        self._build_service()

    def _build_service(self):
        """Build Google services with current credentials"""
        self.service = build('drive', 'v3', credentials=self.credentials)
        self.sheets_service = build('sheets', 'v4', credentials=self.credentials)



    def check_folder_exists(self, folder_id: str) -> bool:
        try:
            self.service.files().get(
                fileId=folder_id,
                supportsAllDrives=True,
                fields='id'
            ).execute()
            return True
        except HttpError:
            return False

    def create_folder(self, folder_name: str, parent_folder_id: str) -> Dict[str, Any]:
        try:
            file_metadata = {
                'name': folder_name,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_folder_id]
            }

            folder = self.service.files().create(
                body=file_metadata,
                supportsAllDrives=True,
                fields='id, webViewLink'
            ).execute()

            return {
                'id': folder.get('id'),
                'link': folder.get('webViewLink')
            }
        except Exception as e:
            logger.error(f"Failed to create folder: {str(e)}")
            raise

    def create_pdf_folder(self, parent_folder_id: str) -> Dict[str, Any]:
        return self.create_folder('PDF Files', parent_folder_id)

    def _extract_targeting_info_for_sheets(self, placement) -> Dict[str, str]:
        """Extract targeting information from placement for Google Sheets using new targeting configuration data"""
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
        if hasattr(placement, 'new_targeting_configuration') and placement.new_targeting_configuration:
            config = placement.new_targeting_configuration
            targeting_info.update({
                'age_range': ', '.join(config.age_range) if config.age_range else 'Not specified',
                'gender': ', '.join(config.gender) if config.gender else 'Not specified',
                'income_level': ', '.join(config.income_level) if config.income_level else 'Not specified',
                'interests': ', '.join(config.interests) if config.interests else 'Not specified',
                'location': ', '.join(config.location) if config.location else 'Not specified',
                'behavioral_data': ', '.join(config.behavioral_data) if config.behavioral_data else 'Not specified'
            })
            logger.info(f"Google Sheets: Using targeting configuration data for {placement.Name}")
        else:
            logger.warning(f"Google Sheets: No targeting configuration data found for placement {placement.Name}")

        return targeting_info

    def create_sheet_from_template(self, folder_id: str, sheet_name: str, template_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new sheet by copying a template and populating it with data.
        The template should have headers in the first row (A1:AA1).
        """
        try:
            # Copy the template to create a new sheet
            copied_sheet = self.service.files().copy(
                fileId=template_id,
                body={
                    'name': sheet_name,
                    'parents': [folder_id]
                },
                supportsAllDrives=True,
                fields='id, webViewLink'
            ).execute()

            sheet_id = copied_sheet['id']

            # Get the template headers from row 1
            header_result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:AA1',  # Headers from A to AA
                majorDimension='ROWS'
            ).execute()

            headers = header_result.get('values', [[]])[0] if header_result.get('values') else []

            if not headers:
                raise ValueError("Template sheet does not contain headers in the first row")

            # Handle multiple placements - create one row per placement
            placements = data.get('placements', [])
            if not placements:
                raise ValueError("No placements provided")

            # Create multiple rows of data - one for each placement
            all_rows = []
            for placement in placements:
                # Extract targeting information using the helper method
                targeting_info = self._extract_targeting_info_for_sheets(placement)

                # Create template mapping for this specific placement
                template_mapping = {
                    'Order Number': data.get('order_number', ''),
                    'Brand': data.get('brand', ''),
                    'Campaign Name': data.get('campaign_name', ''),
                    'Customer Approver': data.get('customer_approver', ''),
                    'Customer Approver Email': data.get('customer_approver_email', ''),
                    'Sales Owner': data.get('sales_owner', ''),
                    'Sales Owner Email': data.get('sales_owner_email', ''),
                    'Fulfillment Owner': data.get('fulfillment_owner', ''),
                    'Fulfillment Owner Email': data.get('fulfillment_owner_email', ''),
                    'Start Date': placement.StartDate,
                    'End Date': placement.EndDate,
                    'Placement Name': placement.Name,
                    'Placement Destination': placement.Destination,
                    'Metrics - Impressions': str(placement.Metrics.Impressions),
                    'Metrics - Clicks': str(placement.Metrics.Clicks),
                    'bid_rate - cpm': str(placement.BidRate.CPM),
                    'bid_rate - cpc': str(placement.BidRate.CPC),  # CPC no longer used
                    'Budget Amount': str(placement.Budget.Amount),
                    'target audience - age_range': targeting_info['age_range'],
                    'target audience - gender': targeting_info['gender'],
                    'target audience - income level': targeting_info['income_level'],
                    'target audience - interests': targeting_info['interests'],
                    'target audience - location': targeting_info['location'],
                    'target_audience - behavioral_data': targeting_info['behavioral_data'],
                    'objective_description': data.get('objective_description', ''),
                    'Sales Approval': 'Pending',
                    'Customer Approval': 'Pending'
                }

                # Create values array matching the header order for this placement
                row_values = []
                for header in headers:
                    row_values.append(template_mapping.get(header, ''))

                all_rows.append(row_values)

            # Update multiple rows starting from row 2
            if all_rows:
                end_row = 1 + len(all_rows)  # Start from row 2, so end at row 1 + number of placements
                body = {
                    'values': all_rows
                }

                self.sheets_service.spreadsheets().values().update(
                    spreadsheetId=sheet_id,
                    range=f'A2:AA{end_row}',  # Multiple rows for multiple placements
                    valueInputOption='RAW',
                    body=body
                ).execute()

            logger.info(f"Successfully created sheet from template: {sheet_name}")
            return {
                'sheet_id': copied_sheet['id'],
                'sheet_web_view_link': copied_sheet['webViewLink']
            }

        except Exception as e:
            logger.error(f"Failed to create sheet from template: {str(e)}")
            raise

    def _extract_placement_names(self, placements: list) -> str:
        """Extract placement names from placement list"""
        if not placements:
            return ''
        names = []
        for placement in placements:
            if isinstance(placement, dict):
                names.append(placement.get('name', ''))
            else:
                names.append(str(placement))
        return ', '.join(names)

    def _extract_placement_destinations(self, placements: list) -> str:
        """Extract placement destinations from placement list"""
        if not placements:
            return ''
        destinations = []
        for placement in placements:
            if isinstance(placement, dict):
                destinations.append(placement.get('destination', ''))
            else:
                destinations.append('')
        return ', '.join(destinations)

    def _extract_placement_names_new(self, placements: list) -> str:
        """Extract placement names from new placement model objects"""
        if not placements:
            return ''
        names = []
        for placement in placements:
            names.append(f"{placement.Name} ({placement.StartDate} - {placement.EndDate})")
        return ', '.join(names)

    def _extract_placement_destinations_new(self, placements: list) -> str:
        """Extract placement destinations from new placement model objects"""
        if not placements:
            return ''
        destinations = []
        for placement in placements:
            destinations.append(placement.Destination)
        return ', '.join(destinations)

    def create_and_populate_sheet(self, folder_id: str, sheet_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
        try:
            # Create new spreadsheet
            spreadsheet = self.service.files().create(
                body={
                    'name': sheet_name,
                    'mimeType': 'application/vnd.google-apps.spreadsheet',
                    'parents': [folder_id]
                },
                supportsAllDrives=True,
                fields='id, webViewLink'
            ).execute()

            sheet_id = spreadsheet['id']

            # Prepare headers and data for horizontal structure
            headers = []
            values = []

            # Process the data to extract headers and values
            for key, value in data.items():
                if isinstance(value, dict):
                    for sub_key, sub_value in value.items():
                        headers.append(f"{key} - {sub_key}")
                        values.append(str(sub_value))
                elif isinstance(value, list):
                    for item in value:
                        if isinstance(item, dict):
                            for sub_key, sub_value in item.items():
                                headers.append(f"{key} - {sub_key}")
                                values.append(str(sub_value))
                        else:
                            headers.append(key)
                            values.append(str(item))
                else:
                    headers.append(key)
                    values.append(str(value))

            # Add approval columns
            headers.extend(['Sales Approval', 'Customer Approval'])
            values.extend(['Pending', 'Pending'])

            # Prepare the data for the sheet
            sheet_data = [
                headers,  # First row: headers
                values    # Second row: values
            ]

            # Update the sheet with data
            body = {
                'values': sheet_data
            }

            self.sheets_service.spreadsheets().values().update(
                spreadsheetId=sheet_id,
                range='A1:ZZ2',  # Expanded range to accommodate all columns
                valueInputOption='RAW',
                body=body
            ).execute()

            # Format the headers (make them bold and add background color)
            requests = [{
                'repeatCell': {
                    'range': {
                        'sheetId': 0,  # First sheet
                        'startRowIndex': 0,
                        'endRowIndex': 1,
                        'startColumnIndex': 0,
                        'endColumnIndex': len(headers)
                    },
                    'cell': {
                        'userEnteredFormat': {
                            'backgroundColor': {
                                'red': 0.9,
                                'green': 0.9,
                                'blue': 0.9
                            },
                            'textFormat': {
                                'bold': True
                            }
                        }
                    },
                    'fields': 'userEnteredFormat(backgroundColor,textFormat)'
                }
            },
            # Add conditional formatting for approval columns
            {
                'addConditionalFormatRule': {
                    'rule': {
                        'ranges': [{
                            'sheetId': 0,
                            'startRowIndex': 1,
                            'endRowIndex': 2,
                            'startColumnIndex': len(headers) - 2,  # Sales Approval column
                            'endColumnIndex': len(headers)  # Until Customer Approval column
                        }],
                        'booleanRule': {
                            'condition': {
                                'type': 'TEXT_EQ',
                                'values': [{'userEnteredValue': 'Approved'}]
                            },
                            'format': {
                                'backgroundColor': {
                                    'red': 0.7,
                                    'green': 0.9,
                                    'blue': 0.7
                                }
                            }
                        }
                    }
                }
            }]

            # Auto-resize columns to fit content
            requests.append({
                'autoResizeDimensions': {
                    'dimensions': {
                        'sheetId': 0,
                        'dimension': 'COLUMNS',
                        'startIndex': 0,
                        'endIndex': len(headers)
                    }
                }
            })

            # Execute formatting requests
            self.sheets_service.spreadsheets().batchUpdate(
                spreadsheetId=sheet_id,
                body={'requests': requests}
            ).execute()

            return {
                'sheet_id': spreadsheet['id'],
                'sheet_web_view_link': spreadsheet['webViewLink']
            }

        except Exception as e:
            logger.error(f"Failed to create and populate sheet: {str(e)}")
            raise

    def share_file(self, file_id: str, email: str, role: str = 'writer') -> Dict[str, Any]:
        """
        Share a file or folder with specific email address

        Args:
            file_id: The ID of the file or folder to share
            email: The email address to share with
            role: The role to grant ('writer', 'reader', or 'commenter')

        Returns:
            The permission resource
        """
        try:
            user_permission = {
                'type': 'user',
                'role': role,
                'emailAddress': email
            }

            result = self.service.permissions().create(
                fileId=file_id,
                body=user_permission,
                sendNotificationEmail=True,
                supportsAllDrives=True,
                fields='id'
            ).execute()

            logger.info(f"Shared file/folder {file_id} with {email} as {role}")
            return result

        except Exception as e:
            logger.error(f"Failed to share file {file_id} with {email}: {str(e)}")
            raise

    def share_file_with_domain(self, file_id: str, domain: str, role: str = 'reader') -> Dict[str, Any]:
        """
        Share a file or folder with anyone from a specific domain who has the link

        Args:
            file_id: The ID of the file or folder to share
            domain: The domain to allow access (e.g., 'iopex.com')
            role: The role to grant ('reader', 'writer', or 'commenter')

        Returns:
            The permission resource
        """
        try:
            domain_permission = {
                'type': 'domain',
                'role': role,
                'domain': domain,
                'allowFileDiscovery': False  # Requires link to access, not discoverable in domain
            }

            result = self.service.permissions().create(
                fileId=file_id,
                body=domain_permission,
                sendNotificationEmail=False,  # Don't send notifications for domain sharing
                supportsAllDrives=True,
                fields='id'
            ).execute()

            logger.info(f"Shared file/folder {file_id} with domain {domain} as {role} (link required)")
            return result

        except Exception as e:
            logger.error(f"Failed to share file {file_id} with domain {domain}: {str(e)}")
            raise

    def get_sheet_data(self, sheet_id: str) -> Dict[str, Any]:
        """
        Get data from a Google Sheet and convert it to template variables format.
        The sheet now has multiple rows (one per placement) with headers in first row.
        """
        try:
            # First, get all data to determine how many rows we have
            result = self.sheets_service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range='A1:AA100',  # Get more rows to capture all placements
                majorDimension='ROWS'
            ).execute()

            values = result.get('values', [])
            if len(values) < 2:
                raise ValueError("Sheet does not contain enough data")

            headers = values[0]  # First row contains headers
            data_rows = values[1:]  # All subsequent rows contain placement data

            # Process multiple placement rows
            placements = []
            order_data = {}

            for row_data in data_rows:
                if not any(row_data):  # Skip empty rows
                    continue

                # Pad row_data to match headers length
                while len(row_data) < len(headers):
                    row_data.append('')

                # Create a dictionary mapping headers to values for this row
                raw_data = dict(zip(headers, row_data))

                # Extract order-level data (same for all rows, so we'll use the first row's data)
                if not order_data:
                    order_data = {
                        'order_number': raw_data.get('Order Number', ''),
                        'brand': raw_data.get('Brand', ''),
                        'campaign_name': raw_data.get('Campaign Name', ''),
                        'customer_approver': raw_data.get('Customer Approver', ''),
                        'customer_approver_email': raw_data.get('Customer Approver Email', ''),
                        'sales_owner': raw_data.get('Sales Owner', ''),
                        'sales_owner_email': raw_data.get('Sales Owner Email', ''),
                        'fulfillment_owner': raw_data.get('Fulfillment Owner', ''),
                        'fulfillment_owner_email': raw_data.get('Fulfillment Owner Email', ''),
                        'objective_description': raw_data.get('objective_description', ''),
                    }

                # Extract placement-specific data
                placement_data = {
                    'name': raw_data.get('Placement Name', ''),
                    'destination': raw_data.get('Placement Destination', ''),
                    'start_date': raw_data.get('Start Date', ''),
                    'end_date': raw_data.get('End Date', ''),
                    'impressions': raw_data.get('Metrics - Impressions', ''),
                    'clicks': raw_data.get('Metrics - Clicks', ''),
                    'cpm': raw_data.get('bid_rate - cpm', ''),
                    'cpc': raw_data.get('bid_rate - cpc', ''),
                    'budget_amount': raw_data.get('Budget Amount', ''),
                    'age_range': raw_data.get('target audience - age_range', ''),
                    'gender': raw_data.get('target audience - gender', ''),
                    'income_level': raw_data.get('target audience - income level', ''),
                    'interests': raw_data.get('target audience - interests', ''),
                    'location': raw_data.get('target audience - location', ''),
                    'behavioral_data': raw_data.get('target_audience - behavioral_data', ''),
                }
                placements.append(placement_data)

            # Create aggregated template data for PDF generation
            total_impressions = sum(int(p.get('impressions', 0) or 0) for p in placements)
            total_clicks = sum(int(p.get('clicks', 0) or 0) for p in placements)
            total_budget = sum(float(p.get('budget_amount', 0) or 0) for p in placements)

            # Get date range
            start_dates = [p.get('start_date', '') for p in placements if p.get('start_date')]
            end_dates = [p.get('end_date', '') for p in placements if p.get('end_date')]
            earliest_start = min(start_dates) if start_dates else ""
            latest_end = max(end_dates) if end_dates else ""

            # Create detailed placement information
            placement_details = []
            media_plan_table_rows = []

            for i, p in enumerate(placements, 1):
                detail = f"""
Placement {i}: {p.get('name', '')}
  Destination: {p.get('destination', '')}
  Duration: {p.get('start_date', '')} - {p.get('end_date', '')}
  Metrics: {p.get('impressions', ''):,} impressions, {p.get('clicks', ''):,} clicks
  Bid Rate: ${p.get('cpm', '')} CPM, ${p.get('cpc', '')} CPC
  Budget: ${float(p.get('budget_amount', 0) or 0):,.2f}
  Target Audience:
    - Age Range: {p.get('age_range', '')}
    - Gender: {p.get('gender', '')}
    - Income Level: {p.get('income_level', '')}
    - Interests: {p.get('interests', '')}
    - Location: {p.get('location', '')}
    - Behavioral Data: {p.get('behavioral_data', '')}
                """.strip()
                placement_details.append(detail)

                # Create table row for media plan table with the required headers:
                # budget, start date, end date, placement name, placement destination, targeting,
                # objective description, target impressions, target clicks, cpm, cpc
                targeting_summary = f"{p.get('age_range', '')}, {p.get('gender', '')}, {p.get('income_level', '')}, {p.get('location', '')}, {p.get('interests', '')}, {p.get('behavioral_data', '')}"
                budget_amount = float(p.get('budget_amount', 0) or 0)

                table_row = [
                    f"${budget_amount:,.2f}",  # budget
                    p.get('start_date', ''),  # start date
                    p.get('end_date', ''),  # end date
                    p.get('name', ''),  # placement name
                    p.get('destination', ''),  # placement destination
                    targeting_summary,  # targeting
                    order_data.get('objective_description', ''),  # objective description
                    p.get('impressions', ''),  # target impressions
                    p.get('clicks', ''),  # target clicks
                    f"${p.get('cpm', '')}",  # cpm
                    f"${p.get('cpc', '')}"  # cpc
                ]
                media_plan_table_rows.append(table_row)

            # Create media plan table data structure
            media_plan_table = {
                'headers': [
                    'Budget',
                    'Start Date',
                    'End Date',
                    'Placement Name',
                    'Placement Destination',
                    'Targeting',
                    'Objective Description',
                    'Target Impressions',
                    'Target Clicks',
                    'CPM',
                    'CPC'
                ],
                'rows': media_plan_table_rows
            }

            template_data = {
                **order_data,
                'start_date': earliest_start,
                'end_date': latest_end,
                'placement_details': "\n\n".join(placement_details),
                'media_plan_table': media_plan_table,  # New table structure
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
                'device_targeting': 'All Devices',
                'generation_date': datetime.now().strftime("%Y-%m-%d")
            }

            logger.info(f"Successfully extracted sheet data for {len(placements)} placements")
            return template_data

        except Exception as e:
            logger.error(f"Error getting sheet data: {str(e)}")
            raise

    def get_file_name(self, file_id: str) -> str:
        """
        Get the name of a file from Google Drive
        """
        try:
            file = self.service.files().get(
                fileId=file_id,
                supportsAllDrives=True,
                fields='name'
            ).execute()
            return file.get('name', '')
        except Exception as e:
            logger.error(f"Error getting file name: {str(e)}")
            raise