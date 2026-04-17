# routers/feedback.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from database import get_db_connection, log_media_query

router = APIRouter(prefix="/api/media/feedback")
logger = logging.getLogger(__name__)

@router.get("/summary")
def get_feedback_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get feedback summary metrics"""
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
        
        # Get feedback metrics
        query = f"""
            SELECT 
                COUNT(*) as total_feedback,
                COUNT(CASE WHEN vote > 0 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN vote < 0 THEN 1 END) as negative_feedback,
                COUNT(CASE WHEN vote = 0 THEN 1 END) as neutral_feedback,
                COUNT(DISTINCT user_id) as unique_users,
                COUNT(DISTINCT query_id) as unique_queries,
                COUNT(DISTINCT session_id) as unique_sessions
            FROM feedback 
            {date_filter}
        """
        log_media_query(query, params)
        cur.execute(query, params)
        feedback_metrics = cur.fetchone()
        
        # Calculate satisfaction rate
        satisfaction_rate = 0
        if feedback_metrics['total_feedback'] > 0:
            satisfaction_rate = round((feedback_metrics['positive_feedback'] / feedback_metrics['total_feedback']) * 100, 2)
        
        # Get feedback by type
        query = f"""
            SELECT 
                feedback_type,
                COUNT(*) as count,
                AVG(CASE WHEN vote > 0 THEN 1 WHEN vote < 0 THEN -1 ELSE 0 END) as avg_sentiment
            FROM feedback 
            {date_filter}
            GROUP BY feedback_type
            ORDER BY count DESC
        """
        log_media_query(query, params)
        cur.execute(query, params)
        feedback_by_type = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "total_feedback": feedback_metrics['total_feedback'],
            "positive_feedback": feedback_metrics['positive_feedback'],
            "negative_feedback": feedback_metrics['negative_feedback'],
            "neutral_feedback": feedback_metrics['neutral_feedback'],
            "satisfaction_rate": satisfaction_rate,
            "unique_users": feedback_metrics['unique_users'],
            "unique_queries": feedback_metrics['unique_queries'],
            "unique_sessions": feedback_metrics['unique_sessions'],
            "feedback_by_type": [
                {
                    "type": row['feedback_type'],
                    "count": row['count'],
                    "avg_sentiment": round(row['avg_sentiment'], 2) if row['avg_sentiment'] else 0
                }
                for row in feedback_by_type
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting feedback summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sentiment")
def get_sentiment_analysis(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get feedback sentiment analysis with user-friendly intent labels"""
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
            date_filter = "WHERE f.timestamp BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE f.timestamp >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE f.timestamp <= %s"
            params = [end_date]

        # Get sentiment by intent
        where_clause = "WHERE q.intent_detected IS NOT NULL"
        if date_filter:
            where_clause = f"{date_filter} AND q.intent_detected IS NOT NULL"

        query = f"""
            SELECT
                q.intent_detected,
                COUNT(*) as total_feedback,
                COUNT(CASE WHEN f.vote > 0 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN f.vote < 0 THEN 1 END) as negative_feedback,
                AVG(CASE WHEN f.vote > 0 THEN 1 WHEN f.vote < 0 THEN -1 ELSE 0 END) as avg_sentiment
            FROM feedback f
            JOIN queries q ON f.query_id = q.query_id
            {where_clause}
            GROUP BY q.intent_detected
            HAVING COUNT(*) >= 3
            ORDER BY total_feedback DESC
        """
        log_media_query(query, params)
        cur.execute(query, params)
        sentiment_by_intent = cur.fetchall()
        
        # Get sentiment correlation with response time
        query = f"""
            WITH response_time_categories AS (
                SELECT
                    CASE
                        WHEN q.total_duration_ms < 5000 THEN 'Fast (< 5s)'
                        WHEN q.total_duration_ms < 15000 THEN 'Medium (5-15s)'
                        ELSE 'Slow (15s+)'
                    END as response_time_category,
                    CASE
                        WHEN q.total_duration_ms < 5000 THEN 1
                        WHEN q.total_duration_ms < 15000 THEN 2
                        ELSE 3
                    END as sort_order,
                    f.vote
                FROM feedback f
                JOIN queries q ON f.query_id = q.query_id
                WHERE q.total_duration_ms IS NOT NULL
                {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            )
            SELECT
                response_time_category,
                COUNT(*) as total_feedback,
                COUNT(CASE WHEN vote > 0 THEN 1 END) as positive_feedback,
                AVG(CASE WHEN vote > 0 THEN 1 WHEN vote < 0 THEN -1 ELSE 0 END) as avg_sentiment
            FROM response_time_categories
            GROUP BY response_time_category, sort_order
            ORDER BY sort_order
        """
        log_media_query(query, params)
        cur.execute(query, params)
        sentiment_by_response_time = cur.fetchall()
        
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

        # Helper function to parse intent
        def parse_intent(raw_intent):
            intent_key = normalize_intent(raw_intent)
            return intent_labels.get(intent_key, f"Intent {raw_intent}")

        return {
            "sentiment_by_intent": [
                {
                    "intent": parse_intent(row['intent_detected']),
                    "total_feedback": row['total_feedback'],
                    "positive_feedback": row['positive_feedback'],
                    "negative_feedback": row['negative_feedback'],
                    "satisfaction_rate": round((row['positive_feedback'] / row['total_feedback']) * 100, 2) if row['total_feedback'] > 0 else 0,
                    "avg_sentiment": round(row['avg_sentiment'], 2) if row['avg_sentiment'] else 0
                }
                for row in sentiment_by_intent
            ],
            "sentiment_by_response_time": [
                {
                    "response_time_category": row['response_time_category'],
                    "total_feedback": row['total_feedback'],
                    "positive_feedback": row['positive_feedback'],
                    "satisfaction_rate": round((row['positive_feedback'] / row['total_feedback']) * 100, 2) if row['total_feedback'] > 0 else 0,
                    "avg_sentiment": round(row['avg_sentiment'], 2) if row['avg_sentiment'] else 0
                }
                for row in sentiment_by_response_time
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting sentiment analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/trends")
def get_feedback_trends(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get feedback trends over time"""
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
        
        # Get feedback trends by date
        query = f"""
            SELECT 
                DATE(timestamp) as date,
                COUNT(*) as total_feedback,
                COUNT(CASE WHEN vote > 0 THEN 1 END) as positive_feedback,
                COUNT(CASE WHEN vote < 0 THEN 1 END) as negative_feedback,
                COUNT(CASE WHEN vote = 0 THEN 1 END) as neutral_feedback
            FROM feedback 
            {date_filter}
            GROUP BY DATE(timestamp)
            ORDER BY date
        """
        log_media_query(query, params)
        cur.execute(query, params)
        trends_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        result = []
        for row in trends_data:
            satisfaction_rate = 0
            if row['total_feedback'] > 0:
                satisfaction_rate = round((row['positive_feedback'] / row['total_feedback']) * 100, 2)
            
            result.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "total_feedback": row['total_feedback'],
                "positive_feedback": row['positive_feedback'],
                "negative_feedback": row['negative_feedback'],
                "neutral_feedback": row['neutral_feedback'],
                "satisfaction_rate": satisfaction_rate
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting feedback trends: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/details")
def get_feedback_details(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    feedback_type: Optional[str] = Query(None, description="Filter by feedback type"),
    vote_filter: Optional[int] = Query(None, description="Filter by vote (1=positive, -1=negative, 0=neutral)"),
    limit: int = Query(50, description="Number of feedback entries to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get detailed feedback entries with pagination and filtering and normalized intents"""
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

        # Helper function to normalize intent values
        def normalize_intent(raw_intent):
            if not raw_intent:
                return raw_intent

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
        
        # Build filters
        filters = []
        params = []
        
        if start_date and end_date:
            filters.append("f.timestamp BETWEEN %s AND %s")
            params.extend([start_date, end_date])
        elif start_date:
            filters.append("f.timestamp >= %s")
            params.append(start_date)
        elif end_date:
            filters.append("f.timestamp <= %s")
            params.append(end_date)
        
        if feedback_type:
            filters.append("f.feedback_type = %s")
            params.append(feedback_type)
        
        if vote_filter is not None:
            filters.append("f.vote = %s")
            params.append(vote_filter)
        
        where_clause = "WHERE " + " AND ".join(filters) if filters else ""
        
        query = f"""
            SELECT 
                f.id,
                f.query_id,
                f.session_id,
                f.user_id,
                f.feedback_type,
                f.feedback_text,
                f.vote,
                f.timestamp,
                q.intent_detected,
                q.total_duration_ms,
                q.original_query
            FROM feedback f
            LEFT JOIN queries q ON f.query_id = q.query_id
            {where_clause}
            ORDER BY f.timestamp DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        log_media_query(query, params)
        cur.execute(query, params)
        feedback_details = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [
            {
                "id": str(row['id']),
                "query_id": row['query_id'],
                "session_id": row['session_id'],
                "user_id": row['user_id'],
                "feedback_type": row['feedback_type'],
                "feedback_text": row['feedback_text'],
                "vote": row['vote'],
                "timestamp": row['timestamp'].isoformat() if row['timestamp'] else None,
                "intent_detected": intent_labels.get(normalize_intent(row['intent_detected']), row['intent_detected'] or 'Unknown'),
                "query_duration_ms": row['total_duration_ms'],
                "original_query": row['original_query'][:100] + "..." if row['original_query'] and len(row['original_query']) > 100 else row['original_query']
            }
            for row in feedback_details
        ]
        
    except Exception as e:
        logger.error(f"Error getting feedback details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
