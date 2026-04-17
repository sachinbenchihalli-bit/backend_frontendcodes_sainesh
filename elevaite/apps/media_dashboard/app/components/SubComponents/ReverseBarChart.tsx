import React from 'react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Cell } from 'recharts';

interface ReverseBarChartProps {
    data: {
        category: string;
        value: number;
    }[];
}

type CategoryColors = Record<string, string>;

const ReverseBarChart: React.FC<ReverseBarChartProps> = ({ data }) => {
    // Color mapping to preserve original colors
    const categoryColors: CategoryColors = {
        "Touch Screen Failure": "#FF6B00",
        "Scanner Problems": "#FFB800",
        "Printer Issues": "#F8E897",
        "Power Problems": "#9F4B53",
        "Software Errors": "#D71313",
        "Network Connectivity": "#E16D40",
        "Hardware Damage": "#93000A",
        "RFID Reader Issues": "#8B0000",
        "Other": "#C2C2C2"
    };

    // Default color for any new categories
    const defaultColor = "#8884d8";

    // Get color for a category
    const getCategoryColor = (category: string): string => {
        return categoryColors[category] ?? defaultColor;
    };

    // Sort data by value for better visualization (ascending for vertical layout)
    const sortedData = [...data].sort((a, b) => a.value - b.value);

    return (
        <ResponsiveContainer width="100%" height={300}>
            <BarChart
                layout="vertical"
                data={sortedData}
                margin={{ top: 10, right: 20, left: 130, bottom: 10 }}
            >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} />
                <XAxis type="number" />
                <YAxis
                    type="category"
                    dataKey="category"
                    width={120}
                    tick={{ fontSize: 12 }}
                />
                <Tooltip
                    formatter={(value: number) => [String(value), 'Count']}
                    labelFormatter={(value: string) => `Category: ${value}`}
                />
                <Bar
                    dataKey="value"
                    radius={[0, 4, 4, 0]}
                    barSize={20}
                >
                    {sortedData.map((entry, index) => (
                        <Cell key={`cell-${entry.category}-${String(index)}`} fill={getCategoryColor(entry.category)} />
                    ))}
                </Bar>
            </BarChart>
        </ResponsiveContainer>
    );
};

export default ReverseBarChart;