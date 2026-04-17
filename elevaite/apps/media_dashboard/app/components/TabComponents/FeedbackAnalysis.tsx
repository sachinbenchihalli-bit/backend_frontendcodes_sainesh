"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { FiThumbsUp, FiThumbsDown, FiMessageCircle, FiTrendingUp, FiUsers, FiBarChart2 } from "react-icons/fi";

import './FeedbackAnalysis.scss';

import CustomBarChart from '../SubComponents/BarChart';
import CustomLineChart from '../SubComponents/LineChart';
import Table from '../SubComponents/Table';
import { DateFilters } from '../Tabs';

interface FeedbackAnalysisProps {
    dateFilters: DateFilters;
}

interface FeedbackSummary {
    total_feedback: number;
    positive_feedback: number;
    negative_feedback: number;
    neutral_feedback: number;
    satisfaction_rate: number;
    unique_users: number;
    unique_queries: number;
    unique_sessions: number;
    feedback_by_type: Array<{
        type: string;
        count: number;
        avg_sentiment: number;
    }>;
}

interface FeedbackDetail {
    id: string;
    query_id: string;
    session_id: string;
    user_id: string;
    feedback_type: string;
    feedback_text: string;
    vote: number;
    timestamp: string;
    intent_detected: string;
    query_duration_ms: number;
    original_query: string;
}

interface SentimentData {
    sentiment_by_intent: Array<{
        intent: string;
        total_feedback: number;
        positive_feedback: number;
        negative_feedback: number;
        satisfaction_rate: number;
        avg_sentiment: number;
    }>;
    sentiment_by_response_time: Array<{
        response_time_category: string;
        total_feedback: number;
        positive_feedback: number;
        satisfaction_rate: number;
        avg_sentiment: number;
    }>;
}

interface TrendData {
    date: string;
    total_feedback: number;
    positive_feedback: number;
    negative_feedback: number;
    neutral_feedback: number;
    satisfaction_rate: number;
}

