import {
  Campaign,
  CampaignPerformanceSnapshot,
  CampaignHealthMetric,
  DashboardOverview,
  Task,
  CreativeChartData,
  CampaignFilters,
  PaginatedResponse,
  ApiResponse,
  ApiError,
  InsertionOrder,
  KevelFlightStatus,
  KevelFlightStatusResponse
} from '../types';
import { backendApi } from './backendApi';

const createApiError = (message: string, code?: string): ApiError => ({
  message,
  code,
  details: null
});

// Dashboard API
export const dashboardApi = {
  async getOverview(): Promise<ApiResponse<DashboardOverview>> {
    try {
      const overview = await backendApi.getDashboardOverview();
      return {
        data: overview,
        success: true,
        message: 'Dashboard overview fetched successfully from backend'
      };
    } catch (error) {
      throw createApiError(
        'Failed to fetch dashboard overview. Please check if the backend is running.',
        'BACKEND_ERROR'
      );
    }
  }
};

// Campaigns API
export const campaignsApi = {
  async getCampaigns(
    page: number = 1,
    limit: number = 100, 
    filters: CampaignFilters = {}
  ): Promise<ApiResponse<PaginatedResponse<Campaign>>> {
    try {
      // Pass page and limit (as Entries) to the backend API call
      const response = await backendApi.getCampaigns(page, limit, filters.search);
      const campaigns = response.data;

      // Apply other filters (like status) on frontend if the backend doesn't support them yet
      let filteredCampaigns = campaigns;

      // REMOVED FRONTEND SEARCH FILTER - Backend now handles this via the API call above
      /*
      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        filteredCampaigns = filteredCampaigns.filter(c =>
          c.name.toLowerCase().includes(searchLower) ||
          c.product?.toLowerCase().includes(searchLower)
        );
      }
      */

      if (filters.status && filters.status.length > 0) {
        filteredCampaigns = filteredCampaigns.filter(c =>
          filters.status!.some(status => status.toLowerCase() === c.status.toLowerCase())
        );
      }

      return {
        data: {
          data: filteredCampaigns,
          total: response.total || filteredCampaigns.length,
          page,
          limit: response.limit || limit, // Ensure we pass back the API's limit value
          total_pages: response.total_pages || Math.ceil((response.total || filteredCampaigns.length) / limit)
        },
        success: true,
        message: 'Campaigns fetched successfully from backend'
      };
    } catch (error) {
      throw createApiError(
        'Failed to fetch campaigns. Please check if the backend is running.',
        'BACKEND_ERROR'
      );
    }
  },

  async getCampaign(id: string): Promise<ApiResponse<Campaign>> {
    try {
      const campaign = await backendApi.getCampaign(id);
      return {
        data: campaign,
        success: true,
        message: 'Campaign fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch campaign', 'CAMPAIGN_ERROR');
    }
  },

  async getCampaignPerformance(
    id: string,
    days: number = 30
  ): Promise<ApiResponse<CampaignPerformanceSnapshot[]>> {
    try {
      const performance = await backendApi.getCampaignPerformance(id, days);
      return {
        data: performance,
        success: true,
        message: 'Campaign performance fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch campaign performance', 'PERFORMANCE_ERROR');
    }
  },

  async getCampaignHealth(id: string): Promise<ApiResponse<CampaignHealthMetric>> {
    try {
      const health = await backendApi.getCampaignHealth(id);
      return {
        data: health,
        success: true,
        message: 'Campaign health fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch campaign health', 'HEALTH_ERROR');
    }
  },

  async updateCampaignStatus(
    id: string,
    _status: Campaign['status']
  ): Promise<ApiResponse<Campaign>> {
    try {
      const campaign = await backendApi.getCampaign(id);
      return {
        data: campaign,
        success: true,
        message: 'Campaign status updated successfully'
      };
    } catch (error) {
      throw createApiError('Failed to update campaign status', 'UPDATE_ERROR');
    }
  },

  async getKevelCampaignStatus(
    campaignId: string,
    days?: number
  ): Promise<ApiResponse<KevelFlightStatus>> {
    try {
      const kevelData = await backendApi.getKevelCampaignStatus(campaignId, days);
      return {
        data: kevelData,
        success: true,
        message: 'Kevel campaign status fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch Kevel campaign status', 'KEVEL_ERROR');
    }
  },

  async syncCampaignWithKevel(
    campaignId: string,
    days?: number
  ): Promise<ApiResponse<any>> {
    try {
      const syncResult = await backendApi.syncCampaignWithKevel(campaignId, days);
      return {
        data: syncResult,
        success: true,
        message: 'Campaign synced with Kevel successfully'
      };
    } catch (error) {
      throw createApiError('Failed to sync campaign with Kevel', 'KEVEL_SYNC_ERROR');
    }
  },

  async getKevelFlightStatus(
    flightId: string,
    days?: number
  ): Promise<ApiResponse<KevelFlightStatus>> {
    try {
      const kevelData = await backendApi.getKevelFlightStatus(flightId, days);
      return {
        data: kevelData,
        success: true,
        message: 'Kevel flight status fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch Kevel flight status', 'KEVEL_ERROR');
    }
  }
};



