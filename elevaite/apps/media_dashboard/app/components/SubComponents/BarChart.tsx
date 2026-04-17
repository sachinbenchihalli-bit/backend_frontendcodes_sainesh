import React from 'react';
import { ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, CartesianGrid, Cell, LabelList } from 'recharts';

interface CustomBarChartProps {
    data: {
        label: string;
        count: number;
        color: string;
    }[];
}

interface CustomTickProps {
    x: number;
    y: number;
    payload: {
        value: string;
    };
}

// Custom tick component for wrapping text
const CustomTick = (props: CustomTickProps) => {
    const { x, y, payload } = props;
    const text = payload.value;
    const maxWidth = 80; // Maximum width for each line
    const words = text.split(' ');
    const lines: string[] = [];
    let currentLine = '';

    words.forEach((word: string) => {
        const testLine = currentLine ? `${currentLine} ${word}` : word;
        if (testLine.length * 6 > maxWidth && currentLine) {
            lines.push(currentLine);
            currentLine = word;
        } else {
            currentLine = testLine;
        }
    });
    if (currentLine) lines.push(currentLine);

    return (
        <g transform={`translate(${x},${y})`}>
            {lines.map((line, index) => (
                <text
                    key={index}
                    x={0}
                    y={index * 12 + 3}
                    textAnchor="middle"
                    fill="#64748b"
                    fontSize="10"
                >
                    {line}
                </text>
            ))}
        </g>
    );
};

interface CustomTooltipProps {
    active?: boolean;
    payload?: {
        color: string;
        value: number;
    }[];
    label?: string;
}

// Perfect tooltip for intents
const CustomTooltip = ({ active, payload, label }: CustomTooltipProps) => {
    if (active && payload?.length) {
        return (
            <div style={{
                backgroundColor: 'rgba(255, 255, 255, 0.98)',
                border: '1px solid #e5e7eb',
                borderRadius: '8px',
                padding: '12px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
                fontSize: '13px',
                minWidth: '180px'
            }}>
                <p style={{
                    margin: '0 0 6px 0',
                    fontWeight: '600',
                    color: '#111927',
                    fontSize: '14px'
                }}>
                     {label}
                </p>
                <p style={{
                    margin: 0,
                    color: payload[0]?.color,
                    fontWeight: '500',
                    fontSize: '13px'
                }}>
                    Count: {payload[0]?.value.toLocaleString()}
                </p>
            </div>
        );
    }
    return null;
};

const CustomBarChart: React.FC<CustomBarChartProps> = ({ data }) => {
    return (
        <div style={{ width: '100%', height: '350px', padding: '0', margin: '0' }}>
            <ResponsiveContainer width="100%" height="100%">
                <BarChart
                    data={data}
                    margin={{
                        top: 25,
                        right: 30,
                        left: 20,
                        bottom: 60  // Space for horizontal labels
                    }}
                    barCategoryGap="20%"
                >
                    <CartesianGrid strokeDasharray="0" vertical={false} stroke="#f0f0f0" />
                    <XAxis
                        dataKey="label"
                        tick={<CustomTick />}
                        axisLine={{ stroke: '#e5e7eb' }}
                        tickLine={{ stroke: '#e5e7eb' }}
                        height={50}
                        interval={0}
                    />
                    <YAxis
                        tick={{ fontSize: 11, fill: '#64748b' }}
                        axisLine={{ stroke: '#e5e7eb' }}
                        tickLine={{ stroke: '#e5e7eb' }}
                        width={60}
                    />
                    <Tooltip content={<CustomTooltip />} cursor={{ fill: 'rgba(255, 104, 31, 0.1)' }} />
                    <Bar
                        dataKey="count"
                        radius={[6, 6, 0, 0]}
                        maxBarSize={80}
                        stroke="rgba(255, 255, 255, 0.8)"
                        strokeWidth={1}
                    >
                        {data.map((entry, index) => (
                            <Cell
                                key={`cell-${index}`}
                                fill={entry.color || '#FF681F'}
                            />
                        ))}
                        <LabelList
                            dataKey="count"
                            position="top"
                            style={{
                                fontSize: '11px',
                                fill: '#64748b',
                                fontWeight: '500'
                            }}
                            offset={8}
                        />
                    </Bar>
                </BarChart>
            </ResponsiveContainer>
        </div>
    );
};

export default CustomBarChart;