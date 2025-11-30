export const runtime = 'edge';

export async function POST(req: Request) {
  try {
    const body = await req.json();
    
    // AI SDK v5 sends messages in different formats
    // Handle both old format (messages array) and new format (parts)
    let messages = body.messages;
    
    // If no messages array, try to extract from AI SDK v5 format
    if (!messages && body.parts) {
      // Convert parts format to messages format
      const textPart = body.parts.find((p: any) => p.type === 'text');
      if (textPart) {
        messages = [{ role: 'user', content: textPart.text }];
      }
    }
    
    // If still no messages, try prompt field
    if (!messages && body.prompt) {
      messages = [{ role: 'user', content: body.prompt }];
    }

    if (!messages || messages.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No messages provided' }),
        { status: 422, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Get authorization token from request headers
    const authHeader = req.headers.get('authorization');
    
    // Forward to backend AI Orchestrator
    const backendUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
    const response = await fetch(`${backendUrl}/api/v1/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(authHeader && { 'Authorization': authHeader }),
      },
      body: JSON.stringify({ messages }),
    });

    if (!response.ok) {
      const error = await response.json();
      return new Response(JSON.stringify(error), {
        status: response.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Return streaming response directly
    return new Response(response.body, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
      },
    });
  } catch (error) {
    console.error('Chat API error:', error);
    return new Response(
      JSON.stringify({
        error: 'Internal server error',
        message: error instanceof Error ? error.message : 'Unknown error',
      }),
      {
        status: 500,
        headers: { 'Content-Type': 'application/json' },
      }
    );
  }
}
