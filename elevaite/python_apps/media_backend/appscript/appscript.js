/**
 * SCALABLE GOOGLE SHEETS MONITORING SYSTEM
 * =======================================
 *
 * This system monitors Google Sheets for changes and generates PDFs automatically,
 * designed to scale beyond Google Apps Script's 20-trigger limit.
 *
 * ARCHITECTURE OVERVIEW:
 * =====================
 *
 * OLD SYSTEM (Limited to 20 sheets):
 * - Individual onEdit triggers per sheet
 * - Hit 20-trigger limit quickly
 *
 * NEW SYSTEM (Scales to hundreds of sheets):
 * - Centralized polling system using 2 time-based triggers
 * - Sheet registry tracks all Order sheets and their modification times
 * - Change detection by comparing file modification timestamps
 * - Debounced processing maintains 5-second delay after edits
 *
 * KEY COMPONENTS:
 * ==============
 *
 * 1. SHEET REGISTRY (stored in Script Properties):
 *    - Tracks all sheets containing "Order_" in their names
 *    - Stores: sheetId, name, folderName, lastModified, lastProcessed
 *    - Updated every 10 minutes to catch new folders/sheets
 *
 * 2. CENTRALIZED MONITORING (runs every minute):
 *    - Checks all registered sheets for modification time changes
 *    - Schedules debounced processing for changed sheets
 *    - Uses only 2 persistent triggers regardless of sheet count
 *
 * 3. DEBOUNCED PROCESSING:
 *    - 5-second delay after last detected change
 *    - Prevents multiple PDF generations for rapid edits
 *    - Temporary triggers created/destroyed per processing cycle
 *
 * TRIGGER USAGE:
 * =============
 * - 2 persistent triggers: monitorAllSheets, updateSheetRegistry
 * - Temporary triggers: processDelayedEdit (created/destroyed as needed)
 * - Total persistent triggers: 2 (vs. 1 per sheet in old system)
 *
 * SCALABILITY:
 * ===========
 * - Supports hundreds of folders with Order sheets
 * - No trigger limit constraints
 * - Efficient polling with 1-minute intervals
 * - Automatic cleanup of invalid/deleted sheets
 *
 * SETUP INSTRUCTIONS:
 * ==================
 * 1. Run initializeFolderMonitoring() to start the system
 * 2. Use getMonitoringStatus() to check system health
 * 3. Use resetMonitoringSystem() to completely reset if needed
 */

// Configuration
const BASE_FOLDER_ID = "0ALgAEVzRkxVWUk9PVA"; // Your base folder ID here
const PDF_GENERATION_TEMPLATE_ID = "1ABDKf9KHRU2xk1kKlOxnjeRr9m_WuIBiJubYCTjP61E"; // Google Docs template for PDF generation

// Scalable monitoring configuration
const MONITORING_INTERVAL_MINUTES = 1; // Check for changes every minute
const DEBOUNCE_DELAY_SECONDS = 5; // Wait 5 seconds after last edit before making API call

// Main function to set up scalable folder monitoring
function initializeFolderMonitoring() {
  cleanupTriggers();
  setupCentralizedMonitoring();
  initializeSheetRegistry();
  Logger.log('Scalable folder monitoring initialized.');
}

// Setup centralized monitoring system that scales beyond 20 sheets
function setupCentralizedMonitoring() {
  // Single time-based trigger for monitoring all sheets
  ScriptApp.newTrigger('monitorAllSheets')
    .timeBased()
    .everyMinutes(MONITORING_INTERVAL_MINUTES)
    .create();

  // Periodic registry update trigger (less frequent)
  ScriptApp.newTrigger('updateSheetRegistry')
    .timeBased()
    .everyMinutes(10) // Update registry every 10 minutes to catch new folders/sheets
    .create();

  Logger.log('Centralized monitoring triggers setup complete.');
}

// Clean up existing triggers associated with this script project
function cleanupTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  let count = 0;
  triggers.forEach(trigger => {
    ScriptApp.deleteTrigger(trigger);
    count++;
  });
  Logger.log(`Cleaned up ${count} existing triggers.`);
}

// Initialize the sheet registry with all existing Order sheets
function initializeSheetRegistry() {
  Logger.log('Initializing sheet registry...');
  const registry = {};
  const baseFolder = DriveApp.getFolderById(BASE_FOLDER_ID);
  const folders = baseFolder.getFolders();

  let sheetCount = 0;
  while (folders.hasNext()) {
    const folder = folders.next();
    const targetSheet = findSheetInFolder(folder);

    if (targetSheet) {
      const sheetId = targetSheet.getId();
      const lastModified = targetSheet.getLastUpdated();

      registry[sheetId] = {
        name: targetSheet.getName(),
        folderName: folder.getName(),
        lastModified: lastModified.getTime(),
        lastProcessed: 0 // Never processed initially
      };

      sheetCount++;
      Logger.log(`Registered sheet: ${targetSheet.getName()} in folder: ${folder.getName()}`);
    }
  }

  // Store registry in script properties
  PropertiesService.getScriptProperties().setProperty('sheetRegistry', JSON.stringify(registry));
  Logger.log(`Sheet registry initialized with ${sheetCount} sheets.`);
}

