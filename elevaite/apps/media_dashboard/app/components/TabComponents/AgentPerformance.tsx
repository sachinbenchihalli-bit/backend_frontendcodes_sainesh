"use client";

import React, { useEffect, useState, useMemo } from 'react';
import { FiCpu, FiZap, FiCheckCircle, FiAlertTriangle, FiUsers, FiBarChart2 } from "react-icons/fi";

import './AgentPerformance.scss';

import CustomBarChart from '../SubComponents/BarChart';
import Table from '../SubComponents/Table';
import { DateFilters } from '../Tabs';

interface AgentPerformanceProps {
    dateFilters: DateFilters;
}

interface AgentPerformanceSummary {
    total_executions: number;
    avg_execution_time: number;
    overall_success_rate: number;
    total_errors: number;
    unique_agents: number;
    total_tokens: number;
}

interface AgentPerformanceData {
    agent_name: string;
    total_executions: number;
    avg_execution_time: number;
    success_rate: number;
    successful_executions: number;
    failed_executions: number;
    unique_queries: number;
}

interface AgentError {
    agent_name: string;
    step_type: string;
    start_time: string;
    duration_ms: number;
    error_details: string;
    query_id: string;
}

interface ExecutionStep {
    id: string;
    query_id: string;
    agent_name: string;
    step_type: string;
    start_time: string;
    end_time: string | null;
    duration_ms: number;
    model_used: string;
    total_tokens: number;
    success: boolean;
    error_details: string | null;
    input_prompt: string;
    output_response: string;
}

interface ExecutionStepsResponse {
    execution_steps: ExecutionStep[];
    total_count: number;
    limit: number;
    offset: number;
}

