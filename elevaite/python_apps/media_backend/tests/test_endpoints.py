#!/usr/bin/env python3
"""
Enhanced test script for Media Backend insertion order and campaign management endpoints with webhook testing.

This script tests the Media Backend API endpoints:
1. Insertion order updates (approval status, field updates)
2. Campaign creation with placements
3. Campaign updates (status changes, placement updates)
4. Webhook endpoints for Salesforce integration
5. Real data scenarios using Salesforce account IO data

Location: python_apps/media_backend/tests/
Target: Media Backend API at http://localhost:8000

Usage:
    cd python_apps/media_backend/tests/
    python test_endpoints.py

Requirements:
    pip install requests
"""

import requests
import json
from datetime import datetime, date, timedelta
from typing import Dict, Any, Optional

# Configuration
BASE_URL = "http://localhost:8000"
HEADERS = {
    "Content-Type": "application/json",
    # Add authentication headers if needed
    # "Authorization": "Bearer YOUR_API_TOKEN"
}

# Real Salesforce data from the provided example
SALESFORCE_TEST_DATA = {
    "insertion_order_id": "2c44b537-106a-40f2-b52f-818b340eb69c",
    "order_number": "IO-504509-4497",
    "salesforce_io_id": "a00Qy00001723i1IAA",
    "salesforce_account_id": "001Qy00001GFCn7IAH",
    "salesforce_opportunity_id": "006Qy00000I6n6vIAB",
    "brand": "Accenture",
    "campaign_name": "Tesging A1",
    "sales_owner": "Vishnu Krishnan",
    "sales_owner_email": "vishnu.krishnan@iopex.com"
}

