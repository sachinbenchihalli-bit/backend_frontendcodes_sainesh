# routers/overview.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from database import get_db_connection, log_media_query

router = APIRouter(prefix="/api/media/overview")
logger = logging.getLogger(__name__)

@router.get("/summary")
def get_overview_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get overview summary metrics for the media dashboard"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE s.creation_time BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE s.creation_time >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE s.creation_time <= %s"
            params = [end_date]
        
        # Get total sessions
        query = f"SELECT COUNT(*) as count FROM sessions s {date_filter}"
        log_media_query(query, params)
        cur.execute(query, params)
        total_sessions = cur.fetchone()['count']
        
        # Get total queries
        query_filter = date_filter.replace("s.creation_time", "q.start_time") if date_filter else ""
        query = f"SELECT COUNT(*) as count FROM queries q {query_filter}"
        log_media_query(query, params)
        cur.execute(query, params)
        total_queries = cur.fetchone()['count']
        
        # Get average queries per session
        avg_queries_per_session = round(total_queries / total_sessions, 2) if total_sessions > 0 else 0
        
        # Get feedback stats
        feedback_filter = date_filter.replace("s.creation_time", "f.timestamp") if date_filter else ""
        query = f"""
            SELECT 
                COUNT(*) as total_feedback,
                SUM(CASE WHEN vote > 0 THEN 1 ELSE 0 END) as positive_feedback,
                SUM(CASE WHEN vote < 0 THEN 1 ELSE 0 END) as negative_feedback
            FROM feedback f {feedback_filter}
        """
        log_media_query(query, params)
        cur.execute(query, params)
        feedback_stats = cur.fetchone()
        
        satisfaction_rate = 0
        if feedback_stats['total_feedback'] > 0:
            satisfaction_rate = round((feedback_stats['positive_feedback'] / feedback_stats['total_feedback']) * 100, 1)
        
        # Get average response time
        query = f"""
            SELECT AVG(total_duration_ms) as avg_duration
            FROM queries q 
            WHERE total_duration_ms IS NOT NULL {query_filter.replace('WHERE', 'AND') if query_filter else ''}
        """
        log_media_query(query, params)
        cur.execute(query, params)
        avg_duration_result = cur.fetchone()
        avg_response_time = round(avg_duration_result['avg_duration'] / 1000, 2) if avg_duration_result['avg_duration'] else 0
        
        cur.close()
        conn.close()
        
        return {
            "total_sessions": total_sessions,
            "total_queries": total_queries,
            "avg_queries_per_session": avg_queries_per_session,
            "satisfaction_rate": satisfaction_rate,
            "avg_response_time_seconds": avg_response_time,
            "total_feedback": feedback_stats['total_feedback'],
            "positive_feedback": feedback_stats['positive_feedback'],
            "negative_feedback": feedback_stats['negative_feedback']
        }
        
    except Exception as e:
        logger.error(f"Error getting overview summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/timeline")
