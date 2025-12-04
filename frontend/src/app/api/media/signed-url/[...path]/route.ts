/**
 * API route to proxy signed URL requests to ai-orchestrator.
 *
 * This proxies requests from /api/media/signed-url/[path] to
 * the ai-orchestrator's /api/v1/media/signed-url/[path] endpoint.
 */

import { NextRequest, NextResponse } from 'next/server';

const AI_ORCHESTRATOR_URL = process.env.NEXT_PUBLIC_AI_ORCHESTRATOR_URL || 'http://localhost:8001';

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ path: string[] }> }
) {
  try {
    const { path } = await params;
    const objectPath = path.join('/');
    const searchParams = request.nextUrl.searchParams;
    const expiration = searchParams.get('expiration') || '60';

    // Forward request to ai-orchestrator
    const url = `${AI_ORCHESTRATOR_URL}/api/v1/media/signed-url/${encodeURIComponent(objectPath)}?expiration=${expiration}`;

    const response = await fetch(url, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('Signed URL API error:', response.status, errorText);
      return NextResponse.json(
        { error: 'Failed to generate signed URL' },
        { status: response.status }
      );
    }

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    console.error('Signed URL proxy error:', error);
    return NextResponse.json(
      { error: 'Internal server error' },
      { status: 500 }
    );
  }
}
