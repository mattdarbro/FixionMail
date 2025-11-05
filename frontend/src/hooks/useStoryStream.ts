import { useState, useCallback, useRef } from 'react';
import { StoryState } from '../types/story';
import { api, StreamEvent } from '../services/api';

export function useStoryStream() {
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamError, setStreamError] = useState<string | null>(null);
  const cancelStreamRef = useRef<(() => void) | null>(null);
  const wordsRef = useRef<string[]>([]);

  const startStream = useCallback(async (
    sessionId: string,
    choiceId: number,
    onUpdate: (state: Partial<StoryState>) => void
  ) => {
    if (isStreaming) {
      console.warn('Stream already in progress');
      return;
    }

    setIsStreaming(true);
    setStreamError(null);
    wordsRef.current = [];

    // Show loading state
    onUpdate({ isLoading: true, narrative: '' });

    // Start real SSE streaming
    cancelStreamRef.current = api.streamContinueStory(
      { session_id: sessionId, choice_id: choiceId },
      (event: StreamEvent) => {
        handleStreamEvent(event, onUpdate);
      },
      (error: Error) => {
        console.error('Streaming error:', error);
        setStreamError(error.message);
        onUpdate({
          isLoading: false,
          error: error.message
        });
        setIsStreaming(false);
      },
      () => {
        // Stream complete
        setIsStreaming(false);
      }
    );
  }, [isStreaming]);

  const handleStreamEvent = (
    event: StreamEvent,
    onUpdate: (state: Partial<StoryState>) => void
  ) => {
    switch (event.type) {
      case 'thinking':
        // Show "thinking" message
        onUpdate({ isLoading: true });
        break;

      case 'narrative_start':
        // Reset words for new narrative
        wordsRef.current = [];
        break;

      case 'word':
        // Add word to array and update narrative
        wordsRef.current.push(event.word);
        onUpdate({
          narrative: wordsRef.current.join(' '),
          isLoading: true
        });
        break;

      case 'narrative_end':
        // Narrative complete, keep loading until choices arrive
        break;

      case 'choices':
        // Update choices and clear loading
        onUpdate({
          choices: event.choices,
          isLoading: false
        });
        break;

      case 'image':
        onUpdate({ imageUrl: event.url });
        break;

      case 'audio':
        onUpdate({ audioUrl: event.url });
        break;

      case 'complete':
        // Final state update
        onUpdate({
          currentBeat: event.beat,
          creditsRemaining: event.credits,
          isLoading: false,
          error: null
        });
        break;

      case 'error':
        setStreamError(event.message);
        onUpdate({
          isLoading: false,
          error: event.message
        });
        break;
    }
  };

  const stopStream = useCallback(() => {
    if (cancelStreamRef.current) {
      cancelStreamRef.current();
      cancelStreamRef.current = null;
    }
    setIsStreaming(false);
  }, []);

  // Cleanup on unmount
  const cleanup = useCallback(() => {
    stopStream();
  }, [stopStream]);

  return {
    isStreaming,
    streamError,
    startStream,
    stopStream,
    cleanup,
  };
}
