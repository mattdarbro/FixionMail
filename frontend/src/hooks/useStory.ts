import { useState, useCallback, useEffect } from 'react';
import { StoryState, Choice } from '../types/story';
import { api } from '../services/api';

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

  // Media settings state
  const [mediaSettings, setMediaSettings] = useState({
    audioEnabled: true,
    imageEnabled: true,
    voiceId: '21m00Tcm4TlvDq8ikWAM' // Rachel default
  });

  // Load session from localStorage on mount
  useEffect(() => {
    const savedSessionId = localStorage.getItem(STORAGE_KEY);
    if (savedSessionId) {
      setState(prev => ({ ...prev, sessionId: savedSessionId }));
    }
  }, []);

  const startStory = useCallback(async (worldId: string = 'west_haven') => {
    setState(prev => ({ ...prev, isLoading: true, error: null, narrative: '', choices: [] }));

    try {
      // Use non-streaming endpoint (streaming endpoints have been removed from backend)
      const response = await api.startStory({
        world_id: worldId,
        generate_audio: mediaSettings.audioEnabled,
        generate_image: mediaSettings.imageEnabled,
        voice_id: mediaSettings.voiceId
      });

      // Save session to localStorage
      localStorage.setItem(STORAGE_KEY, response.session_id);

      // Update state with the complete response
      setState(prev => ({
        ...prev,
        sessionId: response.session_id,
        narrative: response.narrative,
        choices: response.choices,
        currentBeat: response.current_beat,
        creditsRemaining: response.credits_remaining,
        imageUrl: response.image_url,
        audioUrl: response.audio_url,
        isLoading: false,
        error: null
      }));
    } catch (error) {
      const errorMessage = error instanceof Error
        ? error.message
        : 'Failed to start story. Please try again.';

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
    }
  }, [mediaSettings]);

  const continueStory = useCallback(async (choice: Choice) => {
    if (!state.sessionId) {
      setState(prev => ({
        ...prev,
        error: 'No active session. Please start a new story.'
      }));
      return;
    }

    setState(prev => ({ ...prev, isLoading: true, error: null }));

    try {
      // Use non-streaming endpoint (streaming endpoints have been removed from backend)
      const response = await api.continueStory({
        session_id: state.sessionId,
        choice_id: choice.id,
        generate_audio: mediaSettings.audioEnabled,
        generate_image: mediaSettings.imageEnabled,
        voice_id: mediaSettings.voiceId
      });

      // Update state with the complete response
      setState(prev => ({
        ...prev,
        narrative: response.narrative,
        choices: response.choices,
        currentBeat: response.current_beat,
        creditsRemaining: response.credits_remaining,
        imageUrl: response.image_url,
        audioUrl: response.audio_url,
        isLoading: false,
        error: null
      }));
    } catch (error) {
      const errorMessage = error instanceof Error
        ? error.message
        : 'Failed to continue story. Please try again.';

      setState(prev => ({
        ...prev,
        isLoading: false,
        error: errorMessage,
      }));
    }
  }, [state.sessionId, mediaSettings]);

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

  // Media settings handlers
  const setAudioEnabled = useCallback((enabled: boolean) => {
    setMediaSettings(prev => ({ ...prev, audioEnabled: enabled }));
  }, []);

  const setImageEnabled = useCallback((enabled: boolean) => {
    setMediaSettings(prev => ({ ...prev, imageEnabled: enabled }));
  }, []);

  const setVoiceId = useCallback((voiceId: string) => {
    setMediaSettings(prev => ({ ...prev, voiceId }));
  }, []);

  return {
    ...state,
    startStory,
    continueStory,
    clearError,
    resetStory,
    // Media settings
    audioEnabled: mediaSettings.audioEnabled,
    imageEnabled: mediaSettings.imageEnabled,
    selectedVoice: mediaSettings.voiceId,
    setAudioEnabled,
    setImageEnabled,
    setVoiceId,
  };
}
