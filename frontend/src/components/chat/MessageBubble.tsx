'use client';

import ReactMarkdown from 'react-markdown';
import type { UIMessage } from 'ai';

interface MessageBubbleProps {
  message: UIMessage;
  compact?: boolean;
}

export function MessageBubble({ message, compact = false }: MessageBubbleProps) {
  const isUser = message.role === 'user';
  
  // Extract content from message - handle both string content and parts array
  const getMessageContent = () => {
    const msg = message as any;

    // Handle string content (legacy format)
    if (typeof msg.content === 'string') {
      return msg.content;
    }

    // Handle content array (AI SDK v5 format with content array)
    if (Array.isArray(msg.content)) {
      return msg.content
        .filter((part: any) => part.type === 'text')
        .map((part: any) => part.text)
        .join('');
    }

    // Handle parts array (AI SDK v5 format with parts)
    if (Array.isArray(msg.parts)) {
      return msg.parts
        .filter((part: any) => part.type === 'text')
        .map((part: any) => part.text)
        .join('');
    }

    return '';
  };

  const content = getMessageContent();

  return (
    <div
      className={`mb-4 flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[85%] rounded-lg px-4 py-3 ${
          isUser
            ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap break-words">{content}</p>
        ) : (
          <div className="prose prose-sm max-w-none">
            <ReactMarkdown
              components={{
                // Custom code block rendering
                code(props: any) {
                  const { inline, className, children, ...rest } = props;
                  return inline ? (
                    <code
                      className="bg-gray-200 text-gray-800 px-1.5 py-0.5 rounded text-xs font-mono"
                      {...rest}
                    >
                      {children}
                    </code>
                  ) : (
                    <pre className="bg-gray-800 text-white p-3 rounded-md overflow-x-auto my-2">
                      <code className="text-xs font-mono" {...rest}>
                        {children}
                      </code>
                    </pre>
                  );
                },
                // Custom paragraph styling
                p(props: any) {
                  return <p className="text-sm mb-2 last:mb-0">{props.children}</p>;
                },
                // Custom list styling
                ul(props: any) {
                  return <ul className="text-sm list-disc list-inside mb-2">{props.children}</ul>;
                },
                ol(props: any) {
                  return <ol className="text-sm list-decimal list-inside mb-2">{props.children}</ol>;
                },
                // Custom link styling
                a(props: any) {
                  return (
                    <a
                      href={props.href}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-blue-600 hover:text-blue-800 underline"
                    >
                      {props.children}
                    </a>
                  );
                },
                // Custom heading styling
                h1(props: any) {
                  return <h1 className="text-base font-bold mb-2">{props.children}</h1>;
                },
                h2(props: any) {
                  return <h2 className="text-sm font-bold mb-2">{props.children}</h2>;
                },
                h3(props: any) {
                  return <h3 className="text-sm font-semibold mb-1">{props.children}</h3>;
                },
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {/* Timestamp */}
        <div
          className={`text-xs mt-1 ${
            isUser ? 'text-white/70' : 'text-gray-500'
          }`}
        >
          {new Date((message as any).createdAt || Date.now()).toLocaleTimeString('zh-CN', {
            hour: '2-digit',
            minute: '2-digit',
          })}
        </div>
      </div>
    </div>
  );
}
