#!/usr/bin/env python3
"""
Database Schema Visualizer for Media Backend

This Streamlit app provides visualization and exploration of the media backend database schema
including sessions, queries, agent execution steps, and feedback.

Note: Agent performance metrics are calculated dynamically from agent execution steps data.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sqlalchemy as sa
from sqlalchemy.orm import sessionmaker
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Also try to load from parent directory
import pathlib
parent_env = pathlib.Path(__file__).parent.parent / ".env"
if parent_env.exists():
    load_dotenv(parent_env)

# Database connection configuration
@st.cache_resource
def get_database_connection():
    """Create and cache database connection"""
    try:
        # Try to use the same configuration as the media backend
        host = os.getenv("DB_HOST", "localhost")
        port = int(os.getenv("DB_PORT", 5432))
        username = os.getenv("DB_USERNAME", "postgres")
        password = os.getenv("DB_PASSWORD", "12345")
        database = os.getenv("DB_NAME", "creative_db")

        connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        engine = sa.create_engine(connection_string, pool_pre_ping=True)

        # Test connection
        with engine.connect() as conn:
            conn.execute(sa.text("SELECT 1"))

        return engine
    except Exception as e:
        st.error(f"Database connection failed: {e}")
        st.info("Please ensure your database is running and environment variables are set correctly.")
        return None

@st.cache_data
def load_table_data(_engine, table_name, limit=1000):
    """Load data from a specific table"""
    if _engine is None:
        return pd.DataFrame()

    try:
        # Define the appropriate timestamp column for each table
        timestamp_columns = {
            'sessions': 'creation_time',
            'queries': 'start_time',
            'agent_execution_steps': 'start_time',
            'feedback': 'timestamp'
        }

        timestamp_col = timestamp_columns.get(table_name)

        if timestamp_col:
            # First check if the column exists
            check_query = f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = '{table_name}'
            AND column_name = '{timestamp_col}'
            """
            result = pd.read_sql(check_query, _engine)

            if not result.empty:
                query = f"SELECT * FROM {table_name} ORDER BY {timestamp_col} DESC LIMIT {limit}"
            else:
                query = f"SELECT * FROM {table_name} LIMIT {limit}"
        else:
            query = f"SELECT * FROM {table_name} LIMIT {limit}"

        return pd.read_sql(query, _engine)
    except Exception as e:
        st.error(f"Error loading data from {table_name}: {e}")
        return pd.DataFrame()

@st.cache_data
def get_table_info(_engine):
    """Get information about all tables in the database"""
    if _engine is None:
        return {}

    try:
        query = """
        SELECT
            table_name,
            column_name,
            data_type,
            is_nullable,
            column_default
        FROM information_schema.columns
        WHERE table_schema = 'public'
        AND table_name IN ('sessions', 'queries', 'agent_execution_steps', 'feedback', 'related_queries')
        ORDER BY table_name, ordinal_position
        """
        df = pd.read_sql(query, _engine)

        # Group by table
        tables_info = {}
        for table in df['table_name'].unique():
            tables_info[table] = df[df['table_name'] == table][['column_name', 'data_type', 'is_nullable', 'column_default']]

        return tables_info
    except Exception as e:
        st.error(f"Error getting table info: {e}")
        return {}

def main():
    st.set_page_config(
        page_title="Media Backend Database Visualizer",
        page_icon="🗄️",
        layout="wide"
    )

    st.title("🗄️ Media Backend Database Visualizer")
    st.markdown("Explore and visualize the media backend database schema and data")

    # Get database connection
    engine = get_database_connection()

    if engine is None:
        st.stop()

    # Sidebar for navigation
    st.sidebar.title("Navigation")
    page = st.sidebar.selectbox(
        "Choose a view:",
        ["Schema Overview", "Sessions", "Queries", "Agent Execution Steps", "Feedback", "Agent Performance (Calculated)", "Data Relationships"]
    )

    # Get table information
    tables_info = get_table_info(engine)

    if page == "Schema Overview":
        show_schema_overview(tables_info)
    elif page == "Sessions":
        show_sessions_data(engine)
    elif page == "Queries":
        show_queries_data(engine)
    elif page == "Agent Execution Steps":
        show_agent_steps_data(engine)
    elif page == "Feedback":
        show_feedback_data(engine)
    elif page == "Agent Performance (Calculated)":
        show_agent_performance_calculated(engine)
    elif page == "Data Relationships":
        show_data_relationships(engine)

