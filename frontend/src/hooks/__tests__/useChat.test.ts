/**
 * Tests for useChat hook - SSE-based chat functionality
 * 
 * Tests cover:
 * - Message sending and receiving
 * - Streaming responses
 * - User input interactions (Human-in-the-Loop)
 * - Error handling
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useChat } from '../useChat';
import { useChatStore } from '@/lib/store';

// Mock fetch for SSE
global.fetch = jest.fn();

// Mock AuthProvider
jest.mock('@/components/auth/AuthProvider', () => ({
  useAuth: () => ({
    user: { id: 'test-user-123' },
  }),
}));

// Mock sessionStorage
const sessionStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'sessionStorage', {
  value: sessionStorageMock,
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    clear: () => {
      store = {};
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
});

// Helper to create a mock ReadableStream
function createMockStream(events: string[]) {
  let index = 0;
  
  return new ReadableStream({
    start(controller) {
      const encoder = new TextEncoder();
      
      const sendNext = () => {
        if (index < events.length) {
          controller.enqueue(encoder.encode(events[index]));
          index++;
          setTimeout(sendNext, 10);
        } else {
          controller.close();
        }
      };
      
      sendNext();
    },
  });
}

describe('useChat Hook', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    sessionStorageMock.clear();
    localStorageMock.clear();
    useChatStore.setState({ messages: [] });
  });

  describe('Message Sending and Receiving', () => {
    it('should send a message and receive a response', async () => {
      const mockEvents = [
        'data: {"type":"text","content":"Hello"}\n',
        'data: {"type":"text","content":" there"}\n',
        'data: {"type":"text","content":"!"}\n',
        'data: {"type":"done"}\n',
        'data: [DONE]\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      // Send message
      await act(async () => {
        await result.current.append('Test message');
      });

      // Wait for response to complete
      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      }, { timeout: 3000 });

      // Check messages
      expect(result.current.messages).toHaveLength(2);
      expect(result.current.messages[0]).toMatchObject({
        role: 'user',
        content: 'Test message',
      });
      expect(result.current.messages[1]).toMatchObject({
        role: 'assistant',
        content: 'Hello there!',
      });
    });

    it('should handle empty messages', async () => {
      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('');
      });

      expect(result.current.messages).toHaveLength(0);
      expect(global.fetch).not.toHaveBeenCalled();
    });

    it('should prevent sending while loading', async () => {
      const mockEvents = [
        'data: {"type":"text","content":"Response"}\n',
        'data: [DONE]\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      // Send first message
      act(() => {
        result.current.append('First message');
      });

      // Try to send second message while loading
      await act(async () => {
        await result.current.append('Second message');
      });

      // Should only have called fetch once
      expect(global.fetch).toHaveBeenCalledTimes(1);
    });
  });

  describe('Streaming Responses', () => {
    it('should handle streaming text tokens', async () => {
      const mockEvents = [
        'data: {"type":"token","content":"The"}\n',
        'data: {"type":"token","content":" quick"}\n',
        'data: {"type":"token","content":" brown"}\n',
        'data: {"type":"token","content":" fox"}\n',
        'data: {"type":"done"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Tell me a story');
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      const assistantMessage = result.current.messages.find(m => m.role === 'assistant');
      expect(assistantMessage?.content).toBe('The quick brown fox');
    });

    it('should update agent status during streaming', async () => {
      const mockEvents = [
        'data: {"type":"thinking","message":"Analyzing request..."}\n',
        'data: {"type":"tool_start","tool":"search","message":"Searching..."}\n',
        'data: {"type":"text","content":"Found results"}\n',
        'data: {"type":"tool_complete","tool":"search"}\n',
        'data: {"type":"done"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Search for something');
      });

      // Agent status should be cleared after completion
      await waitFor(() => {
        expect(result.current.agentStatus).toBeNull();
      });
    });
  });

  describe('User Input Interactions (Human-in-the-Loop)', () => {
    it('should handle confirmation requests', async () => {
      const mockEvents = [
        'data: {"type":"user_input_request","input_type":"confirmation","message":"Confirm action?"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Do something important');
      });

      await waitFor(() => {
        expect(result.current.userInputRequest).not.toBeNull();
      });

      expect(result.current.userInputRequest).toMatchObject({
        type: 'confirmation',
        message: 'Confirm action?',
      });
    });

    it('should handle selection requests with options', async () => {
      const mockEvents = [
        'data: {"type":"user_input_request","input_type":"selection","message":"Choose an option:","options":["Option 1","Option 2","Option 3"]}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Show me options');
      });

      await waitFor(() => {
        expect(result.current.userInputRequest).not.toBeNull();
      });

      expect(result.current.userInputRequest).toMatchObject({
        type: 'selection',
        message: 'Choose an option:',
        options: ['Option 1', 'Option 2', 'Option 3'],
      });
    });

    it('should handle input requests', async () => {
      const mockEvents = [
        'data: {"type":"user_input_request","input_type":"input","message":"Please provide details:"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Need more info');
      });

      await waitFor(() => {
        expect(result.current.userInputRequest).not.toBeNull();
      });

      expect(result.current.userInputRequest).toMatchObject({
        type: 'input',
        message: 'Please provide details:',
      });
    });

    it('should respond to user input requests', async () => {
      // First request
      const mockEvents1 = [
        'data: {"type":"user_input_request","input_type":"confirmation","message":"Confirm?"}\n',
      ];

      // Response after confirmation
      const mockEvents2 = [
        'data: {"type":"text","content":"Confirmed and processed"}\n',
        'data: {"type":"done"}\n',
      ];

      (global.fetch as jest.Mock)
        .mockResolvedValueOnce({
          ok: true,
          body: createMockStream(mockEvents1),
        })
        .mockResolvedValueOnce({
          ok: true,
          body: createMockStream(mockEvents2),
        });

      const { result } = renderHook(() => useChat());

      // Send initial message
      await act(async () => {
        await result.current.append('Do action');
      });

      await waitFor(() => {
        expect(result.current.userInputRequest).not.toBeNull();
      });

      // Respond to user input request
      await act(async () => {
        await result.current.respondToUserInput('确认');
      });

      await waitFor(() => {
        expect(result.current.userInputRequest).toBeNull();
      });

      // Should have sent the response
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });
  });

  describe('Error Handling', () => {
    it('should handle network errors', async () => {
      (global.fetch as jest.Mock).mockRejectedValueOnce(new Error('Network error'));

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Test message');
      });

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      expect(result.current.error?.message).toBe('Network error');
      expect(result.current.isLoading).toBe(false);
    });

    it('should handle HTTP errors', async () => {
      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: false,
        status: 500,
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Test message');
      });

      await waitFor(() => {
        expect(result.current.error).not.toBeNull();
      });

      expect(result.current.error?.message).toContain('500');
    });

    it('should handle malformed SSE events', async () => {
      const mockEvents = [
        'data: {"type":"text","content":"Valid"}\n',
        'data: {invalid json}\n',
        'data: {"type":"text","content":"Still works"}\n',
        'data: {"type":"done"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Test message');
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      });

      // Should still process valid events
      const assistantMessage = result.current.messages.find(m => m.role === 'assistant');
      expect(assistantMessage?.content).toContain('Valid');
      expect(assistantMessage?.content).toContain('Still works');
    });

    it('should handle timeout', async () => {
      jest.useFakeTimers();

      // Mock a stream that never completes
      const mockStream = new ReadableStream({
        start() {
          // Never send anything - simulates hanging connection
        },
      });

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: mockStream,
      });

      const { result } = renderHook(() => useChat());

      // Start the request
      act(() => {
        result.current.append('Test message');
      });

      // Fast-forward time to trigger timeout
      act(() => {
        jest.advanceTimersByTime(60000);
      });

      // Check timeout state
      expect(result.current.isTimeout).toBe(true);
      expect(result.current.isLoading).toBe(false);

      jest.useRealTimers();
    });

    it('should log error events from stream', async () => {
      // Mock console.error to verify error logging
      const consoleErrorSpy = jest.spyOn(console, 'error').mockImplementation();

      const mockEvents = [
        'data: {"type":"text","content":"Starting..."}\n',
        'data: {"type":"error","error":"Something went wrong"}\n',
        'data: [DONE]\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      await act(async () => {
        await result.current.append('Test message');
      });

      // Wait for the stream to complete
      await waitFor(() => {
        return result.current.isLoading === false;
      }, { timeout: 3000 });

      // Verify that the error was logged
      expect(consoleErrorSpy).toHaveBeenCalledWith(
        'Failed to parse SSE event:',
        expect.objectContaining({
          message: 'Something went wrong',
        })
      );

      consoleErrorSpy.mockRestore();
    });
  });

  describe('Additional Functionality', () => {
    it('should retry last message', async () => {
      const mockEvents = [
        'data: {"type":"text","content":"First response"}\n',
        'data: {"type":"done"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValue({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      // Send initial message
      await act(async () => {
        await result.current.append('Test message');
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      }, { timeout: 3000 });

      // Retry
      await act(async () => {
        result.current.retry();
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      }, { timeout: 3000 });

      // Should have called fetch twice
      expect(global.fetch).toHaveBeenCalledTimes(2);
    });

    it('should stop generation', () => {
      const { result } = renderHook(() => useChat());

      // Manually set loading state
      act(() => {
        result.current.setMessages([
          { id: '1', role: 'user', content: 'Test' },
        ]);
      });

      // Stop generation
      act(() => {
        result.current.stop();
      });

      expect(result.current.isLoading).toBe(false);
      expect(result.current.agentStatus).toBeNull();
    });

    it('should clear history', async () => {
      const mockEvents = [
        'data: {"type":"text","content":"Response"}\n',
        'data: {"type":"done"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      // Send message
      await act(async () => {
        await result.current.append('Test message');
      });

      await waitFor(() => {
        expect(result.current.messages.length).toBeGreaterThan(0);
      }, { timeout: 3000 });

      // Clear history
      act(() => {
        result.current.clearHistory();
      });

      expect(result.current.messages).toHaveLength(0);
      expect(result.current.input).toBe('');
      expect(result.current.error).toBeNull();
    });

    it('should handle input change', () => {
      const { result } = renderHook(() => useChat());

      act(() => {
        result.current.handleInputChange({
          target: { value: 'New input' },
        } as React.ChangeEvent<HTMLInputElement>);
      });

      expect(result.current.input).toBe('New input');
    });

    it('should handle form submit', async () => {
      const mockEvents = [
        'data: {"type":"text","content":"Response"}\n',
        'data: {"type":"done"}\n',
      ];

      (global.fetch as jest.Mock).mockResolvedValueOnce({
        ok: true,
        body: createMockStream(mockEvents),
      });

      const { result } = renderHook(() => useChat());

      // Set input
      act(() => {
        result.current.handleInputChange({
          target: { value: 'Test input' },
        } as React.ChangeEvent<HTMLInputElement>);
      });

      // Submit form
      await act(async () => {
        await result.current.handleSubmit({
          preventDefault: jest.fn(),
        } as unknown as React.FormEvent<HTMLFormElement>);
      });

      await waitFor(() => {
        expect(result.current.isLoading).toBe(false);
      }, { timeout: 3000 });

      // Input should be cleared
      expect(result.current.input).toBe('');
      
      // Message should be sent
      expect(result.current.messages.length).toBeGreaterThan(0);
    });
  });
});
