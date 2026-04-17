"use client";
import { useState, useEffect } from "react";
import { CommonButton, CommonInput, ElevaiteIcons, type CommonSelectOption } from "@repo/ui/components";
import { MultiSelect } from "./MultiSelect";
import type { TargetingConfiguration, TargetingConfigurationCreate, TargetingConfig } from "../lib/interfaces";
import { TargetingConfigurationAPI, getCurrentUserId, validateTargetingConfig } from "../lib/targetingConfigApi";
import "./TargetingConfigModal.scss";

// Targeting options (same as in GenerateIOForm)
const AGE_RANGE_OPTIONS: CommonSelectOption[] = [
  { label: "18-24", value: "18-24" },
  { label: "25-34", value: "25-34" },
  { label: "35-44", value: "35-44" },
  { label: "45-54", value: "45-54" },
  { label: "55+", value: "55+" },
];

const GENDER_OPTIONS: CommonSelectOption[] = [
  { label: "Male", value: "Male" },
  { label: "Female", value: "Female" },
  { label: "All", value: "All" },
];

const INCOME_LEVEL_OPTIONS: CommonSelectOption[] = [
  { label: "Low Income", value: "Low Income" },
  { label: "Middle Income", value: "Middle Income" },
  { label: "High Income", value: "High Income" },
];

const INTERESTS_OPTIONS: CommonSelectOption[] = [
  { label: "Technology", value: "Technology" },
  { label: "Gaming", value: "Gaming" },
  { label: "Sports", value: "Sports" },
  { label: "Fashion", value: "Fashion" },
  { label: "Travel", value: "Travel" },
];

const LOCATION_OPTIONS: CommonSelectOption[] = [
  { label: "United States", value: "United States" },
  { label: "Canada", value: "Canada" },
  { label: "United Kingdom", value: "United Kingdom" },
  { label: "Europe", value: "Europe" },
  { label: "Asia Pacific", value: "Asia Pacific" },
];

const BEHAVIORAL_DATA_OPTIONS: CommonSelectOption[] = [
  { label: "Tech Enthusiasts", value: "Tech Enthusiasts" },
  { label: "Online Shoppers", value: "Online Shoppers" },
  { label: "Frequent Travelers", value: "Frequent Travelers" },
  { label: "Entertainment Seekers", value: "Entertainment Seekers" },
];

export interface TargetingConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSave: (config: TargetingConfiguration) => void;
  editingConfig?: TargetingConfiguration;
}

export function TargetingConfigModal({ isOpen, onClose, onSave, editingConfig }: TargetingConfigModalProps): JSX.Element | null {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [targetingConfig, setTargetingConfig] = useState<TargetingConfig>({
    age_range: [],
    gender: [],
    income_level: [],
    location: [],
    interests: [],
    behavioral_data: [],
  });
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Reset form when modal opens or editingConfig changes
  useEffect(() => {
    if (isOpen) {
      if (editingConfig) {
        setName(editingConfig.name);
        setDescription(editingConfig.description || "");
        setTargetingConfig(editingConfig.targeting_config);
      } else {
        setName("");
        setDescription("");
        setTargetingConfig({
          age_range: [],
          gender: [],
          income_level: [],
          location: [],
          interests: [],
          behavioral_data: [],
        });
      }
      setError(null);
    }
  }, [isOpen, editingConfig]);



  const handleSubmit = async (e?: React.FormEvent | React.MouseEvent) => {
    e?.preventDefault();
    setError(null);

    const configData: TargetingConfigurationCreate = {
      name: name.trim(),
      description: description.trim() || undefined,
      targeting_config: targetingConfig,
    };

    // Validate the configuration
    const validationErrors = validateTargetingConfig(configData);
    if (validationErrors.length > 0) {
      setError(validationErrors.join(', '));
      return;
    }

    setIsSubmitting(true);

    try {
      const userId = getCurrentUserId();
      let savedConfig: TargetingConfiguration;

      if (editingConfig) {
        // Update existing configuration
        savedConfig = await TargetingConfigurationAPI.updateConfiguration(
          editingConfig.id,
          userId,
          configData
        );
      } else {
        // Create new configuration
        savedConfig = await TargetingConfigurationAPI.createConfiguration(userId, configData);
      }

      onSave(savedConfig);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save targeting configuration');
    } finally {
      setIsSubmitting(false);
    }
  };

  const updateTargetingField = (field: keyof TargetingConfig, values: string[]) => {
    setTargetingConfig(prev => ({
      ...prev,
      [field]: values
    }));
  };

  if (!isOpen) return null;

  return (
    <div className="targeting-config-modal-overlay">
      <div className="targeting-config-modal">
        <div className="targeting-config-modal__header">
          <h2>{editingConfig ? 'Edit Targeting Configuration' : 'Create Targeting Configuration'}</h2>
          <CommonButton onClick={onClose} noBackground>
            <ElevaiteIcons.SVGXmark />
          </CommonButton>
        </div>

        <form onSubmit={handleSubmit} className="targeting-config-modal__form">
          <div className="targeting-config-modal__basic-info">
            <CommonInput
              key={`name-${editingConfig?.id || 'new'}-${isOpen}`}
              label="Configuration Name"
              initialValue={editingConfig?.name || ""}
              onChange={setName}
              required
              placeholder="e.g., Tech Enthusiasts 25-34"
            />
            <CommonInput
              key={`description-${editingConfig?.id || 'new'}-${isOpen}`}
              label="Description (Optional)"
              initialValue={editingConfig?.description || ""}
              onChange={setDescription}
              placeholder="Brief description of this targeting configuration"
            />
          </div>

          <div className="targeting-config-modal__targeting-fields">
            <h3>Targeting Options</h3>
            <div className="targeting-config-modal__fields-grid">
              <MultiSelect
                label="Age Range"
                options={AGE_RANGE_OPTIONS}
                selectedValues={targetingConfig.age_range}
                onChange={(values) => updateTargetingField('age_range', values)}
              />
              <MultiSelect
                label="Gender"
                options={GENDER_OPTIONS}
                selectedValues={targetingConfig.gender}
                onChange={(values) => updateTargetingField('gender', values)}
              />
              <MultiSelect
                label="Income Level"
                options={INCOME_LEVEL_OPTIONS}
                selectedValues={targetingConfig.income_level}
                onChange={(values) => updateTargetingField('income_level', values)}
              />
              <MultiSelect
                label="Location"
                options={LOCATION_OPTIONS}
                selectedValues={targetingConfig.location}
                onChange={(values) => updateTargetingField('location', values)}
              />
              <MultiSelect
                label="Interests"
                options={INTERESTS_OPTIONS}
                selectedValues={targetingConfig.interests}
                onChange={(values) => updateTargetingField('interests', values)}
              />
              <MultiSelect
                label="Behavioral Data"
                options={BEHAVIORAL_DATA_OPTIONS}
                selectedValues={targetingConfig.behavioral_data}
                onChange={(values) => updateTargetingField('behavioral_data', values)}
              />
            </div>
          </div>

          {error && (
            <div className="targeting-config-modal__error">
              {error}
            </div>
          )}

          <div className="targeting-config-modal__actions">
            <div className="button-container">
              <CommonButton type="button" onClick={onClose} disabled={isSubmitting}>
                Cancel
              </CommonButton>
              <CommonButton
                type="button"
                onClick={handleSubmit}
                disabled={isSubmitting}
              >
                {isSubmitting ? 'Saving...' : (editingConfig ? 'Update Configuration' : 'Create Configuration')}
              </CommonButton>
            </div>
          </div>
        </form>
      </div>
    </div>
  );
}
