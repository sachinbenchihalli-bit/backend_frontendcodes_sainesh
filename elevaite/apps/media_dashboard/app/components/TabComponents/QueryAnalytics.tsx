'use client';
import React, { useState, useEffect, useMemo } from 'react';
import { FiUsers, FiMessageSquare, FiClock, FiTrendingUp, FiBarChart2, FiCheckCircle } from 'react-icons/fi';
import './QueryAnalytics.scss';

import CustomLineChart from '../SubComponents/LineChart';
import CustomBarChart from '../SubComponents/BarChart';
import Table from '../SubComponents/Table';

import { DateFilters } from '../Tabs';

interface QueryAnalyticsProps {
    dateFilters: DateFilters;
}

interface QuerySummary {
    total_queries: number;
    avg_response_time_ms: number;
    success_rate: number;
    successful_queries: number;
    failed_queries: number;
    unique_intents: number;
    unique_users: number;
    response_time_distribution: Array<{
        range: string;
        count: number;
    }>;
}

interface IntentData {
    intent: string;
    count: number;
    avg_response_time: number;
    success_rate: number;
    successful_queries: number;
    failed_queries: number;
}

interface QueryDetail {
    query_id: string;
    session_id: string;
    original_query: string;
    final_response: string;
    intent_detected: string;
    user_id: string;
    total_duration_ms: number;
    total_tokens: number;
    success: boolean;
    start_time: string;
}

