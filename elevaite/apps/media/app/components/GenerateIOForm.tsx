import type { CommonSelectOption } from "@repo/ui/components";
import {ChatbotIcons, CommonButton, CommonInput, CommonSelect, CommonFormLabels, ElevaiteIcons } from "@repo/ui/components";
import { useState, useEffect, useCallback } from "react";
import { useSession } from "next-auth/react";
import "./GenerateIOForm.scss";
import type { GenerateIOFormProps, PlacementData, TargetingConfiguration } from "../lib/interfaces";
import { IODestination } from "../lib/interfaces";
import { TargetingConfigSelector } from "./TargetingConfigSelector";
import {
  fetchSalesforceAccounts,
  fetchSalesforceOpportunitiesByAccount,
  salesforceAccountsToSelectOptions,
  salesforceOpportunitiesToSelectOptions,
  getAccountSearchFields
} from "../lib/salesforceApi";
import { TargetingConfigurationAPI, getCurrentUserId } from "../lib/targetingConfigApi";
import { SearchableSelect } from "./SearchableSelect";


//Helper function for recomputing from Budget
function recomputeFromBudget(p: PlacementData) {
  const budget = Number(p.Budget?.Amount || 0);
  const cpm    = Number(p.BidRate?.CPM || 0);
  const ctrPct = Number((p as any)?.Metrics?.CTR || 0); // CTR is percent, e.g. 2.5

  // Target Impressions = (Budget × 1000) ÷ CPM
  const impressions = Math.floor((budget * 1000) / cpm);

  // Target Clicks = (CTR × Target Impressions) ÷ 100
  const clicks = Math.floor((ctrPct * impressions) / 100);

  return { impressions, clicks };
}

// No longer need individual targeting options - using targeting configurations instead

