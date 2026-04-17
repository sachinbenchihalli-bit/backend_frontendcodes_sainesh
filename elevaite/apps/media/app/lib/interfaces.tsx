
// Enums, Interfaces, Types, and initializer objects
////////////////////////////////////////////////////


export const SESSION_ID_PREFIX = "sessionId_";
export const USER_MESSAGE_ID_PREFIX = "userMessageId_";
export const CHATBOT_MESSAGE_ID_PREFIX = "chatbotMessageId_";
export const QUERY_ID_PREFIX = "queryId_";


export enum ChatbotV {
    InWarranty = "in-warranty",
    OutOfWarranty = "out-of-warranty",
    AgentAssist = "agent-assist",
    Upsell = "upsell",
}
export const defaultChatbotV = ChatbotV.InWarranty;

export enum ChatBotGenAI {
    // Pan = "pan",
    // Cisco = "cisco",
    MediaPerformance = "mediaperformance",
    IdeateCreative = "ideatecreative",
    ContractsBilling = "contractsbilling",
}
export const defaultGenAIBotOption = ChatBotGenAI.MediaPerformance;

export interface ChatBotPayload {
    actor: string;
    content: string;
}

export interface SessionObject {
    id: string;
    label: string;
    messages: ChatMessageObject[];
    creationDate: string;
    summary?: SessionSummaryObject;
    isNewSession?: boolean; // Explicitly track if this is a brand new session
    hasLoadedMessages?: boolean; // Track if messages have been loaded from backend
}

export interface SessionSummaryObject {
    title: string;
    problem: string;
    solution: string;
    sessionMessageLengthOnLastUpdate?: number;
    isExpectingDisplay?: boolean;
}

export const defaultSession: SessionObject = {
    id: `${SESSION_ID_PREFIX}0`,
    label: "Session 1",
    messages: [],
    creationDate: new Date().toISOString(),
    isNewSession: true,
    hasLoadedMessages: true, // Default session doesn't need loading
}

export interface ChatMessageResponse {
    text: string;
    refs: string[];
    relatedQueries?: string[];
    imageData?: string;
}

export interface ChatMessageObject {
    id: string;
    userName: string;
    isBot: boolean;
    date: string;
    creative?: string;
    text: string;
    query_id?: string;
    vote?: 0 | 1 | -1;
    feedback?: string;
    feedbackfiles?: ChatMessageFileObject[];
    files?: ChatMessageFileObject[];
    relatedQueries?: string[];
    onQueryClick?: (query: string) => void;
    onGenerateIOClick?: () => void;
}

export interface ChatMessageFileObject {
    id: string;
    filename: string;
    fileType?: ChatMessageFileTypes;
    isDownloadable?: boolean;
    isViewable?: boolean;
}


export interface RelatedQueriesDisplayProps {
    queries: string[];
    onQueryClick: (query: string) => void;
    onGenerateIOClick?: () => void;
}

export enum ChatMessageFileTypes {
    DOC = "document",
}

export interface ChatbotInputProps {
    text: string; // Add this line
    setText: (text: string) => void; // Add this line
}

// Targeting Option Interface for multiple options support
export interface TargetingOption {
  option_number: number;
  is_primary: boolean;
  targeting_configuration_id?: string;
  new_targeting_configuration?: TargetingConfig;
  new_targeting_configuration_name?: string;
  new_targeting_configuration_description?: string;
}

export interface PlacementData {
  Name: string;
  Destination: string;
  StartDate: string;
  EndDate: string;
  ConvertToCampaign?: boolean; // Flag to convert placement into individual campaign
  Metrics: {
    Impressions: number;
    Clicks: number;
  };
  BidRate: {
    CPM: number;
    CPC: number;
  };
  Budget: {
    Amount: number;
  };
  targeting_configuration_id?: string; // ID of selected targeting configuration
  new_targeting_configuration?: TargetingConfig; // New targeting configuration details from AI
  new_targeting_configuration_name?: string; // AI-generated name for new targeting configuration
  new_targeting_configuration_description?: string; // AI-generated description for new targeting configuration
  targeting_options?: TargetingOption[]; // Multiple targeting options from enhanced AI response
  TargetingSuggestions?: {
    Demographics: string[];
    Interests: string[];
    Keywords: string[];
    AudienceSegments: string[];
    DeviceTargeting: string[];
    age_range?: string[];
    gender?: string[];
    income_level?: string[];
    location?: string[];
    behavioral_data?: string[];
    interests?: string[];
  };
}

// Targeting Configuration Interfaces
export interface TargetingConfig {
  age_range: string[];
  gender: string[];
  income_level: string[];
  location: string[];
  interests: string[];
  behavioral_data: string[];
}

export interface TargetingConfiguration {
  id: string;
  name: string;
  description?: string;
  targeting_config: TargetingConfig;
  user_id: string;
  created_at: string;
  updated_at: string;
}

export interface TargetingConfigurationCreate {
  name: string;
  description?: string;
  targeting_config: TargetingConfig;
}

export interface TargetingConfigurationUpdate {
  name?: string;
  description?: string;
  targeting_config?: TargetingConfig;
}

export interface GenerateIOFormData {
  OrderNo: string;
  Brand?: string; // Optional for Salesforce
  CampaignName: string;
  CustomerApprover: string;
  CustomerApproverEmail: string;
  SalesOwner: string;
  SalesOwnerEmail: string;
  FulfillmentOwner: string;
  FulfillmentOwnerEmail: string;
  Placement: PlacementData[];
  StartDate: string;
  EndDate: string;
  Metrics: { Impressions: number; Clicks: number };
  BidRate: { CPM: number; CPC: number };
  Budget: { Amount: number };
  TargetingSuggestions: {
    Demographics: string[];
    Interests: string[];
    Keywords: string[];
    AudienceSegments: string[];
    DeviceTargeting: string[];
    age_range?: string[];
    gender?: string[];
    income_level?: string[];
    location?: string[];
    behavioral_data?: string[];
    interests?: string[];
  };
  ObjectiveDetails: { Description: string };
  // Salesforce-specific fields
  SalesforceAccount?: string;
  SalesforceOpportunityId?: string;
  // Media plan content
  MediaPlanContent?: string;
  // Creative inspiration link
  CreativeInspirationLink?: string;
}

export interface GenerateIOFormProps {
    initialData?: Partial<GenerateIOFormData>;
    onClose: () => void;
    onSubmit?: (responseData: OrderGenerationResponse) => Promise<void>;
    selectedDestination?: IODestination;
    onBack?: () => void;
}

export enum IODestination {
    GOOGLE_WORKSPACE = 'google_workspace',
    SALESFORCE = 'salesforce'
}

export interface DestinationSelectionModalProps {
    isOpen: boolean;
    onClose: () => void;
    onDestinationSelect: (destination: IODestination) => void;
}

export interface FileDetails {
    filename: string;
    pdf_file_id: string;
    pdf_web_view_link: string;
}

export interface OrderGenerationResponse {
    status: string;
    message: string;
    campaign_folder_id: string;
    sheet_id: string;
    pdf_folder_id: string;
    file_details: FileDetails;
}

// Salesforce-specific interfaces
export interface SalesforceAccount {
    id: string;
    name: string;
    type?: string;
    industry?: string;
}

export interface SalesforceOpportunity {
    id: string;
    name: string;
    stageName?: string;
    amount?: number;
    closeDate?: string;
    accountName?: string;
}