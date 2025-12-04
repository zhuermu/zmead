/**
 * API Route for fetching GCS signed URLs
 * 
 * This endpoint proxies requests to the backend to get signed URLs
 * for GCS objects (images/videos stored in Google Cloud Storage).
 */

import { NextRequest, NextResponse } from 'next/server';

export const runtime = 'nodejs';

export async function GET(
  request: NextRequest,
  { params }: { params: { objectName: string } }
) {
  const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
  const objectName = decodeURIComponent(params.objectName);

  try {
    // Forward auth header if present
    const authHeader = request.headers.get('Authorization');

    const response = await fetch(
      `${backendUrl}/api/v1/media/signed-url/${encodeURIComponent(objectName)}`,
      {
        method: 'GET',
        headers: {
          ...(authHeader ? { 'Authorization': authHeader } : {}),
        },
      }
    );

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[Signed URL API] Backend error:', response.status, errorText);
      return NextResponse.json(
        { error: errorText || `HTTP ${response.status}` },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);

  } catch (error) {
    console.error('[Signed URL API] Error:', error);
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Internal server error' },
      { status: 500 }
    );
  }
}