export function GenerateIOForm({ initialData, onClose, onSubmit, selectedDestination, onBack }: GenerateIOFormProps): JSX.Element {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const { data: session } = useSession();

  // Get current user info from session
  const currentUserEmail = session?.user?.email || "vishnu.krishnan@iopex.com";
  const currentUserName = session?.user?.name || "Vishnu Krishnan";

  // Mock data for prefill - using logged-in user for sales owner
  const mockData = {
    customerApprover: "Vishnu Krishnan",
    customerApproverEmail: "vishnu.krishnan@iopex.com",
    salesOwner: currentUserName,
    salesOwnerEmail: currentUserEmail,
    fulfillmentOwner:currentUserName,
    fulfillmentOwnerEmail: currentUserEmail
  };

  // Form submit handler
  const generateRandomOrderNo = (): string => {
    const timestamp = Date.now().toString().slice(-6);
    const random = Math.floor(Math.random() * 10000).toString().padStart(4, '0');
    return `IO-${timestamp}-${random}`;
  };

  const [orderNo, setOrderNo] = useState(initialData?.OrderNo || generateRandomOrderNo());
  const [brand, setBrand] = useState(initialData?.Brand || "");
  const [campaignName, setCampaignName] = useState(initialData?.CampaignName || "");
  const [customerApprover, setCustomerApprover] = useState(initialData?.CustomerApprover || mockData.customerApprover);
  const [customerApproverEmail, setCustomerApproverEmail] = useState(initialData?.CustomerApproverEmail || mockData.customerApproverEmail);
  const [salesOwner, setSalesOwner] = useState(initialData?.SalesOwner || mockData.salesOwner);
  const [salesOwnerEmail, setSalesOwnerEmail] = useState(initialData?.SalesOwnerEmail || mockData.salesOwnerEmail);
  const [fulfillmentOwner, setFulfillmentOwner] = useState(initialData?.FulfillmentOwner || mockData.fulfillmentOwner);
  const [fulfillmentOwnerEmail, setFulfillmentOwnerEmail] = useState(initialData?.FulfillmentOwnerEmail || mockData.fulfillmentOwnerEmail);
  const [creativeInspirationLink, setCreativeInspirationLink] = useState(initialData?.CreativeInspirationLink || "");

  // Salesforce-specific state
  const [salesforceAccount, setSalesforceAccount] = useState(initialData?.SalesforceAccount || "");
  const [salesforceAccountName, setSalesforceAccountName] = useState(""); // Store account name for Brand field
  const [salesforceOpportunityId, setSalesforceOpportunityId] = useState(initialData?.SalesforceOpportunityId || "");
  const [salesforceAccounts, setSalesforceAccounts] = useState<CommonSelectOption[]>([]);
  const [salesforceOpportunities, setSalesforceOpportunities] = useState<CommonSelectOption[]>([]);
  const [loadingSalesforceData, setLoadingSalesforceData] = useState(false);
  const [placements, setPlacements] = useState<PlacementData[]>(initialData?.Placement || [{
    Name: "",
    Destination: "",
    StartDate: initialData?.StartDate || "",
    EndDate: initialData?.EndDate || "",
    ConvertToCampaign: false, // Default to false for new placements
    Metrics: {
      Impressions: initialData?.Metrics?.Impressions || 0,
      Clicks: initialData?.Metrics?.Clicks || 0
    },
    BidRate: {
      CPM: initialData?.BidRate?.CPM || 0,
      CPC: initialData?.BidRate?.CPC || 0
    },
    Budget: {
      Amount: initialData?.Budget?.Amount || 0
    },
    targeting_configuration_id: undefined // Will be set when user selects a targeting configuration
  }]);

  const [objectiveDescription, setObjectiveDescription] = useState(initialData?.ObjectiveDetails?.Description || "");
  const [error, setError] = useState<string | null>(null);

  // Campaign-level targeting configuration state
  const [campaignTargetingConfigId, setCampaignTargetingConfigId] = useState<string | undefined>(undefined);
  const [campaignTargetingConfigName, setCampaignTargetingConfigName] = useState<string | undefined>(undefined);
  const [campaignTargetingConfigDescription, setCampaignTargetingConfigDescription] = useState<string | undefined>(undefined);

  // State to track which placements are collapsed (true = collapsed, false = expanded)
  const [placementCollapsed, setPlacementCollapsed] = useState<boolean[]>(
    initialData?.Placement ? initialData.Placement.map(() => false) : [false]
  );

  // State to track if target overview section is collapsed
  const [targetOverviewCollapsed, setTargetOverviewCollapsed] = useState(false);

  // Shared targeting configurations state to prevent multiple API calls
  const [sharedTargetingConfigs, setSharedTargetingConfigs] = useState<TargetingConfiguration[]>([]);
  const [targetingConfigsLoading, setTargetingConfigsLoading] = useState(true);
  const [targetingConfigsError, setTargetingConfigsError] = useState<string | null>(null);

  // Function to load targeting configurations
  const loadTargetingConfigurations = useCallback(async () => {
    try {
      setTargetingConfigsLoading(true);
      setTargetingConfigsError(null);
      const userId = getCurrentUserId();
      const configs = await TargetingConfigurationAPI.getConfigurations(userId);

      // Smart ordering: Recently created configurations first, then alphabetical
      const sortedConfigs = configs.sort((a, b) => {
        const dateA = new Date(a.created_at).getTime();
        const dateB = new Date(b.created_at).getTime();
        if (dateB !== dateA) {
          return dateB - dateA;
        }
        return a.name.localeCompare(b.name);
      });

      setSharedTargetingConfigs(sortedConfigs);
    } catch (error) {
      console.error('Error loading targeting configurations:', error);
      setTargetingConfigsError(error instanceof Error ? error.message : 'Failed to load targeting configurations');
    } finally {
      setTargetingConfigsLoading(false);
    }
  }, []);

  // Load targeting configurations once for the entire form
  useEffect(() => {
    loadTargetingConfigurations();
  }, [loadTargetingConfigurations]);

  // Load Salesforce data when destination is Salesforce
  // Load Salesforce accounts when Salesforce destination is selected
  useEffect(() => {
    if (selectedDestination === IODestination.SALESFORCE) {
      setLoadingSalesforceData(true);

      fetchSalesforceAccounts()
        .then((accounts) => {
          const accountOptions = salesforceAccountsToSelectOptions(accounts);
          setSalesforceAccounts(accountOptions);

          // If there's a pre-selected account, find and set its name
          if (salesforceAccount) {
            const selectedAccount = accountOptions.find(account => account.value === salesforceAccount);
            if (selectedAccount && selectedAccount.label) {
              setSalesforceAccountName(selectedAccount.label);
            }
          }
        })
        .catch((error) => {
          console.error('Error loading Salesforce accounts:', error);
        })
        .finally(() => {
          setLoadingSalesforceData(false);
        });
    }
  }, [selectedDestination, salesforceAccount]);

  // Load opportunities when a Salesforce account is selected
  useEffect(() => {
    if (selectedDestination === IODestination.SALESFORCE && salesforceAccount) {
      setLoadingSalesforceData(true);

      fetchSalesforceOpportunitiesByAccount(salesforceAccount)
        .then((opportunities) => {
          setSalesforceOpportunities(salesforceOpportunitiesToSelectOptions(opportunities));
        })
        .catch((error) => {
          console.error('Error loading Salesforce opportunities for account:', error);
          setSalesforceOpportunities([]); // Clear opportunities on error
        })
        .finally(() => {
          setLoadingSalesforceData(false);
        });
    } else if (selectedDestination === IODestination.SALESFORCE && !salesforceAccount) {
      // Clear opportunities when no account is selected
      setSalesforceOpportunities([]);
      setSalesforceOpportunityId('');
      setSalesforceAccountName(''); // Clear account name as well
    }
  }, [selectedDestination, salesforceAccount]);

  // Helper function to handle account selection and update account name
  const handleAccountSelection = (accountId: string) => {
    setSalesforceAccount(accountId);

    // Find the account name from the loaded accounts
    const selectedAccount = salesforceAccounts.find(account => account.value === accountId);
    if (selectedAccount && selectedAccount.label) {
      setSalesforceAccountName(selectedAccount.label);
    } else {
      setSalesforceAccountName('');
    }
  };

  // Enhanced function to create targeting configuration with robust deduplication
  const createTargetingConfigurationSafely = async (
    targetingConfig: any,
    name: string,
    description: string,
    userId: string,
    TargetingConfigurationAPI: any
  ) => {
    try {
      // Get all existing configurations
      const configs = await TargetingConfigurationAPI.getConfigurations(userId);

      // Normalize targeting config for comparison (sort arrays and stringify consistently)
      const normalizeConfig = (config: any) => {
        const normalized = { ...config };
        Object.keys(normalized).forEach(key => {
          if (Array.isArray(normalized[key])) {
            normalized[key] = [...normalized[key]].sort();
          }
        });
        return JSON.stringify(normalized);
      };

      const normalizedNewConfig = normalizeConfig(targetingConfig);

      // Check for exact match
      const existingConfig = configs.find(config =>
        normalizeConfig(config.targeting_config) === normalizedNewConfig
      );

      if (existingConfig) {
        console.log("Found existing targeting configuration with identical data:", existingConfig);
        return existingConfig;
      }

      // Check for similar name to avoid near-duplicates
      const similarNameConfig = configs.find(config =>
        config.name.toLowerCase() === name.toLowerCase()
      );

      if (similarNameConfig) {
        console.log("Found configuration with similar name, using unique suffix");
        name = `${name} (${new Date().getTime()})`;
      }

      // Create new configuration
      const newConfig = await TargetingConfigurationAPI.createConfiguration(userId, {
        name,
        description,
        targeting_config: targetingConfig
      });

      console.log("Created new targeting configuration:", newConfig);
      return newConfig;

    } catch (error) {
      console.error('Error in createTargetingConfigurationSafely:', error);
      throw error;
    }
  };

  // Process targeting configuration information from AI suggestions
  useEffect(() => {
    const processTargetingConfiguration = async () => {
      if (!initialData?.Placement) return;

      try {
        // Import the targeting configuration API
        const { TargetingConfigurationAPI, getCurrentUserId } = await import("../lib/targetingConfigApi");
        const userId = getCurrentUserId();

        // Track processed configurations to prevent duplicates
        const processedConfigs = new Set<string>();
        let primaryConfigSet = false;

        for (const placement of initialData.Placement) {
          // Handle existing targeting configuration ID
          if (placement.targeting_configuration_id && !primaryConfigSet) {
            try {
              const configs = await TargetingConfigurationAPI.getConfigurations(userId);
              const selectedConfig = configs.find(config => config.id === placement.targeting_configuration_id);

              if (selectedConfig) {
                console.log("Auto-selecting existing targeting configuration:", selectedConfig);
                handleCampaignTargetingChange(
                  placement.targeting_configuration_id,
                  selectedConfig.name,
                  selectedConfig.description
                );
                primaryConfigSet = true;
              }
            } catch (error) {
              console.error('Error fetching targeting configuration details:', error);
            }
          }

          // Handle multiple targeting options (enhanced system)
          if (placement.targeting_options && placement.targeting_options.length > 0 && !primaryConfigSet) {
            console.log(`Processing ${placement.targeting_options.length} targeting configuration options...`);

            // Process all targeting options and create configurations
            const createdConfigs: Array<{id: string, name?: string, description?: string, is_primary: boolean}> = [];

            for (const option of placement.targeting_options) {
              const configKey = option.targeting_configuration_id ||
                JSON.stringify(option.new_targeting_configuration);

              // Skip if already processed
              if (processedConfigs.has(configKey)) {
                continue;
              }

              if (option.targeting_configuration_id) {
                // Existing configuration - just mark as processed
                processedConfigs.add(configKey);
                createdConfigs.push({ id: option.targeting_configuration_id, is_primary: option.is_primary });
              } else if (option.new_targeting_configuration) {
                try {
                  const configName = option.new_targeting_configuration_name ||
                    `AI Generated - ${new Date().toLocaleDateString()}`;
                  const configDescription = option.new_targeting_configuration_description ||
                    "Targeting configuration generated by AI media plan";

                  const newConfig = await createTargetingConfigurationSafely(
                    option.new_targeting_configuration,
                    configName,
                    configDescription,
                    userId,
                    TargetingConfigurationAPI
                  );

                  processedConfigs.add(configKey);
                  createdConfigs.push({ id: newConfig.id, name: newConfig.name, description: newConfig.description, is_primary: option.is_primary });
                } catch (error) {
                  console.error('Error creating targeting configuration for option:', error);
                }
              }
            }

            // Set the primary configuration as campaign-level targeting
            const primaryConfig = createdConfigs.find(config => config.is_primary) || createdConfigs[0];
            if (primaryConfig) {
              handleCampaignTargetingChange(primaryConfig.id, primaryConfig.name, primaryConfig.description);
              primaryConfigSet = true;
            }
          }

          // Fallback: Handle legacy single targeting configuration
          else if (placement.new_targeting_configuration && !primaryConfigSet) {
            const configKey = JSON.stringify(placement.new_targeting_configuration);

            if (!processedConfigs.has(configKey)) {
              try {
                console.log("Processing legacy new targeting configuration from AI...");

                const configName = placement.new_targeting_configuration_name ||
                  `AI Generated - ${new Date().toLocaleDateString()}`;
                const configDescription = placement.new_targeting_configuration_description ||
                  "Targeting configuration generated by AI media plan";

                const newConfig = await createTargetingConfigurationSafely(
                  placement.new_targeting_configuration,
                  configName,
                  configDescription,
                  userId,
                  TargetingConfigurationAPI
                );

                processedConfigs.add(configKey);
                handleCampaignTargetingChange(newConfig.id, newConfig.name, newConfig.description);
                primaryConfigSet = true;
              } catch (error) {
                console.error('Error creating targeting configuration:', error);
              }
            }
          }
        }
      } catch (error) {
        console.error('Error importing targeting configuration API:', error);
      }
    };

    processTargetingConfiguration();
  }, [initialData]);

  // Ensure placements inherit campaign targeting configuration when it's set
  useEffect(() => {
    if (campaignTargetingConfigId && placements.length > 0) {
      // Check if any placements don't have the campaign targeting configuration
      const needsUpdate = placements.some(placement =>
        placement.targeting_configuration_id !== campaignTargetingConfigId
      );

      if (needsUpdate) {
        console.log("Propagating campaign targeting configuration to placements:", campaignTargetingConfigId);
        setPlacements(placements.map(placement => ({
          ...placement,
          targeting_configuration_id: campaignTargetingConfigId
        })));
      }
    }
  }, [campaignTargetingConfigId, placements.length]); // Only depend on the ID and placement count, not the full placements array

  // Helper function to propagate campaign targeting to all placements
  const propagateCampaignTargeting = (configId: string | undefined) => {
    setPlacements(placements.map(placement => ({
      ...placement,
      targeting_configuration_id: configId
    })));
  };

  // Handler for campaign-level targeting configuration changes
  const handleCampaignTargetingChange = (configId: string | undefined, configName?: string, configDescription?: string) => {
    setCampaignTargetingConfigId(configId);
    setCampaignTargetingConfigName(configName);
    setCampaignTargetingConfigDescription(configDescription);
    // Automatically apply to all existing placements
    propagateCampaignTargeting(configId);
    // Auto-collapse the target overview section when a configuration is selected
    if (configId) {
      setTargetOverviewCollapsed(true);
    }
  };

  // Check if placements have custom targeting configurations
  const hasCustomTargeting = () => {
    return placements.some(placement =>
      placement.targeting_configuration_id !== campaignTargetingConfigId
    );
  };

  // Get targeting status description
  const getTargetingStatusDescription = () => {
    if (!campaignTargetingConfigId) {
      return "No campaign-level targeting configuration selected";
    }

    const customPlacements = placements.filter(placement =>
      placement.targeting_configuration_id !== campaignTargetingConfigId
    );

    if (customPlacements.length === 0) {
      return `All placements using campaign-level configuration: ${campaignTargetingConfigName}`;
    } else if (customPlacements.length === placements.length) {
      return "All placements have custom targeting configurations";
    } else {
      return `${placements.length - customPlacements.length} placement(s) using campaign-level, ${customPlacements.length} with custom targeting`;
    }
  };

  // Handler for toggling target overview section
  const toggleTargetOverviewCollapsed = () => {
    setTargetOverviewCollapsed(!targetOverviewCollapsed);
  };

  // Custom targeting config selector for campaign level that uses shared state
  const CampaignTargetingConfigSelector = () => {
    const handleConfigSelect = (configId: string | undefined) => {
      const selectedConfig = sharedTargetingConfigs.find(config => config.id === configId);
      handleCampaignTargetingChange(configId, selectedConfig?.name, selectedConfig?.description);
    };

    return (
      <TargetingConfigSelector
        selectedConfigId={campaignTargetingConfigId}
        onConfigSelect={handleConfigSelect}
        label="Campaign Targeting Configuration"
        // Pass shared state to prevent additional API calls
        configurations={sharedTargetingConfigs}
        isLoading={targetingConfigsLoading}
        error={targetingConfigsError}
        onConfigurationCreated={loadTargetingConfigurations}
      />
    );
  };

  // Placement handlers
  const addPlacement = () => {
    setPlacements([...placements, {
      Name: "",
      Destination: "",
      StartDate: "",
      EndDate: "",
      ConvertToCampaign: false, // Default to false for new placements
      Metrics: { Impressions: 0, Clicks: 0 },
      BidRate: { CPM: 0, CPC: 0 },
      Budget: { Amount: 0 },
      targeting_configuration_id: campaignTargetingConfigId // Inherit campaign-level configuration
    }]);
    // Add collapsed state for new placement (default to expanded)
    setPlacementCollapsed([...placementCollapsed, false]);
  };

  const removePlacement = (index: number) => {
    setPlacements(placements.filter((_, i) => i !== index));
    setPlacementCollapsed(placementCollapsed.filter((_, i) => i !== index));
  };

  const togglePlacementCollapsed = (index: number) => {
    setPlacementCollapsed(placementCollapsed.map((collapsed, i) =>
      i === index ? !collapsed : collapsed
    ));
  };

  const updatePlacement = (index: number, field: keyof PlacementData, value: any) => {
  setPlacements(prev =>
    prev.map((p, i) => {
      if (i !== index) return p;

      const next = { ...p } as PlacementData;
      (next as any)[field] = value;

      // live-recompute only when user changes Budget or CPM (BidRate)
      if (field === "Budget" || field === "BidRate") {
        const { impressions, clicks } = recomputeFromBudget(next);
        next.Metrics = { ...next.Metrics, Impressions: impressions, Clicks: clicks };
      }

      return next;
      })
    );
  };

  // Helper function to get targeting configuration data by ID
  const getTargetingConfigData = async (configId: string) => {
    try {
      const { TargetingConfigurationAPI, getCurrentUserId } = await import("../lib/targetingConfigApi");
      const userId = getCurrentUserId();
      const config = await TargetingConfigurationAPI.getConfiguration(configId, userId);
      return config.targeting_config;
    } catch (error) {
      console.error('Error fetching targeting configuration:', error);
      return null;
    }
  };

  // Validation
  function validate(): string | null {
    // Check common required fields
    if (!orderNo || !campaignName ||
        !customerApprover || !customerApproverEmail ||
        !salesOwner || !salesOwnerEmail ||
        !fulfillmentOwner || !fulfillmentOwnerEmail) {
      return "Please fill in all required fields.";
    }

    // Check destination-specific required fields
    if (selectedDestination === IODestination.SALESFORCE) {
      if (!salesforceAccount || !salesforceOpportunityId) {
        return "Please select both Salesforce Account and Opportunity ID.";
      }
    } else {
      if (!brand) {
        return "Please fill in the Brand field.";
      }
    }

    if (!placements.length) {
      return "Please add at least one placement.";
    }

    for (let i = 0; i < placements.length; i++) {
      const p = placements[i];
      if (!p.Name || !p.Destination) {
        return `Please fill in Name and Destination for Placement ${i + 1}.`;
      }
      if (!p.StartDate || !p.EndDate) {
        return `Please fill in Start Date and End Date for Placement ${i + 1}.`;
      }
      if (!p.Metrics.Impressions || !p.Budget.Amount) {
        return `Please fill in Impressions and Budget Amount for Placement ${i + 1}.`;
      }
      // Check if targeting is configured either at campaign level or placement level
      if (!campaignTargetingConfigId && !p.targeting_configuration_id) {
        return `Please select a targeting configuration either at campaign level or for Placement ${i + 1}.`;
      }
    }


    return null;
  }

  // Form submit handler
  const handleSubmit = async (e: React.MouseEvent) => {
    e.preventDefault();

    const validationError = validate();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);

    try {
      // Fetch targeting configuration data for each placement
      const { TargetingConfigurationAPI, getCurrentUserId } = await import("../lib/targetingConfigApi");
      const userId = getCurrentUserId();

      const placementsWithTargeting = await Promise.all(
        placements.filter(p => p.Name && p.Destination).map(async (placement) => {
          if (placement.targeting_configuration_id) {
            try {
              const config = await TargetingConfigurationAPI.getConfiguration(placement.targeting_configuration_id, userId);
              return {
                ...placement,
                new_targeting_configuration: config.targeting_config
              };
            } catch (error) {
              console.error('Error fetching targeting configuration:', error);
              return placement;
            }
          }
          return placement;
        })
      );

      // Debug: Log the destination and form data being sent
      console.log('🔍 FRONTEND FORM SUBMISSION:');
      console.log('   selectedDestination:', selectedDestination);
      console.log('   IODestination.SALESFORCE:', IODestination.SALESFORCE);
      console.log('   Is Salesforce?:', selectedDestination === IODestination.SALESFORCE);
      console.log('   salesforceAccount:', salesforceAccount);
      console.log('   salesforceOpportunityId:', salesforceOpportunityId);
      console.log('   brand:', brand);

      const formData = {
        OrderNo: orderNo,
        ...(selectedDestination === IODestination.SALESFORCE
          ? {
              SalesforceAccount: salesforceAccount,
              SalesforceOpportunityId: salesforceOpportunityId,
              Brand: salesforceAccountName || "Unknown Account" // Use account name as Brand
            }
          : {
              Brand: brand
            }
        ),
        CampaignName: campaignName,
        CustomerApprover: customerApprover,
        CustomerApproverEmail: customerApproverEmail,
        SalesOwner: salesOwner,
        SalesOwnerEmail: salesOwnerEmail,
        FulfillmentOwner: fulfillmentOwner,
        FulfillmentOwnerEmail: fulfillmentOwnerEmail,
        Placement: placementsWithTargeting,
        ObjectiveDetails: { Description: objectiveDescription },
        // Include media plan content if available
        MediaPlanContent: initialData?.MediaPlanContent,
        // Include creative inspiration link if provided
        CreativeInspirationLink: creativeInspirationLink
      };

      console.log("🔍 FINAL FORM DATA BEING SENT:");
      console.log("   Full formData:", formData);
      console.log("   SalesforceAccount in formData:", (formData as any).SalesforceAccount);
      console.log("   SalesforceOpportunityId in formData:", (formData as any).SalesforceOpportunityId);
      console.log("   Brand in formData:", (formData as any).Brand);
      console.log("   salesforceAccountName:", salesforceAccountName);

      // Close modal immediately after validation passes
      onClose();

      // Note: The backend API call is now handled in the parent component
      if (onSubmit) {
        // We need to cast formData to any because the expected type is OrderGenerationResponse
        // but the actual implementation in createInsertionOrder handles this correctly
        await onSubmit(formData as any);
      }
    } catch (error) {
      console.error('Error submitting form:', error);
      setError('Failed to submit form. Please try again.');
      setIsSubmitting(false);
    }
  };

  return (
    <div className="generate-io-form-modal">
      {/* Header */}
      <div className="generate-io-header">
        <div className="generate-io-header__left">
          {onBack && (
            <button className="generate-io-header__back" onClick={onBack} aria-label="Back to destination selection">
              <ElevaiteIcons.SVGArrowBack />
            </button>
          )}
          <span className="generate-io-header__icon">
            <ElevaiteIcons.SVGRegister />
          </span>
        </div>
        <div className="generate-io-header__title-section">
          <span className="generate-io-header__title">Generate IO</span>
          {selectedDestination && (
            <span className="generate-io-header__destination-tag">
              {selectedDestination === IODestination.GOOGLE_WORKSPACE ? 'Google Workspace' : 'Salesforce'}
            </span>
          )}
        </div>
        <button className="generate-io-header__close" onClick={onClose} aria-label="Close">
          <ElevaiteIcons.SVGXmark/>
        </button>
      </div>

      {/* Scrollable Form Content */}
      <div className="generate-io-form__content" id="generate-io-form__content">
        {error && <div className="generate-io-form__error ">{error}</div>}

        {/* Campaign Overview Section */}
        <div className="generate-io-form__section generate-io-form__section--campaign">
          <div className="generate-io-form__section-header">
            <span className="generate-io-form__section-icon"><ElevaiteIcons.SVGDatasets /></span>
            <h3 className="generate-io-form__section-title">Campaign Overview</h3>
          </div>
          <div className="generate-io-form__section-content">
            <div className="generate-io-form-fields">
              {selectedDestination === IODestination.SALESFORCE ? (
                <>
                  <CommonFormLabels
                    label="Salesforce Account"
                    required
                  >
                    <SearchableSelect
                      options={salesforceAccounts}
                      value={salesforceAccount}
                      onValueChange={handleAccountSelection}
                      placeholder={loadingSalesforceData ? "Loading accounts..." : "Select an account"}
                      disabled={loadingSalesforceData}
                      isLoading={loadingSalesforceData}
                      searchPlaceholder="Type to search accounts..."
                      noResultsMessage="No accounts found matching your search"
                      searchFields={getAccountSearchFields}
                    />
                  </CommonFormLabels>
                  <CommonFormLabels
                    label="Opportunity ID"
                    required
                  >
                    <CommonSelect
                      options={salesforceOpportunities}
                      controlledValue={salesforceOpportunityId}
                      onSelectedValueChange={(value) => setSalesforceOpportunityId(value)}
                      noSelectionMessage={
                        loadingSalesforceData
                          ? "Loading opportunities..."
                          : !salesforceAccount
                            ? "Select an account first"
                            : salesforceOpportunities.length === 0
                              ? "No opportunities found for this account"
                              : "Select an opportunity"
                      }
                      disabled={loadingSalesforceData || !salesforceAccount}
                      useCommonStyling
                    />
                  </CommonFormLabels>
                </>
              ) : (
                <CommonInput label="Brand" initialValue={brand} onChange={setBrand} required />
              )}
              <CommonInput label="Campaign Name" initialValue={campaignName} onChange={setCampaignName} required />
            </div>
            <div className="generate-io-form-fields single-column">
              <CommonInput label="Objective Description" initialValue={objectiveDescription} onChange={setObjectiveDescription}/>
              <CommonInput label="Creative Inspiration Link" initialValue={creativeInspirationLink} onChange={setCreativeInspirationLink} placeholder="https://example.com/creative-inspiration"/>
              <CommonInput label="Order No" initialValue={orderNo} onChange={setOrderNo} required />
            </div>
          </div>
        </div>
        
                {/* Target Overview Section */}
        <div className={[
          "generate-io-form__section",
          "generate-io-form__section--target",
          targetOverviewCollapsed ? "collapsed" : undefined
        ].filter(Boolean).join(" ")}>
          <div
            className="generate-io-form__section-header"
            onClick={toggleTargetOverviewCollapsed}
            style={{ cursor: 'pointer' }}
          >
            <span
              className={[
                "generate-io-form__collapse-toggle",
                targetOverviewCollapsed ? "collapsed" : undefined
              ].filter(Boolean).join(" ")}
              aria-label={targetOverviewCollapsed ? "Expand target overview" : "Collapse target overview"}
            >
              <ElevaiteIcons.SVGChevron />
            </span>
            <span className="generate-io-form__section-icon"><ElevaiteIcons.SVGTarget /></span>
            <h3 className="generate-io-form__section-title">Targeting Recommendation</h3>
          </div>

          {/* Show selected configuration when collapsed */}
          {targetOverviewCollapsed && (
            <div className="generate-io-form__section-content generate-io-form__section-content--collapsed">
              <div className="generate-io-form__subsection">
                {campaignTargetingConfigName ? (
                  <div className="generate-io-form__selected-config">
                    <div className="generate-io-form__selected-config-header">
                      <span className="generate-io-form__selected-config-label">Campaign Configuration:</span>
                      <span className="generate-io-form__selected-config-name">{campaignTargetingConfigName}</span>
                    </div>
                    {campaignTargetingConfigDescription && (
                      <div className="generate-io-form__selected-config-description">
                        {campaignTargetingConfigDescription}
                      </div>
                    )}
                    {/* Show targeting status */}
                    <div className="generate-io-form__targeting-status">
                      <span className="generate-io-form__targeting-status-label">Status:</span>
                      <span className={`generate-io-form__targeting-status-text ${hasCustomTargeting() ? 'custom' : 'uniform'}`}>
                        {getTargetingStatusDescription()}
                      </span>
                    </div>
                  </div>
                ) : (
                  <div className="generate-io-form__selected-config generate-io-form__selected-config--empty">
                    <span className="generate-io-form__selected-config-label">No targeting configuration selected</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {!targetOverviewCollapsed && (
            <div className="generate-io-form__section-content">
              <div className="generate-io-form__subsection">
                <h4 className="generate-io-form__subsection-title">Campaign-Level Targeting</h4>
                <p className="generate-io-form__subsection-description">
                  Select a targeting configuration that will be applied to all placements in this campaign.
                  Individual placements can override this configuration if needed.
                </p>
                <div className="generate-io-form-fields">
                  <CampaignTargetingConfigSelector key={campaignTargetingConfigId || 'no-config'} />
                </div>
              </div>
            </div>
          )}
        </div>


        {/* Contact Information Section */}
        <div className="generate-io-form__section generate-io-form__section--contact">
          <div className="generate-io-form__section-header">
            <span className="generate-io-form__section-icon"><ElevaiteIcons.SVGUser /></span>
            <h3 className="generate-io-form__section-title">Contact Information</h3>
          </div>
          <div className="generate-io-form__section-content">
            <div className="generate-io-form__contact-group">
              <h4 className="generate-io-form__contact-group-title">Customer Approver</h4>
              <div className="generate-io-form-fields">
                <CommonInput label="Name" initialValue={customerApprover} onChange={setCustomerApprover} required />
                <CommonInput label="Email" initialValue={customerApproverEmail} onChange={setCustomerApproverEmail} required />
              </div>
            </div>

            <div className="generate-io-form__contact-group">
              <h4 className="generate-io-form__contact-group-title">Sales Owner</h4>
              <div className="generate-io-form-fields">
                <CommonInput label="Name" initialValue={salesOwner} onChange={setSalesOwner} required />
                <CommonInput label="Email" initialValue={salesOwnerEmail} onChange={setSalesOwnerEmail} required />
              </div>
            </div>

            <div className="generate-io-form__contact-group">
              <h4 className="generate-io-form__contact-group-title">Fulfillment Owner</h4>
              <div className="generate-io-form-fields">
                <CommonInput label="Name" initialValue={fulfillmentOwner} onChange={setFulfillmentOwner} required />
                <CommonInput label="Email" initialValue={fulfillmentOwnerEmail} onChange={setFulfillmentOwnerEmail} required />
              </div>
            </div>
          </div>
        </div>


        {/* Placements */}
        <div className="generate-io-form__placements">
          {placements.map((placement, idx) => (
            <div key={idx} className={[
              "generate-io-form__section",
              "generate-io-form__section--placement",
              placementCollapsed[idx] ? "collapsed" : undefined
            ].filter(Boolean).join(" ")}>
              <div
                className="generate-io-form__section-header"
                onClick={() => togglePlacementCollapsed(idx)}
              >
                <span
                  className={[
                    "generate-io-form__collapse-toggle",
                    placementCollapsed[idx] ? "collapsed" : undefined
                  ].filter(Boolean).join(" ")}
                  aria-label={placementCollapsed[idx] ? "Expand placement" : "Collapse placement"}
                >
                  <ElevaiteIcons.SVGChevron />
                </span>
                <span className="generate-io-form__section-icon"><ElevaiteIcons.SVGAccounts /></span>
                <h3 className="generate-io-form__section-title">Placement {idx + 1}</h3>
                {placements.length > 1 && (
                  <button
                    type="button"
                    className="generate-io-form__remove-placement"
                    onClick={(e) => {
                      e.stopPropagation();
                      removePlacement(idx);
                    }}
                    aria-label="Remove placement"
                  >
                    <ElevaiteIcons.SVGXmark />
                  </button>
                )}
              </div>

              {/* Always show Name and Destination when collapsed */}
              {placementCollapsed[idx] && (
                <div className="generate-io-form__section-content generate-io-form__section-content--collapsed">
                  <div className="generate-io-form__subsection">
                    <div className="generate-io-form-fields">
                      <CommonInput
                        label="Name"
                        initialValue={placement.Name}
                        onChange={value => updatePlacement(idx, "Name", value)}
                        required
                      />
                      <CommonInput
                        label="Destination"
                        initialValue={placement.Destination}
                        onChange={value => updatePlacement(idx, "Destination", value)}
                        required
                      />
                    </div>
                  </div>
                </div>
              )}

              {!placementCollapsed[idx] && (
                <div className="generate-io-form__section-content">
                {/* Basic Info */}
                <div className="generate-io-form__subsection">
                  <h4 className="generate-io-form__subsection-title">Basic Information</h4>
                  <div className="generate-io-form-fields">
                    <CommonInput
                      label="Name"
                      initialValue={placement.Name}
                      onChange={value => updatePlacement(idx, "Name", value)}
                      required
                    />
                    <CommonInput
                      label="Destination"
                      initialValue={placement.Destination}
                      onChange={value => updatePlacement(idx, "Destination", value)}
                      required
                    />
                  </div>
                  <div className="generate-io-form-fields">
                    <div className="generate-io-form__checkbox-field">
                      <label className="generate-io-form__checkbox-label">
                        <input
                          type="checkbox"
                          checked={placement.ConvertToCampaign || false}
                          onChange={(e) => updatePlacement(idx, "ConvertToCampaign", e.target.checked)}
                          className="generate-io-form__checkbox"
                        />
                        <span className="generate-io-form__checkbox-text">
                           Launch this placement as its own campaign
                        </span>
                      </label>
                    </div>
                  </div>
                </div>

                {/* Campaign Period */}
                <div className="generate-io-form__subsection">
                  <h4 className="generate-io-form__subsection-title">Campaign Period</h4>
                  <div className="generate-io-form-fields">
                    <CommonInput
                      label="Start Date"
                      initialValue={placement.StartDate}
                      onChange={value => updatePlacement(idx, "StartDate", value)}
                      required
                    />
                    <CommonInput
                      label="End Date"
                      initialValue={placement.EndDate}
                      onChange={value => updatePlacement(idx, "EndDate", value)}
                      required
                    />
                  </div>
                </div>

                {/* Performance Metrics */}
                <div className="generate-io-form__subsection">
                  <h4 className="generate-io-form__subsection-title">Performance Metrics</h4>
                  <div className="generate-io-form-fields">
                    <CommonInput
                      label="Impressions"
                      controlledValue={placement.Metrics.Impressions.toString()}
                      onChange={value => updatePlacement(idx, "Metrics", { ...placement.Metrics, Impressions: Number(value) })}
                      required
                    />
                    <CommonInput
                      label="Clicks"
                      controlledValue={placement.Metrics.Clicks.toString()}
                      onChange={value => updatePlacement(idx, "Metrics", { ...placement.Metrics, Clicks: Number(value)})}
                    />
                  </div>
                </div>

                {/* Budget & Pricing */}
                <div className="generate-io-form__subsection">
                  <h4 className="generate-io-form__subsection-title">Budget & Pricing</h4>
                  <div className="generate-io-form-fields">
                    <CommonInput
                      label="Budget Amount"
                      controlledValue={placement.Budget.Amount.toString()}
                      onChange={value => updatePlacement(idx, "Budget", { ...placement.Budget, Amount: Number(value) })}
                      required
                    />
                    <CommonInput
                      label="CPM"
                      initialValue={placement.BidRate.CPM.toString()}
                      onChange={value => updatePlacement(idx, "BidRate", { ...placement.BidRate, CPM: Number(value) || 0 })}
                    />
                  </div>
                  <div className="generate-io-form-fields">
                    <CommonInput
                      label="CPC"
                      initialValue={placement.BidRate.CPC.toString()}
                      onChange={value => updatePlacement(idx, "BidRate", { ...placement.BidRate, CPC: Number(value) || 0 })}
                    />
                  </div>
                </div>

                {/* Targeting Configuration */}
                <div className="generate-io-form__subsection">
                  <h4 className="generate-io-form__subsection-title">Targeting</h4>
                  {campaignTargetingConfigId && placement.targeting_configuration_id === campaignTargetingConfigId ? (
                    <p className="generate-io-form__subsection-description">
                      ✓ This placement is using the campaign-level targeting configuration: <strong>{campaignTargetingConfigName}</strong>. You can override it by selecting a different configuration below.
                    </p>
                  ) : campaignTargetingConfigId && placement.targeting_configuration_id !== campaignTargetingConfigId ? (
                    <p className="generate-io-form__subsection-description generate-io-form__subsection-description--custom">
                      ⚠️ This placement has a custom targeting configuration that differs from the campaign-level setting.
                    </p>
                  ) : (
                    <p className="generate-io-form__subsection-description">
                      Select a targeting configuration for this placement.
                    </p>
                  )}
                  <div className="generate-io-form-fields">
                    <TargetingConfigSelector
                      selectedConfigId={placement.targeting_configuration_id}
                      onConfigSelect={(configId) => updatePlacement(idx, "targeting_configuration_id", configId)}
                      label={campaignTargetingConfigId && placement.targeting_configuration_id === campaignTargetingConfigId
                        ? "Override Targeting Configuration (Optional)"
                        : "Targeting Configuration"}
                      required={!campaignTargetingConfigId}
                      // Pass shared state to prevent additional API calls
                      configurations={sharedTargetingConfigs}
                      isLoading={targetingConfigsLoading}
                      error={targetingConfigsError}
                      onConfigurationCreated={loadTargetingConfigurations}
                    />
                  </div>
                </div>
                </div>
              )}
            </div>
          ))}
          <CommonButton type="button" onClick={addPlacement}>
            +  Add Placement
          </CommonButton>
        </div>
      </div>

      {/* Footer */}
      <div className="generate-io-form__footer">
        <div className="button-container">
          <CommonButton type="button" onClick={onClose} disabled={isSubmitting}>
            Cancel
          </CommonButton>
          <CommonButton
            onClick={(e) => {
              e.preventDefault();
              handleSubmit(e);
            }}
            disabled={isSubmitting}
          >
            {isSubmitting ? <ChatbotIcons.SVGSpinner /> : 'Generate IO'}
          </CommonButton>
        </div>
      </div>
    </div>
  );
}