// Update the sheet registry to include new folders/sheets
function updateSheetRegistry() {
  Logger.log('Updating sheet registry...');

  try {
    const existingRegistryJson = PropertiesService.getScriptProperties().getProperty('sheetRegistry');
    const existingRegistry = existingRegistryJson ? JSON.parse(existingRegistryJson) : {};

    const baseFolder = DriveApp.getFolderById(BASE_FOLDER_ID);
    const folders = baseFolder.getFolders();

    let newSheets = 0;
    while (folders.hasNext()) {
      const folder = folders.next();
      const targetSheet = findSheetInFolder(folder);

      if (targetSheet) {
        const sheetId = targetSheet.getId();

        // Only add if not already in registry
        if (!existingRegistry[sheetId]) {
          const lastModified = targetSheet.getLastUpdated();

          existingRegistry[sheetId] = {
            name: targetSheet.getName(),
            folderName: folder.getName(),
            lastModified: lastModified.getTime(),
            lastProcessed: 0
          };

          newSheets++;
          Logger.log(`Added new sheet to registry: ${targetSheet.getName()} in folder: ${folder.getName()}`);
        }
      }
    }

    // Update the registry
    PropertiesService.getScriptProperties().setProperty('sheetRegistry', JSON.stringify(existingRegistry));

    if (newSheets > 0) {
      Logger.log(`Registry updated with ${newSheets} new sheets. Total sheets: ${Object.keys(existingRegistry).length}`);
    } else {
      Logger.log(`Registry update complete. No new sheets found. Total sheets: ${Object.keys(existingRegistry).length}`);
    }

  } catch (error) {
    Logger.log(`Error updating sheet registry: ${error.toString()}`);
  }
}

function findSheetInFolder(folder) {
  const files = folder.getFiles();
  while (files.hasNext()) {
    const file = files.next();
    // Check if the file is a Google Sheet and name contains "Order_"
    if (file.getMimeType() === 'application/vnd.google-apps.spreadsheet' && file.getName().includes("Order_")) {
      Logger.log(`Found matching sheet: "${file.getName()}" in folder "${folder.getName()}"`);
      return file; // Return the first matching sheet found
    }
  }
  return null; // No sheet with "Order_" in the name found
}

// Centralized monitoring function that checks all registered sheets for changes
function monitorAllSheets() {
  try {
    Logger.log('Starting centralized sheet monitoring...');

    const registryJson = PropertiesService.getScriptProperties().getProperty('sheetRegistry');
    if (!registryJson) {
      Logger.log('No sheet registry found. Initializing...');
      initializeSheetRegistry();
      return;
    }

    const registry = JSON.parse(registryJson);
    const sheetIds = Object.keys(registry);

    if (sheetIds.length === 0) {
      Logger.log('No sheets in registry to monitor.');
      return;
    }

    Logger.log(`Monitoring ${sheetIds.length} sheets for changes...`);

    let changedSheets = 0;
    const updatedRegistry = { ...registry };

    for (const sheetId of sheetIds) {
      try {
        const sheetInfo = registry[sheetId];
        const file = DriveApp.getFileById(sheetId);
        const currentModified = file.getLastUpdated().getTime();

        // Check if sheet has been modified since last check
        if (currentModified > sheetInfo.lastModified) {
          Logger.log(`Change detected in sheet: ${sheetInfo.name} (${sheetInfo.folderName})`);

          // Update the last modified time in registry
          updatedRegistry[sheetId].lastModified = currentModified;

          // Schedule debounced processing
          scheduleDelayedProcessing(sheetId, sheetInfo.name);
          changedSheets++;
        }

      } catch (error) {
        Logger.log(`Error checking sheet ${sheetId}: ${error.toString()}`);
        // Remove invalid sheet from registry
        delete updatedRegistry[sheetId];
      }
    }

    // Update registry with new modification times
    PropertiesService.getScriptProperties().setProperty('sheetRegistry', JSON.stringify(updatedRegistry));

    if (changedSheets > 0) {
      Logger.log(`Monitoring complete. Found ${changedSheets} changed sheets.`);
    } else {
      Logger.log('Monitoring complete. No changes detected.');
    }

  } catch (error) {
    Logger.log(`Error in monitorAllSheets: ${error.toString()}`);
  }
}

