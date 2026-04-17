import { NextRequest, NextResponse } from 'next/server';

// Backend service configuration using standardized environment variables
const BACKEND_HOST = process.env.BACKEND_HOST || 'localhost';
const BACKEND_PORT = process.env.BACKEND_PORT || '3001';
const BACKEND_PROTOCOL = process.env.BACKEND_PROTOCOL || 'http';

// Construct backend URL with proper protocol and port handling
const constructBackendUrl = (): string => {
  const isHttps = BACKEND_PROTOCOL === 'https';
  const defaultPort = isHttps ? '443' : '80';

  // Don't include port if it's the default port for the protocol
  const shouldIncludePort = BACKEND_PORT !== defaultPort && BACKEND_PORT !== '';

  return `${BACKEND_PROTOCOL}://${BACKEND_HOST}${shouldIncludePort ? ':' + BACKEND_PORT : ''}`;
};

const BACKEND_BASE_URL = constructBackendUrl();

export async function GET(
  request: NextRequest,
  { params }: { params: { campaignId: string } }
) {
  try {
    const { campaignId } = params;

    // Fetch campaign data from the adopt backend using standardized URL construction
    const response = await fetch(`${BACKEND_BASE_URL}/api/campaigns/${campaignId}`, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      if (response.status === 404) {
        return NextResponse.json(
          { error: 'Campaign not found', success: false },
          { status: 404 }
        );
      }
      
      throw new Error(`Backend responded with status: ${response.status}`);
    }

    const data = await response.json();
    
    return NextResponse.json(data);
  } catch (error) {
    console.error('Error fetching campaign:', error);
    
    return NextResponse.json(
      { 
        error: 'Failed to fetch campaign data', 
        success: false,
        message: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}
