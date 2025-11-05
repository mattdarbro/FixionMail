import { useState, useCallback, useEffect } from 'react';
import { StoryState, Choice } from '../types/story';
import { api, ApiError } from '../services/api';
import { useStoryStream } from './useStoryStream';

const STORAGE_KEY = 'storyteller_session';

export function useStory() {
  const [state, setState] = useState<StoryState>({
    sessionId: null,
    narrative: '',
    choices: [],
    currentBeat: 1,
    creditsRemaining: 0,
    isLoading: false,
    error: null,
    imageUrl: undefined,
    audioUrl: undefined,
  });

  const { startStream, isStreaming, streamError } = useStoryStream();

  // Load session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem(STORAGE_KEY);
    if (savedSessionId) {
      setState(prev => ({ ...prev, sessionId: savedSessionId }));
    }
  }, []);

  const startStory = useCallback(async (worldId: string = 'west_haven') => {
    setState(prev => ({ ...prev, isLoading: true, error: null, narrative: '', choices: [] }));

    // Use streaming for immersive experience
    const cancelFn = api.streamStartStory(
      { world_id: worldId },
      (event) => {
        switch (event.type) {
          case 'session':
            // Save session to localStorage
            localStorage.setItem(STORAGE_KEY, event.session_id);
            setState(prev => ({ ...prev, sessionId: event.session_id }));
            break;

          case 'thinking':
            setState(prev => ({ ...prev, isLoading: true }));
            break;

          case 'narrative_start':
            // Reset narrative for streaming
            setState(prev => ({ ...prev, narrative: '' }));
            break;

          case 'word':
            // Append each word as it arrives
            setState(prev => ({
              ...prev,
              narrative: prev.narrative ? `${prev.narrative} ${event.word}` : event.word
            }));
            break;

          case 'choices':
            setState(prev => ({ ...prev, choices: event.choices, isLoading: false }));
            break;

          case 'image':
            setState(prev => ({ ...prev, imageUrl: event.url }));
            break;

          case 'audio':
            setState(prev => ({ ...prev, audioUrl: event.url }));
            break;

          case 'complete':
            setState(prev => ({
              ...prev,
              currentBeat: event.beat,
              creditsRemaining: event.credits,
              isLoading: false,
              error: null
            }));
            break;

          case 'error':
            setState(prev => ({
              ...prev,
              isLoading: false,
              error: event.message
            }));
            break;
        }
      },
      (error) => {
        const errorMessage = error instanceof Error
          ? error.message
          : 'Failed to start story. Please try again.';

        setState(prev => ({
          ...prev,
          isLoading: false,
          error: errorMessage,
        }));
      }
    );
  }, []);

  const continueStory = useCallback(async (choice: Choice) => {
    if (!state.sessionId) {
      setState(prev => ({ 
        ...prev, 
        error: 'No active session. Please start a new story.' 
      }));
      return;
    }

    // Use streaming for story continuation
    await startStream(state.sessionId, choice.id, (updates) => {
      setState(prev => ({ ...prev, ...updates }));
    });
  }, [state.sessionId, startStream]);

  const clearError = useCallback(() => {
    setState(prev => ({ ...prev, error: null }));
  }, []);

  const resetStory = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setState({
      sessionId: null,
      narrative: '',
      choices: [],
      currentBeat: 1,
      creditsRemaining: 0,
      isLoading: false,
      error: null,
    });
  }, []);

  return {
    ...state,
    isStreaming,
    streamError,
    startStory,
    continueStory,
    clearError,
    resetStory,
  };
}
