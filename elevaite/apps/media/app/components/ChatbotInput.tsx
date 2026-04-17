"use client";
import { ChatbotIcons, CommonButton, SimpleInput, CommonDialog, CommonModal } from "@repo/ui/components";
import { useContext, useState, useRef, forwardRef, useImperativeHandle } from "react";
import { useSession } from "next-auth/react";
import { ChatContext } from "../ui/contexts/ChatContext";
import FileUpload from "./FileUpload";
import { ChatbotInputProps } from "../lib/interfaces";
import "./ChatbotInput.scss";
import "./MarkdownMessage.scss";
import { GenerateIOForm } from "./GenerateIOForm";
import { DestinationSelectionModal } from "./DestinationSelectionModal";
import type {GenerateIOFormData, IODestination} from "../lib/interfaces";
import { createInsertionOrder } from '../lib/actions';


export const ChatbotInput = forwardRef<any, ChatbotInputProps>(({ text, setText }, ref) => {
    const chatContext = useContext(ChatContext);
    const session = useSession();
    const [isExporting, setIsExporting] = useState(false);
    const [isUploading] = useState(false);
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [isExportPdfDialogOpen, setIsExportPdfDialogOpen] = useState(false);
    // const [isExportJiraDialogOpen, setIsExportJiraDialogOpen] = useState(false);
    const [isDestinationSelectionModalOpen, setIsDestinationSelectionModalOpen] = useState(false);
    const [isGenerateIOModalOpen, setIsGenerateIOModalOpen] = useState(false);
    const [selectedDestination, setSelectedDestination] = useState<IODestination | undefined>(undefined);
    const inputRef = useRef<HTMLInputElement | null>(null);
    // Determine if this is a new session ready for first message
    const isNewSessionReady = chatContext.selectedSession?.isNewSession &&
                              chatContext.selectedSession?.hasLoadedMessages &&
                              !chatContext.isSessionLoading;
    const [initialFormData, setInitialFormData] = useState<Partial<GenerateIOFormData> | undefined>(undefined);

    // Expose handleGenerateIOClick to parent component
    useImperativeHandle(ref, () => ({
        handleGenerateIOClick
    }));

    function handleTextChange(value: string): void {
        if (chatContext.isChatLoading) return;
        setText(value);
    }

    async function handleSend(): Promise<void>  {
        if (chatContext.isChatLoading) return;
        const workingText = text;
        setText("");
        if (!workingText.trim() && !selectedFile) return;

        try {
            console.log("Sending the file to the backend: ",selectedFile);
            await chatContext.addNewUserMessageWithLastMessages(workingText, selectedFile || undefined);
            setSelectedFile(null); // Clear the selected file after sending
        } catch (error) {
            console.error('Error sending message and file:', error);
        }
        // chatContext.addNewUserMessageWithLastMessages(workingText)
    }
    function handleKeyDown(key: string): void {
        if (key === "Enter") handleSend();
    }
    function handleFileSelect(file: File): void {
        setSelectedFile(file);
    }
    function handleButtonClick(buttonText: string): void{
        setText(buttonText);
        if (inputRef.current) {
            inputRef.current.focus();
        }
    }


    function parseMediaPlanMarkdown(markdown: string): Partial<GenerateIOFormData> {
        const result: Partial<GenerateIOFormData> = {};

        // Extract Brand(s)
        // const brandMatch = markdown.match(/brands?: ([\w\s,]+)/i);
        // if (brandMatch) {
        //     // Take the first brand as the main brand, or join all if you prefer
        //     result.Brand = brandMatch[1].split(',')[0].trim();
        // }

        // Extract Executive Summary Table
        const execSummaryRegex = /\| Component \| Details \|([\s\S]+?)\n\n/;
        const execSummaryMatch = markdown.match(execSummaryRegex);
        if (execSummaryMatch) {
            const lines = execSummaryMatch[1].split('\n').map(l => l.trim()).filter(Boolean);
            lines.forEach(line => {
                const parts = line.split('|').map(x => x.trim());
                if (parts[1] === 'Objectives') {
                    result.ObjectiveDetails = { Description: parts[2] };
                }
                if (parts[1] === 'Budget') {
                    const budget = parseFloat(parts[2].replace(/[^0-9.]/g, ''));
                    result.Budget = { Amount: budget };
                }
                if (parts[1] === 'Start Date') {
                    result.StartDate = parts[2];
                }
                if (parts[1] === 'End Date') {
                    result.EndDate = parts[2];
                }
            });
        }

        // Extract Impressions from Measurement and Evaluation Table
        const impressionsMatch = markdown.match(/\|\s*Impressions\s*\|[^|]*\|\s*([\d,]+)\s*impressions/i);
        if (impressionsMatch) {
            const impressions = parseInt(impressionsMatch[1].replace(/,/g, ''));
            result.Metrics = { Impressions: impressions, Clicks: 0 };
        }

        // Extract targeting configuration information from HTML comments
        let targetingConfigurationId: string | undefined;
        let newTargetingConfiguration: any = null;
        let newTargetingConfigurationName: string | undefined;
        let newTargetingConfigurationDescription: string | undefined;

        // Extract brand information from HTML comments
        let brandName: string | undefined;

        // Look for targeting configuration ID in HTML comments
        const configIdCommentPattern = /<!--\s*TARGETING_CONFIG_ID:\s*([a-f0-9-]{36})\s*-->/i;
        const configIdCommentMatch = markdown.match(configIdCommentPattern);

        if (configIdCommentMatch) {
            targetingConfigurationId = configIdCommentMatch[1];
            console.log("Found targeting configuration ID from comment:", targetingConfigurationId);
        } else {
            // Look for new targeting configuration in HTML comments
            const newConfigCommentPattern = /<!--\s*NEW_TARGETING_CONFIG:\s*({.*?})\s*-->/i;
            const newConfigCommentMatch = markdown.match(newConfigCommentPattern);

            if (newConfigCommentMatch) {
                try {
                    newTargetingConfiguration = JSON.parse(newConfigCommentMatch[1]);
                    console.log("Found new targeting configuration from comment:", newTargetingConfiguration);

                    // Look for targeting configuration name in HTML comments
                    const configNameCommentPattern = /<!--\s*TARGETING_CONFIG_NAME:\s*(.*?)\s*-->/i;
                    const configNameCommentMatch = markdown.match(configNameCommentPattern);
                    if (configNameCommentMatch) {
                        newTargetingConfigurationName = configNameCommentMatch[1].trim();
                        console.log("Found targeting configuration name from comment:", newTargetingConfigurationName);
                    }

                    // Look for targeting configuration description in HTML comments
                    const configDescCommentPattern = /<!--\s*TARGETING_CONFIG_DESCRIPTION:\s*(.*?)\s*-->/i;
                    const configDescCommentMatch = markdown.match(configDescCommentPattern);
                    if (configDescCommentMatch) {
                        newTargetingConfigurationDescription = configDescCommentMatch[1].trim();
                        console.log("Found targeting configuration description from comment:", newTargetingConfigurationDescription);
                    }
                } catch (error) {
                    console.error("Error parsing new targeting configuration JSON:", error);
                }
            } else {
                // Fallback: Look for targeting configuration ID pattern in text (legacy support)
                const configIdPattern = /Recommended Targeting Configuration ID:\s*([a-f0-9-]{36})/i;
                const configIdMatch = markdown.match(configIdPattern);

                if (configIdMatch) {
                    targetingConfigurationId = configIdMatch[1];
                    console.log("Found targeting configuration ID from text:", targetingConfigurationId);
                } else {
                    // Fallback: Look for new targeting configuration pattern in text (legacy support)
                    const newConfigPattern = /New Targeting Configuration Needed:([\s\S]*?)(?=\n\n|\n#|\Z)/i;
                    const newConfigMatch = markdown.match(newConfigPattern);

                    if (newConfigMatch) {
                        const newConfigText = newConfigMatch[1].trim();
                        console.log("Found new targeting configuration text:", newConfigText);

                        // Parse the targeting configuration details
                        const targetingConfig = {
                            age_range: [] as string[],
                            gender: [] as string[],
                            income_level: [] as string[],
                            location: [] as string[],
                            interests: [] as string[],
                            behavioral_data: [] as string[]
                        };

                        // Extract each field using patterns
                        const fieldPatterns = {
                            age_range: /age_range:\s*\[(.*?)\]/i,
                            gender: /gender:\s*\[(.*?)\]/i,
                            income_level: /income_level:\s*\[(.*?)\]/i,
                            location: /location:\s*\[(.*?)\]/i,
                            interests: /interests:\s*\[(.*?)\]/i,
                            behavioral_data: /behavioral_data:\s*\[(.*?)\]/i
                        };

                        for (const [field, pattern] of Object.entries(fieldPatterns)) {
                            const fieldMatch = newConfigText.match(pattern);
                            if (fieldMatch) {
                                // Parse the list content
                                const listContent = fieldMatch[1];
                                // Split by comma and clean up quotes
                                const items = listContent.split(',').map(item => item.trim().replace(/['"]/g, '')).filter(item => item);
                                (targetingConfig as any)[field] = items;
                            }
                        }

                        newTargetingConfiguration = targetingConfig;
                        console.log("Parsed new targeting configuration from text:", newTargetingConfiguration);
                    }
                }
            }
        }

        // Extract brand information from HTML comments
        const brandCommentPattern = /<!--\s*BRAND:\s*(.*?)\s*-->/i;
        const brandCommentMatch = markdown.match(brandCommentPattern);
        if (brandCommentMatch) {
            brandName = brandCommentMatch[1].trim();
            console.log("Found brand from comment:", brandName);
            result.Brand = brandName;
        }

        // Extract Target Audience Table (fallback for legacy format)
        const targeting: GenerateIOFormData['TargetingSuggestions'] = {
            Demographics: [],
            Interests: [],
            Keywords: [],
            AudienceSegments: [],
            DeviceTargeting: [],
        };
        const targetAudienceRegex = /\| Demographic \| Details \|([\s\S]+?)\n\n/;
        const targetAudienceMatch = markdown.match(targetAudienceRegex);
        if (targetAudienceMatch) {
            const lines = targetAudienceMatch[1].split('\n').map(l => l.trim()).filter(Boolean);
            lines.forEach(line => {
                const parts = line.split('|').map(x => x.trim());
                if (parts[1] === 'Age Range') targeting.Demographics.push(parts[2]);
                if (parts[1] === 'Gender') targeting.Demographics.push(parts[2]);
                if (parts[1] === 'Income Level') targeting.Demographics.push(parts[2]);
                if (parts[1] === 'Location') targeting.DeviceTargeting.push(parts[2]);
                if (parts[1] === 'Behavioral Data') targeting.AudienceSegments.push(parts[2]);
                if (parts[1] === 'Interests') targeting.Interests = parts[2].split(',').map(s => s.trim());
            });
        }
        result.TargetingSuggestions = targeting;

        // Extract Media Mix Strategy Table for Placement
        const mediaMixRegex = /\| Channel \| Tactics \| Budget % \| Allocated Budget \| Target Impressions \| Target Clicks \| CPM \| Expected Reach \| Justification \|([\s\S]+?)\n\n/;
        const mediaMixMatch = markdown.match(mediaMixRegex);
        if (mediaMixMatch) {
            const lines = mediaMixMatch[1].split('\n').map(l => l.trim()).filter(Boolean);

            // Helper function to parse budget amounts (remove currency symbols and commas)
            const parseBudget = (budgetStr: string): number => {
                const cleanBudget = budgetStr.replace(/[$,]/g, '');
                return parseFloat(cleanBudget) || 0;
            };

            // Helper function to parse reach/impressions (handle formats like "2.5M impressions" → 2500000)
            const parseReach = (reachStr: string): number => {
                // Extract numbers and multipliers from the string
                const match = reachStr.match(/([\d,]+(?:\.\d+)?)\s*([mk])?/i);
                if (!match) return 0;

                const baseNumber = parseFloat(match[1].replace(/,/g, '')) || 0;
                const multiplierChar = match[2]?.toLowerCase();

                let multiplier = 1;
                if (multiplierChar === 'm') {
                    multiplier = 1000000;
                } else if (multiplierChar === 'k') {
                    multiplier = 1000;
                }

                return Math.round(baseNumber * multiplier);
            };

            result.Placement = lines
                .filter(line => {
                    // Skip table separator lines (lines with only dashes and pipes)
                    return !line.match(/^\|[\s\-|]+\|$/);
                })
                .map(line => {
                    const parts = line.split('|').map(x => x.trim());

                    // Extract data from table columns:
                    // parts[1] = Channel, parts[2] = Tactics, parts[3] = Budget %, parts[4] = Allocated Budget,
                    // parts[5] = Target Impressions, parts[6] = Target Clicks, parts[7] = CPM, parts[8] = Expected Reach, parts[9] = Justification
                    const channel = parts[1] || "";
                    const allocatedBudget = parts[4] || "";
                    const targetImpressions = parts[5] || "";
                    const targetClicks = parts[6] || "";
                    const cpm = parts[7] || "";
                    const expectedReach = parts[8] || "";

                    return {
                        Name: channel ? `${channel}` : "",
                        Destination: channel,
                        StartDate: result.StartDate || "",
                        EndDate: result.EndDate || "",
                        Metrics: {
                            Impressions: parseReach(targetImpressions) || parseReach(expectedReach),
                            Clicks: parseReach(targetClicks)
                        },
                        BidRate: {
                            CPM: parseBudget(cpm),
                            CPC: 0
                        },
                        Budget: {
                            Amount: parseBudget(allocatedBudget)
                        },
                        TargetingSuggestions: {
                            Demographics: targeting.Demographics || [],
                            Interests: targeting.Interests || [],
                            Keywords: targeting.Keywords || [],
                            AudienceSegments: targeting.AudienceSegments || [],
                            DeviceTargeting: targeting.DeviceTargeting || [],
                            age_range: [],
                            gender: [],
                            income_level: [],
                            location: [],
                            behavioral_data: [],
                            interests: targeting.Interests || []
                        },
                        // Add targeting configuration information
                        targeting_configuration_id: targetingConfigurationId,
                        new_targeting_configuration: newTargetingConfiguration,
                        new_targeting_configuration_name: newTargetingConfigurationName,
                        new_targeting_configuration_description: newTargetingConfigurationDescription
                    };
                })
                .filter(placement => placement.Name && placement.Destination && !placement.Name.includes('-')); // Only include valid placements, exclude separator lines
        }

        console.log("Extracted result:",result)
        return result;
    }


    function handleGenerateIOClick() {
        const mediaPlanMessages = chatContext.selectedSession?.messages.filter(
            msg => msg.text.includes("# Media Plan")
        );
        if (!mediaPlanMessages || mediaPlanMessages.length === 0) {
            // Check if the last bot message is already the "Please generate a media plan first" message
            const botMessages = chatContext.selectedSession?.messages.filter(msg => msg.isBot) || [];
            const lastBotMessage = botMessages[botMessages.length - 1];

            if (!lastBotMessage || lastBotMessage.text !== "In order to create an insertion order, we must first generate a media plan. Would you like to generate a media plan?") {
                chatContext.addNewBotMessage("In order to create an insertion order, we must first generate a media plan. Would you like to generate a media plan?");
            }
            return;
          }
        const latestMediaPlanMessage = mediaPlanMessages[mediaPlanMessages.length - 1];
        const parsedData = parseMediaPlanMarkdown(latestMediaPlanMessage.text);

        // Include the media plan content in the initial form data
        const enrichedFormData = {
            ...parsedData,
            MediaPlanContent: latestMediaPlanMessage.text
        };

        setInitialFormData(enrichedFormData);
        // Show destination selection modal first
        setIsDestinationSelectionModalOpen(true);
    }

    function handleDestinationSelect(destination: IODestination) {
        setSelectedDestination(destination);
        setIsDestinationSelectionModalOpen(false);
        setIsGenerateIOModalOpen(true);
    }

    function handleBackToDestinationSelection() {
        setIsGenerateIOModalOpen(false);
        setIsDestinationSelectionModalOpen(true);
    }

    async function handleExport(): Promise<void> {
        const { selectedSession } = chatContext;
        if (!selectedSession || selectedSession.messages.length === 0) return;

        const markdownMessages = selectedSession.messages.map(message => message.text).join("\n\n");
        setIsExporting(true);
        try {
            const baseUrl = process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL || '';
            const endpoint = baseUrl.endsWith('/') ? `${baseUrl}generate-pdf` : `${baseUrl}/generate-pdf`;
            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ markdown: markdownMessages }),
            });

            if (!response.ok) {
                throw new Error('Failed to generate PDF');
            }

            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);

            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', 'chat_session.pdf');

            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        } catch (error) {
            console.error('Error exporting chat session:', error);
        } finally {
            setIsExporting(false);
        }
    }
    async function handleGenerateIOSubmit(formData: any): Promise<void> {
        try {
            // Add session and user context to the form data so backend can store the message
            const userId = session.data?.user?.id || session.data?.user?.name || "dev-user";
            const enrichedFormData = {
                ...formData,
                session_id: chatContext.selectedSession?.id,
                user_id: userId
            };

            // Start simple loading state
            chatContext.setInsertionOrderLoading(true);

            try {
                const responseData = await createInsertionOrder(enrichedFormData);

                // Detect if this is a Salesforce submission by checking the sheet_link
                const isSalesforceSubmission = responseData.sheet_link &&
                    (responseData.sheet_link.includes('lightning.force.com') ||
                     responseData.sheet_link.includes('salesforce.com'));

                let botMessage: string;

                if (isSalesforceSubmission) {
                    // Salesforce submission - show Salesforce-specific message
                    botMessage = `Your IO was created successfully in Salesforce! 🎉\n\n`;

                    // Always show the real PDF document link (from Google Drive)
                    if (responseData.file_details.pdf_web_view_link &&
                        !responseData.file_details.pdf_web_view_link.includes('salesforce.com')) {
                        botMessage += `📄 IO Document: ${responseData.file_details.pdf_web_view_link}\n\n`;
                    }

                    // Always show the Salesforce record link
                    botMessage += `🔗 View in Salesforce: ${responseData.sheet_link}`;

                    // Add campaign folder link if PDF was generated
                    if (responseData.campaign_folder_link &&
                        !responseData.campaign_folder_link.includes('salesforce.com')) {
                        botMessage += `\n\n📁 Campaign Folder: ${responseData.campaign_folder_link}`;
                    }
                } else {
                    // Google Workspace submission - show Google Drive message
                    botMessage = `Your IO was created successfully! 🎉\n\n` +
                        `📄 IO Document: ${responseData.file_details.pdf_web_view_link}\n\n` +
                        `📊 Campaign Sheet: https://docs.google.com/spreadsheets/d/${responseData.sheet_id}\n\n` +
                        `📁 Campaign Folder: https://drive.google.com/drive/folders/${responseData.campaign_folder_id}`;
                }

                // Add the bot message to the session for immediate display
                // Note: This message is also stored in the database by the backend
                chatContext.addNewBotMessage(botMessage);

            } catch (error) {
                console.error('Error submitting form:', error);

                // Show error message as bot response
                const errorMessage = `Sorry, there was an error creating your insertion order: ${error instanceof Error ? error.message : 'Unknown error'}. Please try again.`;
                chatContext.addNewBotMessage(errorMessage);
            } finally {
                // Always stop the loading state
                chatContext.setInsertionOrderLoading(false);
            }

        } catch (error) {
            console.error('Unexpected error in form submission:', error);
            // Ensure loading state is stopped on unexpected error
            chatContext.setInsertionOrderLoading(false);
        }
    }

    return (

        <div>
                {chatContext.isSessionLoading && (
                    <div className="chatbot-welcome-message">
                        <h1>Loading session...</h1>
                    </div>
                )}
                {isNewSessionReady && (
                    <div className="chatbot-welcome-message">
                        <h1>How can I assist with your campaign performance or media planning?</h1>
                    </div>
                )}

            <div className={["chatbot-input-container", chatContext.isChatLoading ? "loading" : undefined].filter(Boolean).join(" ")}>

                        {/* File Preview Container (Above the Input) */}
                            {selectedFile && (
                                <div className="uploaded-creative-container">
                                    <button
                                    className="close-icon"
                                    onClick={() => setSelectedFile(null)} // Clear the selected file
                                    >
                                    &times; {/* X symbol */}
                                    </button>
                                {selectedFile.type.startsWith("image/") || selectedFile.type === "image/gif" ? (
                                    <img
                                        src={URL.createObjectURL(selectedFile)}
                                        alt="Uploaded Creative"
                                        className="uploaded-creative"
                                    />
                                ) : selectedFile.type.startsWith("video/") ? (
                                    <video
                                        controls
                                        className="uploaded-creative"
                                        src={URL.createObjectURL(selectedFile)}
                                    />
                                ) : null}
                            </div>
                        )}

                        {!selectedFile && (<FileUpload
                            onFileSelect={handleFileSelect}
                            onUpload={() => console.log("File uploaded!")}
                            isUploading={isUploading}
                        />)}

                        <div className="input-wrapper">
                            {chatContext.isChatLoading && (
                                <div className="loading-dots-overlay">
                                    <div className="loading-dots">
                                        <div className="dot"></div>
                                        <div className="dot"></div>
                                        <div className="dot"></div>
                                    </div>
                                    <span className="loading-text">
                                        {chatContext.chatLoadingMessage || "Thinking about your request..."}
                                    </span>
                                </div>
                            )}
                            <SimpleInput
                                wrapperClassName="chatbot-input-field"
                                value={text}
                                onChange={handleTextChange}
                                onKeyDown={handleKeyDown}
                                placeholder={chatContext.isChatLoading ? "" : "Ask ElevAIte"}
                                disabled={chatContext.isChatLoading}
                                rightIcon={
                                    <CommonButton
                                        onClick={handleSend}
                                        disabled={chatContext.isChatLoading}
                                    >
                                        {chatContext.isChatLoading ? <ChatbotIcons.SVGSpinner /> : <ChatbotIcons.SVGSend />}
                                    </CommonButton>
                                }
                                passedRef={inputRef}
                            />
                        </div>

                {!isNewSessionReady && (
                    <div className="action-buttons-container">
                        <CommonButton
                            className="export-button"
                            title="Export IO"
                            onClick={handleGenerateIOClick}
                            disabled={isUploading || chatContext.isChatLoading || isExporting}>
                            <ChatbotIcons.SVGDocument />
                        </CommonButton>
                        <CommonButton
                            className="export-button"
                            title="Download as PDF"
                            onClick={() => setIsExportPdfDialogOpen(true)}
                            disabled={isUploading || chatContext.isChatLoading || isExporting}>
                            {isExporting ? <ChatbotIcons.SVGSpinnerExport /> : <ChatbotIcons.SVGDownloadExport />}
                        </CommonButton>

                    </div>
                )}
            </div>
            {isNewSessionReady && (
                <div className="first-message-buttons">
                    <CommonButton onClick={() => handleButtonClick("Campaign Performance and Insights ")}>Campaign Performance and Insights</CommonButton>
                    <CommonButton onClick={() => handleButtonClick("Provide Creative Insights ")}>Provide Creative Insights</CommonButton>
                    <CommonButton onClick={() => handleButtonClick("Generate a Media plan ")}>Generate a Media plan</CommonButton>
                    <CommonButton onClick={() => handleButtonClick("Generate an Ad Creative ")}>Generate an Ad Creative</CommonButton>
                </div>
            )}
            {/* Export to PDF Confirmation Dialog */}
            {isExportPdfDialogOpen && (
                <CommonDialog
                    title="Are you sure you want to export to PDF?"
                    onConfirm={() => {
                        handleExport();
                        setIsExportPdfDialogOpen(false);
                    }}
                    onCancel={() => { setIsExportPdfDialogOpen(false); }}
                />
            )}

            {/* Destination Selection Modal */}
            {isDestinationSelectionModalOpen && (
                <CommonModal onClose={() => setIsDestinationSelectionModalOpen(false)} className="full-screen-compare-line-items-modal">
                    <DestinationSelectionModal
                        isOpen={isDestinationSelectionModalOpen}
                        onClose={() => setIsDestinationSelectionModalOpen(false)}
                        onDestinationSelect={handleDestinationSelect}
                    />
                </CommonModal>
            )}

            {/* Export to IO */}
            {isGenerateIOModalOpen && (
                <CommonModal onClose={() => setIsGenerateIOModalOpen(false)} className="full-screen-compare-line-items-modal">
                    <GenerateIOForm
                        initialData={initialFormData}
                        onClose={() => setIsGenerateIOModalOpen(false)}
                        onSubmit={handleGenerateIOSubmit}
                        selectedDestination={selectedDestination}
                        onBack={handleBackToDestinationSelection}
                    />
                </CommonModal>
            )}
        </div>

    );
});