const FeedbackAnalysis: React.FC<FeedbackAnalysisProps> = ({ dateFilters }) => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [summary, setSummary] = useState<FeedbackSummary | null>(null);
    const [sentimentData, setSentimentData] = useState<SentimentData | null>(null);
    const [trendsData, setTrendsData] = useState<TrendData[]>([]);
    const [feedbackDetails, setFeedbackDetails] = useState<FeedbackDetail[]>([]);
    const [feedbackFilter, setFeedbackFilter] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');

    const fetchFeedbackData = async () => {
        try {
            setLoading(true);
            setError(null);

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/dashboardhttp://localhost:8000';
            const params = new URLSearchParams();

            if (dateFilters.startDate) params.append('start_date', dateFilters.startDate);
            if (dateFilters.endDate) params.append('end_date', dateFilters.endDate);

            // Fetch feedback summary
            const summaryResponse = await fetch(`${baseUrl}/api/media/feedback/summary?${params}`);
            if (!summaryResponse.ok) throw new Error('Failed to fetch feedback summary');
            const summaryData = await summaryResponse.json();
            setSummary(summaryData);

            // Fetch sentiment analysis
            const sentimentResponse = await fetch(`${baseUrl}/api/media/feedback/sentiment?${params}`);
            if (!sentimentResponse.ok) throw new Error('Failed to fetch sentiment data');
            const sentimentData = await sentimentResponse.json();
            setSentimentData(sentimentData);

            // Fetch trends data
            const trendsResponse = await fetch(`${baseUrl}/api/media/feedback/trends?${params}`);
            if (!trendsResponse.ok) throw new Error('Failed to fetch trends data');
            const trendsData = await trendsResponse.json();
            setTrendsData(trendsData);

            // Fetch feedback details
            const detailsResponse = await fetch(`${baseUrl}/api/media/feedback/details?${params}&limit=50`);
            if (!detailsResponse.ok) throw new Error('Failed to fetch feedback details');
            const detailsData = await detailsResponse.json();
            setFeedbackDetails(detailsData);

        } catch (err) {
            console.error('Error fetching feedback data:', err);
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchFeedbackData();
    }, [dateFilters]);

    // Filter feedback details based on selected filter and search term
    const filteredFeedback = useMemo(() => {
        return feedbackDetails.filter(feedback => {
            // Apply feedback type filter
            let passesFilter = true;
            if (feedbackFilter === 'positive') passesFilter = feedback.vote > 0;
            else if (feedbackFilter === 'negative') passesFilter = feedback.vote < 0;
            else if (feedbackFilter === 'neutral') passesFilter = feedback.vote === 0;

            // Apply search filter
            let passesSearch = true;
            if (searchTerm.trim()) {
                const searchLower = searchTerm.toLowerCase();
                passesSearch =
                    feedback.query_id.toLowerCase().includes(searchLower) ||
                    feedback.session_id.toLowerCase().includes(searchLower);
            }

            return passesFilter && passesSearch;
        });
    }, [feedbackDetails, feedbackFilter, searchTerm]);

    if (loading) {
        return <div className="loading">Loading feedback analysis...</div>;
    }

    if (error) {
        return <div className="error">Error: {error}</div>;
    }

    if (!summary) {
        return <div className="no-data">No feedback data available</div>;
    }

    // Define table columns for feedback details
    const feedbackColumns = [
        {
            label: 'Query ID',
            key: 'query_id' as keyof FeedbackDetail,
            width: '120px',
            minWidth: '80px'
        },
        {
            label: 'Session ID',
            key: 'session_id' as keyof FeedbackDetail,
            width: '120px',
            minWidth: '80px'
        },
        {
            label: 'Query',
            key: 'original_query' as keyof FeedbackDetail,
            render: (value: string) => value ? value.substring(0, 50) + (value.length > 50 ? '...' : '') : 'N/A'
        },
        { label: 'Intent', key: 'intent_detected' as keyof FeedbackDetail },
        { label: 'User', key: 'user_id' as keyof FeedbackDetail },
        {
            label: 'Feedback',
            key: 'feedback_text' as keyof FeedbackDetail,
            render: (value: string) => value ? value.substring(0, 30) + (value.length > 30 ? '...' : '') : 'N/A'
        },
        {
            label: 'Vote',
            key: 'vote' as keyof FeedbackDetail,
            render: (value: number) => {
                if (value > 0) return <span className="vote-positive">👍 Positive</span>;
                if (value < 0) return <span className="vote-negative">👎 Negative</span>;
                return <span className="vote-neutral">➖ Neutral</span>;
            }
        },
        {
            label: 'Timestamp',
            key: 'timestamp' as keyof FeedbackDetail,
            render: (value: string) => value ? new Date(value).toLocaleString() : 'N/A'
        }
    ];

    return (
        <div className="feedback-analysis-container">
            {/* Feedback Metrics */}
            <div className="summary-section">
                <div className="cards-grid-six">
                    <div className="summary-card">
                        <div className="card-icon">
                            <FiMessageCircle />
                        </div>
                        <h3 className="card-title">Total Feedback</h3>
                        <div className="card-value">{(summary.total_feedback || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            User feedback entries
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiThumbsUp />
                        </div>
                        <h3 className="card-title">Positive Feedback</h3>
                        <div className="card-value">{(summary.positive_feedback || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            Satisfied users
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiThumbsDown />
                        </div>
                        <h3 className="card-title">Negative Feedback</h3>
                        <div className="card-value">{(summary.negative_feedback || 0).toLocaleString()}</div>
                        <div className="card-change down">
                            Dissatisfied users
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiTrendingUp />
                        </div>
                        <h3 className="card-title">Satisfaction Rate</h3>
                        <div className="card-value">{summary.satisfaction_rate.toFixed(1)}%</div>
                        <div className="card-change up">
                            Overall satisfaction
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiUsers />
                        </div>
                        <h3 className="card-title">Unique Users</h3>
                        <div className="card-value">{summary.unique_users || 0}</div>
                        <div className="card-change up">
                            Users providing feedback
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiBarChart2 />
                        </div>
                        <h3 className="card-title">Feedback per User</h3>
                        <div className="card-value">{summary.unique_users > 0 ? ((summary.total_feedback || 0) / summary.unique_users).toFixed(1) : 0}</div>
                        <div className="card-change up">
                            Engagement level
                        </div>
                    </div>
                </div>
            </div>
            {/* Feedback Details Table */}
            <div className="feedback-table-section">
                <div className="section-header">
                    <h3>Feedback Details</h3>
                    <div className="table-controls">
                        <input
                            type="text"
                            placeholder="Search by Query ID or Session ID..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="search-input"
                        />
                        <select
                            value={feedbackFilter}
                            onChange={(e) => setFeedbackFilter(e.target.value)}
                            className="filter-select"
                        >
                            <option value="all">All Feedback</option>
                            <option value="positive">Positive Only</option>
                            <option value="negative">Negative Only</option>
                            <option value="neutral">Neutral Only</option>
                        </select>
                    </div>
                </div>

                <Table
                    data={filteredFeedback}
                    columns={feedbackColumns}
                    title="Feedback Details"
                    showPagination={true}
                />

                {filteredFeedback.length === 0 && (
                    <div className="no-data-message">
                        <p>No feedback found for the selected {searchTerm.trim() ? 'search and filter' : 'filter'} criteria</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default FeedbackAnalysis;
