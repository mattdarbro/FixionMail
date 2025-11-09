import { useEffect, useRef, useState } from 'react';
import { useStory } from './hooks/useStory';
import { StoryViewer } from './components/StoryViewer';
import { MediaControls } from './components/MediaControls';
import { Choice } from './types/story';
import { ThemeProvider } from './contexts/ThemeContext';

function App() {
  const {
    sessionId,
    narrative,
    choices,
    currentBeat,
    creditsRemaining,
    isLoading,
    error,
    imageUrl,
    audioUrl,
    startStory,
    continueStory,
    clearError,
    resetStory,
    // Media settings
    audioEnabled,
    imageEnabled,
    selectedVoice,
    setAudioEnabled,
    setImageEnabled,
    setVoiceId,
  } = useStory();

  const [showMediaControls, setShowMediaControls] = useState(false);

  // Track if we've already started to prevent duplicate calls
  const hasStarted = useRef(false);

  // Auto-start story if no session exists
  useEffect(() => {
    if (!sessionId && !isLoading && !error && !hasStarted.current) {
      hasStarted.current = true;
      startStory('west_haven');
    }
  }, [sessionId, isLoading, error, startStory]);

  const handleChoiceSelect = (choice: Choice) => {
    clearError();
    continueStory(choice);
  };

  const handleRetry = () => {
    clearError();
    if (sessionId) {
      // If we have a session, try to continue
      startStory('west_haven');
    } else {
      // Otherwise start fresh
      startStory('west_haven');
    }
  };

  const handleReset = async () => {
    hasStarted.current = false;
    resetStory();
    // Small delay to ensure state is cleared before starting new story
    await new Promise(resolve => setTimeout(resolve, 100));
    hasStarted.current = true;
    await startStory('west_haven');
  };

  return (
    <ThemeProvider worldId="west_haven">
      <div className="min-h-screen bg-story-bg">
      {/* Header */}
      <header className="bg-dark-900/50 backdrop-blur-sm border-b border-primary-500/20 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                <svg fill="currentColor" viewBox="0 0 24 24" className="w-5 h-5 text-white">
                  <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                </svg>
              </div>
              <div>
                <h1 className="text-xl font-fantasy text-primary-300">
                  Storyteller
                </h1>
                <p className="text-xs text-dark-400">
                  Interactive Narratives
                </p>
              </div>
            </div>
            
            {/* Status indicators */}
            <div className="flex items-center gap-4 text-sm">
              {sessionId && (
                <>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-accent-500 rounded-full animate-pulse"></div>
                    <span className="text-dark-300">Beat {currentBeat}</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 bg-secondary-500 rounded-full"></div>
                    <span className="text-dark-300">{creditsRemaining} credits</span>
                  </div>
                </>
              )}

              {/* Dev mode toggle */}
              <button
                onClick={() => setShowMediaControls(!showMediaControls)}
                className="px-3 py-1 bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-dark-100 border border-primary-500/30 rounded-md transition-colors text-xs"
                title="Toggle media controls"
              >
                ⚙️ Dev
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Media Controls (Dev Mode) */}
      {showMediaControls && (
        <div className="max-w-4xl mx-auto px-4 pt-4">
          <MediaControls
            audioEnabled={audioEnabled}
            imageEnabled={imageEnabled}
            selectedVoice={selectedVoice}
            onAudioToggle={setAudioEnabled}
            onImageToggle={setImageEnabled}
            onVoiceChange={setVoiceId}
          />
        </div>
      )}

      {/* Main content */}
      <main className="max-w-4xl mx-auto px-4 py-8">
        <StoryViewer
          state={{
            sessionId,
            narrative,
            choices,
            currentBeat,
            creditsRemaining,
            isLoading,
            error,
            imageUrl,
            audioUrl,
          }}
          onChoiceSelect={handleChoiceSelect}
          onRetry={handleRetry}
          onReset={handleReset}
        />
      </main>

      {/* Footer */}
      <footer className="bg-dark-900/30 border-t border-primary-500/10 mt-16">
        <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="text-center text-sm text-dark-500">
            <p>Powered by AI • Built with React & TypeScript</p>
            <p className="mt-1">West Haven • Space Station Story</p>
          </div>
        </div>
      </footer>
      </div>
    </ThemeProvider>
  );
}

export default App;
