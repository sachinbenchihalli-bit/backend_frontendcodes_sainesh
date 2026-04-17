import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Calendar, Download } from "lucide-react";
import { DateRange } from "@/types";

interface DateRangeFilterProps {
  onDateRangeChange: (range: DateRange | null) => void;
  onExport: () => void;
  isExporting?: boolean;
}

export const DateRangeFilter = ({ onDateRangeChange, onExport, isExporting = false }: DateRangeFilterProps) => {
  const [selectedRange, setSelectedRange] = useState<string>('all_time');
  const [customStartDate, setCustomStartDate] = useState<string>('');
  const [customEndDate, setCustomEndDate] = useState<string>('');

  const handlePresetChange = (value: string) => {
    setSelectedRange(value);
    
    if (value === 'custom') {
      // Don't change date range until custom dates are set
      return;
    }

    const now = new Date();
    let startDate: Date;
    
    switch (value) {
      case 'last_7_days':
        startDate = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
        break;
      case 'last_30_days':
        startDate = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
        break;
      case 'last_90_days':
        startDate = new Date(now.getTime() - 90 * 24 * 60 * 60 * 1000);
        break;
      case 'this_month':
        startDate = new Date(now.getFullYear(), now.getMonth(), 1);
        break;
      case 'last_month':
        startDate = new Date(now.getFullYear(), now.getMonth() - 1, 1);
        const endOfLastMonth = new Date(now.getFullYear(), now.getMonth(), 0);
        onDateRangeChange({ start: startDate, end: endOfLastMonth });
        return;
      case 'all_time':
      default:
        onDateRangeChange(null);
        return;
    }
    
    onDateRangeChange({ start: startDate, end: now });
  };

  const handleCustomDateChange = () => {
    if (customStartDate && customEndDate) {
      const startDate = new Date(customStartDate);
      const endDate = new Date(customEndDate);
      
      if (startDate <= endDate) {
        onDateRangeChange({ start: startDate, end: endDate });
      }
    }
  };

  const formatDateForInput = (date: Date): string => {
    return date.toISOString().split('T')[0];
  };

  const getDefaultDates = () => {
    const now = new Date();
    const thirtyDaysAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    
    return {
      start: formatDateForInput(thirtyDaysAgo),
      end: formatDateForInput(now)
    };
  };

  const defaultDates = getDefaultDates();

  return (
    <div className="flex items-center space-x-3">
      <Select value={selectedRange} onValueChange={handlePresetChange}>
        <SelectTrigger className="w-40 border-gray-300 focus:border-orange-500 focus:ring-orange-500">
          <SelectValue placeholder="Date Range" />
        </SelectTrigger>
        <SelectContent>
          <SelectItem value="all_time">All Time</SelectItem>
          <SelectItem value="last_7_days">Last 7 days</SelectItem>
          <SelectItem value="last_30_days">Last 30 days</SelectItem>
          <SelectItem value="last_90_days">Last 90 days</SelectItem>
          <SelectItem value="this_month">This Month</SelectItem>
          <SelectItem value="last_month">Last Month</SelectItem>
          <SelectItem value="custom">Custom Range</SelectItem>
        </SelectContent>
      </Select>

      {selectedRange === 'custom' && (
        <>
          <div className="flex items-center space-x-2">
            <Input
              type="date"
              value={customStartDate}
              onChange={(e) => {
                setCustomStartDate(e.target.value);
                if (e.target.value && customEndDate) {
                  handleCustomDateChange();
                }
              }}
              className="w-36 border-gray-300 focus:border-orange-500 focus:ring-orange-500"
              placeholder="Start date"
            />
            <span className="text-gray-400 text-sm">to</span>
            <Input
              type="date"
              value={customEndDate}
              onChange={(e) => {
                setCustomEndDate(e.target.value);
                if (customStartDate && e.target.value) {
                  handleCustomDateChange();
                }
              }}
              className="w-36 border-gray-300 focus:border-orange-500 focus:ring-orange-500"
              placeholder="End date"
            />
          </div>
        </>
      )}

      {selectedRange !== 'custom' && (
        <>
          <Input
            type="date"
            defaultValue={defaultDates.start}
            className="w-36 border-gray-300 focus:border-orange-500 focus:ring-orange-500"
            onChange={(e) => {
              const endInput = e.target.parentElement?.querySelector('input[type="date"]:last-child') as HTMLInputElement;
              if (e.target.value && endInput?.value) {
                onDateRangeChange({
                  start: new Date(e.target.value),
                  end: new Date(endInput.value)
                });
              }
            }}
          />
          <span className="text-gray-400 text-sm">to</span>
          <Input
            type="date"
            defaultValue={defaultDates.end}
            className="w-36 border-gray-300 focus:border-orange-500 focus:ring-orange-500"
            onChange={(e) => {
              const startInput = e.target.parentElement?.querySelector('input[type="date"]:first-child') as HTMLInputElement;
              if (startInput?.value && e.target.value) {
                onDateRangeChange({
                  start: new Date(startInput.value),
                  end: new Date(e.target.value)
                });
              }
            }}
          />
        </>
      )}

      <Button
        onClick={onExport}
        disabled={isExporting}
        className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-2 text-sm font-medium flex items-center"
      >
        {isExporting ? (
          <>
            <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin mr-2"></div>
            Exporting...
          </>
        ) : (
          <>
            <Download className="w-4 h-4 mr-2" />
            Export Data
          </>
        )}
      </Button>
    </div>
  );
};
