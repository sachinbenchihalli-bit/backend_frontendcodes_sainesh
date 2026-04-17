from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from datetime import datetime
import logging
import os
from contextlib import asynccontextmanager
from dotenv import load_dotenv


# Import models and classes from the separate file
from models import (
    OrderGenerationRequest,
    InsertionOrderResponse,
    SalesforceManager
)

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global Salesforce manager instance
sf_manager = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    global sf_manager
    sf_manager = SalesforceManager()
    yield
    # Shutdown
    sf_manager = None

# FastAPI app
app = FastAPI(
    title="Insertion Order API",
    description="API for managing Insertion Orders in Salesforce",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Dependency to get Salesforce manager
def get_sf_manager():
    if sf_manager is None:
        raise HTTPException(status_code=500, detail="Salesforce connection not available")
    return sf_manager

@app.get("/")
async def root():
    return {"message": "Insertion Order API is running"}

@app.get("/health")
async def health_check(sf: SalesforceManager = Depends(get_sf_manager)):
    """Health check endpoint"""
    sf_status = sf.test_connection()
    return {
        "status": "healthy" if sf_status else "unhealthy",
        "salesforce_connection": sf_status,
        "timestamp": datetime.now().isoformat()
    }

# NEW FRONTEND-COMPATIBLE ENDPOINT
@app.post("/generate-insertion-order", response_model=InsertionOrderResponse)
async def generate_insertion_order_frontend(
    order_request: OrderGenerationRequest,
    sf: SalesforceManager = Depends(get_sf_manager)
):
    """Create a new Insertion Order using frontend structure"""
    try:
        result = sf.create_insertion_order_from_frontend(order_request)
        
        return InsertionOrderResponse(
            id=result['id'],
            order_number=order_request.OrderNo,
            status="created",
            message="Insertion Order created successfully from frontend"
        )
    except Exception as e:
        logger.error(f"Error creating Insertion Order from frontend: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/insertion-orders/{record_id}")
async def get_insertion_order(
    record_id: str,
    sf: SalesforceManager = Depends(get_sf_manager)
):
    """Get a specific Insertion Order by ID"""
    try:
        result = sf.get_insertion_order(record_id)
        return result
    except Exception as e:
        logger.error(f"Error retrieving Insertion Order: {str(e)}")
        raise HTTPException(status_code=404, detail="Insertion Order not found")

@app.get("/insertion-orders")
async def list_insertion_orders(
    limit: int = 100,
    sf: SalesforceManager = Depends(get_sf_manager)
):
    """List Insertion Orders"""
    try:
        result = sf.list_insertion_orders(limit)
        return {"records": result}
    except Exception as e:
        logger.error(f"Error listing Insertion Orders: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/accounts")
async def get_accounts(sf: SalesforceManager = Depends(get_sf_manager)):
    """Get list of Accounts for dropdown population"""
    try:
        query = "SELECT Id, Name FROM Account ORDER BY Name LIMIT 1000"
        result = sf.sf.query(query)
        return result['records']
    except Exception as e:
        logger.error(f"Error fetching accounts: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching accounts: {str(e)}")

@app.get("/opportunities")
async def get_opportunities(sf: SalesforceManager = Depends(get_sf_manager)):
    """Get list of Opportunities for dropdown population"""
    try:
        query = """SELECT Id, Name, StageName, Amount, CloseDate, Account.Name, 
                          Account__c, Account__r.Name
                   FROM Opportunity 
                   ORDER BY Name 
                   LIMIT 1000"""
        result = sf.sf.query(query)
        return result['records']
    except Exception as e:
        logger.error(f"Error fetching opportunities: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching opportunities: {str(e)}")

@app.get("/opportunities-by-account/{account_id}")
async def get_opportunities_by_account(account_id: str, sf: SalesforceManager = Depends(get_sf_manager)):
    """Get opportunities associated with a specific account"""
    try:
        # Validate the account ID format
        if not sf.is_valid_salesforce_id(account_id):
            raise HTTPException(status_code=400, detail="Invalid Salesforce Account ID format")
        
        # Query using both standard AccountId and custom Account__c lookup field
        query = f"""SELECT Id, Name, StageName, Amount, CloseDate, Type, Description,
                           AccountId, Account.Name, Account__c, Account__r.Name
                    FROM Opportunity 
                    WHERE AccountId = '{account_id}' OR Account__c = '{account_id}'
                    ORDER BY Name
                    LIMIT 1000"""
        result = sf.sf.query(query)
        return result['records']
    except Exception as e:
        logger.error(f"Error fetching opportunities for account {account_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching opportunities: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    # Get port from environment variable, default to 7999
    port = int(os.getenv("PORT", "7999"))
    uvicorn.run(app, host="0.0.0.0", port=port)