import { useState, useEffect } from 'react';
import { StoryState, Choice } from '../types/story';
import { NarrativeCard } from './NarrativeCard';
import { ChoicePanel } from './ChoicePanel';
import { LoadingState } from './LoadingState';
import { ErrorState } from './ErrorState';

interface StoryViewerProps {
  state: StoryState & {
    isStreaming?: boolean;
    streamError?: string | null;
  };
  onChoiceSelect: (choice: Choice) => void;
  onRetry: () => void;
  onReset: () => void;
}

// Delay before showing choices (in milliseconds)
const CHOICE_DELAY_MS = 45000; // 45 seconds

export function StoryViewer({
  state,
  onChoiceSelect,
  onRetry,
  onReset
}: StoryViewerProps) {
  const [choicesVisible, setChoicesVisible] = useState(false);
  const [secondsRemaining, setSecondsRemaining] = useState(CHOICE_DELAY_MS / 1000);

  // Reset and start timer when narrative changes
  useEffect(() => {
    if (state.narrative && state.choices.length > 0 && !state.isLoading) {
      // Reset visibility
      setChoicesVisible(false);
      setSecondsRemaining(CHOICE_DELAY_MS / 1000);

      // Countdown timer (update every second)
      const countdownInterval = setInterval(() => {
        setSecondsRemaining((prev) => {
          if (prev <= 1) {
            clearInterval(countdownInterval);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      // Show choices after delay
      const timer = setTimeout(() => {
        setChoicesVisible(true);
      }, CHOICE_DELAY_MS);

      return () => {
        clearTimeout(timer);
        clearInterval(countdownInterval);
      };
    }
  }, [state.narrative, state.choices.length, state.isLoading]);
  // Show loading state
  if (state.isLoading || state.isStreaming) {
    return <LoadingState message={state.isStreaming ? "Streaming story..." : "The story unfolds..."} />;
  }

  // Show error state
  if (state.error) {
    return (
      <ErrorState 
        error={state.error}
        onRetry={onRetry}
        onReset={onReset}
      />
    );
  }

  // Show empty state (no story started)
  if (!state.sessionId || !state.narrative) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
        <div className="text-center">
          <div className="w-16 h-16 mx-auto mb-4 opacity-50">
            <svg fill="currentColor" viewBox="0 0 24 24" className="w-full h-full text-primary-400">
              <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
            </svg>
          </div>
          <h3 className="text-lg font-fantasy text-primary-300 mb-2">
            Begin Your Journey
          </h3>
          <p className="text-sm text-dark-400 mb-6">
            Start a new story to begin your adventure
          </p>
          <button
            onClick={onRetry}
            className="px-6 py-3 bg-gradient-to-r from-primary-600 to-primary-700 hover:from-primary-700 hover:to-primary-800 text-white rounded-lg font-medium transition-all duration-200 shadow-lg hover:shadow-xl"
          >
            Start Story
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Story narrative */}
      <NarrativeCard
        narrative={state.narrative}
        currentBeat={state.currentBeat}
        imageUrl={state.imageUrl}
        audioUrl={state.audioUrl}
        isGeneratingAudio={state.isLoading && !state.audioUrl}
        isGeneratingImage={state.isLoading && !state.imageUrl}
        isStreaming={state.isStreaming}
        className="animate-fade-in"
      />
      
      {/* Player choices or countdown */}
      {state.choices.length > 0 && (
        <div className="animate-slide-up">
          {!choicesVisible ? (
            <div className="bg-dark-800/50 backdrop-blur-sm border border-primary-500/20 rounded-lg p-6 text-center">
              <div className="flex flex-col items-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-primary-500/10 flex items-center justify-center">
                  <svg className="w-6 h-6 text-primary-400 animate-pulse" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                </div>
                <p className="text-dark-300 text-sm italic">
                  Weaving the threads of possibility...
                </p>
                <p className="text-primary-400 font-medium">
                  Paths emerge in {secondsRemaining} second{secondsRemaining !== 1 ? 's' : ''}
                </p>
              </div>
            </div>
          ) : (
            <ChoicePanel
              choices={state.choices}
              onChoiceSelect={onChoiceSelect}
              disabled={state.creditsRemaining <= 0}
            />
          )}
        </div>
      )}
    </div>
  );
}
