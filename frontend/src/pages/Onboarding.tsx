/**
 * Onboarding Page
 *
 * The main onboarding flow where users meet Fixion and set up their preferences.
 * Uses a conversational interface with confirmation cards for decisions.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { FixionChat } from '../components/FixionChat';
import { GenreGrid, GENRES } from '../components/GenreCard';
import {
  GenreConfirmation,
  ProtagonistConfirmation,
  PreferencesConfirmation,
} from '../components/ConfirmationCard';
import { chatApi } from '../services/chatApi';
import { ChatMessage, OnboardingState } from '../types/chat';

type OnboardingStep = 'welcome' | 'genre' | 'protagonist' | 'preferences' | 'complete';

export function OnboardingPage() {
  const navigate = useNavigate();
  const { session, refreshUser } = useAuth();

  const [state, setState] = useState<OnboardingState>({
    step: 'welcome',
    confirmationCards: [],
    storyBible: {},
  });

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [selectedGenre, setSelectedGenre] = useState<string | undefined>();
  const [genreConfirmed, setGenreConfirmed] = useState(false);
  const [protagonistConfirmed, setProtagonistConfirmed] = useState(false);
  const [preferencesConfirmed, setPreferencesConfirmed] = useState(false);

  // Protagonist form state
  const [protagonist, setProtagonist] = useState({
    name: '',
    age: '',
    occupation: '',
    personality: [] as string[],
  });

  // Preferences state
  const [preferences, setPreferences] = useState({
    story_length: 'medium',
    delivery_time: '08:00',
    timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
  });

  // Start onboarding on mount
  useEffect(() => {
    if (!session?.access_token) return;

    const startOnboarding = async () => {
      try {
        const response = await chatApi.startOnboarding(session.access_token);
        setMessages([
          {
            role: 'assistant',
            content: response.response,
            timestamp: new Date().toISOString(),
          },
        ]);
        setState((prev) => ({
          ...prev,
          conversationId: response.conversation_id,
        }));
      } catch (error) {
        console.error('Failed to start onboarding:', error);
        setMessages([
          {
            role: 'assistant',
            content: "Well, this is embarrassing. I seem to be having some technical difficulties. Could you refresh the page? The IT department here is... well, let's just say they're better at writing stories than fixing computers.",
            timestamp: new Date().toISOString(),
          },
        ]);
      } finally {
        setIsLoading(false);
      }
    };

    startOnboarding();
  }, [session?.access_token]);

  // Handle genre selection
  const handleGenreSelect = async (genreId: string) => {
    setSelectedGenre(genreId);

    if (!session?.access_token || !state.conversationId) return;

    try {
      const response = await chatApi.selectGenre(
        session.access_token,
        genreId,
        state.conversationId
      );

      setMessages((prev) => [
        ...prev,
        {
          role: 'user',
          content: `I'd like ${GENRES.find((g) => g.id === genreId)?.name}`,
          timestamp: new Date().toISOString(),
        },
        {
          role: 'assistant',
          content: response.response,
          timestamp: new Date().toISOString(),
        },
      ]);

      setState((prev) => ({
        ...prev,
        selectedGenre: genreId,
        step: 'genre',
      }));
    } catch (error) {
      console.error('Failed to select genre:', error);
    }
  };

  // Handle genre confirmation
  const handleGenreConfirm = () => {
    setGenreConfirmed(true);
    setState((prev) => ({ ...prev, step: 'protagonist' }));

    // Add Fixion's next message
    setMessages((prev) => [
      ...prev,
      {
        role: 'assistant',
        content: getProtagonistPrompt(),
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  // Handle protagonist confirmation
  const handleProtagonistConfirm = () => {
    setProtagonistConfirmed(true);
    setState((prev) => ({
      ...prev,
      step: 'preferences',
      storyBible: {
        ...prev.storyBible,
        protagonist,
      },
    }));

    setMessages((prev) => [
      ...prev,
      {
        role: 'assistant',
        content: getPreferencesPrompt(),
        timestamp: new Date().toISOString(),
      },
    ]);
  };

  // Handle preferences confirmation and complete onboarding
  const handlePreferencesConfirm = async () => {
    setPreferencesConfirmed(true);

    if (!session?.access_token) return;

    // Save preferences and story bible to backend
    try {
      const API_BASE_URL = import.meta.env.VITE_API_URL
        ? `${import.meta.env.VITE_API_URL}/api`
        : 'http://localhost:8000/api';

      // Update preferences
      await fetch(`${API_BASE_URL}/users/preferences`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(preferences),
      });

      // Set genre
      await fetch(`${API_BASE_URL}/users/genre`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          genre: selectedGenre,
          protagonist,
        }),
      });

      // Update story bible
      await fetch(`${API_BASE_URL}/users/story-bible`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          story_bible: {
            protagonist,
            genre: selectedGenre,
          },
        }),
      });

      // Complete onboarding
      await fetch(`${API_BASE_URL}/users/onboarding/complete`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      });

      // Refresh user data
      await refreshUser();

      setState((prev) => ({ ...prev, step: 'complete' }));

      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: getCompletionMessage(),
          timestamp: new Date().toISOString(),
        },
      ]);

      // Navigate to dashboard after a short delay
      setTimeout(() => {
        navigate('/dashboard');
      }, 3000);
    } catch (error) {
      console.error('Failed to complete onboarding:', error);
    }
  };

  const handleConversationIdChange = (id: string) => {
    setState((prev) => ({ ...prev, conversationId: id }));
  };

  // Get genre-specific protagonist prompt
  const getProtagonistPrompt = (): string => {
    const prompts: Record<string, string> = {
      mystery: "Excellent choice! Now, every good mystery needs a sharp detective - or at least someone who stumbles into trouble. Tell me about your protagonist. What's their name? What do they do? And most importantly... do they have any peculiar habits that might come in handy when solving crimes?",
      romance: "Ah, romance! My favorite. Now, who's our romantic lead? Give me a name, an age, maybe what they do for work. And tell me - are they the hopeless romantic type, or the 'love is just a chemical reaction' skeptic who's about to be proven deliciously wrong?",
      thriller: "Now we're talking! High stakes, heart-pounding action. But first, our protagonist - the one who's going to be running for their life. Who are they? What's their name, their background? Are they trained for danger, or an ordinary person about to have a very bad day?",
      scifi: "To infinity and beyond! Well, maybe not that far. But we do need a protagonist for our cosmic adventure. Who's piloting this ship? Give me a name, maybe their role on the crew, and tell me - are they an idealist or a cynic about humanity's future among the stars?",
      fantasy: "Now for the hero of our tale! Every great fantasy needs a worthy protagonist. Who shall carry our story? A name, perhaps a trade or calling, and tell me - do they know they're destined for greatness, or are they blissfully unaware of the adventure awaiting them?",
      horror: "Oh, this is going to be fun. For you, not so much for our protagonist. Speaking of which - who's our unfortunate hero? Name, occupation, and most importantly - are they the brave type who investigates strange noises, or the sensible sort who knows when to run?",
      literary: "Ah, the thinking person's genre. Our protagonist should be complex, layered. Who are they? Beyond just a name and job, tell me - what drives them? What keeps them up at night? What truth are they running from or toward?",
      adventure: "Adventure awaits! But first, our intrepid hero. Who's brave enough (or foolish enough) to seek fortune and glory? Give me a name, their skillset, and tell me - are they in it for the treasure, the thrill, or something they won't admit even to themselves?",
    };

    return prompts[selectedGenre || ''] || prompts.mystery;
  };

  const getPreferencesPrompt = (): string => {
    return `Perfect! ${protagonist.name} sounds like exactly the kind of character our writers love to work with. Just a few more details - when would you like your stories delivered? I'll make sure the writers have them ready for you. And how long do you like your stories? Short and sweet, medium with a nice arc, or long enough to really get lost in?`;
  };

  const getCompletionMessage = (): string => {
    return `Wonderful! Everything is set up. I've briefed the writers on ${protagonist.name}, and they're already getting excited about the ${GENRES.find((g) => g.id === selectedGenre)?.name.toLowerCase()} stories they'll be crafting.\n\nYour first story will arrive tomorrow at ${preferences.delivery_time}. I'll be here if you want to chat about it - or if you want a different take on any story, just let me know.\n\nWelcome to FixionMail! *adjusts headset and spins dramatically in chair*`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🎭</div>
          <p className="text-stone-600">Fixion is getting ready...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-amber-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center gap-3">
            <span className="text-3xl">🎭</span>
            <div>
              <h1 className="text-xl font-bold text-amber-800">FixionMail</h1>
              <p className="text-xs text-stone-500">Your Personal Story Studio</p>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Chat Panel */}
          <div className="bg-white rounded-2xl shadow-xl overflow-hidden h-[600px] flex flex-col">
            <div className="bg-amber-600 text-white px-4 py-3">
              <div className="flex items-center gap-2">
                <span className="text-xl">🎭</span>
                <div>
                  <h2 className="font-semibold">Chat with Fixion</h2>
                  <p className="text-xs text-amber-200">Your guide to great stories</p>
                </div>
              </div>
            </div>
            <FixionChat
              conversationId={state.conversationId}
              onConversationIdChange={handleConversationIdChange}
              context={{
                genre: selectedGenre,
                onboarding_step: state.step,
              }}
              initialMessages={messages}
              className="flex-1"
            />
          </div>

          {/* Configuration Panel */}
          <div className="space-y-6">
            {/* Progress indicator */}
            <div className="bg-white rounded-xl p-4 shadow-lg">
              <div className="flex items-center justify-between text-sm text-stone-600 mb-3">
                <span>Onboarding Progress</span>
                <span>{getProgressPercentage(state.step)}%</span>
              </div>
              <div className="h-2 bg-stone-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-amber-500 transition-all duration-500"
                  style={{ width: `${getProgressPercentage(state.step)}%` }}
                />
              </div>
            </div>

            {/* Genre Selection */}
            {(state.step === 'welcome' || state.step === 'genre') && !genreConfirmed && (
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-stone-800 mb-4">
                  Choose Your Genre
                </h3>
                <GenreGrid selectedGenre={selectedGenre} onSelect={handleGenreSelect} />
              </div>
            )}

            {/* Genre Confirmation */}
            {selectedGenre && state.step !== 'welcome' && (
              <GenreConfirmation
                genre={selectedGenre}
                genreName={GENRES.find((g) => g.id === selectedGenre)?.name || ''}
                genreDescription={GENRES.find((g) => g.id === selectedGenre)?.description || ''}
                confirmed={genreConfirmed}
                onConfirm={handleGenreConfirm}
                onEdit={() => {
                  setGenreConfirmed(false);
                  setState((prev) => ({ ...prev, step: 'genre' }));
                }}
              />
            )}

            {/* Protagonist Form */}
            {state.step === 'protagonist' && !protagonistConfirmed && (
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-stone-800 mb-4">
                  Your Protagonist
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-1">
                      Name
                    </label>
                    <input
                      type="text"
                      value={protagonist.name}
                      onChange={(e) => setProtagonist((p) => ({ ...p, name: e.target.value }))}
                      placeholder="What should we call them?"
                      className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <label className="block text-sm font-medium text-stone-700 mb-1">
                        Age
                      </label>
                      <input
                        type="text"
                        value={protagonist.age}
                        onChange={(e) => setProtagonist((p) => ({ ...p, age: e.target.value }))}
                        placeholder="30s, 40s..."
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      />
                    </div>
                    <div>
                      <label className="block text-sm font-medium text-stone-700 mb-1">
                        Occupation
                      </label>
                      <input
                        type="text"
                        value={protagonist.occupation}
                        onChange={(e) => setProtagonist((p) => ({ ...p, occupation: e.target.value }))}
                        placeholder="Detective, professor..."
                        className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                      />
                    </div>
                  </div>
                  <button
                    onClick={handleProtagonistConfirm}
                    disabled={!protagonist.name}
                    className="w-full px-4 py-2 bg-amber-600 text-white rounded-lg font-medium
                               hover:bg-amber-700 transition-colors disabled:bg-stone-300"
                  >
                    Continue
                  </button>
                </div>
              </div>
            )}

            {/* Protagonist Confirmation */}
            {protagonistConfirmed && (
              <ProtagonistConfirmation
                protagonist={protagonist}
                confirmed={protagonistConfirmed}
                onConfirm={() => {}}
                onEdit={() => {
                  setProtagonistConfirmed(false);
                  setState((prev) => ({ ...prev, step: 'protagonist' }));
                }}
              />
            )}

            {/* Preferences Form */}
            {state.step === 'preferences' && !preferencesConfirmed && (
              <div className="bg-white rounded-xl p-6 shadow-lg">
                <h3 className="text-lg font-semibold text-stone-800 mb-4">
                  Your Preferences
                </h3>
                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-1">
                      Story Length
                    </label>
                    <select
                      value={preferences.story_length}
                      onChange={(e) => setPreferences((p) => ({ ...p, story_length: e.target.value }))}
                      className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                    >
                      <option value="short">Short (~1,000 words) - 5 min read</option>
                      <option value="medium">Medium (~2,000 words) - 10 min read</option>
                      <option value="long">Long (~3,500 words) - 15 min read</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-stone-700 mb-1">
                      Delivery Time
                    </label>
                    <input
                      type="time"
                      value={preferences.delivery_time}
                      onChange={(e) => setPreferences((p) => ({ ...p, delivery_time: e.target.value }))}
                      className="w-full px-3 py-2 border border-stone-300 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                    />
                    <p className="text-xs text-stone-500 mt-1">
                      Your timezone: {preferences.timezone}
                    </p>
                  </div>
                  <button
                    onClick={handlePreferencesConfirm}
                    className="w-full px-4 py-2 bg-amber-600 text-white rounded-lg font-medium
                               hover:bg-amber-700 transition-colors"
                  >
                    Complete Setup
                  </button>
                </div>
              </div>
            )}

            {/* Preferences Confirmation */}
            {preferencesConfirmed && (
              <PreferencesConfirmation
                preferences={preferences}
                confirmed={preferencesConfirmed}
                onConfirm={() => {}}
                onEdit={() => {
                  setPreferencesConfirmed(false);
                  setState((prev) => ({ ...prev, step: 'preferences' }));
                }}
              />
            )}

            {/* Completion */}
            {state.step === 'complete' && (
              <div className="bg-gradient-to-r from-amber-500 to-orange-500 rounded-xl p-6 shadow-lg text-white text-center">
                <div className="text-4xl mb-3">🎉</div>
                <h3 className="text-xl font-bold mb-2">You're All Set!</h3>
                <p className="text-amber-100">
                  Redirecting you to your dashboard...
                </p>
              </div>
            )}
          </div>
        </div>
      </main>
    </div>
  );
}

function getProgressPercentage(step: OnboardingStep): number {
  const steps: Record<OnboardingStep, number> = {
    welcome: 10,
    genre: 30,
    protagonist: 60,
    preferences: 85,
    complete: 100,
  };
  return steps[step];
}
