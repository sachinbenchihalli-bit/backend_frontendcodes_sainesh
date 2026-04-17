import type { TargetingConfiguration, TargetingConfigurationCreate, TargetingConfigurationUpdate } from './interfaces';

const API_BASE_URL = process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL || 'http://localhost:8000';

export class TargetingConfigurationAPI {
  
  /**
   * Get all targeting configurations for a user
   */
  static async getConfigurations(userId: string): Promise<TargetingConfiguration[]> {
    try {
      const response = await fetch(`${API_BASE_URL}/targeting-configurations?user_id=${encodeURIComponent(userId)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch targeting configurations: ${response.statusText}`);
      }

      const data = await response.json();
      return data.configurations || [];
    } catch (error) {
      console.error('Error fetching targeting configurations:', error);
      throw error;
    }
  }

  /**
   * Get a specific targeting configuration by ID
   */
  static async getConfiguration(configId: string, userId: string): Promise<TargetingConfiguration> {
    try {
      const response = await fetch(`${API_BASE_URL}/targeting-configurations/${configId}?user_id=${encodeURIComponent(userId)}`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to fetch targeting configuration: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error fetching targeting configuration:', error);
      throw error;
    }
  }

  /**
   * Create a new targeting configuration
   */
  static async createConfiguration(userId: string, config: TargetingConfigurationCreate): Promise<TargetingConfiguration> {
    try {
      const response = await fetch(`${API_BASE_URL}/targeting-configurations?user_id=${encodeURIComponent(userId)}`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(config),
      });

      if (!response.ok) {
        throw new Error(`Failed to create targeting configuration: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error creating targeting configuration:', error);
      throw error;
    }
  }

  /**
   * Update an existing targeting configuration
   */
  static async updateConfiguration(configId: string, userId: string, updates: TargetingConfigurationUpdate): Promise<TargetingConfiguration> {
    try {
      const response = await fetch(`${API_BASE_URL}/targeting-configurations/${configId}?user_id=${encodeURIComponent(userId)}`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(updates),
      });

      if (!response.ok) {
        throw new Error(`Failed to update targeting configuration: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Error updating targeting configuration:', error);
      throw error;
    }
  }

  /**
   * Delete a targeting configuration
   */
  static async deleteConfiguration(configId: string, userId: string): Promise<void> {
    try {
      const response = await fetch(`${API_BASE_URL}/targeting-configurations/${configId}?user_id=${encodeURIComponent(userId)}`, {
        method: 'DELETE',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(`Failed to delete targeting configuration: ${response.statusText}`);
      }
    } catch (error) {
      console.error('Error deleting targeting configuration:', error);
      throw error;
    }
  }
}

/**
 * Helper function to get user ID from session
 * This should be replaced with your actual user ID retrieval logic
 */
export function getCurrentUserId(): string {
  // For now, return a default user ID
  // In a real app, this would come from authentication context
  return 'default_user';
}

/**
 * Helper function to validate targeting configuration data
 */
export function validateTargetingConfig(config: TargetingConfigurationCreate): string[] {
  const errors: string[] = [];

  if (!config.name || config.name.trim().length === 0) {
    errors.push('Name is required');
  }

  if (config.name && config.name.length > 255) {
    errors.push('Name must be 255 characters or less');
  }

  if (!config.targeting_config) {
    errors.push('Targeting configuration is required');
  } else {
    // Check if at least one targeting option is selected
    const hasTargeting = Object.values(config.targeting_config).some(
      (value) => Array.isArray(value) && value.length > 0
    );

    if (!hasTargeting) {
      errors.push('At least one targeting option must be selected');
    }
  }

  return errors;
}

/**
 * Helper function to format targeting configuration for display
 */
export function formatTargetingConfigForDisplay(config: TargetingConfiguration): string {
  const targeting = config.targeting_config;
  const parts: string[] = [];

  if (targeting.age_range?.length > 0) {
    parts.push(`Age: ${targeting.age_range.join(', ')}`);
  }
  if (targeting.gender?.length > 0) {
    parts.push(`Gender: ${targeting.gender.join(', ')}`);
  }
  if (targeting.income_level?.length > 0) {
    parts.push(`Income: ${targeting.income_level.join(', ')}`);
  }
  if (targeting.location?.length > 0) {
    parts.push(`Location: ${targeting.location.join(', ')}`);
  }
  if (targeting.interests?.length > 0) {
    parts.push(`Interests: ${targeting.interests.join(', ')}`);
  }
  if (targeting.behavioral_data?.length > 0) {
    parts.push(`Behavior: ${targeting.behavioral_data.join(', ')}`);
  }

  return parts.join(' | ') || 'No targeting specified';
}
