import React from 'react';
import { PieChart, Pie, Cell, Tooltip } from 'recharts';

interface PieChartData {
    name: string;
    value: number;
    color?: string;
    count?: number;
}

interface CustomPieChartProps {
    data: PieChartData[];
    dollorValue?: boolean;
}

interface TooltipProps {
    active?: boolean;
    payload?: {
        payload: PieChartData;
    }[];
}

interface LegendProps {
    payload?: {
        value: string;
        color: string;
    }[];
}

// Custom tooltip formatter - moved outside component
const CustomTooltip: React.FC<TooltipProps & { dollorValue: boolean }> = ({ active, payload, dollorValue }) => {
    if (active && payload?.length) {
        const chartData = payload[0].payload;
        return (
            <div style={{
                backgroundColor: 'white',
                padding: '8px 12px',
                border: '1px solid #e0e0e0',
                borderRadius: '4px',
                boxShadow: '0 2px 8px rgba(0,0,0,0.1)',
                fontSize: '13px'
            }}>
                <p style={{ margin: 0, fontWeight: 'bold' }}>{chartData.name}</p>
                <p style={{ margin: '4px 0 0 0', color: '#666' }}>
                    {dollorValue ? `$${String(chartData.value.toLocaleString())}` : `${String(chartData.value)}%`}
                    {chartData.count && ` (${String(chartData.count.toLocaleString())})`}
                </p>
            </div>
        );
    }
    return null;
};

const CustomPieChart: React.FC<CustomPieChartProps> = ({
    data,
    dollorValue = false
}) => {
    // Ensure we have valid data
    if (data.length === 0) {
        return (
            <div style={{
                width: '100%',
                height: '280px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: '#666',
                fontSize: '14px'
            }}>
                No data available
            </div>
        );
    }

    // Custom legend formatter
    const renderCustomLegend = (props: LegendProps): React.ReactElement | null => {
        const { payload } = props;
        if (!payload) return null;

        return (
            <div style={{
                display: 'flex',
                flexWrap: 'wrap',
                justifyContent: 'center',
                gap: '12px',
                marginTop: '16px',
                fontSize: '12px'
            }}>
                {payload.map((entry, index) => (
                    <div
                        key={`legend-${entry.value}-${String(index)}`}
                        style={{
                            display: 'flex',
                            alignItems: 'center',
                            gap: '6px'
                        }}
                    >
                        <div
                            style={{
                                width: '12px',
                                height: '12px',
                                backgroundColor: entry.color,
                                borderRadius: '2px',
                                flexShrink: 0
                            }}
                        />
                        <span style={{
                            color: '#333',
                            whiteSpace: 'nowrap',
                            maxWidth: '120px',
                            overflow: 'hidden',
                            textOverflow: 'ellipsis'
                        }}>
                            {entry.value}
                        </span>
                    </div>
                ))}
            </div>
        );
    };

    return (
        <div style={{
            width: '100%',
            height: '100%',
            minHeight: '280px',
            display: 'flex',
            flexDirection: 'column'
        }}>
            {/* Fixed size container instead of ResponsiveContainer to prevent shaking */}
            <div style={{
                width: '100%',
                height: '220px',
                display: 'flex',
                justifyContent: 'center',
                alignItems: 'center'
            }}>
                <PieChart width={280} height={200}>
                    <Pie
                        data={data}
                        cx={140}
                        cy={100}
                        innerRadius={45}
                        outerRadius={85}
                        paddingAngle={2}
                        dataKey="value"
                    >
                        {data.map((entry, index) => (
                            <Cell
                                key={`cell-${entry.name}-${String(index)}`}
                                fill={entry.color ?? `hsl(${String(index * 45)}, 70%, 60%)`}
                                stroke="white"
                                strokeWidth={1}
                            />
                        ))}
                    </Pie>
                    <Tooltip content={<CustomTooltip dollorValue={dollorValue} />} />
                </PieChart>
            </div>

            {/* Custom legend */}
            <div style={{ flex: 1, display: 'flex', alignItems: 'flex-start' }}>
                {renderCustomLegend({
                    payload: data.map((item, index) => ({
                        value: item.name,
                        color: item.color ?? `hsl(${String(index * 45)}, 70%, 60%)`
                    }))
                })}
            </div>
        </div>
    );
};

export default CustomPieChart;