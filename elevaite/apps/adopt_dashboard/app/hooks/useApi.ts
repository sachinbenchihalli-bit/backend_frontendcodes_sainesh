import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Campaign,
  CampaignPerformanceSnapshot,
  CampaignHealthMetric,
  DashboardOverview,
  Task,
  CreativeChartData,
  CampaignFilters,
  ApiError,
  InsertionOrder
} from '../types';
import { api, handleApiError } from '../services/api';
import { backendApi } from '../services/backendApi';

// Dashboard hooks
export const useDashboardOverview = () => {
  return useQuery({
    queryKey: ['dashboard', 'overview'],
    queryFn: async () => {
      try {
        const response = await api.dashboard.getOverview();
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30 * 1000, // Refetch every 30 seconds for real-time feel
  });
};

export const useInsertionOrderMetrics = () => {
  return useQuery({
    queryKey: ['insertion-orders', 'metrics'],
    queryFn: async () => {
      try {
        const response = await backendApi.getInsertionOrderMetrics();
        return response;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
};

export const useCampaignMetrics = () => {
  return useQuery({
    queryKey: ['campaigns', 'metrics'],
    queryFn: async () => {
      try {
        const response = await backendApi.getCampaignMetrics();
        return response;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
    refetchInterval: 30 * 1000, // Refetch every 30 seconds
  });
};

// Campaign hooks
export const useCampaigns = (
  page: number = 1, 
  limit: number = 10, 
  filters: CampaignFilters = {}
) => {
  return useQuery({
    queryKey: ['campaigns', page, limit, filters],
    queryFn: async () => {
      try {
        const response = await api.campaigns.getCampaigns(page, limit, filters);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    keepPreviousData: true, // Keep previous data while fetching new data
  });
};

export const useCampaign = (id: string | undefined) => {
  return useQuery({
    queryKey: ['campaign', id],
    queryFn: async () => {
      if (!id) throw new Error('Campaign ID is required');
      try {
        const response = await api.campaigns.getCampaign(id);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useCampaignPerformance = (id: string | undefined, days: number = 30) => {
  return useQuery({
    queryKey: ['campaign', id, 'performance', days],
    queryFn: async () => {
      if (!id) throw new Error('Campaign ID is required');
      try {
        const response = await api.campaigns.getCampaignPerformance(id, days);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    enabled: !!id,
    staleTime: 1 * 60 * 1000, // 1 minute
    refetchInterval: 60 * 1000, // Refetch every minute for performance data
  });
};

// Hook for campaign chart data with time period support
export const useCampaignChartData = (
  id: string | undefined,
  days: number | undefined = 30,
  startDate?: string,
  endDate?: string
) => {
  return useQuery({
    queryKey: ['campaign', id, 'chart-data', startDate && endDate ? 'custom' : 'days', days, startDate, endDate],
    queryFn: async () => {
      if (!id) throw new Error('Campaign ID is required');
      try {
        // Build query parameters
        const params = new URLSearchParams();

        // If we have custom start/end dates, use those instead of days
        if (startDate && endDate) {
          params.append('start_date', startDate);
          params.append('end_date', endDate);
        } else if (days !== undefined) {
          params.append('days', days.toString());
        }

        const queryString = params.toString();
        const url = `/campaigns/${id}/performance${queryString ? `?${queryString}` : ''}`;

        // Make direct API call with proper parameters
        const response = await fetch(`http://localhost:8000/api${url}`, {
          method: 'GET',
          headers: {
            'Content-Type': 'application/json',
          },
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const result = await response.json();
        return result.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    enabled: !!id,
    staleTime: 2 * 60 * 1000, // 2 minutes for chart data
    refetchInterval: 2 * 60 * 1000, // Refetch every 2 minutes
  });
};

// Insertion Order hooks
export const useInsertionOrders = (
  page: number = 1,
  limit: number = 10,
  filters: CampaignFilters = {}
) => {
  return useQuery({
    queryKey: ['insertionOrders', page, limit, filters],
    queryFn: async () => {
      try {
        const response = await api.insertionOrders.getInsertionOrders(page, limit, filters);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    staleTime: 2 * 60 * 1000, // 2 minutes
    keepPreviousData: true, // Keep previous data while fetching new data
  });
};

export const useInsertionOrder = (id: string | undefined) => {
  return useQuery({
    queryKey: ['insertionOrder', id],
    queryFn: async () => {
      if (!id) throw new Error('Insertion Order ID is required');
      try {
        const response = await api.insertionOrders.getInsertionOrder(id);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useCampaignHealth = (id: string | undefined) => {
  return useQuery({
    queryKey: ['campaign', id, 'health'],
    queryFn: async () => {
      if (!id) throw new Error('Campaign ID is required');
      try {
        const response = await api.campaigns.getCampaignHealth(id);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    enabled: !!id,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

// Campaign mutation hooks
export const useUpdateCampaignStatus = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: Campaign['status'] }) => {
      try {
        const response = await api.campaigns.updateCampaignStatus(id, status);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: (updatedCampaign) => {
      // Update the campaign in the cache
      queryClient.setQueryData(['campaign', updatedCampaign.id], updatedCampaign);
      
      // Invalidate campaigns list to refetch with updated data
      queryClient.invalidateQueries({ queryKey: ['campaigns'] });
      
      // Invalidate dashboard overview to update counts
      queryClient.invalidateQueries({ queryKey: ['dashboard', 'overview'] });
    },
  });
};

// Creative hooks
export const useTopPerformingCreatives = (limit: number = 5) => {
  return useQuery({
    queryKey: ['creatives', 'top-performing', limit],
    queryFn: async () => {
      try {
        const response = await api.creatives.getTopPerformingCreatives(limit);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
};

// Task hooks
export const useTasks = () => {
  return useQuery({
    queryKey: ['tasks'],
    queryFn: async () => {
      try {
        const response = await api.tasks.getTasks();
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
};

export const useUpdateTaskStatus = () => {
  const queryClient = useQueryClient();
  
  return useMutation({
    mutationFn: async ({ id, status }: { id: string; status: Task['status'] }) => {
      try {
        const response = await api.tasks.updateTaskStatus(id, status);
        return response.data;
      } catch (error) {
        throw handleApiError(error);
      }
    },
    onSuccess: () => {
      // Invalidate tasks to refetch with updated data
      queryClient.invalidateQueries({ queryKey: ['tasks'] });
    },
  });
};

// Utility hook for handling loading states across multiple queries
export const useLoadingState = (queries: Array<{ isLoading: boolean; error: any }>) => {
  const isLoading = queries.some(query => query.isLoading);
  const errors = queries.map(query => query.error).filter(Boolean);
  const hasError = errors.length > 0;
  
  return {
    isLoading,
    hasError,
    errors: errors as ApiError[],
    firstError: errors[0] as ApiError | undefined
  };
};

// Hook for managing filters state
export const useCampaignFilters = () => {
  const queryClient = useQueryClient();
  
  const invalidateFilters = () => {
    queryClient.invalidateQueries({ queryKey: ['campaigns'] });
  };
  
  return {
    invalidateFilters
  };
};
