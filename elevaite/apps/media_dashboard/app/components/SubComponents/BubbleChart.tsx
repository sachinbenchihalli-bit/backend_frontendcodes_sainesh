import React from 'react';
import {
    ScatterChart,
    XAxis,
    YAxis,
    ZAxis,
    Tooltip,
    Scatter,
    Legend,
    ResponsiveContainer,
} from 'recharts';

interface BubbleChartData {
    month: string;
    category: string;
    value: number;
}

interface BubbleChartProps {
    data: BubbleChartData[];
}

const BubbleChart: React.FC<BubbleChartProps> = ({ data }) => {
    const categoryOrder = ['Medical', 'Bakery', 'Gift'];
    const categoryYMap: Record<string, number> = {
        Medical: 3,
        Bakery: 2,
        Gift: 1,
    };

    const colors: Record<string, string> = {
        Medical: '#8B4513',  // SaddleBrown
        Bakery: '#FF8042',   // Orange
        Gift: '#00C49F',     // Teal
    };

    const preparedData = data.map(item => ({
        ...item,
        y: categoryYMap[item.category],
    }));

    return (
        <ResponsiveContainer width="100%" height={400}>
            <ScatterChart
                margin={{ top: 30, right: 30, left: 50, bottom: 30 }}
            >
                <XAxis
                    type="category"
                    dataKey="month"
                    interval={0}
                    tickLine={false}
                    axisLine
                />
                <YAxis
                    type="number"
                    dataKey="y"
                    domain={[0.5, 3.5]}
                    tickLine={false}
                    axisLine={false}
                    allowDecimals={false}
                    ticks={[1, 2, 3]}
                    tickFormatter={(tick) =>
                        Object.entries(categoryYMap).find(([, val]) => val === tick)?.[0] ?? ''
                    }
                />
                <ZAxis type="number" dataKey="value" range={[100, 200]} />
                <Tooltip />
                <Legend />
                {categoryOrder.map(category => (
                    <Scatter
                        key={category}
                        name={category}
                        data={preparedData.filter(d => d.category === category)}
                        fill={colors[category]}
                    />
                ))}
            </ScatterChart>
        </ResponsiveContainer>
    );
};

export default BubbleChart;