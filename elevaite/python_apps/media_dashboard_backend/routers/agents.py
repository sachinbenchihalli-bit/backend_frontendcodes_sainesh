# routers/agents.py
from fastapi import APIRouter, Query, HTTPException
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
import logging
from database import get_db_connection, log_media_query

router = APIRouter(prefix="/api/media/agents")
logger = logging.getLogger(__name__)

@router.get("/performance")
def get_agent_performance(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get agent performance metrics"""
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
        
        # Get agent performance metrics
        query = f"""
            SELECT 
                agent_name,
                COUNT(*) as total_executions,
                AVG(duration_ms) as avg_execution_time,
                COUNT(CASE WHEN success = true THEN 1 END) as successful_executions,
                COUNT(CASE WHEN success = false THEN 1 END) as failed_executions,
                COUNT(DISTINCT query_id) as unique_queries
            FROM agent_execution_steps 
            {date_filter}
            GROUP BY agent_name
            ORDER BY total_executions DESC
        """
        log_media_query(query, params)
        cur.execute(query, params)
        agent_performance = cur.fetchall()
        
        cur.close()
        conn.close()
        
        result = []
        for row in agent_performance:
            success_rate = 0
            if row['total_executions'] > 0:
                success_rate = round((row['successful_executions'] / row['total_executions']) * 100, 2)
            
            result.append({
                "agent_name": row['agent_name'],
                "total_executions": row['total_executions'],
                "avg_execution_time": round(row['avg_execution_time'], 2) if row['avg_execution_time'] else 0,
                "success_rate": success_rate,
                "successful_executions": row['successful_executions'],
                "failed_executions": row['failed_executions'],
                "unique_queries": row['unique_queries']
            })
        
        return result
        
    except Exception as e:
        logger.error(f"Error getting agent performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/errors")
def get_agent_errors(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(20, description="Number of recent errors to return")
):
    """Get agent error details and analysis"""
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Build date filter
        date_filter = ""
        params = []
        if start_date and end_date:
            date_filter = "WHERE start_time BETWEEN %s AND %s AND success = false"
            params = [start_date, end_date]
        elif start_date:
            date_filter = "WHERE start_time >= %s AND success = false"
            params = [start_date]
        elif end_date:
            date_filter = "WHERE start_time <= %s AND success = false"
            params = [end_date]
        else:
            date_filter = "WHERE success = false"
        
        # Get error summary by agent
        query = f"""
            SELECT 
                agent_name,
                COUNT(*) as error_count,
                COUNT(DISTINCT query_id) as affected_queries
            FROM agent_execution_steps 
            {date_filter}
            GROUP BY agent_name
            ORDER BY error_count DESC
        """
        log_media_query(query, params)
        cur.execute(query, params)
        error_summary = cur.fetchall()
        
        # Get recent error details
        query = f"""
            SELECT 
                agent_name,
                step_type,
                start_time,
                duration_ms,
                error_details,
                query_id
            FROM agent_execution_steps 
            {date_filter}
            ORDER BY start_time DESC
            LIMIT %s
        """
        params.append(limit)
        log_media_query(query, params)
        cur.execute(query, params)
        recent_errors = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "error_summary": [
                {
                    "agent_name": row['agent_name'],
                    "error_count": row['error_count'],
                    "affected_queries": row['affected_queries']
                }
                for row in error_summary
            ],
            "recent_errors": [
                {
                    "agent_name": row['agent_name'],
                    "step_type": row['step_type'],
                    "start_time": row['start_time'].isoformat() if row['start_time'] else None,
                    "duration_ms": row['duration_ms'],
                    "error_details": row['error_details'],
                    "query_id": row['query_id']
                }
                for row in recent_errors
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting agent errors: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/tokens")
def get_token_usage(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get token usage by agent and model"""
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
        
        # Get token usage by agent
        query = f"""
            SELECT 
                agent_name,
                model_used,
                COUNT(*) as executions,
                SUM((tokens_used->>'input')::int) as total_input_tokens,
                SUM((tokens_used->>'output')::int) as total_output_tokens,
                SUM((tokens_used->>'total')::int) as total_tokens
            FROM agent_execution_steps 
            WHERE tokens_used IS NOT NULL 
            AND tokens_used->>'total' IS NOT NULL
            {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            GROUP BY agent_name, model_used
            ORDER BY total_tokens DESC
        """
        log_media_query(query, params)
        cur.execute(query, params)
        token_usage = cur.fetchall()
        
        # Get token usage trends by date
        query = f"""
            SELECT 
                DATE(start_time) as date,
                SUM((tokens_used->>'total')::int) as total_tokens,
                COUNT(*) as executions
            FROM agent_execution_steps 
            WHERE tokens_used IS NOT NULL 
            AND tokens_used->>'total' IS NOT NULL
            {date_filter.replace('WHERE', 'AND') if date_filter else ''}
            GROUP BY DATE(start_time)
            ORDER BY date
        """
        log_media_query(query, params)
        cur.execute(query, params)
        token_trends = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return {
            "usage_by_agent": [
                {
                    "agent_name": row['agent_name'],
                    "model_used": row['model_used'],
                    "executions": row['executions'],
                    "total_input_tokens": row['total_input_tokens'] or 0,
                    "total_output_tokens": row['total_output_tokens'] or 0,
                    "total_tokens": row['total_tokens'] or 0,
                    "avg_tokens_per_execution": round((row['total_tokens'] or 0) / row['executions'], 2) if row['executions'] > 0 else 0
                }
                for row in token_usage
            ],
            "usage_trends": [
                {
                    "date": row['date'].strftime('%Y-%m-%d'),
                    "total_tokens": row['total_tokens'] or 0,
                    "executions": row['executions'],
                    "avg_tokens_per_execution": round((row['total_tokens'] or 0) / row['executions'], 2) if row['executions'] > 0 else 0
                }
                for row in token_trends
            ]
        }
        
    except Exception as e:
        logger.error(f"Error getting token usage: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/step-types")
def get_step_type_analysis(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)")
):
    """Get analysis of agent step types and their performance"""
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

        # Get step type performance
        query = f"""
            SELECT
                step_type,
                COUNT(*) as total_executions,
                AVG(duration_ms) as avg_duration,
                COUNT(CASE WHEN success = true THEN 1 END) as successful_executions,
                COUNT(DISTINCT agent_name) as unique_agents,
                COUNT(DISTINCT query_id) as unique_queries
            FROM agent_execution_steps
            {date_filter}
            GROUP BY step_type
            ORDER BY total_executions DESC
        """
        log_media_query(query, params)
        cur.execute(query, params)
        step_type_data = cur.fetchall()

        cur.close()
        conn.close()

        result = []
        for row in step_type_data:
            success_rate = 0
            if row['total_executions'] > 0:
                success_rate = round((row['successful_executions'] / row['total_executions']) * 100, 2)

            result.append({
                "step_type": row['step_type'],
                "total_executions": row['total_executions'],
                "avg_duration": round(row['avg_duration'], 2) if row['avg_duration'] else 0,
                "success_rate": success_rate,
                "successful_executions": row['successful_executions'],
                "unique_agents": row['unique_agents'],
                "unique_queries": row['unique_queries']
            })

        return result

    except Exception as e:
        logger.error(f"Error getting step type analysis: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/execution-steps")
