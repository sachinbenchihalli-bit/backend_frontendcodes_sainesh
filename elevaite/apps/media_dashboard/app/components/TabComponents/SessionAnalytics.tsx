"use client";

import React, { useEffect, useState } from 'react';
import { FiUsers, FiClock, FiActivity, FiCalendar, FiBarChart2 } from "react-icons/fi";

import './SessionAnalytics.scss';

import CustomBarChart from '../SubComponents/BarChart';
import Table from '../SubComponents/Table';

import { DateFilters } from '../Tabs';

interface SessionAnalyticsProps {
    dateFilters: DateFilters;
}

interface SessionSummary {
    total_sessions: number;
    unique_users: number;
    avg_queries_per_session: number;
    avg_session_duration_minutes: number;
    duration_distribution: Array<{
        range: string;
        count: number;
    }>;
}

interface SessionDetail {
    session_id: string;
    user_id: string;
    session_name: string;
    creation_time: string;
    last_activity_time: string;
    total_queries: number;
    session_summary: string;
    feedback_count: number;
    positive_feedback_count: number;
    negative_feedback_count: number;
    duration_minutes: number;
}

const SessionAnalytics: React.FC<SessionAnalyticsProps> = ({ dateFilters }) => {
    const [summary, setSummary] = useState<SessionSummary | null>(null);
    const [sessionsData, setSessionsData] = useState<SessionDetail[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchSessionData = async () => {
        try {
            setLoading(true);
            setError(null);

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/dashboardhttp://localhost:8000';
            const params = new URLSearchParams();
            
            if (dateFilters.startDate) params.append('start_date', dateFilters.startDate);
            if (dateFilters.endDate) params.append('end_date', dateFilters.endDate);

            // Fetch session summary
            const summaryResponse = await fetch(`${baseUrl}/api/media/sessions/summary?${params}`);
            if (!summaryResponse.ok) throw new Error('Failed to fetch session summary');
            const summaryData = await summaryResponse.json();
            setSummary(summaryData);

            // Fetch session details
            const detailsResponse = await fetch(`${baseUrl}/api/media/sessions/details?${params}&limit=50`);
            if (!detailsResponse.ok) throw new Error('Failed to fetch session details');
            const detailsData = await detailsResponse.json();
            setSessionsData(detailsData);

        } catch (err) {
            console.error('Error fetching session data:', err);
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchSessionData();
    }, [dateFilters]);

    if (loading) {
        return <div className="loading">Loading session analytics...</div>;
    }

    if (error) {
        return <div className="error">Error: {error}</div>;
    }

    if (!summary) {
        return <div className="no-data">No session data available</div>;
    }

    return (
        <div className="session-analytics-container">
            {/* Session Metrics */}
            <div className="summary-section">
                <div className="cards-grid-six">
                    <div className="summary-card">
                        <div className="card-icon">
                            <FiActivity />
                        </div>
                        <h3 className="card-title">Total Sessions</h3>
                        <div className="card-value">{(summary.total_sessions || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            Active user sessions
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiUsers />
                        </div>
                        <h3 className="card-title">Unique Users</h3>
                        <div className="card-value">{(summary.unique_users || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            Distinct user count
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiBarChart2 />
                        </div>
                        <h3 className="card-title">Avg Queries/Session</h3>
                        <div className="card-value">{summary.avg_queries_per_session || 0}</div>
                        <div className="card-change up">
                            User engagement level
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiClock />
                        </div>
                        <h3 className="card-title">Avg Session Duration</h3>
                        <div className="card-value">{summary.avg_session_duration_minutes || 0} min</div>
                        <div className="card-change down">
                            Time spent per session
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiCalendar />
                        </div>
                        <h3 className="card-title">Session Frequency</h3>
                        <div className="card-value">{((summary.total_sessions || 0) / Math.max((summary.unique_users || 1), 1)).toFixed(1)}</div>
                        <div className="card-change up">
                            Sessions per user
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiActivity />
                        </div>
                        <h3 className="card-title">Activity Rate</h3>
                        <div className="card-value">{summary.total_sessions > 0 ? ((summary.total_sessions || 0) / 30).toFixed(1) : 0}</div>
                        <div className="card-change up">
                            Sessions per day (30d avg)
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div className="charts-section">
                <div className="chart-row">
                    <div className="chart-container large">
                        <h3>Session Duration Distribution</h3>
                        <CustomBarChart
                            data={summary.duration_distribution.map(item => ({
                                label: item.range,
                                count: item.count,
                                color: "#8884d8"
                            }))}
                        />
                    </div>
                </div>


            </div>

            {/* Sessions Details Table */}
            <div className="sessions-table-section">
                <h3>Session Details</h3>
                <Table
                    data={sessionsData}
                    columns={[
                        {
                            label: 'Session ID',
                            key: 'session_id' as keyof SessionDetail,
                            width: '120px',
                            minWidth: '80px'
                        },
                        { label: 'User', key: 'user_id' as keyof SessionDetail },
                        {
                            label: 'Session Name',
                            key: 'session_name' as keyof SessionDetail,
                            render: (value: string) => value || 'Unnamed Session'
                        },
                        {
                            label: 'Created',
                            key: 'creation_time' as keyof SessionDetail,
                            render: (value: string) => value ? new Date(value).toLocaleString() : 'N/A'
                        },
                        {
                            label: 'Duration',
                            key: 'duration_minutes' as keyof SessionDetail,
                            render: (value: number) => `${value.toFixed(1)} min`
                        },
                        { label: 'Queries', key: 'total_queries' as keyof SessionDetail },
                        {
                            label: 'Feedback',
                            key: 'feedback_count' as keyof SessionDetail,
                            render: (value: number, row: SessionDetail) => {
                                const positive = row.positive_feedback_count || 0;
                                const negative = row.negative_feedback_count || 0;
                                return `${value} (👍${positive} 👎${negative})`;
                            }
                        }
                    ]}
                    title="Session Details"
                    showPagination={true}
                />

                {sessionsData.length === 0 && (
                    <div className="no-data-message">
                        <p>No session data available for the selected time period</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default SessionAnalytics;