def show_schema_overview(tables_info):
    """Display database schema overview"""
    st.header("📋 Database Schema Overview")

    if not tables_info:
        st.warning("No table information available")
        return

    # Create tabs for each table
    table_names = list(tables_info.keys())
    tabs = st.tabs(table_names)

    for i, table_name in enumerate(table_names):
        with tabs[i]:
            st.subheader(f"Table: {table_name}")

            # Display table schema
            df = tables_info[table_name]
            st.dataframe(df, use_container_width=True)

            # Show table statistics
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Total Columns", len(df))
            with col2:
                nullable_count = len(df[df['is_nullable'] == 'YES'])
                st.metric("Nullable Columns", nullable_count)

def show_sessions_data(engine):
    """Display sessions data and analytics"""
    st.header("👥 Sessions Analysis")

    # Load sessions data
    sessions_df = load_table_data(engine, "sessions")

    if sessions_df.empty:
        st.info("No sessions data available")
        return

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Sessions", len(sessions_df))
    with col2:
        avg_queries = sessions_df['total_queries'].mean() if 'total_queries' in sessions_df.columns else 0
        st.metric("Avg Queries/Session", f"{avg_queries:.1f}")
    with col3:
        total_feedback = sessions_df['feedback_count'].sum() if 'feedback_count' in sessions_df.columns else 0
        st.metric("Total Feedback", total_feedback)
    with col4:
        active_sessions = len(sessions_df[sessions_df['total_queries'] > 0]) if 'total_queries' in sessions_df.columns else 0
        st.metric("Active Sessions", active_sessions)

    # Sessions over time
    if 'creation_time' in sessions_df.columns:
        sessions_df['creation_date'] = pd.to_datetime(sessions_df['creation_time']).dt.date
        daily_sessions = sessions_df.groupby('creation_date').size().reset_index(name='count')

        fig = px.line(daily_sessions, x='creation_date', y='count',
                     title="Sessions Created Over Time")
        st.plotly_chart(fig, use_container_width=True)

    # Display raw data
    st.subheader("Sessions Data")
    st.dataframe(sessions_df, use_container_width=True)

def show_queries_data(engine):
    """Display queries data and analytics"""
    st.header("🔍 Queries Analysis")

    # Load queries data
    queries_df = load_table_data(engine, "queries")

    if queries_df.empty:
        st.info("No queries data available")
        return

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Queries", len(queries_df))
    with col2:
        success_rate = (queries_df['success'].sum() / len(queries_df) * 100) if 'success' in queries_df.columns else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
    with col3:
        avg_duration = queries_df['total_duration_ms'].mean() if 'total_duration_ms' in queries_df.columns else 0
        st.metric("Avg Duration (ms)", f"{avg_duration:.0f}")
    with col4:
        unique_intents = queries_df['intent_detected'].nunique() if 'intent_detected' in queries_df.columns else 0
        st.metric("Unique Intents", unique_intents)

    # Query performance over time
    if 'start_time' in queries_df.columns and 'total_duration_ms' in queries_df.columns:
        queries_df['start_date'] = pd.to_datetime(queries_df['start_time']).dt.date
        daily_performance = queries_df.groupby('start_date')['total_duration_ms'].mean().reset_index()

        fig = px.line(daily_performance, x='start_date', y='total_duration_ms',
                     title="Average Query Duration Over Time")
        st.plotly_chart(fig, use_container_width=True)

    # Intent distribution
    if 'intent_detected' in queries_df.columns:
        intent_counts = queries_df['intent_detected'].value_counts()
        fig = px.pie(values=intent_counts.values, names=intent_counts.index,
                    title="Query Intent Distribution")
        st.plotly_chart(fig, use_container_width=True)

    # Display raw data
    st.subheader("Queries Data")
    st.dataframe(queries_df, use_container_width=True)

