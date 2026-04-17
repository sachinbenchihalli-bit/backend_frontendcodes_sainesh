import { NextRequest, NextResponse } from 'next/server';

/**
 * API Proxy for Adopt Dashboard Backend
 *
 * Configuration via environment variables:
 * - BACKEND_HOST: Backend hostname (e.g., "localhost", "api.example.com")
 * - BACKEND_PORT: Backend port (e.g., "3001", "443", "80")
 * - BACKEND_PROTOCOL: Protocol to use ("http" or "https")
 *
 * Examples:
 * Local development: BACKEND_HOST=localhost, BACKEND_PORT=3001, BACKEND_PROTOCOL=http
 * External HTTPS API: BACKEND_HOST=api.example.com, BACKEND_PORT=443, BACKEND_PROTOCOL=https
 * External HTTP API: BACKEND_HOST=api.example.com, BACKEND_PORT=8080, BACKEND_PROTOCOL=http
 */

// Backend service configuration
const BACKEND_HOST = process.env.BACKEND_HOST || 'backend';
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

// Request timeout in milliseconds
const REQUEST_TIMEOUT = 120000; // 2 mins

/**
 * Creates a timeout promise that rejects after the specified time
 */
function createTimeoutPromise(timeoutMs: number): Promise<never> {
  return new Promise((_, reject) => {
    setTimeout(() => reject(new Error('Request timeout')), timeoutMs);
  });
}

/**
 * Forwards a request to the backend service
 */