const AgentPerformance: React.FC<AgentPerformanceProps> = ({ dateFilters }) => {
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [summary, setSummary] = useState<AgentPerformanceSummary | null>(null);
    const [performanceData, setPerformanceData] = useState<AgentPerformanceData[]>([]);
    const [errorData, setErrorData] = useState<AgentError[]>([]);
    const [executionStepsData, setExecutionStepsData] = useState<ExecutionStep[]>([]);
    const [executionStepsTotal, setExecutionStepsTotal] = useState(0);
    const [searchTerm, setSearchTerm] = useState('');

    const fetchAgentData = async () => {
        try {
            setLoading(true);
            setError(null);

            const baseUrl = process.env.NEXT_PUBLIC_API_URL || '/dashboardhttp://localhost:8000';
            const params = new URLSearchParams();

            if (dateFilters.startDate) params.append('start_date', dateFilters.startDate);
            if (dateFilters.endDate) params.append('end_date', dateFilters.endDate);

            // Fetch agent performance data
            const performanceResponse = await fetch(`${baseUrl}/api/media/agents/performance?${params}`);
            if (!performanceResponse.ok) throw new Error('Failed to fetch agent performance');
            const performanceData = await performanceResponse.json();
            setPerformanceData(performanceData);

            // Calculate summary metrics
            const totalExecutions = performanceData.reduce((sum: number, agent: AgentPerformanceData) => sum + agent.total_executions, 0);
            const avgExecutionTime = performanceData.length > 0
                ? performanceData.reduce((sum: number, agent: AgentPerformanceData) => sum + agent.avg_execution_time, 0) / performanceData.length
                : 0;
            const totalSuccessful = performanceData.reduce((sum: number, agent: AgentPerformanceData) => sum + agent.successful_executions, 0);
            const totalErrors = performanceData.reduce((sum: number, agent: AgentPerformanceData) => sum + agent.failed_executions, 0);
            const overallSuccessRate = totalExecutions > 0 ? (totalSuccessful / totalExecutions) * 100 : 0;

            setSummary({
                total_executions: totalExecutions,
                avg_execution_time: avgExecutionTime,
                overall_success_rate: overallSuccessRate,
                total_errors: totalErrors,
                unique_agents: performanceData.length,
                total_tokens: 0 // Will be updated when we fetch token data
            });

            // Fetch error data
            const errorResponse = await fetch(`${baseUrl}/api/media/agents/errors?${params}&limit=20`);
            if (!errorResponse.ok) throw new Error('Failed to fetch agent errors');
            const errorData = await errorResponse.json();
            setErrorData(errorData.recent_errors || []);

            // Fetch execution steps data
            const executionStepsResponse = await fetch(`${baseUrl}/api/media/agents/execution-steps?${params}&limit=50`);
            if (!executionStepsResponse.ok) throw new Error('Failed to fetch execution steps');
            const executionStepsData = await executionStepsResponse.json();
            setExecutionStepsData(executionStepsData.execution_steps || []);
            setExecutionStepsTotal(executionStepsData.total_count || 0);

        } catch (err) {
            console.error('Error fetching agent data:', err);
            setError(err instanceof Error ? err.message : 'An error occurred');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchAgentData();
    }, [dateFilters]);

    // Filter execution steps based on search term
    const filteredExecutionSteps = useMemo(() => {
        if (!searchTerm.trim()) {
            return executionStepsData;
        }

        const searchLower = searchTerm.toLowerCase();
        return executionStepsData.filter(step =>
            step.query_id.toLowerCase().includes(searchLower)
        );
    }, [executionStepsData, searchTerm]);

    if (loading) {
        return <div className="loading">Loading agent performance...</div>;
    }

    if (error) {
        return <div className="error">Error: {error}</div>;
    }

    if (!summary) {
        return <div className="no-data">No agent performance data available</div>;
    }

    // Define table columns for agent performance
    const performanceColumns = [
        {
            label: 'Agent Name',
            key: 'agent_name' as keyof AgentPerformanceData,
            width: '200px',
            minWidth: '150px'
        },
        {
            label: 'Total Executions',
            key: 'total_executions' as keyof AgentPerformanceData,
            width: '120px',
            minWidth: '100px'
        },
        {
            label: 'Avg Execution Time',
            key: 'avg_execution_time' as keyof AgentPerformanceData,
            render: (value: number) => `${value.toFixed(1)}ms`,
            width: '140px',
            minWidth: '120px'
        },
        {
            label: 'Success Rate',
            key: 'success_rate' as keyof AgentPerformanceData,
            render: (value: number) => `${value.toFixed(1)}%`,
            width: '100px',
            minWidth: '90px'
        },
        {
            label: 'Successful',
            key: 'successful_executions' as keyof AgentPerformanceData,
            width: '100px',
            minWidth: '80px'
        },
        {
            label: 'Failed',
            key: 'failed_executions' as keyof AgentPerformanceData,
            width: '80px',
            minWidth: '60px'
        },
        {
            label: 'Unique Queries',
            key: 'unique_queries' as keyof AgentPerformanceData,
            width: '120px',
            minWidth: '100px'
        }
    ];

    // Define table columns for errors
    const errorColumns = [
        {
            label: 'Agent',
            key: 'agent_name' as keyof AgentError,
            width: '150px',
            minWidth: '120px'
        },
        {
            label: 'Step Type',
            key: 'step_type' as keyof AgentError,
            width: '120px',
            minWidth: '100px'
        },
        {
            label: 'Duration',
            key: 'duration_ms' as keyof AgentError,
            render: (value: number) => `${value}ms`,
            width: '90px',
            minWidth: '80px'
        },
        {
            label: 'Error Details',
            key: 'error_details' as keyof AgentError,
            render: (value: string) => value ? value.substring(0, 80) + (value.length > 80 ? '...' : '') : 'N/A',
            width: '300px',
            minWidth: '200px'
        },
        {
            label: 'Timestamp',
            key: 'start_time' as keyof AgentError,
            render: (value: string) => value ? new Date(value).toLocaleString() : 'N/A',
            width: '160px',
            minWidth: '140px'
        }
    ];

    // Define table columns for execution steps
    const executionStepsColumns = [
        {
            label: 'Query ID',
            key: 'query_id' as keyof ExecutionStep,
            width: '120px',
            minWidth: '80px'
        },
        {
            label: 'Agent',
            key: 'agent_name' as keyof ExecutionStep,
            width: '150px',
            minWidth: '120px'
        },
        {
            label: 'Step Type',
            key: 'step_type' as keyof ExecutionStep,
            width: '120px',
            minWidth: '100px'
        },
        {
            label: 'Duration',
            key: 'duration_ms' as keyof ExecutionStep,
            render: (value: number) => value ? `${(value / 1000).toFixed(2)}s` : 'N/A',
            width: '90px',
            minWidth: '80px'
        },
        {
            label: 'Model',
            key: 'model_used' as keyof ExecutionStep,
            width: '120px',
            minWidth: '100px'
        },
        {
            label: 'Status',
            key: 'success' as keyof ExecutionStep,
            render: (value: boolean) => (
                <span style={{
                    color: value ? '#22c55e' : '#ef4444',
                    fontWeight: 'bold'
                }}>
                    {value ? '✓ Success' : '✗ Failed'}
                </span>
            ),
            width: '90px',
            minWidth: '80px'
        },
        {
            label: 'Tokens',
            key: 'total_tokens' as keyof ExecutionStep,
            render: (value: number) => value ? value.toLocaleString() : '0',
            width: '80px',
            minWidth: '70px'
        },
        {
            label: 'Input Preview',
            key: 'input_prompt' as keyof ExecutionStep,
            render: (value: string) => (
                <span title={value} style={{ fontSize: '0.85em', color: '#666' }}>
                    {value ? (value.length > 30 ? value.substring(0, 30) + '...' : value) : 'N/A'}
                </span>
            ),
            width: '200px',
            minWidth: '150px'
        },
        {
            label: 'Output Preview',
            key: 'output_response' as keyof ExecutionStep,
            render: (value: string) => (
                <span title={value} style={{ fontSize: '0.85em', color: '#666' }}>
                    {value ? (value.length > 30 ? value.substring(0, 30) + '...' : value) : 'N/A'}
                </span>
            ),
            width: '200px',
            minWidth: '150px'
        },
        {
            label: 'Timestamp',
            key: 'start_time' as keyof ExecutionStep,
            render: (value: string) => value ? new Date(value).toLocaleString() : 'N/A',
            width: '160px',
            minWidth: '140px'
        }
    ];

    // Define expandable row content for execution steps
    const executionStepsExpandableRow = {
        render: (row: ExecutionStep) => (
            <div className="expanded-details">
                <div className="detail-section">
                    <div className="detail-label">Input Prompt:</div>
                    <div className="detail-content">
                        {row.input_prompt || 'No input prompt available'}
                    </div>
                </div>
                <div className="detail-section">
                    <div className="detail-label">Output Response:</div>
                    <div className="detail-content">
                        {row.output_response || 'No output response available'}
                    </div>
                </div>
                {row.error_details && (
                    <div className="detail-section">
                        <div className="detail-label">Error Details:</div>
                        <div className="detail-content" style={{ color: '#dc3545' }}>
                            {row.error_details}
                        </div>
                    </div>
                )}
            </div>
        )
    };

    return (
        <div className="agent-performance-container">
            {/* Agent Performance Metrics */}
            <div className="summary-section">
                <div className="cards-grid-six">
                    <div className="summary-card">
                        <div className="card-icon">
                            <FiCpu />
                        </div>
                        <h3 className="card-title">Total Executions</h3>
                        <div className="card-value">{(summary.total_executions || 0).toLocaleString()}</div>
                        <div className="card-change up">
                            Agent execution count
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiZap />
                        </div>
                        <h3 className="card-title">Avg Execution Time</h3>
                        <div className="card-value">{summary.avg_execution_time.toFixed(1)}ms</div>
                        <div className="card-change down">
                            Processing speed
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiCheckCircle />
                        </div>
                        <h3 className="card-title">Success Rate</h3>
                        <div className="card-value">{summary.overall_success_rate.toFixed(1)}%</div>
                        <div className="card-change up">
                            Overall success rate
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiAlertTriangle />
                        </div>
                        <h3 className="card-title">Total Errors</h3>
                        <div className="card-value">{(summary.total_errors || 0).toLocaleString()}</div>
                        <div className="card-change down">
                            Failed executions
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiUsers />
                        </div>
                        <h3 className="card-title">Active Agents</h3>
                        <div className="card-value">{summary.unique_agents || 0}</div>
                        <div className="card-change up">
                            Unique agent count
                        </div>
                    </div>

                    <div className="summary-card">
                        <div className="card-icon">
                            <FiBarChart2 />
                        </div>
                        <h3 className="card-title">Avg Queries/Agent</h3>
                        <div className="card-value">{summary.unique_agents > 0 ? ((summary.total_executions || 0) / summary.unique_agents).toFixed(1) : 0}</div>
                        <div className="card-change up">
                            Execution distribution
                        </div>
                    </div>
                </div>
            </div>

            {/* Charts Section */}
            <div className="charts-section">
                {/* <div className="chart-row">
                    <div className="chart-container large">
                        <h3>Success Rate by Agent</h3>
                        <CustomBarChart
                            data={performanceData.slice(0, 10).map(agent => ({
                                label: agent.agent_name,
                                count: agent.success_rate,
                                color: "#82ca9d"
                            }))}
                        />
                    </div>
                </div> */}

                <div className="chart-row">
                    <div className="chart-container large">
                        <h3>Execution Count by Agent</h3>
                        <CustomBarChart
                            data={performanceData.slice(0, 10).map(agent => ({
                                label: agent.agent_name,
                                count: agent.total_executions,
                                color: "#8884d8"
                            }))}
                        />
                    </div>
                </div>
            </div>
            {/* Agent Execution Steps Table */}
            <div className="table-section">
                <div className="section-header">
                    <h3>Agent Execution Steps</h3>
                    <div className="table-controls">
                        <input
                            type="text"
                            placeholder="Search by Query ID..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="search-input"
                        />
                    </div>
                </div>
                <p style={{ color: '#666', marginBottom: '1rem', fontSize: '0.9em' }}>
                    Detailed execution steps for all agents ({executionStepsTotal.toLocaleString()} total records). Click on any row to view full input prompt and output response.
                </p>
                <Table
                    data={filteredExecutionSteps}
                    columns={executionStepsColumns}
                    title="Agent Execution Steps"
                    showPagination={true}
                    expandableRow={executionStepsExpandableRow}
                />

                {filteredExecutionSteps.length === 0 && searchTerm.trim() && (
                    <div className="no-data-message">
                        <p>No execution steps found for the search criteria</p>
                    </div>
                )}
            </div>
            
            {/* Agent Performance Table */}
            <div className="table-section">
                <h3>Agent Performance Details</h3>
                <Table
                    data={performanceData}
                    columns={performanceColumns}
                    title="Agent Performance"
                    showPagination={true}
                />
            </div>



            {/* Recent Errors Table */}
            {errorData.length > 0 && (
                <div className="table-section">
                    <h3>Recent Agent Errors</h3>
                    <Table
                        data={errorData}
                        columns={errorColumns}
                        title="Recent Errors"
                        showPagination={true}
                    />
                </div>
            )}
        </div>
    );
};

export default AgentPerformance;
