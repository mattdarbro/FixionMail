import { StoryResponse, StartStoryRequest, ContinueStoryRequest } from '../types/story';

// Get API URL from environment variable, fallback to localhost for development
const API_BASE_URL = import.meta.env.VITE_API_URL 
  ? `${import.meta.env.VITE_API_URL}/api`
  : 'http://localhost:8000/api';

class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

async function fetchWithErrorHandling<T>(
  url: string,
  options: RequestInit = {}
): Promise<T> {
  try {
    const response = await fetch(url, {
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
      ...options,
    });

    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new ApiError(
        errorData.detail || errorData.error || `HTTP ${response.status}`,
        response.status,
        response.statusText
      );
    }

    return await response.json();
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }
    
    // Network or other errors
    throw new ApiError(
      'Network error - please check your connection',
      0,
      'Network Error'
    );
  }
}

export const api = {
  /**
   * Start a new story session
   */
  async startStory(request: StartStoryRequest): Promise<StoryResponse> {
    return fetchWithErrorHandling<StoryResponse>(
      `${API_BASE_URL}/story/start`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    );
  },

  /**
   * Continue the story with a player choice
   */
  async continueStory(request: ContinueStoryRequest): Promise<StoryResponse> {
    return fetchWithErrorHandling<StoryResponse>(
      `${API_BASE_URL}/story/continue`,
      {
        method: 'POST',
        body: JSON.stringify(request),
      }
    );
  },

  /**
   * Get current session state
   */
  async getSession(sessionId: string): Promise<StoryResponse> {
    return fetchWithErrorHandling<StoryResponse>(
      `${API_BASE_URL}/story/session/${sessionId}`
    );
  },

  /**
   * List available story worlds
   */
  async listWorlds(): Promise<string[]> {
    return fetchWithErrorHandling<string[]>(`${API_BASE_URL}/worlds`);
  },

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string; config: any }> {
    return fetchWithErrorHandling<{ status: string; config: any }>(
      `${API_BASE_URL.replace('/api', '')}/health`
    );
  },

  /**
   * Start a story with Server-Sent Events streaming
   */
  streamStartStory(
    request: StartStoryRequest,
    onEvent: (event: StreamEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): () => void {
    const url = `${API_BASE_URL}/story/start/stream`;

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                onEvent(data);
              } catch (e) {
                console.warn('Failed to parse SSE data:', line);
              }
            }
          }
        }

        onComplete?.();
      })
      .catch((error) => {
        onError?.(error);
      });

    // Return cancel function
    return () => {
      // Abort is handled by closing the response stream
    };
  },

  /**
   * Continue a story with Server-Sent Events streaming
   */
  streamContinueStory(
    request: ContinueStoryRequest,
    onEvent: (event: StreamEvent) => void,
    onError?: (error: Error) => void,
    onComplete?: () => void
  ): () => void {
    const url = `${API_BASE_URL}/story/continue/stream`;

    fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(request),
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                onEvent(data);
              } catch (e) {
                console.warn('Failed to parse SSE data:', line);
              }
            }
          }
        }

        onComplete?.();
      })
      .catch((error) => {
        onError?.(error);
      });

    // Return cancel function
    return () => {
      // Abort is handled by closing the response stream
    };
  },
};

// Stream event types
export type StreamEvent =
  | { type: 'session'; session_id: string; user_id: string; world_id: string }
  | { type: 'thinking'; message: string }
  | { type: 'narrative_start'; total_words: number }
  | { type: 'word'; word: string; index: number }
  | { type: 'narrative_end' }
  | { type: 'choices'; choices: any[] }
  | { type: 'image'; url: string }
  | { type: 'audio'; url: string }
  | { type: 'complete'; beat: number; credits: number; session_id: string }
  | { type: 'error'; message: string };

export { ApiError };
