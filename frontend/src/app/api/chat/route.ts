/**
 * Chat API Route with Node.js Runtime
 *
 * Uses Node.js Runtime for local development compatibility.
 * Proxies requests to AI Orchestrator and forwards SSE events.
 */

export const runtime = 'nodejs';
export const dynamic = 'force-dynamic';

// Helper to extract string content from message (handles legacy AI SDK v5 format)
function getMessageContent(msg: any): string {
  if (typeof msg.content === 'string') {
    return msg.content;
  }
  if (Array.isArray(msg.content)) {
    return msg.content
      .filter((part: any) => part.type === 'text')
      .map((part: any) => part.text || '')
      .join('');
  }
  if (Array.isArray(msg.parts)) {
    return msg.parts
      .filter((part: any) => part.type === 'text')
      .map((part: any) => part.text || '')
      .join('');
  }
  return '';
}

export async function POST(req: Request) {
  // Use 127.0.0.1 instead of localhost for Edge Runtime compatibility
  const aiOrchestratorUrl = process.env.AI_ORCHESTRATOR_URL || 'http://127.0.0.1:8001';

  try {
    const body = await req.json();

    // Extract user info from headers or body (ensure string type for Pydantic validation)
    const userId = String(body.user_id || req.headers.get('x-user-id') || 'anonymous');
    const sessionId = String(body.session_id || req.headers.get('x-session-id') || `session-${Date.now()}`);

    // Normalize messages format (handle legacy AI SDK v5 format)
    const normalizedMessages = (body.messages || [])
      .map((msg: any) => ({
        role: msg.role,
        content: getMessageContent(msg),
      }))
      .filter((msg: any) => msg.content); // Filter out empty messages

    // Forward request to AI Orchestrator
    const response = await fetch(`${aiOrchestratorUrl}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'text/event-stream',
        // Forward auth header if present
        ...(req.headers.get('Authorization')
          ? { 'Authorization': req.headers.get('Authorization')! }
          : {}),
        // Forward language preference
        ...(req.headers.get('Accept-Language')
          ? { 'Accept-Language': req.headers.get('Accept-Language')! }
          : {}),
      },
      body: JSON.stringify({
        messages: normalizedMessages,
        user_id: userId,
        session_id: sessionId,
      }),
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error('[Chat API] AI Orchestrator error:', response.status, errorText);
      return new Response(
        JSON.stringify({
          type: 'error',
          error: errorText || `HTTP ${response.status}`
        }),
        {
          status: response.status,
          headers: { 'Content-Type': 'application/json' },
        }
      );
    }

    // Stream the response directly without buffering
    // Edge Runtime passes through the stream as-is
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache, no-transform',
        'Connection': 'keep-alive',
        'X-Accel-Buffering': 'no',
      },
    });

  } catch (error) {
    console.error('Chat API error:', error);
    return new Response(
      JSON.stringify({
        type: 'error',
        error: error instanceof Error ? error.message : 'Internal server error',
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
