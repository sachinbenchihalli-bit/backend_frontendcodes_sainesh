from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
import io
from datetime import datetime
import logging
from typing import Dict, Any, Optional
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

class PDFGenerator:
    def __init__(self, credentials=None):
        """Initialize with OAuth credentials - REQUIRED"""
        if not credentials:
            raise ValueError("OAuth credentials are required for PDFGenerator")

        self.credentials = credentials
        self.docs_service = None
        self.drive_service = None
        self._build_services()

    def update_credentials(self, credentials):
        """Update credentials and rebuild services"""
        self.credentials = credentials
        self._build_services()

    def _build_services(self):
        """Build Google services with current credentials"""
        self.docs_service = build('docs', 'v1', credentials=self.credentials)
        self.drive_service = build('drive', 'v3', credentials=self.credentials)

    async def generate(
        self,
        template_variables: Dict[str, Any],
        output_folder_id: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate PDF from template and save to Drive
        """
        try:
            pdf_template_id = os.getenv("PDF_GENERATION_TEMPLATE_ID")
            if not pdf_template_id:
                raise ValueError("PDF_GENERATION_TEMPLATE_ID not configured")

            logger.info(f"Using template ID: {pdf_template_id}")

            # 1. Create a copy of the template
            copied_doc = self.drive_service.files().copy(
                fileId=pdf_template_id,
                body={
                    'name': f'Generated_IO_{datetime.now().strftime("%Y%m%d_%H%M%S")}',
                    'parents': [output_folder_id]
                },
                supportsAllDrives=True
            ).execute()

            doc_id = copied_doc['id']

            # 2. Handle regular text replacements first (excluding media_plan_table)
            requests = []
            table_data = None

            for key, value in template_variables.items():
                if key == 'media_plan_table':
                    # Store table data for special handling
                    table_data = value
                else:
                    # Regular text replacement
                    requests.append({
                        'replaceAllText': {
                            'containsText': {
                                'text': '{{' + key + '}}',
                                'matchCase': True
                            },
                            'replaceText': str(value)
                        }
                    })

            # Execute regular text replacements first
            if requests:
                self.docs_service.documents().batchUpdate(
                    documentId=doc_id,
                    body={'requests': requests}
                ).execute()

            # Handle table insertion if media_plan_table data exists
            if table_data:
                await self._insert_media_plan_table(doc_id, table_data)

            # 3. Export as PDF
            pdf_response = self.drive_service.files().export(
                fileId=doc_id,
                mimeType='application/pdf'
            ).execute()

            # 4. Create PDF file in Drive
            pdf_filename = filename or f'IO_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
            file_metadata = {
                'name': f'{pdf_filename}.pdf',
                'parents': [output_folder_id],
                'mimeType': 'application/pdf'
            }

            # Create a BytesIO object from the PDF content
            pdf_file = io.BytesIO(pdf_response)

            # Upload PDF to Drive
            media = MediaIoBaseUpload(
                pdf_file,
                mimetype='application/pdf',
                resumable=True
            )

            pdf_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
                fields='id, webViewLink'
            ).execute()

            # 5. Delete the temporary Google Doc
            self.drive_service.files().delete(
                fileId=doc_id,
                supportsAllDrives=True
            ).execute()

            return {
                'status': 'success',
                'pdf_file_id': pdf_file['id'],
                'pdf_web_view_link': pdf_file['webViewLink']
            }

        except Exception as e:
            logger.error(f"Error generating PDF: {str(e)}")
            raise

    async def generate_media_plan_pdf(
        self,
        media_plan_content: str,
        output_folder_id: str,
        filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generate PDF from media plan markdown content using HTML conversion
        Converts markdown to HTML and uploads to Google Drive as a Google Doc
        """
        try:
            logger.info("Generating media plan PDF using HTML conversion")

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            doc_name = filename or f'MediaPlan_{timestamp}'

            # Step 1: Convert markdown to styled HTML
            html_content = self._convert_markdown_to_html(media_plan_content)
            logger.info("Converted markdown to HTML")

            # Step 2: Upload HTML as Google Doc (automatic conversion)
            doc_file = self._upload_html_as_google_doc(html_content, output_folder_id, doc_name)
            doc_id = doc_file['id']
            logger.info(f"Created Google Doc from HTML: {doc_id}")

            # Wait a moment for conversion to complete
            import time
            time.sleep(1)

            # Export as PDF
            pdf_response = self.drive_service.files().export(
                fileId=doc_id,
                mimeType='application/pdf'
            ).execute()

            # Create PDF file in Drive
            pdf_filename = f'{doc_name}.pdf'
            file_metadata = {
                'name': pdf_filename,
                'parents': [output_folder_id],
                'mimeType': 'application/pdf'
            }

            # Create a BytesIO object from the PDF content
            pdf_file = io.BytesIO(pdf_response)

            # Upload PDF to Drive
            media = MediaIoBaseUpload(
                pdf_file,
                mimetype='application/pdf',
                resumable=True
            )

            pdf_file = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                supportsAllDrives=True,
                fields='id, webViewLink'
            ).execute()

            # Clean up the temporary document
            self.drive_service.files().delete(
                fileId=doc_id,
                supportsAllDrives=True
            ).execute()

            logger.info(f"Media plan PDF generated successfully: {pdf_file['id']}")

            return {
                'status': 'success',
                'pdf_file_id': pdf_file['id'],
                'pdf_web_view_link': pdf_file['webViewLink']
            }

        except Exception as e:
            logger.error(f"Error generating media plan PDF: {str(e)}")
            raise

    def _convert_markdown_to_html(self, markdown_content: str) -> str:
        """
        Convert markdown content to styled HTML that matches frontend appearance
        """
        import re

        logger.info("Converting markdown to HTML")

        # Find "Media Plan" and extract content from that point
        media_plan_start = markdown_content.find("Media Plan")
        if media_plan_start != -1:
            # Find the start of the line containing "Media Plan"
            line_start = markdown_content.rfind('\n', 0, media_plan_start)
            if line_start == -1:
                line_start = 0
            else:
                line_start += 1  # Move past the newline
            markdown_content = markdown_content[line_start:]
            logger.info("Extracted content starting from 'Media Plan'")
        else:
            logger.warning("'Media Plan' not found in content, using full content")

        # Start with HTML document structure with improved styling
        html = """<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
</head>
<body style="font-size: 16px;">
"""

        # Convert markdown content to HTML with proper section grouping
        lines = markdown_content.split('\n')
        in_table = False
        current_section = []
        sections = []

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Check if this is a header that should start a new section
            if (line.startswith('# ') or line.startswith('## ') or line.startswith('### ')) and current_section:
                # Save current section
                sections.append(current_section)
                current_section = []

            # Add line to current section
            current_section.append(lines[i])
            i += 1

        # Add the last section
        if current_section:
            sections.append(current_section)

        # Process each section
        for section_lines in sections:
            html += '<div class="section">\n'
            in_table = False

            for line in section_lines:
                line = line.strip()

                if not line:
                    if not in_table:
                        html += "<br>\n"
                    continue

                # Handle headers
                if line.startswith('### '):
                    if in_table:
                        html += "</tbody>\n</table></center>\n"
                        in_table = False
                    html += f'<h4 style="font-size: 22px; font-weight: bold;">{line[4:].strip()}</h3>\n'
                elif line.startswith('## '):
                    if in_table:
                        html += "</tbody>\n</table>\n"
                        in_table = False
                    html += f'<h3 style="font-size: 26px; font-weight: bold;">{line[3:].strip()}</h2>\n'
                elif line.startswith('# '):
                    if in_table:
                        html += "</tbody>\n</table>\n"
                        in_table = False
                    html += f'<h2 style="font-size: 32px; font-weight: bold; color: #333;">{line[2:].strip()}</h1>\n'

                # Handle tables
                elif line.startswith('|') and '|' in line[1:]:
                    if not in_table:
                        # Start of table
                        in_table = True
                        html += '<table style="font-size: 16px;">\n'

                        # Parse header row
                        cells = [cell.strip() for cell in line.split('|')[1:-1]]
                        html += "<thead><tr>\n"
                        for cell in cells:
                            html += f'<th style="font-size: 16px; padding: 10px; border: 1px solid #ccc; background-color: #f8f9fa; font-weight: bold;">{cell}</th>\n'
                        html += "</tr></thead>\n<tbody>\n"

                    elif line.startswith('|---') or line.startswith('|-'):
                        # Table separator row, skip
                        continue

                    else:
                        # Data row
                        cells = [cell.strip() for cell in line.split('|')[1:-1]]
                        html += "<tr>\n"
                        for cell in cells:
                            # Handle basic markdown formatting in cells
                            cell = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', cell)
                            cell = re.sub(r'\*(.*?)\*', r'<em>\1</em>', cell)
                            html += f'<td style="font-size: 14px; padding: 8px; border: 1px solid #ccc;">{cell}</td>\n'
                        html += "</tr>\n"

                # Handle HTML comments (skip them)
                elif line.startswith('<!--') and line.endswith('-->'):
                    continue

                else:
                    # End table if we were in one
                    if in_table:
                        html += "</tbody>\n</table>\n"
                        in_table = False

                    # Regular paragraph
                    if line:
                        # Handle basic markdown formatting
                        line = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', line)
                        line = re.sub(r'\*(.*?)\*', r'<em>\1</em>', line)
                        html += f'<p style="font-size: 18px;">{line}</p>\n'

            # Close any open table at end of section
            if in_table:
                html += "</tbody>\n</table>\n"
                in_table = False

            html += '</div>\n'

        # Close HTML document
        html += "</body>\n</html>"

        logger.info("Markdown to HTML conversion completed")
        return html

    def _upload_html_as_google_doc(self, html_content: str, folder_id: str, filename: str) -> Dict[str, Any]:
        """
        Upload HTML content as a Google Doc using Drive API conversion
        """
        logger.info(f"Uploading HTML as Google Doc: {filename}")

        file_metadata = {
            'name': filename,
            'parents': [folder_id],
            'mimeType': 'application/vnd.google-apps.document'  # This triggers HTML conversion
        }

        media = MediaIoBaseUpload(
            io.BytesIO(html_content.encode('utf-8')),
            mimetype='text/html',  # Source is HTML
            resumable=True
        )

        # Upload and convert
        doc_file = self.drive_service.files().create(
            body=file_metadata,
            media_body=media,
            supportsAllDrives=True,
            fields='id, name, webViewLink'
        ).execute()

        logger.info(f"Successfully created Google Doc: {doc_file['id']}")
        return doc_file

    async def _insert_media_plan_table(self, doc_id: str, table_data: Dict[str, Any]):
        """
        Insert a proper Google Docs table using the approach from tanaikech's implementation
        """
        try:
            logger.info("Starting media plan table insertion...")

            # Prepare table data
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])

            if not headers or not rows:
                logger.warning("No table headers or rows provided for media_plan_table")
                self._fallback_text_replacement(doc_id, table_data)
                return

            logger.info(f"Creating table with {len(headers)} columns and {len(rows) + 1} rows")
            logger.info(f"Headers: {headers}")

            # Find the {{media_plan_table}} placeholder
            placeholder_text = "{{media_plan_table}}"
            placeholder_index = self._find_placeholder_index(doc_id, placeholder_text)

            if placeholder_index is None:
                logger.warning("{{media_plan_table}} placeholder not found in document")
                self._fallback_text_replacement(doc_id, table_data)
                return

            logger.info(f"Found placeholder at index {placeholder_index}")

            # Step 1: Replace placeholder with table and populate in one go
            await self._create_and_populate_table(doc_id, placeholder_index, placeholder_text, headers, rows)

        except Exception as e:
            logger.error(f"Error inserting media plan table: {str(e)}")
            # Fallback to simple text replacement
            self._fallback_text_replacement(doc_id, table_data)

    def _find_placeholder_index(self, doc_id: str, placeholder_text: str) -> int:
        """Find the index of the placeholder text in the document"""
        doc = self.docs_service.documents().get(documentId=doc_id).execute()

        for element in doc.get('body', {}).get('content', []):
            if 'paragraph' in element:
                paragraph = element['paragraph']
                for text_element in paragraph.get('elements', []):
                    if 'textRun' in text_element:
                        text_content = text_element['textRun'].get('content', '')
                        if placeholder_text in text_content:
                            return text_element.get('startIndex')
        return None

    async def _create_and_populate_table(self, doc_id: str, placeholder_index: int, placeholder_text: str, headers: list, rows: list):
        """
        Create table and populate it using the Tanaikech approach with calculated indices
        """
        try:
            # Calculate required dimensions
            num_rows = len(rows) + 1  # +1 for header row
            num_cols = len(headers)

            logger.info(f"Creating table with {num_rows} rows and {num_cols} columns")

            # Prepare all table data (headers + rows)
            all_table_data = [headers] + rows

            # Create requests using the Tanaikech approach
            requests = self._create_table_requests(placeholder_index, placeholder_text, all_table_data)

            # Execute all requests in one batch
            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

            logger.info(f"Successfully created and populated table with {len(headers)} headers and {len(rows)} data rows")

        except Exception as e:
            logger.error(f"Error creating and populating table: {str(e)}")
            raise

    def _create_table_requests(self, placeholder_index: int, placeholder_text: str, table_data: list):
        """
        Create requests for table creation and population using the Tanaikech approach
        Based on: https://tanaikech.github.io/2019/05/22/creating-new-table-and-putting-values-to-cells-using-google-docs-api-with-google-apps-script/
        """
        try:
            if not table_data or not table_data[0]:
                return []

            num_rows = len(table_data)
            max_cols = max(len(row) for row in table_data)

            logger.info(f"Creating table requests for {num_rows} rows and {max_cols} columns")

            # Start with deleting the placeholder and creating the table
            requests = [
                {
                    'deleteContentRange': {
                        'range': {
                            'startIndex': placeholder_index,
                            'endIndex': placeholder_index + len(placeholder_text)
                        }
                    }
                },
                {
                    'insertTable': {
                        'location': {'index': placeholder_index},
                        'rows': num_rows,
                        'columns': max_cols
                    }
                }
            ]

            # Calculate cell indices and create insertion requests using the improved Tanaikech approach
            # Based on the updated createRequests_ function from the reference
            table_index = placeholder_index
            index = table_index + 5  # Table starts at index + 5

            cell_requests = []

            # Process each row to calculate indices correctly
            for row_idx, row_data in enumerate(table_data):
                row_index = index + (0 if row_idx == 0 else 3) - 1  # First row: index, subsequent rows: index + 3 - 1

                # Process each cell in the row
                for col_idx, cell_value in enumerate(row_data):
                    cell_index = row_index + col_idx * 2
                    cell_value_str = str(cell_value)

                    logger.info(f"Adding cell [{row_idx}][{col_idx}] = '{cell_value_str}' at index {cell_index}")

                    # Add text insertion request
                    cell_requests.append({
                        'insertText': {
                            'text': cell_value_str,
                            'location': {'index': cell_index}
                        }
                    })

                    # Make header row bold
                    if row_idx == 0:
                        cell_requests.append({
                            'updateTextStyle': {
                                'range': {
                                    'startIndex': cell_index,
                                    'endIndex': cell_index + len(cell_value_str)
                                },
                                'textStyle': {'bold': True},
                                'fields': 'bold'
                            }
                        })

                    index = cell_index + 1

                # Adjust index for missing columns in this row
                if len(row_data) < max_cols:
                    index += (max_cols - len(row_data)) * 2

            # Reverse the cell requests (insert from bottom-right to top-left)
            cell_requests.reverse()

            # Add cell requests to the main requests
            requests.extend(cell_requests)

            logger.info(f"Created {len(requests)} total requests for table creation and population")
            return requests

        except Exception as e:
            logger.error(f"Error creating table requests: {str(e)}")
            raise



    def _fallback_text_replacement(self, doc_id: str, table_data: Dict[str, Any]):
        """
        Fallback method to replace {{media_plan_table}} with formatted text if table insertion fails
        """
        try:
            headers = table_data.get('headers', [])
            rows = table_data.get('rows', [])

            if not headers or not rows:
                fallback_text = "No table data available"
            else:
                # Create a simple text table
                lines = []

                # Add headers
                lines.append(" | ".join(str(header) for header in headers))
                lines.append("-" * 50)  # Separator line

                # Add rows
                for row in rows:
                    if isinstance(row, list):
                        lines.append(" | ".join(str(cell) for cell in row))
                    else:
                        lines.append(str(row))

                fallback_text = "\n".join(lines)

            # Replace the placeholder with formatted text
            requests = [{
                'replaceAllText': {
                    'containsText': {
                        'text': '{{media_plan_table}}',
                        'matchCase': True
                    },
                    'replaceText': fallback_text
                }
            }]

            self.docs_service.documents().batchUpdate(
                documentId=doc_id,
                body={'requests': requests}
            ).execute()

        except Exception as e:
            logger.error(f"Error in fallback text replacement: {str(e)}")