def get_sessions_and_queries_timeline(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get sessions and queries over time for timeline chart"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE DATE(creation_time) BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE DATE(creation_time) >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE DATE(creation_time) <= %s"
            params = [end_date]
        
        # Get sessions by date
        query = f"""
            SELECT 
                DATE(creation_time) as date,
                COUNT(*) as sessions
            FROM sessions 
            {date_filter}
            GROUP BY DATE(creation_time)
            ORDER BY date
        """
        log_media_query(query, params)
        cur.execute(query, params)
        sessions_data = cur.fetchall()
        
        # Get queries by date
        query_filter = date_filter.replace("creation_time", "start_time") if date_filter else ""
        query = f"""
            SELECT 
                DATE(start_time) as date,
                COUNT(*) as queries
            FROM queries 
            {query_filter}
            GROUP BY DATE(start_time)
            ORDER BY date
        """
        log_media_query(query, params)
        cur.execute(query, params)
        queries_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Combine the data
        timeline_data = {}
        
        for row in sessions_data:
            date_str = row['date'].strftime('%Y-%m-%d')
            timeline_data[date_str] = {"date": date_str, "sessions": row['sessions'], "queries": 0}
        
        for row in queries_data:
            date_str = row['date'].strftime('%Y-%m-%d')
            if date_str in timeline_data:
                timeline_data[date_str]["queries"] = row['queries']
            else:
                timeline_data[date_str] = {"date": date_str, "sessions": 0, "queries": row['queries']}
        
        # Convert to list and sort by date
        result = list(timeline_data.values())
        result.sort(key=lambda x: x['date'])
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting timeline data: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intents")
def get_top_intents(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(10, description="Number of top intents to return")
):
    """Get top detected intents with user-friendly labels"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Intent mapping for user-friendly labels
        intent_labels = {
            "1": "Media Plan",
            "3": "Campaign Performance and Insights",
            "4": "Existing Creative Insights",
            "5": "Performance Summary",
            "6": "Creative Trends",
            "7": "Creative Inspiration",
            "8": "Creative Feedback",
            "9": "Follow Up Question",
            "10": "Generic Media Chatbot Questions",
            "11": "Irrelevant Questions"
        }

        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE start_time BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE start_time >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE start_time <= %s"
            params = [end_date]

        # Add intent filter
        if date_filter:
            date_filter += " AND intent_detected IS NOT NULL"
        else:
            date_filter = "WHERE intent_detected IS NOT NULL"

        query = f"""
            SELECT
                intent_detected as intent,
                COUNT(*) as count
            FROM queries
            {date_filter}
            GROUP BY intent_detected
            ORDER BY count DESC
            LIMIT %s
        """
        params.append(limit)
        log_media_query(query, params)
        cur.execute(query, params)
        intents_data = cur.fetchall()

        cur.close()
        conn.close()

        # Helper function to normalize intent values
        def normalize_intent(raw_intent):
            raw_intent = str(raw_intent).strip()

            if raw_intent.startswith('[') and raw_intent.endswith(']'):
                # Handle array format like [7], [1], [3, 5]
                try:
                    # Remove brackets and split by comma
                    numbers = raw_intent[1:-1].split(',')
                    # Take the first number if multiple
                    return numbers[0].strip()
                except:
                    return raw_intent
            elif raw_intent.isdigit():
                # Handle simple number format
                return raw_intent
            elif raw_intent == "insertion_order":
                # Map insertion_order to Media Plan (intent 1)
                return "1"
            else:
                # Keep as is for unknown formats
                return raw_intent

        # Group by normalized intent key to avoid duplicates
        intent_counts = {}
        for row in intents_data:
            raw_intent = str(row['intent']).strip()
            intent_key = normalize_intent(raw_intent)

            if intent_key in intent_counts:
                intent_counts[intent_key] += row['count']
            else:
                intent_counts[intent_key] = row['count']

        # Map intent numbers to user-friendly labels and sort by count
        result = []
        for intent_key, count in intent_counts.items():
            intent_label = intent_labels.get(intent_key, f"Intent {intent_key}")
            result.append({
                "intent": intent_label,
                "intent_id": intent_key,
                "count": count
            })

        # Sort by count descending and apply limit
        result.sort(key=lambda x: x['count'], reverse=True)
        return result[:limit]

    except Exception as e:
        logger.error(f"Error getting top intents: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/feedback-distribution")
def get_feedback_distribution(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get feedback distribution for pie chart"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE timestamp BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE timestamp >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE timestamp <= %s"
            params = [end_date]
        
        query = f"""
            SELECT
                CASE
                    WHEN vote > 0 THEN 'Positive'
                    WHEN vote < 0 THEN 'Negative'
                    ELSE 'Neutral'
                END as feedback_type,
                COUNT(*) as count
            FROM feedback
            {date_filter}
            GROUP BY
                CASE
                    WHEN vote > 0 THEN 'Positive'
                    WHEN vote < 0 THEN 'Negative'
                    ELSE 'Neutral'
                END
            ORDER BY count DESC
        """
        log_media_query(query, params)
        cur.execute(query, params)
        feedback_data = cur.fetchall()

        # Calculate total feedback count for percentage calculation
        total_feedback = sum(row['count'] for row in feedback_data)

        # Convert counts to percentages with consistent colors
        result = []
        color_map = {
            'Positive': '#22c55e',  # Green
            'Negative': '#ef4444',  # Red
            'Neutral': '#f59e0b'    # Orange/Yellow
        }

        if total_feedback > 0:
            for row in feedback_data:
                percentage = round((row['count'] / total_feedback) * 100, 1)
                result.append({
                    "name": row['feedback_type'],
                    "value": percentage,
                    "count": row['count'],  # Include raw count for tooltip
                    "color": color_map.get(row['feedback_type'], '#6b7280')  # Default gray
                })
        else:
            # If no feedback data, return empty array
            result = []

        cur.close()
        conn.close()

        return result
        
    except Exception as e:
        logger.error(f"Error getting feedback distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))