const QueryAnalyticsDashboard: React.FC<QueryAnalyticsProps> = ({ dateFilters }) => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [summary, setSummary] = useState<QuerySummary | null>(null);
    const [intentsData, setIntentsData] = useState<IntentData[]>([]);
    const [performanceData, setPerformanceData] = useState<any[]>([]);
    const [queriesData, setQueriesData] = useState<any[]>([]);
    const [queryFilter, setQueryFilter] = useState('all');
    const [searchTerm, setSearchTerm] = useState('');

    const fetchQueryData = async () => {
        try {
            setLoading(true);
            setError(null);

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/dashboardhttp://localhost:8000';
            const params = new URLSearchParams();

            if (dateFilters.startDate) params.append('start_date', dateFilters.startDate);
            if (dateFilters.endDate) params.append('end_date', dateFilters.endDate);

            // Fetch query summary
            const summaryResponse = await fetch(`${baseUrl}/api/media/queries/summary?${params}`);
            if (!summaryResponse.ok) throw new Error('Failed to fetch query summary');
            const summaryData = await summaryResponse.json();
            setSummary(summaryData);

            // Fetch intent distribution
            const intentsResponse = await fetch(`${baseUrl}/api/media/queries/intents?${params}&limit=15`);
            if (!intentsResponse.ok) throw new Error('Failed to fetch intents data');
            const intentsData = await intentsResponse.json();
            setIntentsData(intentsData);

            // Fetch performance data
            const performanceResponse = await fetch(`${baseUrl}/api/media/queries/performance?${params}`);
            if (!performanceResponse.ok) throw new Error('Failed to fetch performance data');
            const performanceData = await performanceResponse.json();
            setPerformanceData(performanceData);

            // Fetch recent queries data
            const queriesResponse = await fetch(`${baseUrl}/api/media/queries/recent?${params}&limit=50`);
            if (!queriesResponse.ok) throw new Error('Failed to fetch queries data');
            const queriesData = await queriesResponse.json();
            console.log("Query Data: ", queriesData);
            setQueriesData(queriesData);

        } catch (err) {
            console.error('Error fetching query data:', err);
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchQueryData();
    }, [dateFilters]);

    // Filter queries based on selected filter and search term
    const filteredQueries = useMemo(() => {
        return queriesData.filter(query => {
            // Apply query status filter
            let passesFilter = true;
            if (queryFilter === 'successful') passesFilter = query.success === true;
            else if (queryFilter === 'failed') passesFilter = query.success === false;

            // Apply search filter
            let passesSearch = true;
            if (searchTerm.trim()) {
                const searchLower = searchTerm.toLowerCase();
                passesSearch =
                    query.query_id.toLowerCase().includes(searchLower) ||
                    query.session_id.toLowerCase().includes(searchLower);
            }

            return passesFilter && passesSearch;
        });
    }, [queriesData, queryFilter, searchTerm]);



    if (loading) {
        return <div className="loading">Loading query analytics...</div>;
    }

    if (error) {
        return <div className="error">Error: {error}</div>;
    }

    if (!summary) {
        return <div className="no-data">No query data available</div>;
    }

    // Define table columns for recent queries
    const queryColumns = [
        {
            label: 'Query ID',
            key: 'query_id' as keyof QueryDetail,
            width: '120px',
            minWidth: '80px'
        },
        {
            label: 'Session ID',
            key: 'session_id' as keyof QueryDetail,
            width: '120px',
            minWidth: '80px'
        },
        {
            label: 'Query',
            key: 'original_query' as keyof QueryDetail,
            render: (value: string) => value || 'N/A',
            width: '200px',
            minWidth: '150px'
        },
        {
            label: 'Response',
            key: 'final_response' as keyof QueryDetail,
            render: (value: string) => (
                <div style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {value ? `${value.substring(0, 50)}${value.length > 50 ? '...' : ''}` : 'N/A'}
                </div>
            ),
            width: '200px',
            minWidth: '150px'
        },
        {
            label: 'Intent',
            key: 'intent_detected' as keyof QueryDetail,
            render: (value: string) => (
                <span className="intent-badge">
                    {value || 'Unknown'}
                </span>
            ),
            width: '120px',
            minWidth: '100px'
        },
        {
            label: 'User',
            key: 'user_id' as keyof QueryDetail,
            render: (value: string) => value || 'N/A',
            width: '120px',
            minWidth: '100px'
        },
        {
            label: 'Response Time',
            key: 'total_duration_ms' as keyof QueryDetail,
            render: (value: number) => value ? `${(value / 1000).toFixed(1)}s` : 'N/A',
            width: '120px',
            minWidth: '100px'
        },
        {
            label: 'Tokens',
            key: 'total_tokens' as keyof QueryDetail,
            render: (value: number) => value || 0,
            width: '80px',
            minWidth: '70px'
        },
        {
            label: 'Status',
            key: 'success' as keyof QueryDetail,
            render: (value: boolean) => (
                <span className={`status-badge ${value ? 'success' : 'failed'}`}>
                    {value ? 'Success' : 'Failed'}
                </span>
            ),
            width: '100px',
            minWidth: '80px'
        },
        {
            label: 'Timestamp',
            key: 'start_time' as keyof QueryDetail,
            render: (value: string) => value ? new Date(value).toLocaleString() : 'N/A',
            width: '160px',
            minWidth: '140px'
        }
    ];

    // Define expandable row content for recent queries
    const queryExpandableRow = {
        render: (row: QueryDetail) => (
            <div className="expanded-details">
                <div className="detail-section">
                    <div className="detail-label">Original Query:</div>
                    <div className="detail-content">
                        {row.original_query || 'No query available'}
                    </div>
                </div>
                <div className="detail-section">
                    <div className="detail-label">Complete Response:</div>
                    <div className="detail-content">
                        {row.final_response || 'No response available'}
                    </div>
                </div>
            </div>
        )
    };

    return (
        <div className="query-analytics-container">
            {/* Query Metrics */}
            <div className="summary-section">
                <div className="cards-grid-six">
                    <div className="summary-card">
                        <div className="card-icon">
                            <FiMessageSquare />
                        </div>
                        <h3 className="card-title">Total Queries</h3>
                        <div className="card-value">{(summary.total_queries || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            User interactions tracked
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiCheckCircle />
                        </div>
                        <h3 className="card-title">Success Rate</h3>
                        <div className="card-value">{summary.success_rate || 0}%</div>
                        <div className="card-change up">
                            Query completion rate
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiClock />
                        </div>
                        <h3 className="card-title">Avg Response Time</h3>
                        <div className="card-value">{((summary.avg_response_time_ms || 0) / 1000).toFixed(1)}s</div>
                        <div className="card-change down">
                            Processing speed
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiBarChart2 />
                        </div>
                        <h3 className="card-title">Unique Intents</h3>
                        <div className="card-value">{summary.unique_intents || 0}</div>
                        <div className="card-change up">
                            Intent variety detected
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiUsers />
                        </div>
                        <h3 className="card-title">Unique Users</h3>
                        <div className="card-value">{summary.unique_users || 0}</div>
                        <div className="card-change up">
                            Active user count
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiTrendingUp />
                        </div>
                        <h3 className="card-title">Queries per User</h3>
                        <div className="card-value">{summary.unique_users > 0 ? ((summary.total_queries || 0) / summary.unique_users).toFixed(1) : 0}</div>
                        <div className="card-change up">
                            User engagement level
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div className="charts-section">
                <div className="chart-row">
                    <div className="chart-container large">
                        <h3>Response Time Distribution</h3>
                        <CustomBarChart
                            data={summary.response_time_distribution.map(item => ({
                                label: item.range,
                                count: item.count,
                                color: "#8884d8"
                            }))}
                        />
                    </div>
                </div>

                <div className="chart-row">
                    <div className="chart-container large">
                        <h3>Top Intents by Count</h3>
                        <CustomBarChart
                            data={intentsData.slice(0, 10).map(item => ({
                                label: item.intent,
                                count: item.count,
                                color: "#82ca9d"
                            }))}
                        />
                    </div>
                </div>

                {performanceData.length > 0 && (
                    <div className="chart-row">
                        <div className="chart-container large">
                            <h3>Total Queries Over Time</h3>
                            <CustomLineChart
                                data={performanceData.map(item => ({
                                    date: item.date,
                                    value: item.total_queries
                                }))}
                                YAxislabel="Total Queries"
                            />
                        </div>
                    </div>
                )}
            </div>

            {/* Recent Queries Table */}
            <div className="queries-table-section">
                <div className="section-header">
                    <h3>Recent Queries</h3>
                    <div className="table-controls">
                        <input
                            type="text"
                            placeholder="Search by Query ID or Session ID..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="search-input"
                        />
                        <select
                            value={queryFilter}
                            onChange={(e) => setQueryFilter(e.target.value)}
                            className="filter-select"
                        >
                            <option value="all">All Queries</option>
                            <option value="successful">Successful Only</option>
                            <option value="failed">Failed Only</option>
                        </select>
                    </div>
                </div>

                <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.9em', paddingLeft: '20px' }}>
                    Click on any row to view the complete query text and full response content.
                </p>

                <Table
                    data={filteredQueries}
                    columns={queryColumns}
                    title="Recent Queries"
                    showPagination={true}
                    expandableRow={queryExpandableRow}
                />

                {filteredQueries.length === 0 && (
                    <div className="no-data-message">
                        <p>No queries found for the selected {searchTerm.trim() ? 'search and filter' : 'filter'} criteria</p>
                    </div>
                )}
            </div>
        </div>
    );
};

export default QueryAnalyticsDashboard;