def show_agent_steps_data(engine):
    """Display agent execution steps data"""
    st.header("🤖 Agent Execution Steps")

    # Load agent steps data
    steps_df = load_table_data(engine, "agent_execution_steps")

    if steps_df.empty:
        st.info("No agent execution steps data available")
        return

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Steps", len(steps_df))
    with col2:
        unique_agents = steps_df['agent_name'].nunique() if 'agent_name' in steps_df.columns else 0
        st.metric("Unique Agents", unique_agents)
    with col3:
        success_rate = (steps_df['success'].sum() / len(steps_df) * 100) if 'success' in steps_df.columns else 0
        st.metric("Success Rate", f"{success_rate:.1f}%")
    with col4:
        avg_duration = steps_df['duration_ms'].mean() if 'duration_ms' in steps_df.columns else 0
        st.metric("Avg Duration (ms)", f"{avg_duration:.0f}")

    # Agent performance comparison
    if 'agent_name' in steps_df.columns and 'duration_ms' in steps_df.columns:
        agent_performance = steps_df.groupby('agent_name')['duration_ms'].agg(['mean', 'count']).reset_index()
        agent_performance.columns = ['agent_name', 'avg_duration', 'execution_count']

        fig = px.scatter(agent_performance, x='execution_count', y='avg_duration',
                        text='agent_name', title="Agent Performance: Duration vs Execution Count")
        fig.update_traces(textposition="top center")
        st.plotly_chart(fig, use_container_width=True)

    # Display raw data
    st.subheader("Agent Execution Steps Data")
    st.dataframe(steps_df, use_container_width=True)

def show_feedback_data(engine):
    """Display feedback data and analytics"""
    st.header("👍 Feedback Analysis")

    # Load feedback data
    feedback_df = load_table_data(engine, "feedback")

    if feedback_df.empty:
        st.info("No feedback data available")
        return

    # Display metrics
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Feedback", len(feedback_df))
    with col2:
        positive_feedback = len(feedback_df[feedback_df['vote'] > 0]) if 'vote' in feedback_df.columns else 0
        st.metric("Positive Feedback", positive_feedback)
    with col3:
        negative_feedback = len(feedback_df[feedback_df['vote'] < 0]) if 'vote' in feedback_df.columns else 0
        st.metric("Negative Feedback", negative_feedback)
    with col4:
        satisfaction_rate = (positive_feedback / len(feedback_df) * 100) if len(feedback_df) > 0 else 0
        st.metric("Satisfaction Rate", f"{satisfaction_rate:.1f}%")

    # Feedback over time
    if 'timestamp' in feedback_df.columns:
        feedback_df['feedback_date'] = pd.to_datetime(feedback_df['timestamp']).dt.date
        daily_feedback = feedback_df.groupby('feedback_date').size().reset_index(name='count')

        fig = px.line(daily_feedback, x='feedback_date', y='count',
                     title="Feedback Submissions Over Time")
        st.plotly_chart(fig, use_container_width=True)

    # Feedback type distribution
    if 'feedback_type' in feedback_df.columns:
        type_counts = feedback_df['feedback_type'].value_counts()
        fig = px.bar(x=type_counts.index, y=type_counts.values,
                    title="Feedback Type Distribution")
        st.plotly_chart(fig, use_container_width=True)

    # Display raw data
    st.subheader("Feedback Data")
    st.dataframe(feedback_df, use_container_width=True)