// Schedule debounced processing for a specific sheet
function scheduleDelayedProcessing(sheetId, sheetName) {
  try {
    // Clean up any existing pending triggers for this sheet
    deletePendingTriggersForSheet(sheetId);

    // Store the sheet information with timestamp
    const scriptProperties = PropertiesService.getScriptProperties();
    const pendingKey = `pending_${sheetId}`;
    const pendingData = {
      sheetId: sheetId,
      sheetName: sheetName,
      scheduledTime: new Date().getTime()
    };

    scriptProperties.setProperty(pendingKey, JSON.stringify(pendingData));

    // Create a new time-based trigger for this specific sheet
    const trigger = ScriptApp.newTrigger('processDelayedEdit')
      .timeBased()
      .after(DEBOUNCE_DELAY_SECONDS * 1000)
      .create();

    // Store trigger ID for cleanup
    scriptProperties.setProperty(`trigger_${sheetId}`, trigger.getUniqueId());

    Logger.log(`Scheduled delayed processing for sheet: ${sheetName} in ${DEBOUNCE_DELAY_SECONDS} seconds`);

  } catch (error) {
    Logger.log(`Error scheduling delayed processing for sheet ${sheetId}: ${error.toString()}`);
  }
}

// Delete pending triggers for a specific sheet
function deletePendingTriggersForSheet(sheetId) {
    try {
        const scriptProperties = PropertiesService.getScriptProperties();
        const triggerIdKey = `trigger_${sheetId}`;
        const triggerId = scriptProperties.getProperty(triggerIdKey);

        if (triggerId) {
            const triggers = ScriptApp.getProjectTriggers();
            const trigger = triggers.find(t => t.getUniqueId() === triggerId);

            if (trigger) {
                ScriptApp.deleteTrigger(trigger);
                Logger.log(`Deleted pending trigger for sheet: ${sheetId}`);
            }

            // Clean up the stored trigger ID
            scriptProperties.deleteProperty(triggerIdKey);
        }

        // Also clean up the pending data
        const pendingKey = `pending_${sheetId}`;
        scriptProperties.deleteProperty(pendingKey);

    } catch (error) {
        Logger.log(`Error deleting pending triggers for sheet ${sheetId}: ${error.toString()}`);
    }
}

// Delete all pending triggers (for cleanup)
function deletePendingTriggers() {
    const triggers = ScriptApp.getProjectTriggers();
    triggers.forEach(trigger => {
        if (trigger.getHandlerFunction() === 'processDelayedEdit') {
            ScriptApp.deleteTrigger(trigger);
        }
    });
}

// Process delayed edit - now works with the new centralized system
function processDelayedEdit() {
    try {
        Logger.log('Processing delayed edit...');

        const scriptProperties = PropertiesService.getScriptProperties();

        // Find which sheet triggered this by looking for pending data
        const allProperties = scriptProperties.getProperties();
        let pendingSheetId = null;
        let pendingData = null;

        for (const [key, value] of Object.entries(allProperties)) {
            if (key.startsWith('pending_')) {
                try {
                    const data = JSON.parse(value);
                    if (data.sheetId) {
                        pendingSheetId = data.sheetId;
                        pendingData = data;
                        break;
                    }
                } catch (e) {
                    // Skip invalid JSON
                }
            }
        }

        if (!pendingSheetId || !pendingData) {
            Logger.log('No pending sheet information found. Exiting.');
            return;
        }

        const sheetId = pendingData.sheetId;

        // Clean up the pending data and triggers
        deletePendingTriggersForSheet(sheetId);

        // Get the spreadsheet and sheet
        const spreadsheet = SpreadsheetApp.openById(sheetId);
        const sheet = spreadsheet.getActiveSheet(); // Use active sheet instead of by name

        if (!spreadsheet || !sheet) {
            Logger.log('Could not find spreadsheet or sheet. Exiting.');
            return;
        }

        Logger.log(`Processing delayed edit for spreadsheet: ${spreadsheet.getName()}`);

        // Update the registry to mark this sheet as processed
        updateSheetProcessedTime(sheetId);

        // Generate PDF locally
        generatePDFLocally(spreadsheet, sheet);

    } catch (error) {
        Logger.log(`Error in processDelayedEdit: ${error.toString()}`);
    }
}

