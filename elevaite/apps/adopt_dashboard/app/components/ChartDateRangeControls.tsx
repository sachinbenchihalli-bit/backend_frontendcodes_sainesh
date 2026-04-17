"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Calendar, ChevronDown } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { TimePeriod } from "@/hooks/useChartTimePeriod";

interface ChartDateRangeControlsProps {
  timePeriod: TimePeriod;
  onTimePeriodChange: (period: TimePeriod) => void;
  getTimePeriodLabel: () => string;
  getTimePeriodDescription: () => string;
  campaignStartDate?:string | Date;
  campaignEndDate?:string | Date;
}

const TIME_PERIOD_OPTIONS: { value: TimePeriod; label: string; description: string }[] = [
  { value: 'monthly', label: 'Monthly', description: 'Year-Month over campaign date range' },
  { value: 'quarterly', label: 'Quarterly', description: 'Year-Quarterly over campaign date range' },
  { value: 'weekly', label: 'Weekly', description: '7-day splits with year over campaign date range' },
  { value: 'daily', label: 'Daily', description: '1-day splits with year over campaign date range' },
];

export default function ChartDateRangeControls({
  timePeriod,
  onTimePeriodChange,
  getTimePeriodLabel,
  getTimePeriodDescription,
  campaignStartDate,
  campaignEndDate,
}: ChartDateRangeControlsProps) {

//Calculate the number of days in the date range
const calculateDateRangeDays = ():number => {
  if(!campaignStartDate || !campaignEndDate) return 0;
  const start = new Date(campaignStartDate);
  const end = new Date(campaignEndDate);
  if(isNaN(start.getTime()) || isNaN(end.getTime())){
    return 0;
  }
  const diffTime = Math.abs(end.getTime() - start.getTime());
  const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
  return diffDays;
}
const dateRangeDays = calculateDateRangeDays();
const DATE_RANGE_LIMIT = 20 ;
const isDailyDisabled = dateRangeDays > DATE_RANGE_LIMIT;

  return (
    <div className="flex items-center gap-3 flex-wrap">
      {/* Current Period Display */}
      <div className="flex items-center gap-2">
        <Badge variant="outline" className="px-3 py-1 text-sm">
          <Calendar className="w-3 h-3 mr-1" />
          {getTimePeriodLabel()}
        </Badge>
        
        {/* Reset button removed with drill down functionality */}
      </div>

      {/* Time Period Dropdown */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button variant="outline" size="sm" className="h-8">
            Change Period
            <ChevronDown className="w-3 h-3 ml-1" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-56">
          {TIME_PERIOD_OPTIONS.map((option) => {
            const isDisabled = option.value === 'daily' && isDailyDisabled;
            return(
              <DropdownMenuItem
              key={option.value}
              onClick={() => !isDisabled && onTimePeriodChange(option.value)}
              className={`${isDisabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}  ${timePeriod === option.value ? 'bg-orange-50 text-orange-700' : ''}`}
              disabled = {isDisabled}
            >
              <div className="flex flex-col">
                <span className="font-medium">{option.label}</span>
                <span className="text-xs text-gray-500">
                  {isDisabled ? `Disabled (date range > 20 days)` : option.description}</span>
              </div>
            </DropdownMenuItem>
            );
            
        })}
          
        </DropdownMenuContent>
      </DropdownMenu>

      {/* Drill controls removed for now */}

      {/* Period Description */}
      <div className="text-xs text-gray-500 hidden sm:block">
        {getTimePeriodDescription()}
      </div>
    </div>
  );
}
