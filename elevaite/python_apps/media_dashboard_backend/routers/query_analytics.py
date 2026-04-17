from fastapi import APIRouter, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from typing import Optional, List, Dict, Any
from database import get_db_connection
import traceback
from datetime import datetime, timedelta
import pandas as pd
import io
import json

router = APIRouter(prefix="/api/query-analytics")

def build_chatbot_date_filter(start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Build date filter for chatbot queries - FIXED VERSION"""
    if start_date and end_date:
        return "WHERE request_timestamp BETWEEN %s AND %s", [start_date, end_date]
    elif start_date:
        return "WHERE request_timestamp >= %s", [start_date]
    elif end_date:
        return "WHERE request_timestamp <= %s", [end_date]
    else:
        return "", []  # No filter, no params

@router.get("/date-range-info")
def get_query_date_range_info(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get available date range information for query data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get actual date range of query data
        query = """
            SELECT 
                MIN(request_timestamp::date) as min_date,
                MAX(request_timestamp::date) as max_date,
                COUNT(*) as total_records,
                COUNT(DISTINCT session_id) as total_sessions
            FROM chat_data_final
            WHERE request_timestamp IS NOT NULL
        """
        
        cur.execute(query)
        date_info = cur.fetchone()
        
        # Get date range after applying user filters
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        
        # Build the WHERE clause properly
        if date_filter:
            # We have date filters
            filtered_where = f"{date_filter} AND request_timestamp IS NOT NULL"
        else:
            # No date filters
            filtered_where = "WHERE request_timestamp IS NOT NULL"
        
        filtered_query = f"""
            SELECT 
                MIN(request_timestamp::date) as filtered_min_date,
                MAX(request_timestamp::date) as filtered_max_date,
                COUNT(*) as filtered_records,
                COUNT(DISTINCT session_id) as filtered_sessions
            FROM chat_data_final
            {filtered_where}
        """
        
        cur.execute(filtered_query, params)
        filtered_info = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            "available_range": {
                "start_date": date_info['min_date'].strftime("%Y-%m-%d") if date_info['min_date'] else None,
                "end_date": date_info['max_date'].strftime("%Y-%m-%d") if date_info['max_date'] else None,
                "total_records": date_info['total_records'],
                "total_sessions": date_info['total_sessions']
            },
            "filtered_range": {
                "start_date": filtered_info['filtered_min_date'].strftime("%Y-%m-%d") if filtered_info['filtered_min_date'] else None,
                "end_date": filtered_info['filtered_max_date'].strftime("%Y-%m-%d") if filtered_info['filtered_max_date'] else None,
                "total_records": filtered_info['filtered_records'],
                "total_sessions": filtered_info['filtered_sessions']
            },
            "requested_range": {
                "start_date": start_date,
                "end_date": end_date
            },
            "has_data_in_range": filtered_info['filtered_records'] > 0,
            "message": _generate_date_range_message(date_info, filtered_info, start_date, end_date)
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

def _generate_date_range_message(date_info, filtered_info, start_date, end_date):
    """Generate appropriate message for date range display"""
    if not start_date and not end_date:
        return f"Showing all available query data ({date_info['min_date'].strftime('%Y-%m-%d')} to {date_info['max_date'].strftime('%Y-%m-%d')})"
    
    if filtered_info['filtered_records'] == 0:
        return f"No query data available for selected range. Available data: {date_info['min_date'].strftime('%Y-%m-%d')} to {date_info['max_date'].strftime('%Y-%m-%d')}"
    
    if filtered_info['filtered_min_date'] and filtered_info['filtered_max_date']:
        return f"Showing query data from {filtered_info['filtered_min_date'].strftime('%Y-%m-%d')} to {filtered_info['filtered_max_date'].strftime('%Y-%m-%d')}"
    
    return "Query data loaded successfully"

@router.get("/test-connection")
def test_chatbot_connection():
    """Test endpoint to verify chatbot database connection"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT COUNT(*) as total FROM chat_data_final")
        result = cur.fetchone()
        
        cur.close()
        conn.close()
        
        return {
            "status": "success",
            "message": f"Connected to chatbot database with {result['total']} records",
            "total_queries": result['total']
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/metrics")
def get_query_metrics(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get comprehensive query analytics metrics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        
        # Build WHERE clause properly
        where_clause = date_filter if date_filter else "WHERE 1=1"
        
        # 1. Basic Metrics
        basic_query = f"""
            SELECT 
                COUNT(DISTINCT session_id) as total_sessions,
                COUNT(*) as total_queries,
                ROUND(COUNT(*) / NULLIF(COUNT(DISTINCT session_id), 0)::DECIMAL, 2) as queries_per_session
            FROM chat_data_final
            {where_clause}
        """
        cur.execute(basic_query, params)
        basic_metrics = cur.fetchone()
        
        # 2. Repeat Queries (same request text in same session)
        repeat_query = f"""
            WITH query_counts AS (
                SELECT session_id, request, COUNT(*) as count
                FROM chat_data_final
                {where_clause}
                {'AND' if not date_filter else 'AND'} request IS NOT NULL
                GROUP BY session_id, request
            )
            SELECT 
                COUNT(*) FILTER (WHERE count > 1) as repeat_queries,
                COUNT(*) as total_unique_queries
            FROM query_counts
        """
        cur.execute(repeat_query, params)
        repeat_data = cur.fetchone()
        
        repeat_percentage = 0
        if repeat_data and repeat_data['total_unique_queries'] > 0:
            repeat_percentage = round((repeat_data['repeat_queries'] / repeat_data['total_unique_queries']) * 100, 1)
        
        # 3. Response Time Analysis
        response_time_query = f"""
            SELECT 
                AVG(EXTRACT(EPOCH FROM (response_timestamp - request_timestamp))) as avg_response_seconds,
                MIN(EXTRACT(EPOCH FROM (response_timestamp - request_timestamp))) as min_response_seconds,
                MAX(EXTRACT(EPOCH FROM (response_timestamp - request_timestamp))) as max_response_seconds
            FROM chat_data_final
            {where_clause}
            {'AND' if not date_filter else 'AND'} response_timestamp IS NOT NULL 
            {'AND' if not date_filter else 'AND'} request_timestamp IS NOT NULL
            {'AND' if not date_filter else 'AND'} response_timestamp > request_timestamp
        """
        cur.execute(response_time_query, params)
        response_time = cur.fetchone()
        
        # 4. Feedback Distribution
        feedback_query = f"""
            SELECT 
                CASE 
                    WHEN vote = 1 THEN 'thumbs_up'
                    WHEN vote = -1 THEN 'thumbs_down'
                    ELSE 'no_vote'
                END as feedback_type,
                COUNT(*) as count
            FROM chat_data_final
            {where_clause}
            GROUP BY vote
        """
        cur.execute(feedback_query, params)
        feedback_data = cur.fetchall()
        
        # Calculate percentages
        total_feedback = sum(row['count'] for row in feedback_data)
        feedback_distribution = []
        thumbs_up_percentage = 0
        thumbs_down_percentage = 0
        
        for row in feedback_data:
            percentage = round((row['count'] / total_feedback) * 100, 1) if total_feedback > 0 else 0
            feedback_distribution.append({
                "type": row['feedback_type'],
                "count": row['count'],
                "percentage": percentage
            })
            
            if row['feedback_type'] == 'thumbs_up':
                thumbs_up_percentage = percentage
            elif row['feedback_type'] == 'thumbs_down':
                thumbs_down_percentage = percentage
        
        # 5. Calculate daily average
        date_range_query = f"""
            SELECT 
                MIN(request_timestamp::date) as min_date,
                MAX(request_timestamp::date) as max_date
            FROM chat_data_final
            {where_clause}
        """
        cur.execute(date_range_query, params)
        date_range = cur.fetchone()
        
        avg_queries_per_day = 0
        if date_range and date_range['min_date'] and date_range['max_date']:
            days_diff = (date_range['max_date'] - date_range['min_date']).days + 1
            avg_queries_per_day = round(basic_metrics['total_queries'] / days_diff, 1) if days_diff > 0 else 0
        
        cur.close()
        conn.close()
        
        return {
            "total_sessions": basic_metrics['total_sessions'] or 0,
            "total_queries": basic_metrics['total_queries'] or 0,
            "queries_per_session": float(basic_metrics['queries_per_session']) if basic_metrics['queries_per_session'] else 0,
            "repeat_queries_percentage": repeat_percentage,
            "accuracy_percentage": max(0, 100 - thumbs_down_percentage),
            "avg_response_time_seconds": round(float(response_time['avg_response_seconds']) if response_time and response_time['avg_response_seconds'] else 0, 2),
            "avg_queries_per_day": avg_queries_per_day,
            "thumbs_up_percentage": thumbs_up_percentage,
            "thumbs_down_percentage": thumbs_down_percentage,
            "feedback_distribution": feedback_distribution,
            "_source": "real_chatbot_database"
        }
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/hourly-usage")
def get_hourly_usage(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Get 24-hour usage pattern"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        where_clause = date_filter if date_filter else "WHERE 1=1"
        
        query = f"""
            SELECT 
                EXTRACT(HOUR FROM request_timestamp) as hour,
                COUNT(*) as query_count
            FROM chat_data_final
            {where_clause}
            {'AND' if not date_filter else 'AND'} request_timestamp IS NOT NULL
            GROUP BY EXTRACT(HOUR FROM request_timestamp)
            ORDER BY hour
        """
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Format for frontend (ensure all 24 hours are represented)
        hourly_data = {}
        for row in results:
            hourly_data[int(row['hour'])] = row['query_count']
        
        # Fill missing hours with 0
        formatted_results = []
        for hour in range(24):
            formatted_results.append({
                "hour": f"{hour:02d}:00",
                "queries": hourly_data.get(hour, 0)
            })
        
        return formatted_results
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback-queries")
def get_feedback_queries(
    feedback_type: str = Query(..., description="thumbs_up or thumbs_down"),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(50)
):
    """Get queries with specific feedback"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        
        # Map feedback type to vote value
        vote_value = 1 if feedback_type == "thumbs_up" else -1
        
        # Build WHERE clause properly
        if date_filter:
            where_clause = f"{date_filter} AND vote = %s"
        else:
            where_clause = "WHERE vote = %s"
        
        params.append(vote_value)
        
        query = f"""
            SELECT 
                request,
                response,
                request_timestamp,
                user_id,
                feedback,
                session_id
            FROM chat_data_final
            {where_clause}
            AND request IS NOT NULL
            ORDER BY request_timestamp DESC
            LIMIT %s
        """
        
        params.append(limit)
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [{
            "query": row['request'],
            "response": row['response'][:200] + "..." if row['response'] and len(row['response']) > 200 else row['response'],
            "timestamp": row['request_timestamp'].strftime("%Y-%m-%d %H:%M:%S") if row['request_timestamp'] else None,
            "user": row['user_id'],
            "feedback": row['feedback'] or "",
            "session_id": str(row['session_id'])
        } for row in results]
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/unresolved-queries")
def get_unresolved_queries(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    limit: int = Query(20)
):
    """Get top unresolved queries (thumbs down with high frequency)"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        where_clause = date_filter if date_filter else "WHERE 1=1"
        
        # Build the subquery for total count
        total_count_clause = where_clause
        
        query = f"""
            SELECT 
                request,
                COUNT(*) as query_count,
                COUNT(*) FILTER (WHERE vote = -1) as thumbs_down_count,
                COUNT(*) FILTER (WHERE vote = 1) as thumbs_up_count,
                ROUND((COUNT(*) * 100.0 / (
                    SELECT COUNT(*) FROM chat_data_final 
                    {total_count_clause}
                )), 2) as percentage_of_total
            FROM chat_data_final
            {where_clause}
            {'AND' if not date_filter else 'AND'} request IS NOT NULL
            GROUP BY request
            HAVING COUNT(*) FILTER (WHERE vote = -1) > 0
            ORDER BY thumbs_down_count DESC, query_count DESC
            LIMIT %s
        """
        
        params_with_limit = params + params + [limit]
        cur.execute(query, params_with_limit)
        results = cur.fetchall()
        
        cur.close()
        conn.close()
        
        unresolved_queries = []
        for row in results:
            feedback_status = "Mostly 👎"
            if row['thumbs_up_count'] > row['thumbs_down_count']:
                feedback_status = "Mixed"
            
            confidence = max(10, 100 - (row['thumbs_down_count'] * 20))
            
            unresolved_queries.append({
                "text": row['request'],
                "count": row['query_count'],
                "percentage": f"{row['percentage_of_total']}%",
                "feedback": feedback_status,
                "botConfidence": f"{confidence}%",
                "thumbs_down_count": row['thumbs_down_count'],
                "thumbs_up_count": row['thumbs_up_count']
            })
        
        return unresolved_queries
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

# Excel Export Endpoints (keeping the same structure but fixing WHERE clauses)

@router.get("/export/all-queries")
def export_all_queries_excel(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Export all queries to Excel format"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        where_clause = date_filter if date_filter else "WHERE 1=1"
        
        query = f"""
            SELECT 
                qid as "Query ID",
                session_id as "Session ID",
                request as "Query Text",
                response as "Response",
                request_timestamp as "Request Time",
                response_timestamp as "Response Time",
                user_id as "User ID",
                CASE 
                    WHEN vote = 1 THEN 'Thumbs Up'
                    WHEN vote = -1 THEN 'Thumbs Down'
                    ELSE 'No Vote'
                END as "Feedback",
                feedback as "Written Feedback",
                sr_ticket_id as "SR Ticket ID"
            FROM chat_data_final
            {where_clause}
            ORDER BY request_timestamp DESC
            LIMIT 5000
        """
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # Convert to pandas DataFrame
        df = pd.DataFrame([dict(row) for row in results])
        
        # Format timestamps
        if not df.empty:
            if 'Request Time' in df.columns:
                df['Request Time'] = pd.to_datetime(df['Request Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'Response Time' in df.columns:
                df['Response Time'] = pd.to_datetime(df['Response Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='All Queries', index=False)
        
        excel_buffer.seek(0)
        
        # Generate filename
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"all_queries_{current_date}.xlsx"
        
        cur.close()
        conn.close()
        
        return StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/thumbs-up")
def export_thumbs_up_excel(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Export thumbs up queries to Excel format"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        
        # Add vote filter for thumbs up
        if date_filter:
            where_clause = f"{date_filter} AND vote = 1"
        else:
            where_clause = "WHERE vote = 1"
        
        query = f"""
            SELECT 
                qid as "Query ID",
                session_id as "Session ID",
                request as "Query Text",
                response as "Response",
                request_timestamp as "Request Time",
                response_timestamp as "Response Time",
                user_id as "User ID",
                feedback as "Written Feedback",
                sr_ticket_id as "SR Ticket ID"
            FROM chat_data_final
            {where_clause}
            AND request IS NOT NULL
            ORDER BY request_timestamp DESC
            LIMIT 2000
        """
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # Convert to pandas DataFrame
        df = pd.DataFrame([dict(row) for row in results])
        
        # Format timestamps
        if not df.empty:
            if 'Request Time' in df.columns:
                df['Request Time'] = pd.to_datetime(df['Request Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'Response Time' in df.columns:
                df['Response Time'] = pd.to_datetime(df['Response Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Thumbs Up Queries', index=False)
        
        excel_buffer.seek(0)
        
        # Generate filename
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"thumbs_up_queries_{current_date}.xlsx"
        
        cur.close()
        conn.close()
        
        return StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/thumbs-down")
def export_thumbs_down_excel(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Export thumbs down queries to Excel format"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        
        # Add vote filter for thumbs down
        if date_filter:
            where_clause = f"{date_filter} AND vote = -1"
        else:
            where_clause = "WHERE vote = -1"
        
        query = f"""
            SELECT 
                qid as "Query ID",
                session_id as "Session ID",
                request as "Query Text",
                response as "Response",
                request_timestamp as "Request Time",
                response_timestamp as "Response Time",
                user_id as "User ID",
                feedback as "Written Feedback",
                sr_ticket_id as "SR Ticket ID"
            FROM chat_data_final
            {where_clause}
            AND request IS NOT NULL
            ORDER BY request_timestamp DESC
            LIMIT 2000
        """
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # Convert to pandas DataFrame
        df = pd.DataFrame([dict(row) for row in results])
        
        # Format timestamps
        if not df.empty:
            if 'Request Time' in df.columns:
                df['Request Time'] = pd.to_datetime(df['Request Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'Response Time' in df.columns:
                df['Response Time'] = pd.to_datetime(df['Response Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Thumbs Down Queries', index=False)
        
        excel_buffer.seek(0)
        
        # Generate filename
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"thumbs_down_queries_{current_date}.xlsx"
        
        cur.close()
        conn.close()
        
        return StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/export/queries-with-fst-feedback")
def export_queries_with_fst_feedback_excel(
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None)
):
    """Export queries with FST written feedback to Excel format"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        date_filter, params = build_chatbot_date_filter(start_date, end_date)
        
        # Add feedback filter for non-empty feedback
        if date_filter:
            where_clause = f"{date_filter} AND feedback IS NOT NULL AND feedback != ''"
        else:
            where_clause = "WHERE feedback IS NOT NULL AND feedback != ''"
        
        query = f"""
            SELECT 
                qid as "Query ID",
                session_id as "Session ID",
                request as "Query Text",
                response as "Response",
                request_timestamp as "Request Time",
                response_timestamp as "Response Time",
                user_id as "User ID",
                CASE 
                    WHEN vote = 1 THEN 'Thumbs Up'
                    WHEN vote = -1 THEN 'Thumbs Down'
                    ELSE 'No Vote'
                END as "User Feedback",
                feedback as "FST Written Feedback",
                feedback_timestamp as "FST Feedback Time",
                sr_ticket_id as "SR Ticket ID"
            FROM chat_data_final
            {where_clause}
            AND request IS NOT NULL
            ORDER BY feedback_timestamp DESC
            LIMIT 2000
        """
        
        cur.execute(query, params)
        results = cur.fetchall()
        
        # Convert to pandas DataFrame
        df = pd.DataFrame([dict(row) for row in results])
        
        # Format timestamps
        if not df.empty:
            if 'Request Time' in df.columns:
                df['Request Time'] = pd.to_datetime(df['Request Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'Response Time' in df.columns:
                df['Response Time'] = pd.to_datetime(df['Response Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
            if 'FST Feedback Time' in df.columns:
                df['FST Feedback Time'] = pd.to_datetime(df['FST Feedback Time']).dt.strftime('%Y-%m-%d %H:%M:%S')
        
        # Create Excel file in memory
        excel_buffer = io.BytesIO()
        with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Queries with FST Feedback', index=False)
        
        excel_buffer.seek(0)
        
        # Generate filename
        current_date = datetime.now().strftime("%Y-%m-%d")
        filename = f"queries_with_fst_feedback_{current_date}.xlsx"
        
        cur.close()
        conn.close()
        
        return StreamingResponse(
            io.BytesIO(excel_buffer.read()),
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
        
    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))