// Update the last processed time for a sheet in the registry
function updateSheetProcessedTime(sheetId) {
    try {
        const scriptProperties = PropertiesService.getScriptProperties();
        const registryJson = scriptProperties.getProperty('sheetRegistry');

        if (registryJson) {
            const registry = JSON.parse(registryJson);

            if (registry[sheetId]) {
                registry[sheetId].lastProcessed = new Date().getTime();
                scriptProperties.setProperty('sheetRegistry', JSON.stringify(registry));
                Logger.log(`Updated last processed time for sheet: ${sheetId}`);
            }
        }

    } catch (error) {
        Logger.log(`Error updating sheet processed time: ${error.toString()}`);
    }
}
function generatePDFLocally(spreadsheet, sheet) {
    try {
        Logger.log(`Starting local PDF generation for sheet tab: "${sheet.getName()}"`);
        Logger.log(`Spreadsheet name: "${spreadsheet.getName()}"`);
        Logger.log(`Spreadsheet ID: ${spreadsheet.getId()}`);

        // Get the file by ID first, then get its parent folder
        const file = DriveApp.getFileById(spreadsheet.getId());
        const parents = file.getParents();

        if (!parents.hasNext()) {
            Logger.log('No parent folder found for the spreadsheet');
            return;
        }

        const parent = parents.next();
        Logger.log(`Parent folder: "${parent.getName()}" (ID: ${parent.getId()})`);

        // Find PDF folder within the same parent folder
        const pdfFolder = findPDFFolderInParent(parent);
        if (!pdfFolder) {
            Logger.log('PDF folder not found in parent folder');
            return;
        }
        Logger.log(`PDF folder found: "${pdfFolder.getName()}" (ID: ${pdfFolder.getId()})`);

        // Extract order number from spreadsheet name (not sheet tab name)
        const spreadsheetName = spreadsheet.getName();
        Logger.log(`Extracting order number from spreadsheet name: "${spreadsheetName}"`);

        const orderParts = spreadsheetName.split('Order_');
        if (orderParts.length < 2) {
            Logger.log(`Could not extract order number from spreadsheet name: "${spreadsheetName}"`);
            Logger.log('Expected format: "Order_{number}" (e.g., "Order_IO-220030-9952")');
            return;
        }
        const orderId = orderParts[1];
        Logger.log(`Extracted order ID: "${orderId}"`);

        // Get the most recent PDF version
        const currentVersion = getLatestPDFVersion(pdfFolder, spreadsheetName);
        const newVersion = currentVersion + 1;
        Logger.log(`Current version: ${currentVersion}, New version: ${newVersion}`);

        // Get sheet data and convert to template variables
        const templateVariables = getSheetData(spreadsheet.getId());

        // Generate PDF with versioned filename
        const filename = `${orderId}_v${newVersion}`;
        const pdfResult = createPDFFromTemplate(templateVariables, pdfFolder.getId(), filename);

        if (pdfResult.success) {
            Logger.log(`PDF generated successfully: ${filename}.pdf`);
            Logger.log(`PDF URL: ${pdfResult.webViewLink}`);
        } else {
            Logger.log(`PDF generation failed: ${pdfResult.error}`);
        }

    } catch (error) {
        Logger.log(`Error in generatePDFLocally: ${error.toString()}`);
    }
}

function findPDFFolderInParent(parentFolder) {
  const folders = parentFolder.getFoldersByName('PDF Files');
  return folders.hasNext() ? folders.next() : null;
}
function getLatestPDFVersion(pdfFolder, spreadsheetName) {
  Logger.log(`Getting latest PDF version for spreadsheet: "${spreadsheetName}"`);

  const orderParts = spreadsheetName.split('Order_');
  if (orderParts.length < 2) {
    Logger.log(`Cannot extract order ID from spreadsheet name: "${spreadsheetName}"`);
    return -1;
  }

  const orderId = orderParts[1];
  Logger.log(`Extracted order ID: "${orderId}"`);
  Logger.log(`Looking for PDF files with pattern: "${orderId}_v*.pdf"`);

  const files = pdfFolder.getFiles();
  let maxVersion = -1;
  let foundFiles = [];
  let allPdfFiles = [];

  while (files.hasNext()) {
    const file = files.next();
    const fileName = file.getName();

    // Log all PDF files for debugging
    if (file.getMimeType() === 'application/pdf') {
      allPdfFiles.push(fileName);
    }

    // Check if it matches our naming pattern: {orderId}_v{number}.pdf
    if (file.getMimeType() === 'application/pdf' && fileName.startsWith(`${orderId}_v`)) {
      foundFiles.push(fileName);
      const versionMatch = fileName.match(/_v(\d+)\.pdf$/);
      if (versionMatch) {
        const version = parseInt(versionMatch[1]);
        maxVersion = Math.max(maxVersion, version);
        Logger.log(`Found matching PDF version ${version}: ${fileName}`);
      }
    }
  }

  Logger.log(`All PDF files in folder: ${allPdfFiles.join(', ')}`);
  Logger.log(`Found ${foundFiles.length} matching PDF files for order "${orderId}"`);
  Logger.log(`Latest version found: ${maxVersion}`);

  if (foundFiles.length > 0) {
    Logger.log(`Matching files: ${foundFiles.join(', ')}`);
  }

  return maxVersion;
}

// Utility functions for managing the new scalable system

// Clear all script properties (useful for testing and reset)
function clearScriptProperties() {
  PropertiesService.getScriptProperties().deleteAllProperties();
  Logger.log('Cleared all script properties.');
}