def get_execution_steps(
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    limit: int = Query(50, description="Number of execution steps to return"),
    offset: int = Query(0, description="Number of execution steps to skip")
):
    """Get detailed agent execution steps data"""
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

        # Get execution steps with detailed information
        query = f"""
            SELECT
                id,
                query_id,
                agent_name,
                step_type,
                start_time,
                end_time,
                duration_ms,
                model_used,
                tokens_used,
                success,
                error_details,
                input_prompt,
                output_response
            FROM agent_execution_steps
            {date_filter}
            ORDER BY start_time DESC
            LIMIT %s OFFSET %s
        """
        params.extend([limit, offset])
        log_media_query(query, params)
        cur.execute(query, params)
        execution_steps = cur.fetchall()

        # Get total count for pagination
        count_query = f"""
            SELECT COUNT(*) as total_count
            FROM agent_execution_steps
            {date_filter}
        """
        count_params = params[:-2]  # Remove limit and offset
        log_media_query(count_query, count_params)
        cur.execute(count_query, count_params)
        total_count = cur.fetchone()['total_count']

        cur.close()
        conn.close()

        result = []
        for row in execution_steps:
            # Extract token information
            tokens_used = row['tokens_used'] or {}
            total_tokens = tokens_used.get('total', 0) if isinstance(tokens_used, dict) else 0

            result.append({
                "id": str(row['id']),
                "query_id": row['query_id'],
                "agent_name": row['agent_name'],
                "step_type": row['step_type'],
                "start_time": row['start_time'].isoformat() if row['start_time'] else None,
                "end_time": row['end_time'].isoformat() if row['end_time'] else None,
                "duration_ms": row['duration_ms'],
                "model_used": row['model_used'],
                "total_tokens": total_tokens,
                "success": row['success'],
                "error_details": row['error_details'],
                "input_prompt": row['input_prompt'],
                "output_response": row['output_response']
            })

        return {
            "execution_steps": result,
            "total_count": total_count,
            "limit": limit,
            "offset": offset
        }

    except Exception as e:
        logger.error(f"Error getting execution steps: {e}")
        raise HTTPException(status_code=500, detail=str(e))
