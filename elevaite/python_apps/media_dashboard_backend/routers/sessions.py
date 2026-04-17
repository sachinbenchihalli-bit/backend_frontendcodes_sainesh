# routers/sessions.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from database import get_db_connection, log_media_query

router = APIRouter(prefix="/api/media/sessions")
logger = logging.getLogger(__name__)

@router.get("/test")
def test_sessions():
    """Simple test endpoint to verify session data"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()

        # Get basic session count and sample data
        cur.execute("SELECT COUNT(*) as count FROM sessions")
        count = cur.fetchone()['count']

        cur.execute("SELECT session_id, user_id, total_queries, creation_time, last_activity_time FROM sessions LIMIT 3")
        samples = cur.fetchall()

        cur.close()
        conn.close()

        return {
            "total_sessions": count,
            "sample_sessions": [
                {
                    "session_id": row['session_id'],
                    "user_id": row['user_id'],
                    "total_queries": row['total_queries'],
                    "creation_time": row['creation_time'].isoformat() if row['creation_time'] else None,
                    "last_activity_time": row['last_activity_time'].isoformat() if row['last_activity_time'] else None
                }
                for row in samples
            ]
        }

    except Exception as e:
        logger.error(f"Error in session test: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/summary")
def get_session_summary(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get session summary metrics"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE creation_time BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE creation_time >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE creation_time <= %s"
            params = [end_date]
        
        # Get session metrics - handle NULL values and short durations
        query = f"""
            SELECT
                COUNT(*) as total_sessions,
                COUNT(DISTINCT user_id) as unique_users,
                COALESCE(AVG(NULLIF(total_queries, 0)), 0) as avg_queries_per_session,
                COALESCE(AVG(GREATEST(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0)), 0) as avg_session_duration_minutes
            FROM sessions
            {date_filter}
        """
        log_media_query(query, params)
        cur.execute(query, params)
        session_metrics = cur.fetchone()
        
        # Get session duration distribution - simplified approach
        query = f"""
            WITH session_durations AS (
                SELECT
                    CASE
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 1 THEN '0-1 min'
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 5 THEN '1-5 min'
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 15 THEN '5-15 min'
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 30 THEN '15-30 min'
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 60 THEN '30-60 min'
                        ELSE '60+ min'
                    END as duration_range,
                    CASE
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 1 THEN 1
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 5 THEN 2
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 15 THEN 3
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 30 THEN 4
                        WHEN COALESCE(EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60, 0) < 60 THEN 5
                        ELSE 6
                    END as sort_order
                FROM sessions
                {date_filter}
            )
            SELECT
                duration_range,
                COUNT(*) as count
            FROM session_durations
            GROUP BY duration_range, sort_order
            ORDER BY sort_order
        """
        log_media_query(query, params)
        cur.execute(query, params)
        duration_distribution = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "total_sessions": session_metrics['total_sessions'],
            "unique_users": session_metrics['unique_users'],
            "avg_queries_per_session": round(session_metrics['avg_queries_per_session'], 2) if session_metrics['avg_queries_per_session'] else 0,
            "avg_session_duration_minutes": round(session_metrics['avg_session_duration_minutes'], 2) if session_metrics['avg_session_duration_minutes'] else 0,
            "duration_distribution": [{"range": row['duration_range'], "count": row['count']} for row in duration_distribution]
        }
        
    except Exception as e:
        logger.error(f"Error getting session summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/activity-heatmap")
def get_session_activity_heatmap(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get session activity heatmap by hour and day of week"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE creation_time BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE creation_time >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE creation_time <= %s"
            params = [end_date]
        
        query = f"""
            SELECT 
                EXTRACT(DOW FROM creation_time) as day_of_week,
                EXTRACT(HOUR FROM creation_time) as hour,
                COUNT(*) as session_count
            FROM sessions 
            {date_filter}
            GROUP BY EXTRACT(DOW FROM creation_time), EXTRACT(HOUR FROM creation_time)
            ORDER BY day_of_week, hour
        """
        log_media_query(query, params)
        cur.execute(query, params)
        heatmap_data = cur.fetchall()
        
        cur.close()
        conn.close()
        
        # Convert to format suitable for heatmap
        result = []
        day_names = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
        
        for row in heatmap_data:
            result.append({
                "day": day_names[int(row['day_of_week'])],
                "hour": int(row['hour']),
                "count": row['session_count']
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting activity heatmap: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/user-engagement")
def get_user_engagement_patterns(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get user engagement patterns"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE creation_time BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE creation_time >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE creation_time <= %s"
            params = [end_date]
        
        # Get user session frequency
        query = f"""
            SELECT 
                user_id,
                COUNT(*) as session_count,
                AVG(total_queries) as avg_queries_per_session,
                MAX(creation_time) as last_session
            FROM sessions 
            {date_filter}
            GROUP BY user_id
            ORDER BY session_count DESC
            LIMIT 20
        """
        log_media_query(query, params)
        cur.execute(query, params)
        user_engagement = cur.fetchall()
        
        # Get engagement distribution
        query = f"""
            SELECT
                CASE
                    WHEN session_count = 1 THEN 'Single Session'
                    WHEN session_count BETWEEN 2 AND 5 THEN '2-5 Sessions'
                    WHEN session_count BETWEEN 6 AND 10 THEN '6-10 Sessions'
                    ELSE '10+ Sessions'
                END as engagement_level,
                COUNT(*) as user_count
            FROM (
                SELECT user_id, COUNT(*) as session_count
                FROM sessions
                {date_filter}
                GROUP BY user_id
            ) user_sessions
            GROUP BY
                CASE
                    WHEN session_count = 1 THEN 'Single Session'
                    WHEN session_count BETWEEN 2 AND 5 THEN '2-5 Sessions'
                    WHEN session_count BETWEEN 6 AND 10 THEN '6-10 Sessions'
                    ELSE '10+ Sessions'
                END
            ORDER BY
                CASE
                    WHEN session_count = 1 THEN 1
                    WHEN session_count BETWEEN 2 AND 5 THEN 2
                    WHEN session_count BETWEEN 6 AND 10 THEN 3
                    ELSE 4
                END
        """
        log_media_query(query, params)
        cur.execute(query, params)
        engagement_distribution = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "top_users": [
                {
                    "user_id": row['user_id'],
                    "session_count": row['session_count'],
                    "avg_queries_per_session": round(row['avg_queries_per_session'], 2) if row['avg_queries_per_session'] else 0,
                    "last_session": row['last_session'].isoformat() if row['last_session'] else None
                }
                for row in user_engagement
            ],
            "engagement_distribution": [
                {"level": row['engagement_level'], "user_count": row['user_count']}
                for row in engagement_distribution
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting user engagement patterns: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/details")
def get_session_details(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Number of sessions to return"),
    offset: int = Query(0, description="Offset for pagination")
):
    """Get detailed session information with pagination"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE creation_time BETWEEN %s AND %s"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE creation_time >= %s"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE creation_time <= %s"
            params = [end_date]
        
        query = f"""
            SELECT 
                session_id,
                user_id,
                session_name,
                creation_time,
                last_activity_time,
                total_queries,
                session_summary,
                feedback_count,
                positive_feedback_count,
                negative_feedback_count,
                EXTRACT(EPOCH FROM (last_activity_time - creation_time))/60 as duration_minutes
            FROM sessions 
            {date_filter}
            ORDER BY creation_time DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        log_media_query(query, params)
        cur.execute(query, params)
        sessions = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return [
            {
                "session_id": row['session_id'],
                "user_id": row['user_id'],
                "session_name": row['session_name'],
                "creation_time": row['creation_time'].isoformat() if row['creation_time'] else None,
                "last_activity_time": row['last_activity_time'].isoformat() if row['last_activity_time'] else None,
                "total_queries": row['total_queries'],
                "session_summary": row['session_summary'],
                "feedback_count": row['feedback_count'],
                "positive_feedback_count": row['positive_feedback_count'],
                "negative_feedback_count": row['negative_feedback_count'],
                "duration_minutes": round(row['duration_minutes'], 2) if row['duration_minutes'] else 0
            }
            for row in sessions
        ]
        
    except Exception as e:
        logger.error(f"Error getting session details: {e}")
        raise HTTPException(status_code=500, detail=str(e))
