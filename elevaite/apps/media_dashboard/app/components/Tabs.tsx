"use client";

import React, { useState } from 'react';
import './Tabs.scss';
import Overview from './TabComponents/Overview';
import SessionAnalytics from './TabComponents/SessionAnalytics';
import QueryAnalytics from './TabComponents/QueryAnalytics';
import AgentPerformance from './TabComponents/AgentPerformance';
import FeedbackAnalysis from './TabComponents/FeedbackAnalysis';

const tabOptions = [
    'Overview',
    'Session Analytics',
    'Query Analytics',
    'Agent Performance',
    'Feedback Analysis'
];

export interface DateFilters {
    startDate: string;
    endDate: string;
}

const Tabs = () => {
    const [activeTab, setActiveTab] = useState('Overview');
    const [dateFilters, setDateFilters] = useState<DateFilters>({
        startDate: '',
        endDate: ''
    });
    const [quickFilter, setQuickFilter] = useState('All Time');

    const handleQuickFilterChange = (value: string) => {
        setQuickFilter(value);

        const today = new Date();
        let startDate = '';
        let endDate = today.toISOString().split('T')[0];

        switch (value) {
            case 'Last 7 Days':
                const weekAgo = new Date(today);
                weekAgo.setDate(today.getDate() - 7);
                startDate = weekAgo.toISOString().split('T')[0];
                break;
            case 'Last 30 Days':
                const monthAgo = new Date(today);
                monthAgo.setDate(today.getDate() - 30);
                startDate = monthAgo.toISOString().split('T')[0];
                break;
            case 'All Time':
            default:
                startDate = '';
                endDate = '';
                break;
        }

        setDateFilters({ startDate, endDate });
    };

    const handleStartDateChange = (date: string) => {
        setDateFilters({ ...dateFilters, startDate: date });
        setQuickFilter('Custom');
    };

    const handleEndDateChange = (date: string) => {
        setDateFilters({ ...dateFilters, endDate: date });
        setQuickFilter('Custom');
    };

    const clearFilters = () => {
        setDateFilters({ startDate: '', endDate: '' });
        setQuickFilter('All Time');
    };

    const renderTabContent = () => {
        const props = { dateFilters };

        switch (activeTab) {
            case 'Overview': return <Overview {...props} />;
            case 'Session Analytics': return <SessionAnalytics {...props} />;
            case 'Query Analytics': return <QueryAnalytics {...props} />;
            case 'Agent Performance': return <AgentPerformance {...props} />;
            case 'Feedback Analysis': return <FeedbackAnalysis {...props} />;
            default: return <div>No content available</div>;
        }
    };

    return (
        <div className="tabs-container">
            <div className="tabs-header">
                <div className="tabs-left">
                    {tabOptions.map((tab) => (
                        <button
                            key={tab}
                            className={`tab-button ${activeTab === tab ? 'active' : ''}`}
                            onClick={() => setActiveTab(tab)}
                        >
                            {tab}
                        </button>
                    ))}
                </div>
                <div className="tabs-right">
                    <select
                        className="time-dropdown"
                        value={quickFilter}
                        onChange={(e) => handleQuickFilterChange(e.target.value)}
                    >
                        <option>All Time</option>
                        <option>Last 30 Days</option>
                        <option>Last 7 Days</option>
                        <option>Custom</option>
                    </select>
                    <input
                        type="date"
                        className="date-picker"
                        value={dateFilters.startDate}
                        onChange={(e) => handleStartDateChange(e.target.value)}
                    />
                    <span>to</span>
                    <input
                        type="date"
                        className="date-picker"
                        value={dateFilters.endDate}
                        onChange={(e) => handleEndDateChange(e.target.value)}
                    />
                    <button
                        className="clear-button"
                        onClick={clearFilters}
                    >
                        Clear
                    </button>
                </div>
            </div>
            <div>
                {renderTabContent()}
            </div>
        </div>
    );
};

export default Tabs;