// Get status of the monitoring system
function getMonitoringStatus() {
  try {
    const scriptProperties = PropertiesService.getScriptProperties();
    const registryJson = scriptProperties.getProperty('sheetRegistry');

    if (!registryJson) {
      Logger.log('No sheet registry found.');
      return;
    }

    const registry = JSON.parse(registryJson);
    const sheetCount = Object.keys(registry).length;

    Logger.log(`=== Monitoring System Status ===`);
    Logger.log(`Total sheets monitored: ${sheetCount}`);
    Logger.log(`Monitoring interval: ${MONITORING_INTERVAL_MINUTES} minute(s)`);
    Logger.log(`Debounce delay: ${DEBOUNCE_DELAY_SECONDS} second(s)`);

    // Show recent activity
    const now = new Date().getTime();
    let recentChanges = 0;
    let pendingProcessing = 0;

    for (const [sheetId, info] of Object.entries(registry)) {
      const timeSinceModified = (now - info.lastModified) / (1000 * 60); // minutes

      if (timeSinceModified < 60) { // Modified in last hour
        recentChanges++;
      }

      // Check for pending processing
      const pendingKey = `pending_${sheetId}`;
      if (scriptProperties.getProperty(pendingKey)) {
        pendingProcessing++;
      }
    }

    Logger.log(`Sheets modified in last hour: ${recentChanges}`);
    Logger.log(`Sheets pending processing: ${pendingProcessing}`);

    // Show active triggers
    const triggers = ScriptApp.getProjectTriggers();
    const monitoringTriggers = triggers.filter(t =>
      t.getHandlerFunction() === 'monitorAllSheets' ||
      t.getHandlerFunction() === 'updateSheetRegistry'
    ).length;
    const delayedTriggers = triggers.filter(t => t.getHandlerFunction() === 'processDelayedEdit').length;

    Logger.log(`Active monitoring triggers: ${monitoringTriggers}`);
    Logger.log(`Active delayed processing triggers: ${delayedTriggers}`);
    Logger.log(`Total triggers: ${triggers.length}/20`);

  } catch (error) {
    Logger.log(`Error getting monitoring status: ${error.toString()}`);
  }
}

// Force process all pending sheets (useful for testing)
function forceProcessAllPending() {
  try {
    const scriptProperties = PropertiesService.getScriptProperties();
    const allProperties = scriptProperties.getProperties();

    let processedCount = 0;
    for (const [key, value] of Object.entries(allProperties)) {
      if (key.startsWith('pending_')) {
        try {
          const pendingData = JSON.parse(value);
          if (pendingData.sheetId) {
            Logger.log(`Force processing sheet: ${pendingData.sheetName}`);

            const spreadsheet = SpreadsheetApp.openById(pendingData.sheetId);
            const sheet = spreadsheet.getActiveSheet();

            if (spreadsheet && sheet) {
              generatePDFLocally(spreadsheet, sheet);
              deletePendingTriggersForSheet(pendingData.sheetId);
              updateSheetProcessedTime(pendingData.sheetId);
              processedCount++;
            }
          }
        } catch (e) {
          Logger.log(`Error processing pending sheet ${key}: ${e.toString()}`);
        }
      }
    }

    Logger.log(`Force processed ${processedCount} pending sheets.`);

  } catch (error) {
    Logger.log(`Error in forceProcessAllPending: ${error.toString()}`);
  }
}

// Reset the entire monitoring system
function resetMonitoringSystem() {
  Logger.log('Resetting monitoring system...');

  // Clean up all triggers
  cleanupTriggers();

  // Clear all properties
  clearScriptProperties();

  // Reinitialize
  initializeFolderMonitoring();

  Logger.log('Monitoring system reset complete.');
}

// Test function to verify the new system is working
function testNewSystem() {
  Logger.log('=== TESTING NEW SCALABLE MONITORING SYSTEM ===');

  try {
    // Test 1: Check if registry exists and has sheets
    const registryJson = PropertiesService.getScriptProperties().getProperty('sheetRegistry');
    if (!registryJson) {
      Logger.log('❌ No sheet registry found. Run initializeFolderMonitoring() first.');
      return;
    }

    const registry = JSON.parse(registryJson);
    const sheetCount = Object.keys(registry).length;
    Logger.log(`✅ Registry found with ${sheetCount} sheets`);

    // Test 2: Check triggers
    const triggers = ScriptApp.getProjectTriggers();
    const monitoringTrigger = triggers.find(t => t.getHandlerFunction() === 'monitorAllSheets');
    const registryTrigger = triggers.find(t => t.getHandlerFunction() === 'updateSheetRegistry');

    if (monitoringTrigger && registryTrigger) {
      Logger.log('✅ Both required triggers are active');
      Logger.log(`   - monitorAllSheets: ${monitoringTrigger.getEventType()}`);
      Logger.log(`   - updateSheetRegistry: ${registryTrigger.getEventType()}`);
    } else {
      Logger.log('❌ Missing required triggers');
      if (!monitoringTrigger) Logger.log('   - Missing: monitorAllSheets');
      if (!registryTrigger) Logger.log('   - Missing: updateSheetRegistry');
    }

    // Test 3: Test monitoring function manually
    Logger.log('Testing monitoring function...');
    monitorAllSheets();

    // Test 4: Show system status
    getMonitoringStatus();

    Logger.log('=== TEST COMPLETE ===');
    Logger.log('If no errors above, the new system is working correctly!');

  } catch (error) {
    Logger.log(`❌ Test failed: ${error.toString()}`);
  }
}



