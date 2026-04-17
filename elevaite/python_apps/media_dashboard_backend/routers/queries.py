# routers/queries.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from database import get_db_connection, log_media_query

router = APIRouter(prefix="/api/media/queries")
logger = logging.getLogger(__name__)

@router.get("/test")
def test_queries():
    """Simple test endpoint to verify query data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get basic query count and sample data
        cur.execute("SELECT COUNT(*) as count FROM queries")
        count = cur.fetchone()['count']

        cur.execute("SELECT query_id, user_id, intent_detected, total_duration_ms, success FROM queries LIMIT 3")
        samples = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "total_queries": count,
            "sample_queries": [
                {
                    "query_id": row['query_id'],
                    "user_id": row['user_id'],
                    "intent_detected": row['intent_detected'],
                    "total_duration_ms": row['total_duration_ms'],
                    "success": row['success']
                }
                for row in samples
            ]
        }

    except Exception as e:
        logger.error(f"Error in query test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
def get_query_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get query summary metrics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
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
        
        # Get query metrics
        query = f"""
            SELECT 
                COUNT(*) as total_queries,
                AVG(total_duration_ms) as avg_response_time_ms,
                COUNT(CASE WHEN success = true THEN 1 END) as successful_queries,
                COUNT(CASE WHEN success = false THEN 1 END) as failed_queries,
                COUNT(DISTINCT intent_detected) as unique_intents,
                COUNT(DISTINCT user_id) as unique_users
            FROM queries 
            {date_filter}
        """
        log_media_query(query, params)
        cur.execute(query, params)
        query_metrics = cur.fetchone()
        
        # Calculate success rate
        success_rate = 0
        if query_metrics['total_queries'] > 0:
            success_rate = round((query_metrics['successful_queries'] / query_metrics['total_queries']) * 100, 2)
        
        # Get response time distribution - using CTE to avoid GROUP BY issues
        query = f"""
            WITH response_times AS (
                SELECT
                    CASE
                        WHEN COALESCE(total_duration_ms, 0) < 1000 THEN '< 1s'
                        WHEN COALESCE(total_duration_ms, 0) < 5000 THEN '1-5s'
                        WHEN COALESCE(total_duration_ms, 0) < 10000 THEN '5-10s'
                        WHEN COALESCE(total_duration_ms, 0) < 30000 THEN '10-30s'
                        ELSE '30s+'
                    END as response_time_range,
                    CASE
                        WHEN COALESCE(total_duration_ms, 0) < 1000 THEN 1
                        WHEN COALESCE(total_duration_ms, 0) < 5000 THEN 2
                        WHEN COALESCE(total_duration_ms, 0) < 10000 THEN 3
                        WHEN COALESCE(total_duration_ms, 0) < 30000 THEN 4
                        ELSE 5
                    END as sort_order
                FROM queries
                WHERE total_duration_ms IS NOT NULL {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            )
            SELECT
                response_time_range,
                COUNT(*) as count
            FROM response_times
            GROUP BY response_time_range, sort_order
            ORDER BY sort_order
        """
        log_media_query(query, params)
        cur.execute(query, params)
        response_time_distribution = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "total_queries": query_metrics['total_queries'],
            "avg_response_time_ms": round(query_metrics['avg_response_time_ms'], 2) if query_metrics['avg_response_time_ms'] else 0,
            "success_rate": success_rate,
            "successful_queries": query_metrics['successful_queries'],
            "failed_queries": query_metrics['failed_queries'],
            "unique_intents": query_metrics['unique_intents'],
            "unique_users": query_metrics['unique_users'],
            "response_time_distribution": [
                {"range": row['response_time_range'], "count": row['count']}
                for row in response_time_distribution
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting query summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance")
def get_query_performance(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get query performance metrics over time"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
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
        
        # Get performance by date
        query = f"""
            SELECT 
                DATE(start_time) as date,
                COUNT(*) as total_queries,
                AVG(total_duration_ms) as avg_response_time,
                COUNT(CASE WHEN success = true THEN 1 END) as successful_queries,
                COUNT(CASE WHEN success = false THEN 1 END) as failed_queries
            FROM queries 
            {date_filter}
            GROUP BY DATE(start_time)
            ORDER BY date
        """
        log_media_query(query, params)
        cur.execute(query, params)
        performance_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        result = []
        for row in performance_data:
            success_rate = 0
            if row['total_queries'] > 0:
                success_rate = round((row['successful_queries'] / row['total_queries']) * 100, 2)
            
            result.append({
                "date": row['date'].strftime('%Y-%m-%d'),
                "total_queries": row['total_queries'],
                "avg_response_time": round(row['avg_response_time'], 2) if row['avg_response_time'] else 0,
                "success_rate": success_rate,
                "successful_queries": row['successful_queries'],
                "failed_queries": row['failed_queries']
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting query performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/intents")
def get_intent_distribution(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(15, description="Number of top intents to return")
):
    """Get intent distribution and analysis"""
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
        
        # Get intent distribution with performance metrics
        query = f"""
            SELECT 
                intent_detected as intent,
                COUNT(*) as count,
                AVG(total_duration_ms) as avg_response_time,
                COUNT(CASE WHEN success = true THEN 1 END) as successful_queries,
                COUNT(CASE WHEN success = false THEN 1 END) as failed_queries
            FROM queries 
            {date_filter}
            GROUP BY intent_detected
            ORDER BY count DESC
            LIMIT %s
        """
        params.append(limit)
        log_media_query(query, params)
        cur.execute(query, params)
        intent_data = cur.fetchall()
        
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

        # Group by normalized intent key to avoid duplicates
        intent_metrics = {}
        for row in intent_data:
            raw_intent = str(row['intent']).strip()
            intent_key = normalize_intent(raw_intent)

            if intent_key in intent_metrics:
                # Merge metrics for duplicate intents
                existing = intent_metrics[intent_key]
                total_count = existing['count'] + row['count']
                total_successful = existing['successful_queries'] + row['successful_queries']
                total_failed = existing['failed_queries'] + row['failed_queries']

                # Calculate weighted average response time
                total_response_time = (existing['avg_response_time'] * existing['count'] +
                                     (row['avg_response_time'] or 0) * row['count'])
                avg_response_time = total_response_time / total_count if total_count > 0 else 0

                intent_metrics[intent_key] = {
                    'count': total_count,
                    'avg_response_time': avg_response_time,
                    'successful_queries': total_successful,
                    'failed_queries': total_failed
                }
            else:
                intent_metrics[intent_key] = {
                    'count': row['count'],
                    'avg_response_time': row['avg_response_time'] or 0,
                    'successful_queries': row['successful_queries'],
                    'failed_queries': row['failed_queries']
                }

        # Convert to result format and sort by count
        result = []
        for intent_key, metrics in intent_metrics.items():
            success_rate = 0
            if metrics['count'] > 0:
                success_rate = round((metrics['successful_queries'] / metrics['count']) * 100, 2)

            intent_label = intent_labels.get(intent_key, f"Intent {intent_key}")
            result.append({
                "intent": intent_label,
                "count": metrics['count'],
                "avg_response_time": round(metrics['avg_response_time'], 2),
                "success_rate": success_rate,
                "successful_queries": metrics['successful_queries'],
                "failed_queries": metrics['failed_queries']
            })

        # Sort by count descending and apply limit
        result.sort(key=lambda x: x['count'], reverse=True)
        return result[:limit]
        
    except Exception as e:
        logger.error(f"Error getting intent distribution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/complexity")
def get_query_complexity_analysis(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get query complexity analysis based on agents used and tokens"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
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
        
        # Get complexity distribution based on agents used - using CTE
        query = f"""
            WITH complexity_levels AS (
                SELECT
                    CASE
                        WHEN COALESCE(jsonb_array_length(agents_used), 0) = 0 THEN 'No Agents'
                        WHEN COALESCE(jsonb_array_length(agents_used), 0) = 1 THEN 'Single Agent'
                        WHEN COALESCE(jsonb_array_length(agents_used), 0) BETWEEN 2 AND 3 THEN '2-3 Agents'
                        ELSE '4+ Agents'
                    END as complexity_level,
                    CASE
                        WHEN COALESCE(jsonb_array_length(agents_used), 0) = 0 THEN 1
                        WHEN COALESCE(jsonb_array_length(agents_used), 0) = 1 THEN 2
                        WHEN COALESCE(jsonb_array_length(agents_used), 0) BETWEEN 2 AND 3 THEN 3
                        ELSE 4
                    END as sort_order,
                    total_duration_ms
                FROM queries
                {date_filter}
            )
            SELECT
                complexity_level,
                COUNT(*) as count,
                AVG(total_duration_ms) as avg_response_time
            FROM complexity_levels
            GROUP BY complexity_level, sort_order
            ORDER BY sort_order
        """
        log_media_query(query, params)
        cur.execute(query, params)
        complexity_data = cur.fetchall()
        
        # Get token usage distribution - using CTE
        query = f"""
            WITH token_ranges AS (
                SELECT
                    CASE
                        WHEN COALESCE((total_tokens_used->>'total')::int, 0) < 1000 THEN '< 1K tokens'
                        WHEN COALESCE((total_tokens_used->>'total')::int, 0) < 5000 THEN '1K-5K tokens'
                        WHEN COALESCE((total_tokens_used->>'total')::int, 0) < 10000 THEN '5K-10K tokens'
                        ELSE '10K+ tokens'
                    END as token_range,
                    CASE
                        WHEN COALESCE((total_tokens_used->>'total')::int, 0) < 1000 THEN 1
                        WHEN COALESCE((total_tokens_used->>'total')::int, 0) < 5000 THEN 2
                        WHEN COALESCE((total_tokens_used->>'total')::int, 0) < 10000 THEN 3
                        ELSE 4
                    END as sort_order
                FROM queries
                WHERE total_tokens_used->>'total' IS NOT NULL
                {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            )
            SELECT
                token_range,
                COUNT(*) as count
            FROM token_ranges
            GROUP BY token_range, sort_order
            ORDER BY sort_order
        """
        log_media_query(query, params)
        cur.execute(query, params)
        token_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "complexity_distribution": [
                {
                    "level": row['complexity_level'],
                    "count": row['count'],
                    "avg_response_time": round(row['avg_response_time'], 2) if row['avg_response_time'] else 0
                }
                for row in complexity_data
            ],
            "token_distribution": [
                {"range": row['token_range'], "count": row['count']}
                for row in token_data
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting query complexity analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/recent")
def get_recent_queries(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Number of recent queries to return")
):
    """Get recent queries with details including responses and normalized intents"""
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

        # Get recent queries
        query = f"""
            SELECT
                query_id,
                session_id,
                user_id,
                original_query,
                intent_detected,
                total_duration_ms,
                success,
                start_time,
                end_time,
                total_tokens_used,
                final_response
            FROM queries
            {date_filter}
            ORDER BY start_time DESC
            LIMIT %s
        """
        params.append(limit)

        log_media_query(query, params)
        cur.execute(query, params)
        queries = cur.fetchall()

        cur.close()
        conn.close()

        # Convert to list of dictionaries
        result = []
        for query in queries:
            # Calculate total tokens from JSONB data
            total_tokens = 0
            if query['total_tokens_used']:
                token_data = query['total_tokens_used']
                if isinstance(token_data, dict):
                    # Sum all token values in the JSONB object
                    for key, value in token_data.items():
                        if isinstance(value, (int, float)):
                            total_tokens += value
                        elif isinstance(value, dict):
                            # Handle nested token structures
                            for nested_key, nested_value in value.items():
                                if isinstance(nested_value, (int, float)):
                                    total_tokens += nested_value

            # Normalize and map intent
            raw_intent = query['intent_detected']
            normalized_intent = normalize_intent(raw_intent)
            friendly_intent = intent_labels.get(normalized_intent, raw_intent or 'Unknown')

            result.append({
                "query_id": query['query_id'],
                "session_id": query['session_id'],
                "user_id": query['user_id'],
                "original_query": query['original_query'],
                "intent_detected": friendly_intent,
                "total_duration_ms": query['total_duration_ms'],
                "success": query['success'],
                "start_time": query['start_time'].isoformat() if query['start_time'] else None,
                "end_time": query['end_time'].isoformat() if query['end_time'] else None,
                "total_tokens": total_tokens,
                "final_response": query['final_response']
            })

        return result

    except Exception as e:
        logger.error(f"Error getting recent queries: {e}")
        raise HTTPException(status_code=500, detail=str(e))
