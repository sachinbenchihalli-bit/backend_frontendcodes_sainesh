"use client";
import { useState, useEffect } from "react";
import { CommonButton, ElevaiteIcons, ChatbotIcons } from "@repo/ui/components";
import type { TargetingConfiguration } from "../lib/interfaces";
import { TargetingConfigurationAPI, getCurrentUserId } from "../lib/targetingConfigApi";
import { TargetingConfigModal } from "./TargetingConfigModal";
import "./TargetingConfigSelector.scss";

export interface TargetingConfigSelectorProps {
  selectedConfigId?: string;
  onConfigSelect: (configId: string | undefined) => void;
  label?: string;
  required?: boolean;
  // Optional shared state props to prevent multiple API calls
  configurations?: TargetingConfiguration[];
  isLoading?: boolean;
  error?: string | null;
  // Optional callback to refresh shared configurations when a new one is created
  onConfigurationCreated?: () => void;
}

export function TargetingConfigSelector({
  selectedConfigId,
  onConfigSelect,
  label = "Targeting Configuration",
  required = false,
  // Shared state props
  configurations: sharedConfigurations,
  isLoading: sharedIsLoading,
  error: sharedError,
  onConfigurationCreated
}: TargetingConfigSelectorProps): JSX.Element {
  // Use shared state if provided, otherwise use local state
  const [localConfigurations, setLocalConfigurations] = useState<TargetingConfiguration[]>([]);
  const [localIsLoading, setLocalIsLoading] = useState(true);
  const [localError, setLocalError] = useState<string | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingConfig, setEditingConfig] = useState<TargetingConfiguration | undefined>();

  // Determine which state to use
  const configurations = sharedConfigurations ?? localConfigurations;
  const isLoading = sharedIsLoading ?? localIsLoading;
  const error = sharedError ?? localError;

  // Only load configurations if shared state is not provided
  useEffect(() => {
    if (!sharedConfigurations) {
      loadConfigurations();
    }
  }, [sharedConfigurations]);

  const loadConfigurations = async () => {
    try {
      setLocalIsLoading(true);
      setLocalError(null);
      const userId = getCurrentUserId();
      const configs = await TargetingConfigurationAPI.getConfigurations(userId);

      // Smart ordering: Recently created configurations first, then alphabetical
      const sortedConfigs = configs.sort((a, b) => {
        // First, sort by creation date (newest first)
        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();
        if (dateB !== dateA) {
          return dateB - dateA;
        }
        // If same date, sort alphabetically by name
        return a.name.localeCompare(b.name);
      });

      setLocalConfigurations(sortedConfigs);
    } catch (err) {
      setLocalError(err instanceof Error ? err.message : 'Failed to load targeting configurations');
    } finally {
      setLocalIsLoading(false);
    }
  };

  const handleCreateNew = () => {
    setEditingConfig(undefined);
    setIsModalOpen(true);
  };

  const handleEdit = (config: TargetingConfiguration) => {
    setEditingConfig(config);
    setIsModalOpen(true);
  };

  const handleModalSave = async (savedConfig: TargetingConfiguration) => {
    // Refresh configurations based on whether we're using shared or local state
    if (sharedConfigurations && onConfigurationCreated) {
      // Using shared state - call the parent's refresh function
      onConfigurationCreated();
    } else if (!sharedConfigurations) {
      // Using local state - reload locally
      await loadConfigurations();
    }

    // If this was a new configuration, select it
    if (!editingConfig) {
      onConfigSelect(savedConfig.id);
    }
  };

  const handleCardClick = (config: TargetingConfiguration) => {
    // Toggle selection - if already selected, deselect it
    if (selectedConfigId === config.id) {
      onConfigSelect(undefined);
    } else {
      onConfigSelect(config.id);
    }
  };

  const formatTargetingValue = (value: string[] | undefined, fallback: string = "Not specified") => {
    if (!value || value.length === 0) return fallback;
    return value.join(", ");
  };

  const getTagsFromConfig = (config: TargetingConfiguration): string[] => {
    const tags: string[] = [];

    // Add interests as tags
    if (config.targeting_config.interests?.length > 0) {
      tags.push(...config.targeting_config.interests);
    }

    // Add behavioral data as tags
    if (config.targeting_config.behavioral_data?.length > 0) {
      tags.push(...config.targeting_config.behavioral_data);
    }

    return tags;
  };

  return (
    <div className="targeting-config-selector">
      {/* Header */}
      <div className="targeting-config-selector__header">
        <h3 className="targeting-config-selector__title">Targeting Configuration</h3>
        <CommonButton
          onClick={handleCreateNew}
          className="targeting-config-selector__add-button"
        >
          <ChatbotIcons.SVGAdd />
          Add New Targeting
        </CommonButton>
      </div>

      {/* Subheader */}
      <div className="targeting-config-selector__subheader">
        <h4>Select Targeting Configuration</h4>
      </div>

      {/* Loading State */}
      {isLoading && (
        <div className="targeting-config-selector__loading">
          Loading targeting configurations...
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="targeting-config-selector__error">
          <p>{error}</p>
          <CommonButton onClick={loadConfigurations}>
            Retry
          </CommonButton>
        </div>
      )}

      {/* Empty State */}
      {!isLoading && configurations.length === 0 && !error && (
        <div className="targeting-config-selector__empty">
          <p>No targeting configurations found.</p>
          <CommonButton onClick={handleCreateNew}>
            Create Your First Configuration
          </CommonButton>
        </div>
      )}

      {/* Configuration Cards Grid */}
      {!isLoading && configurations.length > 0 && (
        <div className="targeting-config-selector__grid">
          {configurations.map((config) => {
            const isSelected = selectedConfigId === config.id;
            const tags = getTagsFromConfig(config);

            return (
              <div
                key={config.id}
                className={`targeting-config-card ${isSelected ? 'targeting-config-card--selected' : ''}`}
                onClick={() => handleCardClick(config)}
              >
                {/* Card Header */}
                <div className="targeting-config-card__header">
                  <div className="targeting-config-card__title-section">
                    <div className={`targeting-config-card__radio ${isSelected ? 'targeting-config-card__radio--checked' : ''}`}>
                    </div>
                    <h5 className="targeting-config-card__title">{config.name}</h5>
                  </div>
                  <button
                    type="button"
                    className="targeting-config-card__edit-btn"
                    onClick={(e) => {
                      e.stopPropagation();
                      e.preventDefault();
                      handleEdit(config);
                    }}
                    title="Edit configuration"
                  >
                    <ElevaiteIcons.SVGSettings />
                  </button>
                </div>

                {/* Description */}
                {config.description && (
                  <p className="targeting-config-card__description">
                    {config.description}
                  </p>
                )}

                {/* Targeting Details */}
                <div className="targeting-config-card__details">
                  <div className="targeting-config-card__detail-row">
                    <span className="targeting-config-card__label">Age:</span>
                    <span className="targeting-config-card__value">
                      {formatTargetingValue(config.targeting_config.age_range, "All")}
                    </span>
                  </div>

                  <div className="targeting-config-card__detail-row">
                    <span className="targeting-config-card__label">Gender:</span>
                    <span className="targeting-config-card__value">
                      {formatTargetingValue(config.targeting_config.gender, "All")}
                    </span>
                  </div>

                  <div className="targeting-config-card__detail-row">
                    <span className="targeting-config-card__label">Location:</span>
                    <span className="targeting-config-card__value">
                      {formatTargetingValue(config.targeting_config.location, "Global")}
                    </span>
                  </div>
                </div>

                {/* Tags */}
                {tags.length > 0 && (
                  <div className="targeting-config-card__tags">
                    {tags.slice(0, 3).map((tag, index) => (
                      <span key={index} className="targeting-config-card__tag">
                        {tag}
                      </span>
                    ))}
                    {tags.length > 3 && (
                      <span className="targeting-config-card__tag targeting-config-card__tag--more">
                        +{tags.length - 3} more
                      </span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Targeting Configuration Modal */}
      <TargetingConfigModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={handleModalSave}
        editingConfig={editingConfig}
      />
    </div>
  );
}