/**
 * Get sheet data and convert to template variables format
 * Replicates the Python backend's get_sheet_data functionality
 */
function getSheetData(spreadsheetId) {
    try {
        Logger.log(`Getting sheet data for spreadsheet: ${spreadsheetId}`);

        const spreadsheet = SpreadsheetApp.openById(spreadsheetId);
        const sheet = spreadsheet.getActiveSheet();

        // Get data from A1:AA100 to capture all placements
        const range = sheet.getRange('A1:AA100');
        const values = range.getValues();

        if (values.length < 2) {
            throw new Error('Sheet does not contain enough data');
        }

        const headers = values[0]; // First row contains headers
        const dataRows = values.slice(1).filter(row => row.some(cell => cell !== '')); // Filter out empty rows

        Logger.log(`Found ${headers.length} headers and ${dataRows.length} data rows`);
        Logger.log(`Headers: ${headers.join(', ')}`);

        // Log first data row for debugging
        if (dataRows.length > 0) {
            Logger.log(`First data row: ${dataRows[0].join(', ')}`);
        }

        // Process multiple placement rows
        const placements = [];
        let orderData = {};

        // Extract order-level data from first row
        if (dataRows.length > 0) {
            const firstRow = dataRows[0];
            orderData = extractOrderData(headers, firstRow);
        }

        // Process each placement row
        let totalImpressions = 0;
        let totalClicks = 0;
        let totalBudget = 0;
        const mediaplanTableRows = [];

        for (let i = 0; i < dataRows.length; i++) {
            const row = dataRows[i];
            const placement = extractPlacementData(headers, row);

            if (placement) {
                placements.push(placement);

                // Add to totals
                totalImpressions += placement.impressions || 0;
                totalClicks += placement.clicks || 0;
                totalBudget += placement.budget || 0;

                // Create table row for media plan
                const tableRow = [
                    `$${(placement.budget || 0).toLocaleString('en-US', {minimumFractionDigits: 2})}`,
                    placement.startDate || '',
                    placement.endDate || '',
                    placement.name || '',
                    placement.destination || '',
                    placement.targeting || '',
                    placement.objectiveDescription || orderData.objectiveDescription || '',
                    (placement.impressions || 0).toLocaleString('en-US'),
                    (placement.clicks || 0).toLocaleString('en-US'),
                    `$${placement.cpm || '0.00'}`,
                    `$${placement.cpc || '0.00'}`
                ];
                mediaplanTableRows.push(tableRow);
            }
        }

        // Create media plan table structure
        const mediaPlanTable = {
            headers: [
                'Budget',
                'Start Date',
                'End Date',
                'Placement Name',
                'Placement Destination',
                'Targeting',
                'Objective Description',
                'Target Impressions',
                'Target Clicks',
                'CPM',
                'CPC'
            ],
            rows: mediaplanTableRows
        };

        // Get overall date range
        const startDates = placements.map(p => p.startDate).filter(d => d);
        const endDates = placements.map(p => p.endDate).filter(d => d);
        const earliestStart = startDates.length > 0 ? startDates.sort()[0] : '';
        const latestEnd = endDates.length > 0 ? endDates.sort().reverse()[0] : '';

        // Create template variables
        const templateData = {
            order_number: orderData.orderNumber || '',
            brand: orderData.brand || '',
            campaign_name: orderData.campaignName || '',
            customer_approver: orderData.customerApprover || '',
            customer_approver_email: orderData.customerApproverEmail || '',
            sales_owner: orderData.salesOwner || '',
            sales_owner_email: orderData.salesOwnerEmail || '',
            fulfillment_owner: orderData.fulfillmentOwner || '',
            fulfillment_owner_email: orderData.fulfillmentOwnerEmail || '',
            start_date: earliestStart,
            end_date: latestEnd,
            total_impressions: totalImpressions.toLocaleString('en-US'),
            total_clicks: totalClicks.toLocaleString('en-US'),
            cpm: placements.length > 0 ? `$${placements[0].cpm || '0.00'}` : '$0.00',
            cpc: placements.length > 0 ? `$${placements[0].cpc || '0.00'}` : '$0.00',
            budget_amount: totalBudget.toLocaleString('en-US', {minimumFractionDigits: 2}),
            age_range: 'Multiple (see placement details)',
            gender: 'Multiple (see placement details)',
            income_level: 'Multiple (see placement details)',
            interests: 'Multiple (see placement details)',
            location: 'Multiple (see placement details)',
            audience_segments: 'Multiple (see placement details)',
            device_targeting: 'All Devices',
            objective_description: orderData.objectiveDescription || '',
            generation_date: new Date().toISOString().split('T')[0],
            media_plan_table: mediaPlanTable
        };

        Logger.log(`Successfully extracted sheet data for ${placements.length} placements`);
        return templateData;

    } catch (error) {
        Logger.log(`Error getting sheet data: ${error.toString()}`);
        throw error;
    }
}

