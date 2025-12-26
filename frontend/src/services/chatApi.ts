/**
 * Fixion Chat API Service
 *
 * Handles all communication with the Fixion chat backend.
 */

import {
  ChatResponse,
  OnboardingStartResponse,
  GenreSelectionResponse,
  StoryDiscussResponse,
  RetellRequestResponse,
} from '../types/chat';

const API_BASE_URL = import.meta.env.VITE_API_URL
  ? `${import.meta.env.VITE_API_URL}/api`
  : '/api';

class ChatApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public statusText: string
  ) {
    super(message);
    this.name = 'ChatApiError';
  }
}

async function fetchWithAuth<T>(
  url: string,
  accessToken: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      'Authorization': `Bearer ${accessToken}`,
      'Content-Type': 'application/json',
      ...options.headers,
    },
  });

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({}));
    throw new ChatApiError(
      errorData.detail || errorData.error || `HTTP ${response.status}`,
      response.status,
      response.statusText
    );
  }

  return await response.json();
}

export const chatApi = {
  /**
   * Send a message to Fixion
   */
  async sendMessage(
    accessToken: string,
    message: string,
    conversationId?: string,
    context?: {
      genre?: string;
      onboarding_step?: string;
    }
  ): Promise<ChatResponse> {
    return fetchWithAuth<ChatResponse>(
      `${API_BASE_URL}/chat/message`,
      accessToken,
      {
        method: 'POST',
        body: JSON.stringify({
          message,
          conversation_id: conversationId,
          context,
        }),
      }
    );
  },

  /**
   * Send a message with streaming response
   */
  streamMessage(
    accessToken: string,
    message: string,
    conversationId: string | undefined,
    context: { genre?: string; onboarding_step?: string } | undefined,
    onToken: (token: string) => void,
    onComplete: (response: ChatResponse) => void,
    onError: (error: Error) => void
  ): () => void {
    const controller = new AbortController();

    fetch(`${API_BASE_URL}/chat/message/stream`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${accessToken}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message,
        conversation_id: conversationId,
        context,
      }),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('No response body');
        }

        let fullResponse = '';
        let conversationIdFromStream = conversationId || '';

        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === 'token') {
                  fullResponse += data.content;
                  onToken(data.content);
                } else if (data.type === 'done') {
                  conversationIdFromStream = data.conversation_id || conversationIdFromStream;
                }
              } catch {
                // Ignore parse errors for partial chunks
              }
            }
          }
        }

        onComplete({
          response: fullResponse,
          conversation_id: conversationIdFromStream,
        });
      })
      .catch((error) => {
        if (error.name !== 'AbortError') {
          onError(error);
        }
      });

    return () => controller.abort();
  },

  /**
   * Start onboarding conversation
   */
  async startOnboarding(accessToken: string): Promise<OnboardingStartResponse> {
    return fetchWithAuth<OnboardingStartResponse>(
      `${API_BASE_URL}/chat/onboarding/start`,
      accessToken,
      { method: 'POST' }
    );
  },

  /**
   * Select a genre during onboarding
   */
  async selectGenre(
    accessToken: string,
    genre: string,
    conversationId: string
  ): Promise<GenreSelectionResponse> {
    return fetchWithAuth<GenreSelectionResponse>(
      `${API_BASE_URL}/chat/onboarding/genre`,
      accessToken,
      {
        method: 'POST',
        body: JSON.stringify({
          genre,
          conversation_id: conversationId,
        }),
      }
    );
  },

  /**
   * Discuss a specific story with Fixion
   */
  async discussStory(
    accessToken: string,
    storyId: string,
    message: string,
    conversationId?: string
  ): Promise<StoryDiscussResponse> {
    return fetchWithAuth<StoryDiscussResponse>(
      `${API_BASE_URL}/chat/story/discuss`,
      accessToken,
      {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyId,
          message,
          conversation_id: conversationId,
        }),
      }
    );
  },

  /**
   * Request a retell/revision of a story
   */
  async requestRetell(
    accessToken: string,
    storyId: string,
    feedback: string,
    conversationId?: string
  ): Promise<RetellRequestResponse> {
    return fetchWithAuth<RetellRequestResponse>(
      `${API_BASE_URL}/chat/story/retell`,
      accessToken,
      {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyId,
          feedback,
          conversation_id: conversationId,
        }),
      }
    );
  },

  /**
   * Confirm a retell request
   */
  async confirmRetell(
    accessToken: string,
    storyId: string,
    revisionType: 'surface' | 'prose' | 'structure',
    feedback: string
  ): Promise<{ story_id: string; message: string }> {
    return fetchWithAuth<{ story_id: string; message: string }>(
      `${API_BASE_URL}/chat/story/retell/confirm`,
      accessToken,
      {
        method: 'POST',
        body: JSON.stringify({
          story_id: storyId,
          revision_type: revisionType,
          feedback,
        }),
      }
    );
  },
};

export { ChatApiError };
