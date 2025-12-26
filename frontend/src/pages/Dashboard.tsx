/**
 * Dashboard Page
 *
 * The main user dashboard showing recent stories, credits, and quick actions.
 */

import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';

export function DashboardPage() {
  const { user, signOut } = useAuth();
  const navigate = useNavigate();

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

        {/* Recent Stories Placeholder */}
        <div className="bg-white rounded-2xl shadow-lg p-6">
          <h3 className="text-xl font-bold text-stone-800 mb-4">Recent Stories</h3>
          <div className="text-center py-12 text-stone-500">
            <div className="text-5xl mb-4">📚</div>
            <p className="text-lg">Your stories will appear here</p>
            <p className="text-sm mt-2">
              Your first story will arrive at your scheduled delivery time.
            </p>
          </div>
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
