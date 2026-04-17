"use client";

import React from 'react';
import { Card, CardContent } from "@/components/ui/card";

type InsightCardProps = {
    icon: React.ReactNode;
    title: string;
    value: string | number;
    description: string;
    isLoading?: boolean;
    iconBgColor?: string;
    iconColor?: string;
    valueColor?: string;
    descriptionColor?: string;
    onClick?: () => void;
    isClickable?: boolean;
};

const InsightCard: React.FC<InsightCardProps> = ({
    icon,
    title,
    value,
    description,
    isLoading = false,
    iconBgColor = "bg-blue-100",
    iconColor = "text-blue-600",
    valueColor = "text-gray-900",
    descriptionColor = "text-green-600",
    onClick,
    isClickable = false
}) => {
    if (isLoading) {
        return (
            <Card className="metric-card">
                <CardContent className="p-4">
                    <div className="space-y-2">
                        <div className="flex items-center space-x-3">
                            <div className={`w-8 h-8 ${iconBgColor} rounded-full animate-pulse`}></div>
                            <div className="h-4 bg-gray-200 rounded w-20 animate-pulse"></div>
                        </div>
                        <div className="h-10 bg-gray-200 rounded w-16 animate-pulse"></div>
                        <div className="h-3 bg-gray-200 rounded w-24 animate-pulse"></div>
                    </div>
                </CardContent>
            </Card>
        );
    }

    return (
        <Card
            className={`metric-card ${isClickable ? 'cursor-pointer hover:shadow-lg hover:scale-105 transition-all duration-200' : ''}`}
            onClick={isClickable ? onClick : undefined}
        >
            <CardContent className="p-1">
                <div className="flex items-start space-x-3">
                    {/* Icon positioned to the left */}
                    <div className={`w-10 h-10 ${iconBgColor} rounded-full flex items-center justify-center flex-shrink-0 mt-1`}>
                        <div className={iconColor}>
                            {icon}
                        </div>
                    </div>

                    {/* Content to the right */}
                    <div className="flex-1 min-w-0">
                        <div className="text-md text-gray-600 font-medium mb-2">
                            {title}
                        </div>
                        <div className={`text-4xl font-medium ${valueColor} mb-1`}>
                            {value}
                        </div>
                        <div className={`text-xs font-medium ${descriptionColor}`}>
                            {description}
                        </div>
                    </div>
                </div>
            </CardContent>
        </Card>
    );
};

export default InsightCard;