class EndpointTester:
    def __init__(self, base_url: str = BASE_URL):
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        
    def log(self, message: str, level: str = "INFO"):
        """Log messages with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        print(f"[{timestamp}] {level}: {message}")
        
    def make_request(self, method: str, endpoint: str, data: Optional[Dict] = None) -> Dict[str, Any]:
        """Make HTTP request and return response"""
        url = f"{self.base_url}{endpoint}"
        
        try:
            if method.upper() == "GET":
                response = self.session.get(url)
            elif method.upper() == "POST":
                response = self.session.post(url, json=data)
            elif method.upper() == "PUT":
                response = self.session.put(url, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")
                
            self.log(f"{method} {endpoint} - Status: {response.status_code}")
            
            if response.status_code >= 400:
                self.log(f"Error response: {response.text}", "ERROR")
            else:
                # Log successful response summary
                if data and response.content:
                    response_data = response.json()
                    if isinstance(response_data, dict):
                        if "id" in response_data:
                            self.log(f"Response ID: {response_data['id']}")
                        if "message" in response_data:
                            self.log(f"Response message: {response_data['message']}")
                
            return {
                "status_code": response.status_code,
                "data": response.json() if response.content else None,
                "success": 200 <= response.status_code < 300
            }
            
        except requests.exceptions.RequestException as e:
            self.log(f"Request failed: {e}", "ERROR")
            return {"status_code": 0, "data": None, "success": False, "error": str(e)}
        except json.JSONDecodeError as e:
            self.log(f"JSON decode error: {e}", "ERROR")
            return {"status_code": response.status_code, "data": None, "success": False, "error": "Invalid JSON response"}

    def test_salesforce_approval_via_update(self):
        """Test Salesforce approval using the main insertion order update endpoint with Salesforce IO ID"""
        self.log("=== Testing Salesforce Approval via Update Endpoint ===")

        # Test Salesforce approval using the main update endpoint with Salesforce IO ID
        approval_payload = {
            "status": "approved",
            "customer_approver": "John Smith",
            "customer_approver_email": "john.smith@accenture.com",
            "update_reason": "Approved via Salesforce workflow - Q3 campaign launch",
            "updated_by": "salesforce_webhook",
            "sales_owner": SALESFORCE_TEST_DATA["sales_owner"],
            "sales_owner_email": SALESFORCE_TEST_DATA["sales_owner_email"]
        }

        # Use Salesforce IO ID instead of internal insertion order ID
        salesforce_io_id = SALESFORCE_TEST_DATA["salesforce_io_id"]
        self.log(f"Using Salesforce IO ID: {salesforce_io_id}")

        result = self.make_request("POST", f"/insertion-orders/{salesforce_io_id}/update?source=salesforce", approval_payload)
        if result["success"]:
            self.log("✓ Successfully processed Salesforce approval via update endpoint")
            if result["data"]:
                self.log(f"  - Internal IO ID: {result['data'].get('id')}")
                self.log(f"  - Salesforce IO ID: {result['data'].get('salesforce_io_id')}")
                self.log(f"  - Previous status: {result['data'].get('previous_status')}")
                self.log(f"  - New status: {result['data'].get('new_status')}")
        else:
            self.log("✗ Failed to process Salesforce approval via update endpoint", "ERROR")

    def test_insertion_order_update(self, use_salesforce_id: bool = True):
        """Test insertion order update endpoint using real Salesforce data"""
        self.log("=== Testing Media Backend Insertion Order Updates ===")

        if use_salesforce_id:
            order_id = SALESFORCE_TEST_DATA["salesforce_io_id"]
            source = "salesforce"
            self.log(f"Testing with Salesforce IO ID: {order_id}")
        else:
            order_id = SALESFORCE_TEST_DATA["insertion_order_id"]
            source = "google_drive"
            self.log(f"Testing with internal insertion order ID: {order_id}")

        # Test 1: Update status to pending
        test_data = {
            "status": "draft",
            "update_reason": "Submitting for client review - Accenture campaign",
            "updated_by": SALESFORCE_TEST_DATA["sales_owner"]
        }

        result = self.make_request("POST", f"/insertion-orders/{order_id}/update?source={source}", test_data)
        if result["success"]:
            self.log("✓ Successfully updated to pending approval")
        else:
            self.log("✗ Failed to update to pending approval", "ERROR")

        # Test 2: Approve with additional details using Salesforce data
        test_data = {
            "status": "approved",
            "customer_approver": "John Smith",
            "customer_approver_email": "john.smith@accenture.com",
            "sales_owner": SALESFORCE_TEST_DATA["sales_owner"],
            "sales_owner_email": SALESFORCE_TEST_DATA["sales_owner_email"],
            "brand": SALESFORCE_TEST_DATA["brand"],
            "campaign_name": SALESFORCE_TEST_DATA["campaign_name"],
            "update_reason": "Client approved Accenture Tesging A1 campaign",
            "updated_by": SALESFORCE_TEST_DATA["sales_owner"]
        }

        result = self.make_request("POST", f"/insertion-orders/{order_id}/update?source={source}", test_data)
        if result["success"]:
            self.log("✓ Successfully approved insertion order with budget update")
            if result["data"] and source == "salesforce":
                self.log(f"  - Salesforce IO ID: {result['data'].get('salesforce_io_id')}")
        else:
            self.log("✗ Failed to approve insertion order", "ERROR")

    def test_campaign_creation(self):
        """Test campaign creation with Kevel ID and Salesforce IO ID"""
        self.log("=== Testing Campaign Creation with Kevel ID and Salesforce IO ID ===")

        # Generate test Kevel ID
        kevel_id = f"kevel-test-{datetime.now().strftime('%H%M%S')}"
        salesforce_io_id = SALESFORCE_TEST_DATA["salesforce_io_id"]

        self.log(f"Using Kevel ID: {kevel_id}")
        self.log(f"Using Salesforce IO ID: {salesforce_io_id}")

        # Create campaign with only placement data in body (matching campaign_placements table)
        campaign_data = {
            "placements": [
                {
                    "flight_id": f"flight-test-{datetime.now().strftime('%H%M%S')}",
                    "start_date": (date.today() + timedelta(days=3)).isoformat(),
                    "end_date": (date.today() + timedelta(days=33)).isoformat(),
                    "impressions_booked": 300000,
                    "impressions_delivered": 0,
                    "booked_clicks": 10000,
                    "delivered_clicks": 0,
                    "ctr": 0.0,
                    "budget": 6000.00,
                    "cpm": 20.00,
                    "cpc": 0.60
                }
            ]
        }

        # Use path parameters for kevel_id and salesforce_io_id
        result = self.make_request("POST", f"/campaigns/{kevel_id}/{salesforce_io_id}", campaign_data)
        if result["success"]:
            self.log("✓ Successfully created campaign with Kevel ID and Salesforce IO ID")
            if result["data"]:
                self.log(f"  - Campaign ID: {result['data'].get('id')}")
                self.log(f"  - Campaign Name: {result['data'].get('name')}")
                self.log(f"  - Kevel ID: {kevel_id}")
                self.log(f"  - Status: {result['data'].get('status')}")
                self.log(f"  - Placement Count: {result['data'].get('placement_count')}")
                self.log(f"  - Total Budget: ${result['data'].get('total_budget')}")
            return result["data"].get("id")
        else:
            self.log("✗ Failed to create campaign", "ERROR")
            return None

    def test_health_check(self):
        """Test Media Backend health check endpoint"""
        self.log("=== Testing Media Backend Health Check ===")

        result = self.make_request("GET", "/hc")
        if result["success"]:
            self.log("✓ Health check passed")
            if result["data"]:
                self.log(f"  - Status: {result['data'].get('status')}")
                self.log(f"  - IO Service: {result['data'].get('insertion_order_service')}")
                self.log(f"  - OAuth: {result['data'].get('oauth_credentials')}")
        else:
            self.log("✗ Health check failed", "ERROR")

    def run_all_tests(self, insertion_order_id: Optional[str] = None, test_salesforce: bool = True):
        """Run all Media Backend endpoint tests"""
        self.log("Starting comprehensive Media Backend endpoint tests...")
        self.log(f"Base URL: {self.base_url}")
        self.log(f"Using Salesforce test data:")
        self.log(f"  - Order: {SALESFORCE_TEST_DATA['order_number']}")
        self.log(f"  - Campaign: {SALESFORCE_TEST_DATA['campaign_name']}")
        self.log(f"  - Brand: {SALESFORCE_TEST_DATA['brand']}")

        # Test health check first
        self.test_health_check()

        # Test Salesforce integration if enabled
        if test_salesforce:
            self.test_salesforce_approval_via_update()

        # Test insertion order updates
        if insertion_order_id:
            # Test with both Salesforce ID and Google Drive ID if provided
            self.log("Testing with custom insertion order ID (assuming Google Drive)")
            self.test_insertion_order_update(use_salesforce_id=False)
        else:
            # Use the default Salesforce test data
            self.log("Testing with default Salesforce IO ID")
            self.test_insertion_order_update(use_salesforce_id=True)

        # Test campaign creation
        campaign_id = self.test_campaign_creation()
        if campaign_id:
            self.log(f"Campaign created successfully: {campaign_id}")
        else:
            self.log("Campaign creation failed", "WARN")

        self.log("=== Test Summary ===")
        self.log("All Media Backend tests completed. Check the logs above for results.")
        self.log("Note: Some tests may fail if the insertion order doesn't exist in the database.")

def main():
    """Main function to run Media Backend tests"""
    print("Media Backend API Test Script")
    print("=" * 40)
    print(f"Target: {BASE_URL}")
    print("This script tests Media Backend webhooks and API endpoints using real Salesforce data")
    print()
    
    # Show default test data
    print("Default Salesforce Test Data:")
    print(f"  - Insertion Order: {SALESFORCE_TEST_DATA['order_number']}")
    print(f"  - Campaign: {SALESFORCE_TEST_DATA['campaign_name']}")
    print(f"  - Brand: {SALESFORCE_TEST_DATA['brand']}")
    print(f"  - Sales Owner: {SALESFORCE_TEST_DATA['sales_owner']}")
    print(f"  - Salesforce IO ID: {SALESFORCE_TEST_DATA['salesforce_io_id']}")
    print(f"  - Account ID: {SALESFORCE_TEST_DATA['salesforce_account_id']}")
    print(f"  - Opportunity ID: {SALESFORCE_TEST_DATA['salesforce_opportunity_id']}")
    print()
    
    # Get options from user
    print("Test Options:")
    print("1. Use default Salesforce insertion order ID")
    print("2. Enter a different insertion order ID")
    print("3. Skip insertion order tests")
    
    choice = input("Choose option (1-3) [default: 1]: ").strip()
    
    insertion_order_id = None
    if choice == "2":
        insertion_order_id = input("Enter insertion order ID: ").strip()
        if not insertion_order_id:
            print("No ID provided, using default")
            insertion_order_id = None
    elif choice == "3":
        insertion_order_id = "SKIP"
    
    # Ask about Salesforce testing
    test_salesforce = input("Test Salesforce integration? (y/n) [default: y]: ").strip().lower()
    test_salesforce = test_salesforce != "n"
    
    print()
    print("Starting tests...")
    print()

    # Create tester and run tests
    tester = EndpointTester()
    
    try:
        if insertion_order_id == "SKIP":
            tester.run_all_tests(None, test_salesforce)
        else:
            tester.run_all_tests(insertion_order_id, test_salesforce)
    except KeyboardInterrupt:
        print("\nTests interrupted by user")
    except Exception as e:
        print(f"Test execution failed: {e}")

if __name__ == "__main__":
    main()
