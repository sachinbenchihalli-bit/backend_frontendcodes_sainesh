import type { SalesforceAccount, SalesforceOpportunity } from './interfaces';

/**
 * Fetch Salesforce Accounts from the backend API
 */
export async function fetchSalesforceAccounts(): Promise<SalesforceAccount[]> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/salesforce/accounts`);

    if (!response.ok) {
      throw new Error(`Failed to fetch Salesforce accounts: ${response.status} ${response.statusText}`);
    }

    const accounts = await response.json();

    // Transform the Salesforce API response to match our interface
    return accounts.map((account: any) => ({
      id: account.Id,
      name: account.Name,
      type: account.Type || 'Customer',
      industry: account.Industry || 'Unknown'
    }));
  } catch (error) {
    console.error('Error fetching Salesforce accounts:', error);
    throw new Error('Unable to load Salesforce accounts. Please check your connection and try again.');
  }
}

/**
 * Fetch Salesforce Opportunities for a specific Account
 */
export async function fetchSalesforceOpportunitiesByAccount(accountId: string): Promise<SalesforceOpportunity[]> {
  try {
    const response = await fetch(`${process.env.NEXT_PUBLIC_MEDIA_BACKEND_URL}/salesforce/opportunities-by-account/${accountId}`);

    if (!response.ok) {
      throw new Error(`Failed to fetch Salesforce opportunities for account: ${response.status} ${response.statusText}`);
    }

    const opportunities = await response.json();

    // Transform the Salesforce API response to match our interface
    return opportunities.map((opportunity: any) => ({
      id: opportunity.Id,
      name: opportunity.Name,
      stageName: opportunity.StageName || 'Unknown',
      amount: opportunity.Amount || 0,
      closeDate: opportunity.CloseDate || '',
      accountName: opportunity.Account?.Name || opportunity.Account__r?.Name || 'Unknown'
    }));
  } catch (error) {
    console.error('Error fetching Salesforce opportunities by account:', error);
    throw new Error('Unable to load opportunities for the selected account. Please check your connection and try again.');
  }
}

/**
 * Helper function to convert Salesforce Accounts to CommonSelectOption format
 */
export function salesforceAccountsToSelectOptions(accounts: SalesforceAccount[]) {
  return accounts.map(account => ({
    value: account.id,
    label: account.name,
    extras: {
      postfix: {
        label: account.industry ? `${account.type} - ${account.industry}` : account.type || '',
        tooltip: `Account Type: ${account.type}${account.industry ? `, Industry: ${account.industry}` : ''}`
      }
    }
  }));
}

/**
 * Helper function to convert Salesforce Opportunities to CommonSelectOption format
 */
export function salesforceOpportunitiesToSelectOptions(opportunities: SalesforceOpportunity[]) {
  return opportunities.map(opportunity => ({
    value: opportunity.id,
    label: opportunity.name,
    extras: {
      postfix: {
        label: opportunity.stageName ? `${opportunity.stageName}${opportunity.amount ? ` - $${opportunity.amount.toLocaleString()}` : ''}` : '',
        tooltip: `Stage: ${opportunity.stageName}${opportunity.amount ? `, Amount: $${opportunity.amount.toLocaleString()}` : ''}${opportunity.closeDate ? `, Close Date: ${opportunity.closeDate}` : ''}`
      }
    }
  }));
}

/**
 * Search function for Salesforce Account options
 * Returns array of searchable strings for each account option
 */
export function getAccountSearchFields(option: any) {
  const fields = [
    option.label || '', // Account name
    option.value || '', // Account ID
  ];

  // Add type and industry from extras
  if (option.extras?.postfix?.label) {
    fields.push(option.extras.postfix.label);
  }

  return fields.filter(field => field.length > 0);
}