def show_agent_performance_calculated(engine):
    """Display calculated agent performance metrics from execution steps"""
    st.header("📊 Agent Performance Metrics (Calculated)")

    st.info("📝 Note: Agent performance metrics are now calculated dynamically from agent execution steps data instead of being stored in a separate table.")

    # Load agent execution steps data
    steps_df = load_table_data(engine, "agent_execution_steps", limit=5000)

    if steps_df.empty:
        st.info("No agent execution steps data available for performance calculation")
        return

    # Calculate performance metrics by agent
    if 'agent_name' in steps_df.columns:
        agent_performance = steps_df.groupby('agent_name').agg({
            'id': 'count',  # Total executions
            'success': ['sum', 'mean'],  # Successful executions and success rate
            'duration_ms': ['mean', 'median', 'std'],  # Duration statistics
            'tokens_used': lambda x: x.apply(lambda tokens: tokens.get('total', 0) if isinstance(tokens, dict) else 0).sum()  # Total tokens
        }).round(2)

        # Flatten column names
        agent_performance.columns = [
            'total_executions', 'successful_executions', 'success_rate',
            'avg_duration_ms', 'median_duration_ms', 'std_duration_ms', 'total_tokens'
        ]
        agent_performance = agent_performance.reset_index()

        # Convert success rate to percentage
        agent_performance['success_rate'] = agent_performance['success_rate'] * 100

        # Display overall metrics
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            total_executions = agent_performance['total_executions'].sum()
            st.metric("Total Executions", total_executions)
        with col2:
            overall_success_rate = (agent_performance['successful_executions'].sum() / total_executions * 100) if total_executions > 0 else 0
            st.metric("Overall Success Rate", f"{overall_success_rate:.1f}%")
        with col3:
            unique_agents = len(agent_performance)
            st.metric("Active Agents", unique_agents)
        with col4:
            avg_duration = agent_performance['avg_duration_ms'].mean()
            st.metric("Avg Duration (ms)", f"{avg_duration:.0f}")

        # Agent success rate comparison
        fig = px.bar(agent_performance, x='agent_name', y='success_rate',
                    title="Success Rate by Agent (%)",
                    labels={'success_rate': 'Success Rate (%)', 'agent_name': 'Agent Name'})
        fig.update_layout(xaxis_tickangle=-45)
        st.plotly_chart(fig, use_container_width=True)

        # Agent execution count vs average duration
        fig2 = px.scatter(agent_performance, x='total_executions', y='avg_duration_ms',
                         size='total_tokens', hover_name='agent_name',
                         title="Agent Performance: Execution Count vs Average Duration",
                         labels={'total_executions': 'Total Executions', 'avg_duration_ms': 'Average Duration (ms)'})
        st.plotly_chart(fig2, use_container_width=True)

        # Display calculated performance table
        st.subheader("Calculated Agent Performance Metrics")
        st.dataframe(agent_performance, use_container_width=True)

        # Show recent errors if any
        if 'error_details' in steps_df.columns:
            failed_steps = steps_df[steps_df['success'] == False]
            if not failed_steps.empty:
                st.subheader("Recent Errors")
                error_summary = failed_steps.groupby('agent_name')['error_details'].count().reset_index()
                error_summary.columns = ['agent_name', 'error_count']
                st.dataframe(error_summary, use_container_width=True)
    else:
        st.warning("Agent execution steps data does not contain agent_name column")

def show_data_relationships(engine):
    """Display data relationships and cross-table analytics"""
    st.header("🔗 Data Relationships")

    # Load all data
    sessions_df = load_table_data(engine, "sessions", limit=500)
    queries_df = load_table_data(engine, "queries", limit=500)
    feedback_df = load_table_data(engine, "feedback", limit=500)

    if sessions_df.empty or queries_df.empty:
        st.info("Insufficient data for relationship analysis")
        return

    # Session-Query relationship
    if not sessions_df.empty and not queries_df.empty:
        session_query_stats = queries_df.groupby('session_id').agg({
            'query_id': 'count',
            'total_duration_ms': 'mean',
            'success': 'mean'
        }).reset_index()
        session_query_stats.columns = ['session_id', 'query_count', 'avg_duration', 'success_rate']

        fig = px.scatter(session_query_stats, x='query_count', y='avg_duration',
                        color='success_rate', title="Session Analysis: Query Count vs Average Duration")
        st.plotly_chart(fig, use_container_width=True)

    # Query-Feedback relationship
    if not queries_df.empty and not feedback_df.empty:
        query_feedback = queries_df.merge(feedback_df, on='query_id', how='left')
        feedback_by_intent = query_feedback.groupby('intent_detected')['vote'].mean().reset_index()

        fig = px.bar(feedback_by_intent, x='intent_detected', y='vote',
                    title="Average Feedback Score by Intent")
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Database Relationship Summary")
    st.markdown("""
    **Table Relationships:**
    - **Sessions** → **Queries** (1:many via session_id)
    - **Queries** → **Agent Execution Steps** (1:many via query_id)
    - **Queries** → **Feedback** (1:many via query_id)
    - **Sessions** → **Feedback** (1:many via session_id)
    - **Queries** → **Related Queries** (1:many via query_id)

    **Schema Changes:**
    - ✅ **Removed unused fields**: Sessions.primary_intent, Sessions.topics_discussed
    - ✅ **Removed unused fields**: Feedback.agent_specific_feedback
    - ✅ **Removed table**: AgentPerformanceMetrics (now calculated from AgentExecutionSteps)
    - ✅ **Enhanced tracking**: Queries.intent_detected now properly populated
    - ✅ **Enhanced tracking**: Queries.success and error_details properly set
    """)

if __name__ == "__main__":
    main()


#  python run_visualizer.py