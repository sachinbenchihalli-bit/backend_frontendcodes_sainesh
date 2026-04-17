# Database Visualizer for Media Backend

A Streamlit-based visualization tool for exploring and analyzing the media backend database schema and data.

## Features

- **Schema Overview**: View detailed information about all database tables and their columns
- **Sessions Analysis**: Explore user sessions, activity patterns, and session metrics
- **Queries Analysis**: Analyze query performance, success rates, and intent distribution
- **Agent Execution Steps**: Monitor agent performance and execution patterns
- **Feedback Analysis**: Track user feedback trends and satisfaction rates
- **Agent Performance Metrics**: View aggregated performance data for all agents
- **Data Relationships**: Explore cross-table relationships and correlations

## Quick Start

### Option 1: Using the Setup Script (Recommended)

```bash
cd python_apps/media_backend
python run_visualizer.py
```

The setup script will:
1. Install required dependencies
2. Check environment variables
3. Start the Streamlit app on http://localhost:8502

### Option 2: Manual Setup

1. **Install Dependencies**
   ```bash
   cd python_apps/media_backend
   pip install -r requirements_visualizer.txt
   ```

2. **Set Environment Variables**
   
   Create a `.env` file or set these environment variables:
   ```bash
   DB_HOST=localhost
   DB_PORT=5432
   DB_USERNAME=postgres
   DB_PASSWORD=12345
   DB_NAME=creative_db
   ```

3. **Run the Visualizer**
   ```bash
   streamlit run database_visualizer.py --server.port 8502
   ```

## Database Schema

The visualizer works with the following tables:

### Sessions Table
- `session_id` (Primary Key)
- `user_id`
- `session_name`
- `creation_time`
- `last_activity_time`
- `total_queries`
- `topics_discussed` (JSON)
- `primary_intent`
- `session_summary`
- `total_tokens_used` (JSON)
- `feedback_count`
- `positive_feedback_count`
- `negative_feedback_count`

### Queries Table
- `query_id` (Primary Key)
- `session_id` (Foreign Key)
- `user_id`
- `original_query`
- `start_time`
- `end_time`
- `total_duration_ms`
- `final_response`
- `intent_detected`
- `agents_used` (JSON)
- `total_tokens_used` (JSON)
- `success`
- `error_details`

### Agent Execution Steps Table
- `id` (Primary Key)
- `query_id` (Foreign Key)
- `agent_name`
- `step_type`
- `start_time`
- `end_time`
- `duration_ms`
- `input_prompt`
- `output_response`
- `model_used`
- `tokens_used` (JSON)
- `success`
- `error_details`
- `metadata` (JSON)

### Feedback Table
- `id` (Primary Key)
- `query_id` (Foreign Key)
- `session_id` (Foreign Key)
- `user_id`
- `feedback_type`
- `feedback_text`
- `vote` (1=up, -1=down, 0=neutral)
- `timestamp`
- `agent_specific_feedback` (JSON)

### Agent Performance Metrics Table
- `id` (Primary Key)
- `agent_name`
- `date`
- `total_executions`
- `successful_executions`
- `failed_executions`
- `average_duration_ms`
- `total_tokens_used` (JSON)
- `positive_feedback_count`
- `negative_feedback_count`
- `last_updated`

## Navigation

The app includes several views accessible via the sidebar:

1. **Schema Overview**: Database table structures and column information
2. **Sessions**: User session analytics and trends
3. **Queries**: Query performance and intent analysis
4. **Agent Execution Steps**: Individual agent step monitoring
5. **Feedback**: User feedback trends and satisfaction metrics
6. **Agent Performance**: Aggregated agent performance data
7. **Data Relationships**: Cross-table analytics and correlations

## Troubleshooting

### Database Connection Issues

1. **Check Database Status**
   ```bash
   # For local PostgreSQL
   pg_isready -h localhost -p 5432
   ```

2. **Verify Credentials**
   - Ensure your database credentials are correct
   - Check that the database exists and is accessible

3. **Environment Variables**
   - Verify all required environment variables are set
   - Check the `.env` file in the media_backend directory

### Common Error Messages

- **"Database connection failed"**: Check your database credentials and ensure PostgreSQL is running
- **"No table information available"**: Verify that the database tables exist and you have read permissions
- **"No data available"**: The tables exist but contain no data

### Performance Considerations

- The visualizer limits data loading to 1000 rows by default for performance
- Large datasets may take longer to load and render
- Consider filtering data by date range for better performance

## Development

To modify or extend the visualizer:

1. **Add New Visualizations**: Edit `database_visualizer.py` and add new functions
2. **Modify Queries**: Update the SQL queries in the `load_table_data` function
3. **Add New Tables**: Extend the table list in `get_table_info` function
4. **Custom Styling**: Modify Streamlit configuration and Plotly chart styling

## Dependencies

- `streamlit`: Web app framework
- `pandas`: Data manipulation and analysis
- `plotly`: Interactive visualizations
- `sqlalchemy`: Database ORM and connection management
- `psycopg2-binary`: PostgreSQL adapter for Python
- `python-dotenv`: Environment variable management

## Support

For issues or questions:
1. Check the application logs in the terminal
2. Verify database connectivity and permissions
3. Review this README for troubleshooting steps
4. Check the media backend documentation for database schema details