async function forwardRequest(
  method: string,
  path: string,
  request: NextRequest
): Promise<NextResponse> {
  const startTime = Date.now();

  try {
    // Construct the backend URL
    const backendUrl = new URL(path, BACKEND_BASE_URL);

    // Copy query parameters from the original request
    const searchParams = request.nextUrl.searchParams;
    searchParams.forEach((value, key) => {
      backendUrl.searchParams.append(key, value);
    });

    // Prepare headers for the backend request
    const headers = new Headers();

    // Copy relevant headers from the original request
    const headersToForward = [
      'content-type',
      'authorization',
      'accept',
      'accept-language',
      'cache-control',
      'user-agent',
      'x-forwarded-for',
      'x-real-ip'
    ];

    headersToForward.forEach(headerName => {
      const headerValue = request.headers.get(headerName);
      if (headerValue) {
        headers.set(headerName, headerValue);
      }
    });

    // Add custom headers for backend identification
    headers.set('X-Forwarded-By', 'adopt-dashboard-proxy');

    // Prepare the request body for methods that support it
    let body: BodyInit | null = null;
    if (['POST', 'PUT', 'PATCH'].includes(method.toUpperCase())) {
      try {
        const contentType = request.headers.get('content-type');
        if (contentType?.includes('application/json')) {
          // For JSON content, parse and re-stringify to ensure valid JSON
          const jsonBody = await request.json();
          body = JSON.stringify(jsonBody);
        } else {
          // For other content types, read as text
          body = await request.text();
        }
      } catch (error) {
        console.warn(`[API Proxy] Failed to read request body for ${method} ${path}:`, error);
        // Continue without body if reading fails
      }
    }

    // Log the outgoing request (in development)
    if (process.env.NODE_ENV === 'development') {
      console.log(`[API Proxy] Forwarding ${method} ${backendUrl.toString()}`);
      console.log(`[API Proxy] Backend config: ${BACKEND_PROTOCOL}://${BACKEND_HOST}:${BACKEND_PORT}`);
    }

    // Create the fetch request with timeout
    const fetchPromise = fetch(backendUrl.toString(), {
      method,
      headers,
      body,
    });

    // Race between the fetch request and timeout
    const response = await Promise.race([
      fetchPromise,
      createTimeoutPromise(REQUEST_TIMEOUT)
    ]);

    // Read the response body
    let responseBody: string;
    try {
      responseBody = await response.text();
    } catch (error) {
      console.error(`[API Proxy] Failed to read response body for ${method} ${path}:`, error);
      responseBody = '';
    }

    // Prepare response headers
    const responseHeaders = new Headers();

    // Copy relevant headers from the backend response
    const headersToReturn = [
      'content-type',
      'content-length',
      'cache-control',
      'expires',
      'last-modified',
      'etag'
    ];

    headersToReturn.forEach(headerName => {
      const headerValue = response.headers.get(headerName);
      if (headerValue) {
        responseHeaders.set(headerName, headerValue);
      }
    });

    // Add CORS headers for browser compatibility
    responseHeaders.set('Access-Control-Allow-Origin', '*');
    responseHeaders.set('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, PATCH, OPTIONS');
    responseHeaders.set('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With');

    // Add proxy identification headers
    responseHeaders.set('X-Proxied-By', 'nextjs-api-proxy');
    responseHeaders.set('X-Response-Time', `${Date.now() - startTime}ms`);

    // Log the response (in development)
    if (process.env.NODE_ENV === 'development') {
      const responseTime = Date.now() - startTime;
      console.log(`[API Proxy] ${method} ${path} -> ${response.status} (${responseTime}ms)`);
    }

    // Return the proxied response
    return new NextResponse(responseBody, {
      status: response.status,
      statusText: response.statusText,
      headers: responseHeaders,
    });

  } catch (error) {
    const responseTime = Date.now() - startTime;
    console.error(`[API Proxy] Error forwarding ${method} ${path} (${responseTime}ms):`, error);

    // Return appropriate error response based on error type
    if (error instanceof Error) {
      if (error.message === 'Request timeout') {
        return NextResponse.json(
          {
            error: 'Gateway Timeout',
            message: 'The backend service did not respond in time',
            details: `Request timed out after ${REQUEST_TIMEOUT}ms`
          },
          { status: 504 }
        );
      }

      if (error.message.indexOf('ECONNREFUSED') !== -1 || error.message.indexOf('fetch failed') !== -1) {
        return NextResponse.json(
          {
            error: 'Bad Gateway',
            message: 'Unable to connect to backend service',
            details: 'The backend service may be down or unreachable'
          },
          { status: 502 }
        );
      }
    }

    // Generic error response
    return NextResponse.json(
      {
        error: 'Internal Server Error',
        message: 'An unexpected error occurred while proxying the request',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}

// HTTP method handlers
export async function GET(
  request: NextRequest,
  { params }: { params: { path: string[] } }
): Promise<NextResponse> {
  const path = '/' + (params.path?.join('/') || '');
  return forwardRequest('GET', path, request);
}

export async function POST(
  request: NextRequest,
  { params }: { params: { path: string[] } }
): Promise<NextResponse> {
  const path = '/' + (params.path?.join('/') || '');
  return forwardRequest('POST', path, request);
}

export async function PUT(
  request: NextRequest,
  { params }: { params: { path: string[] } }
): Promise<NextResponse> {
  const path = '/' + (params.path?.join('/') || '');
  return forwardRequest('PUT', path, request);
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: { path: string[] } }
): Promise<NextResponse> {
  const path = '/' + (params.path?.join('/') || '');
  return forwardRequest('DELETE', path, request);
}

export async function PATCH(
  request: NextRequest,
  { params }: { params: { path: string[] } }
): Promise<NextResponse> {
  const path = '/' + (params.path?.join('/') || '');
  return forwardRequest('PATCH', path, request);
}

export async function OPTIONS(
  _request: NextRequest,
  { params: _params }: { params: { path: string[] } }
): Promise<NextResponse> {
  // Handle CORS preflight requests
  return new NextResponse(null, {
    status: 200,
    headers: {
      'Access-Control-Allow-Origin': '*',
      'Access-Control-Allow-Methods': 'GET, POST, PUT, DELETE, PATCH, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type, Authorization',
      'Access-Control-Max-Age': '86400',
    },
  });
}
