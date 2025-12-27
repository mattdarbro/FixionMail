/**
 * Dashboard Page
 *
 * The main user dashboard showing recent stories, credits, and quick actions.
 */

import { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Story } from '../types/story';

const GENRE_ICONS: Record<string, string> = {
  mystery: '🔍',
  romance: '💕',
  comedy: '😂',
  fantasy: '🧙',
  scifi: '🚀',
  cozy: '☕',
  western: '🤠',
  action: '💥',
  historical: '📜',
  strange_fables: '🌀',
};

export function DashboardPage() {
  const { user, session, signOut } = useAuth();
  const navigate = useNavigate();
  const [recentStories, setRecentStories] = useState<Story[]>([]);
  const [totalStories, setTotalStories] = useState(0);
  const [isLoadingStories, setIsLoadingStories] = useState(true);

  useEffect(() => {
    if (session?.access_token) {
      fetchRecentStories();
    }
  }, [session]);

  const fetchRecentStories = async () => {
    if (!session?.access_token) return;

    try {
      const response = await fetch('/api/stories?limit=3', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setRecentStories(data.stories);
        setTotalStories(data.total);
      }
    } catch {
      // Silent fail for stories
    } finally {
      setIsLoadingStories(false);
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
    });
  };

  const handleSignOut = async () => {
    await signOut();
    navigate('/login');
  };

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🎭</div>
          <p className="text-stone-600">Loading your dashboard...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-amber-200 sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-3xl">🎭</span>
              <div>
                <h1 className="text-xl font-bold text-amber-800">FixionMail</h1>
                <p className="text-xs text-stone-500">Your Personal Story Studio</p>
              </div>
            </div>
            <div className="flex items-center gap-4">
              <div className="text-right">
                <p className="text-sm font-medium text-stone-800">{user.email}</p>
                <p className="text-xs text-stone-500">
                  {user.credits} credit{user.credits !== 1 ? 's' : ''} remaining
                </p>
              </div>
              <button
                onClick={() => navigate('/settings')}
                className="px-3 py-1.5 text-sm bg-amber-100 text-amber-700 hover:bg-amber-200 rounded-lg transition-colors"
              >
                ⚙️ Settings
              </button>
              <button
                onClick={handleSignOut}
                className="px-3 py-1 text-sm text-stone-600 hover:text-stone-800 transition-colors"
              >
                Sign Out
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Welcome Section */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <div className="flex items-start gap-4">
            <div className="text-4xl">👋</div>
            <div>
              <h2 className="text-2xl font-bold text-stone-800">Welcome Back!</h2>
              <p className="text-stone-600 mt-1">
                Your next story will arrive at {user.preferences?.delivery_time || '8:00 AM'}.
                Currently reading: <strong>{user.current_genre || 'Mystery'}</strong> stories.
              </p>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">📖</span>
              <h3 className="font-semibold text-stone-700">Credits</h3>
            </div>
            <p className="text-3xl font-bold text-amber-600">{user.credits}</p>
            <p className="text-sm text-stone-500 mt-1">
              {user.subscription_status === 'active' ? 'Renews monthly' : 'Trial credits'}
            </p>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">🎭</span>
              <h3 className="font-semibold text-stone-700">Genre</h3>
            </div>
            <p className="text-3xl font-bold text-amber-600 capitalize">
              {user.current_genre || 'Not Set'}
            </p>
            <button
              onClick={() => navigate('/settings')}
              className="text-sm text-amber-600 hover:text-amber-700 mt-1"
            >
              Change genre
            </button>
          </div>

          <div className="bg-white rounded-xl shadow-lg p-6">
            <div className="flex items-center gap-3 mb-2">
              <span className="text-2xl">⏰</span>
              <h3 className="font-semibold text-stone-700">Delivery</h3>
            </div>
            <p className="text-3xl font-bold text-amber-600">
              {user.preferences?.delivery_time || '08:00'}
            </p>
            <button
              onClick={() => navigate('/settings')}
              className="text-sm text-amber-600 hover:text-amber-700 mt-1"
            >
              Change time
            </button>
          </div>
        </div>

        {/* Recent Stories */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-stone-800">Recent Stories</h3>
            {totalStories > 0 && (
              <button
                onClick={() => navigate('/stories')}
                className="text-sm text-amber-600 hover:text-amber-700 font-medium"
              >
                View All ({totalStories}) →
              </button>
            )}
          </div>

          {isLoadingStories ? (
            <div className="text-center py-8">
              <div className="w-8 h-8 border-4 border-amber-600 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="text-stone-500 text-sm">Loading stories...</p>
            </div>
          ) : recentStories.length > 0 ? (
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {recentStories.map((story) => (
                <button
                  key={story.id}
                  onClick={() => navigate('/stories')}
                  className="bg-stone-50 rounded-xl p-4 text-left hover:bg-amber-50 transition-colors group"
                >
                  <div className="flex items-start gap-3">
                    <div className="text-3xl">
                      {GENRE_ICONS[story.genre] || '📖'}
                    </div>
                    <div className="flex-1 min-w-0">
                      <h4 className="font-semibold text-stone-800 truncate group-hover:text-amber-700 transition-colors">
                        {story.title}
                      </h4>
                      <p className="text-xs text-stone-500 mt-1">
                        {formatDate(story.created_at)} · {Math.ceil(story.word_count / 200)} min
                      </p>
                      {story.rating && (
                        <div className="mt-1 text-amber-500 text-xs">
                          {'★'.repeat(story.rating)}{'☆'.repeat(5 - story.rating)}
                        </div>
                      )}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          ) : (
            <div className="text-center py-12 text-stone-500">
              <div className="text-5xl mb-4">📚</div>
              <p className="text-lg">Your stories will appear here</p>
              <p className="text-sm mt-2">
                Your first story will arrive at your scheduled delivery time.
              </p>
            </div>
          )}
        </div>

        {/* Chat with Fixion CTA */}
        <div className="mt-8 bg-gradient-to-r from-amber-500 to-orange-500 rounded-2xl shadow-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <span className="text-4xl">💬</span>
              <div>
                <h3 className="text-xl font-bold">Talk to Fixion</h3>
                <p className="text-amber-100">
                  Want a different take on a story? Or just want to chat?
                </p>
              </div>
            </div>
            <button
              onClick={() => navigate('/chat')}
              className="px-6 py-3 bg-white text-amber-600 rounded-lg font-semibold hover:bg-amber-50 transition-colors"
            >
              Open Chat
            </button>
          </div>
        </div>
      </main>
    </div>
  );
}
