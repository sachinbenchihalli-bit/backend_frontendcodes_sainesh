from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

# Import routers from modules
from routers import overview, sessions, queries, agents, feedback

load_dotenv()

app = FastAPI(
    title="Media Dashboard API",
    # root path
    root_path="/dashboard/api",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Enable CORS for your frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.getenv("FRONTEND_URL", "https://elevaite-ads.iopex.ai")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root():
    return {"message": "Media Dashboard API is running"}

@app.get("/api/test-db")
def test_database():
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("SELECT COUNT(*) as count FROM sessions")
        result = cur.fetchone()

        cur.close()
        conn.close()

        return {"status": "success", "sessions_count": result['count']}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@app.get("/api/debug/database-inspection")
def debug_database_inspection():
    """Show raw data from database tables to verify real data is being used"""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Dictionary to store our inspection results
        inspection = {}
        
        # 1. Check all tables - get row counts
        tables = ["sessions", "queries", "agent_execution_steps", "feedback", "related_queries"]
        table_counts = {}

        for table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            table_counts[table] = count

        inspection["table_counts"] = table_counts
        
        # 2. Sample data from each table (first 3 rows)
        sample_data = {}
        
        for table in tables:
            if table_counts[table] > 0:
                try:
                    cur.execute(f"SELECT * FROM {table} LIMIT 3")
                    rows = cur.fetchall()
                    
                    # Convert rows to list of dicts for JSON serialization
                    sample_rows = []
                    for row in rows:
                        # Convert any non-serializable values to strings
                        clean_row = {}
                        for key, value in dict(row).items():
                            if hasattr(value, 'isoformat'):  # Handle dates
                                clean_row[key] = value.isoformat()
                            elif value is None:
                                clean_row[key] = None
                            else:
                                clean_row[key] = str(value)
                        sample_rows.append(clean_row)
                    
                    sample_data[table] = sample_rows
                except Exception as e:
                    sample_data[table] = f"Error getting sample: {str(e)}"
            else:
                sample_data[table] = "No data"
        
        inspection["sample_data"] = sample_data
        
        # 3. Session date range
        cur.execute("SELECT MIN(creation_time) as min_date, MAX(creation_time) as max_date FROM sessions")
        date_range = cur.fetchone()

        inspection["date_range"] = {
            "min_date": date_range['min_date'].isoformat() if date_range['min_date'] else None,
            "max_date": date_range['max_date'].isoformat() if date_range['max_date'] else None
        }

        # 4. Check unique intents and agents
        cur.execute("SELECT DISTINCT intent_detected FROM queries WHERE intent_detected IS NOT NULL")
        intents = [row['intent_detected'] for row in cur.fetchall()]

        cur.execute("SELECT DISTINCT agent_name FROM agent_execution_steps WHERE agent_name IS NOT NULL")
        agents = [row['agent_name'] for row in cur.fetchall()]

        inspection["unique_intents"] = intents
        inspection["unique_agents"] = agents

        # 5. List some distinct user IDs
        cur.execute("SELECT DISTINCT user_id FROM sessions WHERE user_id IS NOT NULL LIMIT 10")
        user_ids = [row['user_id'] for row in cur.fetchall()]

        inspection["user_ids"] = user_ids
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "message": "Database inspection completed",
            "inspection": inspection,
            "note": "This output confirms whether you're seeing real data or fallback data"
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Error inspecting database: {str(e)}"
        }
@app.get("/api/verify-data-source")
def verify_data_source():
    """Endpoint to verify if we're using real data"""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        verification = {}
        
        # Get row counts
        tables = ["sessions", "queries", "agent_execution_steps", "feedback", "related_queries"]
        for table in tables:
            cur.execute(f"SELECT COUNT(*) as count FROM {table}")
            count = cur.fetchone()['count']
            verification[f"{table}_count"] = count

        # Get date range
        cur.execute("SELECT MIN(creation_time) as min_date, MAX(creation_time) as max_date FROM sessions")
        date_range = cur.fetchone()
        verification["date_range"] = {
            "min_date": date_range['min_date'].strftime("%Y-%m-%d") if date_range['min_date'] else None,
            "max_date": date_range['max_date'].strftime("%Y-%m-%d") if date_range['max_date'] else None
        }

        # Sample a few rows for verification
        cur.execute("SELECT * FROM sessions LIMIT 1")
        sample_session = cur.fetchone()
        verification["sample_session"] = {
            "session_id": sample_session['session_id'] if sample_session else None,
            "user_id": sample_session['user_id'] if sample_session else None
        }
        
        cur.close()
        conn.close()
        
        return {
            "using_real_data": True,
            "verification": verification
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "using_real_data": False,
            "error": str(e)
        }
@app.get("/api/test-summary")
def test_summary():
    """Test endpoint for debugging summary data fetching"""
    try:
        from database import get_db_connection
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Test basic queries for summary
        results = {}
        
        # Check total sessions
        cur.execute("SELECT COUNT(*) as count FROM sessions")
        results['total_sessions'] = cur.fetchone()['count']

        # Check total queries
        cur.execute("SELECT COUNT(*) as count FROM queries")
        results['total_queries'] = cur.fetchone()['count']

        # Check date range
        cur.execute("SELECT MIN(creation_time) as min_date, MAX(creation_time) as max_date FROM sessions")
        date_range = cur.fetchone()
        results['date_range'] = {
            'min_date': date_range['min_date'].strftime('%Y-%m-%d') if date_range['min_date'] else None,
            'max_date': date_range['max_date'].strftime('%Y-%m-%d') if date_range['max_date'] else None
        }

        # Check top intents
        cur.execute("SELECT intent_detected, COUNT(*) as count FROM queries WHERE intent_detected IS NOT NULL GROUP BY intent_detected ORDER BY count DESC LIMIT 3")
        results['top_intents'] = [{'intent': row['intent_detected'], 'count': row['count']} for row in cur.fetchall()]

        # Check feedback stats
        cur.execute("SELECT COUNT(*) as total_feedback, SUM(CASE WHEN vote > 0 THEN 1 ELSE 0 END) as positive_feedback FROM feedback")
        feedback_stats = cur.fetchone()
        results['feedback_stats'] = {
            'total_feedback': feedback_stats['total_feedback'],
            'positive_feedback': feedback_stats['positive_feedback']
        }
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "message": "Successfully connected to database and retrieved summary test data",
            "data": results
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "status": "error",
            "message": f"Error testing summary: {str(e)}"
        }

# Include routers for each feature section
app.include_router(overview.router, tags=["Overview"])
app.include_router(sessions.router, tags=["Session Analytics"])
app.include_router(queries.router, tags=["Query Analytics"])
app.include_router(agents.router, tags=["Agent Performance"])
app.include_router(feedback.router, tags=["Feedback Analysis"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app:app", 
        host=os.getenv("API_HOST", "0.0.0.0"), 
        port=int(os.getenv("API_PORT", "8000")),
        reload=True
    )
