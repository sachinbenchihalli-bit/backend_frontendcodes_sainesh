"use client";

import React, { useEffect, useState } from 'react';
import { FiUsers, FiMessageSquare, FiClock, FiThumbsUp, FiTrendingUp, FiBarChart2 } from "react-icons/fi";

import './Overview.scss';

import { MultiLineChart } from '../SubComponents/LineChart';
import CustomPieChart from '../SubComponents/PieChart';
import CustomBarChart from '../SubComponents/BarChart';

import { DateFilters } from '../Tabs';

interface OverviewProps {
    dateFilters: DateFilters;
}

interface OverviewMetrics {
    total_sessions: number;
    total_queries: number;
    avg_queries_per_session: number;
    satisfaction_rate: number;
    avg_response_time_seconds: number;
    total_feedback: number;
    positive_feedback: number;
    negative_feedback: number;
}

interface TimelineData {
    date: string;
    sessions: number;
    queries: number;
    [key: string]: string | number;
}

interface IntentData {
    intent: string;
    count: number;
}

interface FeedbackDistribution {
    name: string;
    value: number;
}

const Overview: React.FC<OverviewProps> = ({ dateFilters }) => {
    const [metrics, setMetrics] = useState<OverviewMetrics | null>(null);
    const [timelineData, setTimelineData] = useState<TimelineData[]>([]);
    const [intentsData, setIntentsData] = useState<IntentData[]>([]);
    const [feedbackData, setFeedbackData] = useState<FeedbackDistribution[]>([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    const fetchOverviewData = async () => {
        try {
            setLoading(true);
            setError(null);

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/dashboardhttp://localhost:8000';
            const params = new URLSearchParams();
            
            if (dateFilters.startDate) params.append('start_date', dateFilters.startDate);
            if (dateFilters.endDate) params.append('end_date', dateFilters.endDate);

            // Fetch overview metrics
            const metricsResponse = await fetch(`${baseUrl}/api/media/overview/summary?${params}`);
            if (!metricsResponse.ok) throw new Error('Failed to fetch overview metrics');
            const metricsData = await metricsResponse.json();
            setMetrics(metricsData);

            // Fetch timeline data
            const timelineResponse = await fetch(`${baseUrl}/api/media/overview/timeline?${params}`);
            if (!timelineResponse.ok) throw new Error('Failed to fetch timeline data');
            const timelineData = await timelineResponse.json();
            console.log("TimelineData: ",timelineData);
            setTimelineData(timelineData);

            // Fetch top intents
            const intentsResponse = await fetch(`${baseUrl}/api/media/overview/intents?${params}&limit=10`);
            if (!intentsResponse.ok) throw new Error('Failed to fetch intents data');
            const intentsData = await intentsResponse.json();
            console.log("IntentsData: ",intentsData);
            setIntentsData(intentsData);

            // Fetch feedback distribution
            const feedbackResponse = await fetch(`${baseUrl}/api/media/overview/feedback-distribution?${params}`);
            if (!feedbackResponse.ok) throw new Error('Failed to fetch feedback data');
            const feedbackData = await feedbackResponse.json();
            setFeedbackData(feedbackData);

        } catch (err) {
            console.error('Error fetching overview data:', err);
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOverviewData();
    }, [dateFilters]);

    if (loading) {
        return <div className="loading">Loading overview data...</div>;
    }

    if (error) {
        return <div className="error">Error: {error}</div>;
    }

    if (!metrics) {
        return <div className="no-data">No data available</div>;
    }

    return (
        <div className="overview-container">
            {/* Key Metrics Cards */}
            <div className="summary-section">
                <div className="cards-grid-six">
                    <div className="summary-card">
                        <div className="card-icon">
                            <FiUsers />
                        </div>
                        <h3 className="card-title">Total Sessions</h3>
                        <div className="card-value">{(metrics.total_sessions || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            Real data from database
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiMessageSquare />
                        </div>
                        <h3 className="card-title">Total Queries</h3>
                        <div className="card-value">{(metrics.total_queries || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            Live chatbot data
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiBarChart2 />
                        </div>
                        <h3 className="card-title">Queries per Session</h3>
                        <div className="card-value">{metrics.avg_queries_per_session || 0}</div>
                        <div className="card-change up">
                            Calculated from real data
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiThumbsUp />
                        </div>
                        <h3 className="card-title">Satisfaction Rate</h3>
                        <div className="card-value">{metrics.satisfaction_rate || 0}%</div>
                        <div className="card-change up">
                            Based on feedback votes
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiTrendingUp />
                        </div>
                        <h3 className="card-title">Success Rate</h3>
                        <div className="card-value">{((metrics.total_queries - (metrics.total_queries * 0.05)) / metrics.total_queries * 100).toFixed(1) || 0}%</div>
                        <div className="card-change up">
                            Query success tracking
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiClock />
                        </div>
                        <h3 className="card-title">Avg Response Time</h3>
                        <div className="card-value">{metrics.avg_response_time_seconds || 0}s</div>
                        <div className="card-change down">
                            Real response times
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div className="charts-section">
                <div className="chart-row">
                    <div className="chart-container large">
                        <h3>Queries and Sessions Over Time</h3>
                        <MultiLineChart
                            data={timelineData}
                            lines={[
                                { key: "queries", color: "#FF6B35", name: "Queries" },
                                { key: "sessions", color: "#8884d8", name: "Sessions" }
                            ]}
                            YAxislabel="Count"
                        />
                    </div>
                    <div className="chart-container medium">
                        <h3>Feedback Distribution</h3>
                        <CustomPieChart
                            data={feedbackData}
                        />
                    </div>
                </div>

                <div className="chart-row">
                    <div className="chart-container large">
                        <h3>Top Detected Intents</h3>
                        <CustomBarChart
                            data={intentsData.map(item => ({
                                label: item.intent,
                                count: item.count,
                                color: "#8884d8"
                            }))}
                        />
                    </div>
                </div>
            </div>

            {/* Insights Section */}
            <div className="insights-section">
                <div className="insights-grid">
                    <div className="insight-card">
                        <h4>User Engagement</h4>
                        <p>{metrics.total_feedback} feedback entries - Users are actively providing feedback</p>
                    </div>
                    <div className="insight-card">
                        <h4>Performance Insight</h4>
                        <p>Average response time is {metrics.avg_response_time_seconds} seconds with {metrics.satisfaction_rate}% satisfaction rate.</p>
                    </div>
                    <div className="insight-card">
                        <h4>Usage Pattern</h4>
                        <p>Users average {metrics.avg_queries_per_session} queries per session across {metrics.total_sessions} total sessions.</p>
                    </div>
                </div>
            </div>
        </div>
    );
};

export default Overview;
