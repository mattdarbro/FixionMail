import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import { LoginPage } from './pages/Login';
import { AuthCallbackPage } from './pages/AuthCallback';
import { OnboardingPage } from './pages/Onboarding';
import { DashboardPage } from './pages/Dashboard';
import { ChatPage } from './pages/Chat';
import { StorySettingsPage } from './pages/StorySettings';
import { StoriesPage } from './pages/Stories';

// Legacy imports for dev mode
import { useStory } from './hooks/useStory';
import { StoryViewer } from './components/StoryViewer';
import { MediaControls } from './components/MediaControls';
import { Choice } from './types/story';
import { ThemeProvider } from './contexts/ThemeContext';
import { useEffect, useRef, useState } from 'react';

/**
 * Protected Route Wrapper
 * Redirects to login if not authenticated, or to onboarding if not completed.
 */
function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🎭</div>
          <p className="text-stone-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  // Redirect to onboarding if not completed
  if (user && !user.onboarding_completed && window.location.pathname !== '/onboarding') {
    return <Navigate to="/onboarding" replace />;
  }

  return <>{children}</>;
}

/**
 * Auth Route Wrapper
 * Redirects to dashboard if already authenticated.
 */
function AuthRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated, isLoading, user } = useAuth();

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🎭</div>
          <p className="text-stone-600">Loading...</p>
        </div>
      </div>
    );
  }

  if (isAuthenticated) {
    if (user && !user.onboarding_completed) {
      return <Navigate to="/onboarding" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }

  return <>{children}</>;
}

/**
 * Legacy Dev Dashboard
 * The original story viewer for development/testing.
 */
function DevDashboard() {
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
    audioEnabled,
    imageEnabled,
    selectedVoice,
    setAudioEnabled,
    setImageEnabled,
    setVoiceId,
  } = useStory();

  const [showMediaControls, setShowMediaControls] = useState(false);
  const hasStarted = useRef(false);

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
    startStory('west_haven');
  };

  const handleReset = async () => {
    hasStarted.current = false;
    resetStory();
    await new Promise(resolve => setTimeout(resolve, 100));
    hasStarted.current = true;
    await startStory('west_haven');
  };

  return (
    <ThemeProvider worldId="west_haven">
      <div className="min-h-screen bg-story-bg">
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
                  <h1 className="text-xl font-fantasy text-primary-300">Dev Dashboard</h1>
                  <p className="text-xs text-dark-400">Story Generation Testing</p>
                </div>
              </div>

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
                <button
                  onClick={() => setShowMediaControls(!showMediaControls)}
                  className="px-3 py-1 bg-dark-800 hover:bg-dark-700 text-dark-300 hover:text-dark-100 border border-primary-500/30 rounded-md transition-colors text-xs"
                >
                  ⚙️ Dev
                </button>
              </div>
            </div>
          </div>
        </header>

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

        <footer className="bg-dark-900/30 border-t border-primary-500/10 mt-16">
          <div className="max-w-4xl mx-auto px-4 py-6">
            <div className="text-center text-sm text-dark-500">
              <p>Developer Mode • Story Generation Testing</p>
            </div>
          </div>
        </footer>
      </div>
    </ThemeProvider>
  );
}

/**
 * Main App Component
 */
function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          {/* Public routes */}
          <Route path="/login" element={<AuthRoute><LoginPage /></AuthRoute>} />
          <Route path="/auth/callback" element={<AuthCallbackPage />} />

          {/* Protected routes */}
          <Route path="/onboarding" element={<ProtectedRoute><OnboardingPage /></ProtectedRoute>} />
          <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
          <Route path="/settings" element={<ProtectedRoute><StorySettingsPage /></ProtectedRoute>} />
          <Route path="/stories" element={<ProtectedRoute><StoriesPage /></ProtectedRoute>} />
          <Route path="/chat" element={<ProtectedRoute><ChatPage /></ProtectedRoute>} />

          {/* Dev mode - accessible without auth */}
          <Route path="/dev" element={<DevDashboard />} />

          {/* Default redirect */}
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="*" element={<Navigate to="/dashboard" replace />} />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  );
}

export default App;