// Insertion Orders API
export const insertionOrdersApi = {
  async getInsertionOrders(
    page: number = 1,
    limit: number = 10,
    filters: CampaignFilters = {}
  ): Promise<ApiResponse<PaginatedResponse<InsertionOrder>>> {
    try {
      const response = await backendApi.getInsertionOrders();
      const insertionOrders = response as any;

      let filteredOrders = insertionOrders;

      if (filters.search) {
        const searchLower = filters.search.toLowerCase();
        filteredOrders = filteredOrders.filter((io: any) =>
          io.name.toLowerCase().includes(searchLower)
        );
      }

      if (filters.status && filters.status.length > 0) {
        filteredOrders = filteredOrders.filter((io: any) =>
          filters.status!.some(status => status.toLowerCase() === io.status.toLowerCase())
        );
      }

      const total = filteredOrders.length;
      const totalPages = Math.ceil(total / limit);
      const startIndex = (page - 1) * limit;
      const endIndex = startIndex + limit;
      const paginatedData = filteredOrders.slice(startIndex, endIndex);

      return {
        data: {
          data: paginatedData,
          total,
          page,
          limit,
          total_pages: totalPages
        },
        success: true,
        message: 'Insertion orders fetched successfully from backend'
      };
    } catch (error) {
      throw createApiError(
        'Failed to fetch insertion orders. Please check if the backend is running.',
        'BACKEND_ERROR'
      );
    }
  },

  async getInsertionOrder(id: string): Promise<ApiResponse<InsertionOrder>> {
    try {
      const allOrders = await this.getInsertionOrders(1, 100);
      const insertionOrder = allOrders.data.data.find((io: InsertionOrder) => io.id === id);

      if (!insertionOrder) {
        throw createApiError('Insertion order not found', 'INSERTION_ORDER_NOT_FOUND');
      }

      return {
        data: insertionOrder,
        success: true,
        message: 'Insertion order fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch insertion order', 'INSERTION_ORDER_ERROR');
    }
  }
};

// Creative Performance API
export const creativesApi = {
  async getTopPerformingCreatives(limit: number = 5): Promise<ApiResponse<CreativeChartData[]>> {
    try {
      const creatives = await backendApi.getTopPerformingCreatives(limit);
      return {
        data: creatives,
        success: true,
        message: 'Top performing creatives fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch creative performance', 'CREATIVES_ERROR');
    }
  }
};

// Tasks API
export const tasksApi = {
  async getTasks(): Promise<ApiResponse<Task[]>> {
    try {
      const tasks = await backendApi.getTasks();
      return {
        data: tasks,
        success: true,
        message: 'Tasks fetched successfully'
      };
    } catch (error) {
      throw createApiError('Failed to fetch tasks', 'TASKS_ERROR');
    }
  },

  async updateTaskStatus(
    id: string,
    _status: Task['status']
  ): Promise<ApiResponse<Task>> {
    try {
      const tasks = await backendApi.getTasks();
      const task = tasks.find(t => t.id === id);

      if (!task) {
        throw createApiError('Task not found', 'TASK_NOT_FOUND');
      }

      return {
        data: task,
        success: true,
        message: 'Task status updated successfully'
      };
    } catch (error) {
      throw createApiError('Failed to update task status', 'TASK_UPDATE_ERROR');
    }
  }
};

// Export utility functions for error handling
export const handleApiError = (error: any): ApiError => {
  if (error.message && typeof error.message === 'string') {
    return error as ApiError;
  }
  
  return {
    message: 'An unexpected error occurred',
    code: 'UNKNOWN_ERROR',
    details: error
  };
};

// Export all APIs
export const api = {
  dashboard: dashboardApi,
  campaigns: campaignsApi,
  insertionOrders: insertionOrdersApi,
  creatives: creativesApi,
  tasks: tasksApi
};