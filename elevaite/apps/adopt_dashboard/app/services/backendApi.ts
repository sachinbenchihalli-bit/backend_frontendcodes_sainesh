// Backend API service for real database integration
import {
  Campaign,
  DashboardOverview,
  ApiResponse,
  CampaignPerformanceSnapshot,
  CampaignHealthMetric,
  CreativePerformance,
  Task,
  CreativeChartData
} from '../types';

const BACKEND_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

// Utility function for API calls
async function apiCall<T>(endpoint: string): Promise<T> {
  try {
    const response = await fetch(`${BACKEND_URL}/api${endpoint}`, {
      method: 'GET',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();

    if (!data.success) {
      throw new Error(data.message || 'API call failed');
    }

    // Return the whole data object so wrappers can access metadata like 'limit'
    return data;
  } catch (error) {
    console.error(`Backend API call failed for ${endpoint}:`, error);
    throw error;
  }
}

// Utility function for POST API calls
async function apiPostCall<T>(endpoint: string, body?: any): Promise<T> {
  try {
    const response = await fetch(`${BACKEND_URL}/api${endpoint}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: body ? JSON.stringify(body) : undefined
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    const data = await response.json();
    if (!data.success) throw new Error(data.message || 'API call failed');
    return data;
  } catch (error) {
    console.error(`API POST call failed for ${endpoint}:`, error);
    throw error;
  }
}

export async function testBackendConnection(): Promise<{
  connected: boolean; message: string; error?: string;
}> {
  try {
    const response = await fetch(`${BACKEND_URL}/api/health`);
    const data = await response.json();
    if (data.status === 'ok' && data.database === 'connected') {
      return { connected: true, message: 'Backend and database connected successfully' };
    }
    return { connected: false, message: 'Backend connected but database failed', error: 'Database connection failed' };
  } catch (error) {
    return {
      connected: false,
      message: 'Backend server not reachable',
      error: error instanceof Error ? error.message : 'Unknown error'
    };
  }
}

// STREAMING TYPES

export interface StreamChunk {
  type:
    | 'start'
    | 'content'
    | 'tool_call_start'
    | 'tool_executing'
    | 'tool_completed'
    | 'tool_error'
    | 'final_response_start'
    | 'done'
    | 'error'
    | 'followup_prompts';
  content?: string;
  tool_name?: string;
  source?: 'cache' | 'live';
  prompts?: string[];
  finish_reason?: string;
  error?: string;
  model?: string;
  tools_used?: string[];
}

export interface StreamCallbacks {
  onChunk: (text: string) => void;
  onFollowupPrompts: (prompts: string[]) => void;
  onDone: () => void;
  onError: (error: string) => void;
  onToolStart?: (toolName: string) => void;
  onToolDone?: (toolName: string, source: 'cache' | 'live') => void;
}

// SSE STREAMING HELPER
async function sendCampaignOptimizationMessageStream(
  campaignId: string,
  message: string,
  sessionId: string = 'default',
  callbacks: StreamCallbacks
): Promise<void> {
  try {
    const response = await fetch(
      `${BACKEND_URL}/api/campaign-optimization/${campaignId}/stream`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'text/event-stream',
        },
        credentials: 'include',
        body: JSON.stringify({ message, session_id: sessionId }),
      }
    );

    if (!response.ok) throw new Error(`HTTP error: ${response.status}`);
    if (!response.body) throw new Error('ReadableStream not supported in this environment');

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const frames = buffer.split('\n\n');
      buffer = frames.pop() ?? '';

      for (const frame of frames) {
        if (!frame.trim()) continue;

        const dataLine = frame
          .split('\n')
          .find(line => line.startsWith('data:'));

        if (!dataLine) continue;

        const jsonStr = dataLine.slice(5).trim();
        if (!jsonStr) continue;

        let chunk: StreamChunk;
        try {
          chunk = JSON.parse(jsonStr) as StreamChunk;
        } catch {
          console.warn('[stream] Could not parse SSE data:', jsonStr);
          continue;
        }

        switch (chunk.type) {
          case 'start':
            break;
          case 'content':
            if (chunk.content) callbacks.onChunk(chunk.content);
            break;
          case 'tool_call_start':
          case 'tool_executing':
            if (chunk.tool_name && callbacks.onToolStart) {
              callbacks.onToolStart(chunk.tool_name);
            }
            break;
          case 'tool_completed':
            if (chunk.tool_name && callbacks.onToolDone) {
              callbacks.onToolDone(chunk.tool_name, chunk.source ?? 'live');
            }
            break;
          case 'tool_error':
            console.warn('[stream] Tool error:', chunk.tool_name, chunk.error);
            break;
          case 'final_response_start':
            break;
          case 'followup_prompts':
            if (chunk.prompts) callbacks.onFollowupPrompts(chunk.prompts);
            break;
          case 'done':
            callbacks.onDone();
            break;
          case 'error':
            callbacks.onError(chunk.error ?? 'Unknown stream error');
            break;
        }
      }
    }

    if (buffer.trim()) {
      const dataLine = buffer.split('\n').find(l => l.startsWith('data:'));
      if (dataLine) {
        try {
          const chunk = JSON.parse(dataLine.slice(5).trim()) as StreamChunk;
          if (chunk.type === 'done') callbacks.onDone();
          if (chunk.type === 'error') callbacks.onError(chunk.error ?? 'Unknown error');
          if (chunk.type === 'followup_prompts' && chunk.prompts) {
            callbacks.onFollowupPrompts(chunk.prompts);
          }
        } catch {
          // ignore
        }
      }
    }
  } catch (error) {
    const msg = error instanceof Error ? error.message : 'Streaming failed';
    console.error('[stream] Fatal error:', msg);
    callbacks.onError(msg);
  }
}

// PREWARM HELPER
function prewarmCampaignContext(campaignId: string): void {
  fetch(`${BACKEND_URL}/api/campaign-optimization/${campaignId}/prewarm`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
  })
    .then((res) => res.json())
    .then((data) => { console.log(`[prewarm] Status for ${campaignId}:`, data.status); })
    .catch((err) => { console.warn('[prewarm] Non-fatal error:', err); });
}

// BACKEND API OBJECT
export const backendApi = {

  async getDashboardOverview(): Promise<DashboardOverview> {
    const response = await apiCall<any>('/dashboard/overview');
    return response.data;
  },

  // Campaigns from database
  // FIX: Added page, Entries, and search parameters to match FastAPI Request URL requirement
  async getCampaigns(page: number = 1, limit: number = 100, search?: string): Promise<any> {
    const params = new URLSearchParams();
    params.append('page', page.toString());
    params.append('Entries', limit.toString());
    if (search) params.append('search', search);

    return await apiCall<any>(`/campaigns?${params.toString()}`);
  },

  async getCampaign(id: string): Promise<Campaign> {
    const response = await apiCall<any>(`/campaigns/${id}`);
    return response.data;
  },

  async getCampaignPerformance(campaignId: string, days: number = 30): Promise<CampaignPerformanceSnapshot[]> {
    const response = await apiCall<any>(`/campaigns/${campaignId}/performance?days=${days}`);
    return response.data;
  },

  async getCampaignHealth(campaignId: string): Promise<CampaignHealthMetric> {
    const response = await apiCall<any>(`/campaigns/${campaignId}/health`);
    return response.data;
  },

  async getCreativePerformance(campaignId: string): Promise<CreativePerformance[]> {
    const response = await apiCall<any>(`/campaigns/${campaignId}/creatives`);
    return response.data;
  },

  async getInsertionOrders(): Promise<any[]> {
    const response = await apiCall<any[]>('/insertion-orders');
    return (response as any).data;
  },

  async getInsertionOrderMetrics(): Promise<any> {
    const response = await apiCall<any>('/insertion-orders-metrics');
    return response.data;
  },

  async getCampaignMetrics(): Promise<any> {
    const response = await apiCall<any>('/campaigns/metrics');
    return response.data;
  },

  async getTasks(): Promise<Task[]> {
    const response = await apiCall<any>('/tasks');
    return response.data;
  },

  async getTopPerformingCreatives(limit: number = 5): Promise<CreativeChartData[]> {
    const response = await apiCall<any>(`/creatives/top-performing?limit=${limit}`);
    return response.data;
  },

  async getHealth(): Promise<any> {
    return await apiCall<any>('/health');
  },

  async getKevelCampaignStatus(campaignId: string, days?: number): Promise<any> {
    const params = days ? `?days=${days}` : '';
    return await apiCall<any>(`/campaigns/${campaignId}/kevel-status${params}`);
  },

  async syncCampaignWithKevel(campaignId: string, days?: number): Promise<any> {
    const params = days ? `?days=${days}` : '';
    return await apiPostCall<any>(`/campaigns/${campaignId}/sync-with-kevel${params}`);
  },

  async getKevelFlightStatus(flightId: string, days?: number): Promise<any> {
    const params = days ? `?days=${days}` : '';
    return await apiCall<any>(`/flights/${flightId}/kevel-status${params}`);
  },

  async getCampaignOptimizationContext(campaignId: string, forceRefresh?: boolean): Promise<any> {
    const params = forceRefresh ? '?force_refresh=true' : '';
    return await apiCall<any>(`/campaign-optimization/${campaignId}${params}`);
  },

  // Send chat message for campaign optimization (non-streaming)
  async sendCampaignOptimizationMessage(
    campaignId: string,
    message: string,
    sessionId?: string,
    userId?: string
  ): Promise<any> {
    const body = { message, session_id: sessionId, user_id: userId };
    return await apiPostCall<any>(`/campaign-optimization/${campaignId}`, body);
  },

  // Send chat message for campaign optimization (streaming)
  sendCampaignOptimizationMessageStream(
    campaignId: string,
    message: string,
    sessionId: string = 'default',
    callbacks: StreamCallbacks
  ): Promise<void> {
    return sendCampaignOptimizationMessageStream(campaignId, message, sessionId, callbacks);
  },

  // Prewarm campaign context cache before user opens chat
  prewarmCampaignContext(campaignId: string): void {
    prewarmCampaignContext(campaignId);
  },

  async getCampaignAIAnalysis(campaignId: string): Promise<any> {
    return await apiCall<any>(`/campaign-optimization/${campaignId}/analyze`);
  },

  async testOpenAIConnection(): Promise<any> {
    return await apiCall<any>('/campaign-optimization/test-ai');
  },

  async getCampaignOptimizationCacheStats(campaignId: string): Promise<any> {
    return await apiCall<any>(`/campaign-optimization/${campaignId}/cache-stats`);
  },

  async clearCampaignOptimizationCache(campaignId: string): Promise<any> {
    const response = await fetch(`${BACKEND_URL}/api/campaign-optimization/${campaignId}/cache`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include'
    });
    if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
    return await response.json();
  }
};

export async function isBackendAvailable(): Promise<boolean> {
  try {
    const result = await testBackendConnection();
    return result.connected;
  } catch {
    return false;
  }
}