/**
 * Extract order-level data from the first row
 * Updated to match the actual Google Sheet column headers
 */
function extractOrderData(headers, row) {
    const orderData = {};

    for (let i = 0; i < headers.length && i < row.length; i++) {
        const header = headers[i].toString().trim(); // Keep original case for exact matching
        const value = row[i] ? row[i].toString().trim() : '';

        // Log header mapping for debugging
        if (value) {
            Logger.log(`Order Header: "${header}" = "${value}"`);
        }

        switch (header) {
            case 'Order Number':
                orderData.orderNumber = value;
                break;
            case 'Brand':
                orderData.brand = value;
                break;
            case 'Campaign Name':
                orderData.campaignName = value;
                break;
            case 'Customer Approver':
                orderData.customerApprover = value;
                break;
            case 'Customer Approver Email':
                orderData.customerApproverEmail = value;
                break;
            case 'Sales Owner':
                orderData.salesOwner = value;
                break;
            case 'Sales Owner Email':
                orderData.salesOwnerEmail = value;
                break;
            case 'Fulfillment Owner':
                orderData.fulfillmentOwner = value;
                break;
            case 'Fulfillment Owner Email':
                orderData.fulfillmentOwnerEmail = value;
                break;
            case 'objective_description':
                orderData.objectiveDescription = value;
                break;
        }
    }

    Logger.log(`Extracted order data: ${JSON.stringify(orderData)}`);
    return orderData;
}

/**
 * Extract placement-specific data from a row
 * Updated to match the actual Google Sheet column headers
 */
function extractPlacementData(headers, row) {
    const placement = {};

    for (let i = 0; i < headers.length && i < row.length; i++) {
        const header = headers[i].toString().trim(); // Keep original case for exact matching
        const value = row[i] ? row[i].toString().trim() : '';

        // Log header mapping for debugging
        if (value) {
            Logger.log(`Header: "${header}" = "${value}"`);
        }

        switch (header) {
            case 'Placement Name':
                placement.name = value;
                break;
            case 'Placement Destination':
                placement.destination = value;
                break;
            case 'Start Date':
                placement.startDate = value;
                break;
            case 'End Date':
                placement.endDate = value;
                break;
            case 'Budget Amount':
                placement.budget = parseFloat(value.replace(/[$,]/g, '')) || 0;
                break;
            case 'Metrics - Impressions':
                placement.impressions = parseInt(value.replace(/[,]/g, '')) || 0;
                break;
            case 'Metrics - Clicks':
                placement.clicks = parseInt(value.replace(/[,]/g, '')) || 0;
                break;
            case 'bid_rate - cpm':
                placement.cpm = parseFloat(value.replace(/[$,]/g, '')) || 0;
                break;
            case 'bid_rate - cpc':
                placement.cpc = parseFloat(value.replace(/[$,]/g, '')) || 0;
                break;
            case 'target audience - age_range':
            case 'target audience - gender':
            case 'target audience - income level':
            case 'target audience - interests':
            case 'target audience - location':
            case 'target_audience - behavioral_data':
                // Combine targeting fields
                if (!placement.targeting) placement.targeting = '';
                if (value && placement.targeting.indexOf(value) === -1) {
                    placement.targeting += (placement.targeting ? ', ' : '') + value;
                }
                break;
            case 'objective_description':
                placement.objectiveDescription = value;
                break;
        }
    }

    // Log extracted placement data
    Logger.log(`Extracted placement: ${JSON.stringify(placement)}`);

    // Only return placement if it has essential data
    if (placement.name || placement.destination) {
        return placement;
    }

    return null;
}

/**
 * Create PDF from template using Google Docs API
 * Replicates the Python backend's PDF generation functionality
 */
