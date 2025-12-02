/**
 * Chat API v3 Route
 *
 * This route handles chat requests using the new v3 AI Orchestrator architecture:
 * - Gemini 3 Pro with native image generation
 * - Sub-agents via function calling
 * - Simplified streaming format
 */

export const runtime = 'edge';

export async function POST(req: Request) {
  try {
    const body = await req.json();

    // Extract messages from various formats
    let messages: Array<{ role: string; content: string }> = [];

    if (body.messages && Array.isArray(body.messages)) {
      messages = body.messages.map((msg: any) => {
        if (typeof msg.content === 'string') {
          return { role: msg.role, content: msg.content };
        }
        if (msg.parts && Array.isArray(msg.parts)) {
          const textParts = msg.parts
            .filter((p: any) => p.type === 'text')
            .map((p: any) => p.text)
            .join('');
          return { role: msg.role, content: textParts };
        }
        return { role: msg.role, content: String(msg.content || '') };
      }).filter((msg: any) => msg.content);
    }

    if (messages.length === 0 && body.parts) {
      const textPart = body.parts.find((p: any) => p.type === 'text');
      if (textPart) {
        messages = [{ role: 'user', content: textPart.text }];
      }
    }

    if (messages.length === 0 && body.prompt) {
      messages = [{ role: 'user', content: body.prompt }];
    }

    if (messages.length === 0 && body.content) {
      messages = [{ role: 'user', content: body.content }];
    }

    if (messages.length === 0) {
      return new Response(
        JSON.stringify({ error: 'No messages provided' }),
        { status: 422, headers: { 'Content-Type': 'application/json' } }
      );
    }

    // Get user info
    const userId = body.user_id || req.headers.get('x-user-id') || 'anonymous';
    const sessionId = body.session_id || req.headers.get('x-session-id') || `session-${Date.now()}`;

    // Get the last user message content
    const lastUserMessage = messages.filter(m => m.role === 'user').pop();
    const content = lastUserMessage?.content || '';

    // Build conversation history (exclude the last message)
    const history = messages.slice(0, -1).map(m => ({
      role: m.role === 'assistant' ? 'assistant' : 'user',
      content: m.content,
    }));

    // Service token for authentication
    const serviceToken = process.env.AI_ORCHESTRATOR_SERVICE_TOKEN || '';

    // Forward to AI Orchestrator v3 endpoint
    const aiOrchestratorUrl = process.env.AI_ORCHESTRATOR_URL || 'http://localhost:8001';

    // Choose between streaming and non-streaming
    const useStreaming = body.stream !== false;

    if (useStreaming) {
      // Use streaming endpoint
      const response = await fetch(`${aiOrchestratorUrl}/api/v1/chat/v3/stream`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${serviceToken}`,
        },
        body: JSON.stringify({
          content,
          user_id: userId,
          session_id: sessionId,
          history,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        return new Response(JSON.stringify({ error }), {
          status: response.status,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      // Transform v3 SSE to AI SDK format
      const encoder = new TextEncoder();
      const decoder = new TextDecoder();
      const messageId = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
      let buffer = '';

      const transformStream = new TransformStream({
        async start(controller) {
          // AI SDK start events
          controller.enqueue(encoder.encode(
            `data: ${JSON.stringify({ type: 'start', messageId })}\n\n`
          ));
          controller.enqueue(encoder.encode(
            `data: ${JSON.stringify({ type: 'text-start', id: messageId })}\n\n`
          ));
        },
        async transform(chunk, controller) {
          buffer += decoder.decode(chunk, { stream: true });
          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === 'text' && data.content) {
                  // Text chunk
                  controller.enqueue(encoder.encode(
                    `data: ${JSON.stringify({
                      type: 'text-delta',
                      id: messageId,
                      delta: data.content
                    })}\n\n`
                  ));
                } else if (data.type === 'tool_call') {
                  // Tool being called - show as status
                  controller.enqueue(encoder.encode(
                    `data: ${JSON.stringify({
                      type: 'data-agent-status',
                      data: {
                        statusType: 'tool_start',
                        tool: data.tool,
                        message: `调用 ${data.tool}...`,
                      }
                    })}\n\n`
                  ));
                } else if (data.type === 'tool_result') {
                  // Tool result - may contain final response
                  if (data.response) {
                    controller.enqueue(encoder.encode(
                      `data: ${JSON.stringify({
                        type: 'text-delta',
                        id: messageId,
                        delta: data.response
                      })}\n\n`
                    ));
                  }
                  controller.enqueue(encoder.encode(
                    `data: ${JSON.stringify({
                      type: 'data-agent-status',
                      data: {
                        statusType: 'tool_complete',
                        message: '处理完成',
                      }
                    })}\n\n`
                  ));
                } else if (data.type === 'image') {
                  // Image generated - send as data
                  controller.enqueue(encoder.encode(
                    `data: ${JSON.stringify({
                      type: 'data-image',
                      data: {
                        imageData: data.data,
                        mimeType: 'image/png',
                      }
                    })}\n\n`
                  ));
                } else if (data.type === 'done') {
                  // Stream complete
                  controller.enqueue(encoder.encode(
                    `data: ${JSON.stringify({ type: 'text-end', id: messageId })}\n\n`
                  ));
                  controller.enqueue(encoder.encode(
                    `data: ${JSON.stringify({ type: 'finish', finishReason: 'stop' })}\n\n`
                  ));
                } else if (data.type === 'error') {
                  controller.enqueue(encoder.encode(
                    `data: ${JSON.stringify({
                      type: 'error',
                      error: data.error || 'Unknown error'
                    })}\n\n`
                  ));
                }
              } catch (e) {
                console.error('Failed to parse v3 SSE:', e);
              }
            }
          }
        },
        async flush(controller) {
          controller.enqueue(encoder.encode('data: [DONE]\n\n'));
        }
      });

      const readable = response.body?.pipeThrough(transformStream);

      return new Response(readable, {
        headers: {
          'Content-Type': 'text/event-stream',
          'Cache-Control': 'no-cache, no-transform',
          'Connection': 'keep-alive',
          'X-Accel-Buffering': 'no',
          'x-vercel-ai-ui-message-stream': 'v1',
        },
      });
    } else {
      // Non-streaming request
      const response = await fetch(`${aiOrchestratorUrl}/api/v1/chat/v3`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${serviceToken}`,
        },
        body: JSON.stringify({
          content,
          user_id: userId,
          session_id: sessionId,
          history,
        }),
      });

      if (!response.ok) {
        const error = await response.text();
        return new Response(JSON.stringify({ error }), {
          status: response.status,
          headers: { 'Content-Type': 'application/json' },
        });
      }

      const result = await response.json();

      return new Response(JSON.stringify({
        message: {
          role: 'assistant',
          content: result.response,
        },
        success: result.success,
      }), {
        headers: { 'Content-Type': 'application/json' },
      });
    }
  } catch (error) {
    console.error('Chat v3 API error:', error);
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
