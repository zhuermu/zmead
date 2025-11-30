export const runtime = 'edge';

export async function POST(req: Request) {
  try {
    const body = await req.json();

    // AI SDK v5 sends messages in different formats
    // Handle both old format (messages with content) and new format (messages with parts)
    let messages: Array<{ role: string; content: string }> = [];

    if (body.messages && Array.isArray(body.messages)) {
      // Process each message - handle both content string and parts array formats
      messages = body.messages.map((msg: any) => {
        // If message has content string, use it directly
        if (typeof msg.content === 'string') {
          return { role: msg.role, content: msg.content };
        }

        // If message has parts array (AI SDK v5 format), extract text
        if (msg.parts && Array.isArray(msg.parts)) {
          const textParts = msg.parts
            .filter((p: any) => p.type === 'text')
            .map((p: any) => p.text)
            .join('');
          return { role: msg.role, content: textParts };
        }

        // Fallback: try to stringify content if it's an object
        return { role: msg.role, content: String(msg.content || '') };
      }).filter((msg: any) => msg.content); // Remove empty messages
    }

    // If no messages from above, try top-level parts (single message format)
    if (messages.length === 0 && body.parts) {
      const textPart = body.parts.find((p: any) => p.type === 'text');
      if (textPart) {
        messages = [{ role: 'user', content: textPart.text }];
      }
    }

    // If still no messages, try prompt field
    if (messages.length === 0 && body.prompt) {
      messages = [{ role: 'user', content: body.prompt }];
    }

    if (messages.length === 0) {
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
      const error = await response.text();
      return new Response(JSON.stringify({ error }), {
        status: response.status,
        headers: { 'Content-Type': 'application/json' },
      });
    }

    // Create a TransformStream to convert backend SSE to AI SDK v5 UI Message Stream format
    const encoder = new TextEncoder();
    const decoder = new TextDecoder();

    // Generate a unique message ID for this response
    const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    let buffer = '';

    const transformStream = new TransformStream({
      async start(controller) {
        // AI SDK v5 requires a 'start' event with messageId at the beginning
        const startMessageEvent = `data: ${JSON.stringify({ type: 'start', messageId: messageId })}\n\n`;
        controller.enqueue(encoder.encode(startMessageEvent));
        // Send text-start event to indicate beginning of text content with message ID
        const startEvent = `data: ${JSON.stringify({ type: 'text-start', id: messageId })}\n\n`;
        controller.enqueue(encoder.encode(startEvent));
      },
      async transform(chunk, controller) {
        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop() || ''; // Keep incomplete line in buffer

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));

              if (data.type === 'token' && data.content) {
                // Convert to AI SDK v5 text-delta format with required id and delta fields
                const deltaEvent = `data: ${JSON.stringify({
                  type: 'text-delta',
                  id: messageId,
                  delta: data.content
                })}\n\n`;
                controller.enqueue(encoder.encode(deltaEvent));
              } else if (data.type === 'thinking' || data.type === 'status' || data.type === 'tool_start' || data.type === 'tool_complete') {
                // Forward agent status events as custom data using AI SDK v5 data-* format
                const statusEvent = `data: ${JSON.stringify({
                  type: 'data-agent-status',
                  data: {
                    statusType: data.type,
                    message: data.message,
                    node: data.node,
                    tool: data.tool,
                  }
                })}\n\n`;
                controller.enqueue(encoder.encode(statusEvent));
              } else if (data.type === 'done') {
                // Send text-end and finish events with message ID
                const textEndEvent = `data: ${JSON.stringify({ type: 'text-end', id: messageId })}\n\n`;
                const finishEvent = `data: ${JSON.stringify({
                  type: 'finish',
                  finishReason: 'stop'
                })}\n\n`;
                controller.enqueue(encoder.encode(textEndEvent));
                controller.enqueue(encoder.encode(finishEvent));
              } else if (data.type === 'error') {
                const errorEvent = `data: ${JSON.stringify({
                  type: 'error',
                  error: data.error?.message || 'Unknown error'
                })}\n\n`;
                controller.enqueue(encoder.encode(errorEvent));
              }
            } catch (e) {
              // Ignore parse errors for incomplete chunks
              console.error('Failed to parse SSE data:', e);
            }
          }
        }
      },
      async flush(controller) {
        // Process any remaining buffer
        if (buffer.startsWith('data: ')) {
          try {
            const data = JSON.parse(buffer.slice(6));
            if (data.type === 'token' && data.content) {
              const deltaEvent = `data: ${JSON.stringify({
                type: 'text-delta',
                id: messageId,
                delta: data.content
              })}\n\n`;
              controller.enqueue(encoder.encode(deltaEvent));
            }
          } catch (e) {
            // Ignore
          }
        }
        // Send [DONE] to signal end of stream
        controller.enqueue(encoder.encode('data: [DONE]\n\n'));
      }
    });

    // Pipe the backend response through the transform stream
    const readable = response.body?.pipeThrough(transformStream);

    return new Response(readable, {
      headers: {
        'Content-Type': 'text/event-stream',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'x-vercel-ai-ui-message-stream': 'v1',
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