function createPDFFromTemplate(templateVariables, outputFolderId, filename) {
    try {
        Logger.log(`Creating PDF from template with filename: ${filename}`);

        if (!PDF_GENERATION_TEMPLATE_ID) {
            throw new Error('PDF_GENERATION_TEMPLATE_ID not configured');
        }

        // 1. Create a copy of the template
        const templateFile = DriveApp.getFileById(PDF_GENERATION_TEMPLATE_ID);
        const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
        const tempName = `Generated_IO_${timestamp}`;

        const copiedFile = templateFile.makeCopy(tempName, DriveApp.getFolderById(outputFolderId));
        const docId = copiedFile.getId();

        Logger.log(`Created document copy with ID: ${docId}`);

        // 2. Replace text placeholders (excluding media_plan_table)
        replaceTextPlaceholders(docId, templateVariables);

        // 3. Handle media plan table insertion
        if (templateVariables.media_plan_table) {
            insertMediaPlanTable(docId, templateVariables.media_plan_table);
        }

        // 4. Export as PDF
        const pdfBlob = DriveApp.getFileById(docId).getAs('application/pdf');

        // 5. Create PDF file in Drive
        const pdfFilename = `${filename}.pdf`;
        const pdfFile = DriveApp.getFolderById(outputFolderId).createFile(pdfBlob.setName(pdfFilename));

        // 6. Clean up temporary document
        DriveApp.getFileById(docId).setTrashed(true);

        Logger.log(`PDF created successfully: ${pdfFilename}`);

        return {
            success: true,
            fileId: pdfFile.getId(),
            webViewLink: pdfFile.getUrl(),
            filename: pdfFilename
        };

    } catch (error) {
        Logger.log(`Error creating PDF from template: ${error.toString()}`);
        return {
            success: false,
            error: error.toString()
        };
    }
}

/**
 * Replace text placeholders in the document
 */
function replaceTextPlaceholders(docId, templateVariables) {
    try {
        const doc = DocumentApp.openById(docId);
        const body = doc.getBody();

        for (const [key, value] of Object.entries(templateVariables)) {
            if (key !== 'media_plan_table') {
                const placeholder = `{{${key}}}`;
                const replacement = value ? value.toString() : '';
                body.replaceText(placeholder, replacement);
                Logger.log(`Replaced ${placeholder} with: ${replacement.substring(0, 50)}${replacement.length > 50 ? '...' : ''}`);
            }
        }

        doc.saveAndClose();
        Logger.log('Text placeholders replaced successfully');

    } catch (error) {
        Logger.log(`Error replacing text placeholders: ${error.toString()}`);
        throw error;
    }
}

/**
 * Insert media plan table into the document
 * Replicates the Python backend's table insertion functionality
 */
function insertMediaPlanTable(docId, tableData) {
    try {
        Logger.log('Starting media plan table insertion...');

        const headers = tableData.headers || [];
        const rows = tableData.rows || [];

        if (!headers.length || !rows.length) {
            Logger.log('No table headers or rows provided for media_plan_table');
            fallbackTextReplacement(docId, tableData);
            return;
        }

        Logger.log(`Creating table with ${headers.length} columns and ${rows.length + 1} rows`);

        const doc = DocumentApp.openById(docId);
        const body = doc.getBody();

        // Find and replace the {{media_plan_table}} placeholder
        const placeholder = '{{media_plan_table}}';
        const searchResult = body.findText(placeholder);

        if (!searchResult) {
            Logger.log('{{media_plan_table}} placeholder not found in document');
            fallbackTextReplacement(docId, tableData);
            return;
        }

        // Get the element containing the placeholder
        const element = searchResult.getElement();
        const parent = element.getParent();

        // Create table with proper dimensions
        const numCols = headers.length;

        // Insert table after the paragraph containing the placeholder
        const table = body.insertTable(body.getChildIndex(parent) + 1, [headers, ...rows]);

        // Format the header row (make it bold)
        const headerRow = table.getRow(0);
        for (let col = 0; col < numCols; col++) {
            const cell = headerRow.getCell(col);
            cell.getChild(0).asParagraph().getChild(0).asText().setBold(true);
        }

        // Remove the placeholder text
        const textElement = element.asText();
        const startOffset = searchResult.getStartOffset();
        const endOffset = searchResult.getEndOffsetInclusive();
        textElement.deleteText(startOffset, endOffset);

        doc.saveAndClose();
        Logger.log(`Successfully created and populated table with ${headers.length} headers and ${rows.length} data rows`);

    } catch (error) {
        Logger.log(`Error inserting media plan table: ${error.toString()}`);
        // Fallback to simple text replacement
        fallbackTextReplacement(docId, tableData);
    }
}

/**
 * Fallback method to replace {{media_plan_table}} with formatted text if table insertion fails
 */
function fallbackTextReplacement(docId, tableData) {
    try {
        const headers = tableData.headers || [];
        const rows = tableData.rows || [];

        let fallbackText;
        if (!headers.length || !rows.length) {
            fallbackText = 'No table data available';
        } else {
            // Create a simple text table
            const lines = [];

            // Add headers
            lines.push(headers.join(' | '));
            lines.push('-'.repeat(50)); // Separator line

            // Add rows
            for (const row of rows) {
                if (Array.isArray(row)) {
                    lines.push(row.join(' | '));
                } else {
                    lines.push(row.toString());
                }
            }

            fallbackText = lines.join('\n');
        }

        const doc = DocumentApp.openById(docId);
        const body = doc.getBody();
        body.replaceText('{{media_plan_table}}', fallbackText);
        doc.saveAndClose();

        Logger.log('Used fallback text replacement for media_plan_table');

    } catch (error) {
        Logger.log(`Error in fallback text replacement: ${error.toString()}`);
    }
}
