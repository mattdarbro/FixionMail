/**
 * Dashboard Page
 *
 * The main user dashboard showing recent stories, credits, and quick actions.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { useNavigate } from 'react-router-dom';
import { Story } from '../types/story';

interface ActiveJob {
  job_id: string;
  status: string;
  current_step?: string;
  progress_percent: number;
  genre?: string;
  created_at: string;
  started_at?: string;
}

interface NextDelivery {
  delivery_id: string;
  deliver_at: string;
  timezone: string;
  story_title?: string;
  story_genre?: string;
}

interface DashboardStatus {
  active_jobs: ActiveJob[];
  next_delivery?: NextDelivery;
  has_pending_story: boolean;
}

interface JobActivityItem {
  job_id: string;
  status: string;
  current_step?: string;
  progress_percent: number;
  genre?: string;
  title?: string;
  error_message?: string;
  is_daily: boolean;
  created_at: string;
  started_at?: string;
  completed_at?: string;
  generation_time_seconds?: number;
}

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

const STEP_LABELS: Record<string, string> = {
  'pending': 'Queued',
  'starting': 'Starting up',
  'structure': 'Planning story structure',
  'writing': 'Writing narrative',
  'editing': 'Polishing prose',
  'audio': 'Generating audio',
  'image': 'Creating cover image',
  'saving': 'Saving story',
  'done': 'Complete',
};

export function DashboardPage() {
  const { user, session, signOut, refreshUser } = useAuth();
  const navigate = useNavigate();
  const [recentStories, setRecentStories] = useState<Story[]>([]);
  const [totalStories, setTotalStories] = useState(0);
  const [isLoadingStories, setIsLoadingStories] = useState(true);
  const [status, setStatus] = useState<DashboardStatus | null>(null);
  const [isGenerating, setIsGenerating] = useState(false);
  const [activity, setActivity] = useState<JobActivityItem[]>([]);
  const [showActivity, setShowActivity] = useState(false);
  const [isUpgrading, setIsUpgrading] = useState(false);

  const fetchStatus = useCallback(async () => {
    if (!session?.access_token) return;

    try {
      const response = await fetch('/api/stories/status', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data: DashboardStatus = await response.json();
        setStatus(data);
      }
    } catch {
      // Silent fail
    }
  }, [session?.access_token]);

  useEffect(() => {
    if (session?.access_token) {
      fetchRecentStories();
      fetchStatus();

      // Poll for status updates every 10 seconds if there's an active job
      const interval = setInterval(() => {
        fetchStatus();
      }, 10000);

      return () => clearInterval(interval);
    }
  }, [session, fetchStatus]);

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

  const fetchActivity = async () => {
    if (!session?.access_token) return;

    try {
      const response = await fetch('/api/stories/activity?limit=20', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data = await response.json();
        setActivity(data.jobs);
      }
    } catch {
      // Silent fail for activity
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

  const handleGenerateStory = async () => {
    if (!session?.access_token || isGenerating) return;

    setIsGenerating(true);
    try {
      const response = await fetch('/api/stories/generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({}),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to generate story');
      }

      // Refresh status to show the new job
      await fetchStatus();
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate story');
    } finally {
      setIsGenerating(false);
    }
  };

  const handleUpgrade = async () => {
    if (!session?.access_token || isUpgrading) return;

    setIsUpgrading(true);
    try {
      const response = await fetch('/api/users/upgrade-to-premium', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to upgrade');
      }

      // Refresh user data to reflect new subscription status
      if (refreshUser) {
        await refreshUser();
      }

      alert('Welcome to Premium! You now have 30 credits per month.');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to upgrade');
    } finally {
      setIsUpgrading(false);
    }
  };

  const formatDeliveryTime = (isoString: string, tz: string) => {
    try {
      const date = new Date(isoString);
      return date.toLocaleTimeString('en-US', {
        hour: 'numeric',
        minute: '2-digit',
        hour12: true,
        timeZone: tz,
      });
    } catch {
      return new Date(isoString).toLocaleTimeString();
    }
  };

  const getActiveJob = () => status?.active_jobs?.[0];

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
        {/* Story Generation Status - Shows when there's an active job */}
        {getActiveJob() && (
          <div className="bg-gradient-to-r from-blue-500 to-indigo-600 rounded-2xl shadow-lg p-6 mb-8 text-white">
            <div className="flex items-center gap-4">
              <div className="text-4xl animate-pulse">
                {GENRE_ICONS[getActiveJob()?.genre || ''] || '✨'}
              </div>
              <div className="flex-1">
                <h2 className="text-xl font-bold">Your story is being crafted!</h2>
                <p className="text-blue-100 mt-1">
                  {STEP_LABELS[getActiveJob()?.current_step || 'pending'] || getActiveJob()?.current_step || 'Processing...'}
                </p>
                {/* Progress bar */}
                <div className="mt-3 bg-white/20 rounded-full h-2 overflow-hidden">
                  <div
                    className="bg-white h-full rounded-full transition-all duration-500"
                    style={{ width: `${getActiveJob()?.progress_percent || 5}%` }}
                  />
                </div>
                <p className="text-xs text-blue-200 mt-1">
                  {getActiveJob()?.progress_percent || 0}% complete
                </p>
              </div>
            </div>
          </div>
        )}

        {/* Next Scheduled Delivery - Shows when there's a pending delivery but no active job */}
        {!getActiveJob() && status?.next_delivery && (
          <div className="bg-gradient-to-r from-emerald-500 to-teal-600 rounded-2xl shadow-lg p-6 mb-8 text-white">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-4">
                <div className="text-4xl">📬</div>
                <div>
                  <h2 className="text-xl font-bold">Story ready for delivery!</h2>
                  <p className="text-emerald-100 mt-1">
                    "{status.next_delivery.story_title || 'Your story'}" will arrive at{' '}
                    {formatDeliveryTime(status.next_delivery.deliver_at, status.next_delivery.timezone)}
                  </p>
                </div>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold">
                  {formatDeliveryTime(status.next_delivery.deliver_at, status.next_delivery.timezone)}
                </p>
                <p className="text-xs text-emerald-200">scheduled delivery</p>
              </div>
            </div>
          </div>
        )}

        {/* Welcome Section with Generate Button */}
        <div className="bg-white rounded-2xl shadow-lg p-6 mb-8">
          <div className="flex items-start justify-between gap-4">
            <div className="flex items-start gap-4">
              <div className="text-4xl">👋</div>
              <div>
                <h2 className="text-2xl font-bold text-stone-800">Welcome Back!</h2>
                <p className="text-stone-600 mt-1">
                  {status?.has_pending_story ? (
                    <>A story is on its way! </>
                  ) : (
                    <>Daily stories arrive at {user.preferences?.delivery_time || '8:00 AM'}. </>
                  )}
                  Currently reading: <strong className="capitalize">{user.current_genre || 'Mystery'}</strong> stories.
                </p>
              </div>
            </div>
            {!getActiveJob() && (
              <button
                onClick={handleGenerateStory}
                disabled={isGenerating || user.credits < 1}
                className="px-5 py-2.5 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700 transition-colors disabled:bg-stone-300 disabled:cursor-not-allowed flex items-center gap-2 whitespace-nowrap"
              >
                {isGenerating ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    Generating...
                  </>
                ) : (
                  <>✨ Generate Story Now</>
                )}
              </button>
            )}
          </div>
        </div>

        {/* Quick Actions - Prominent section for key user tasks */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-8">
          {/* Story Settings - Most prominent */}
          <button
            onClick={() => navigate('/settings')}
            className="bg-gradient-to-br from-amber-500 to-orange-500 rounded-2xl shadow-lg p-6 text-left hover:from-amber-600 hover:to-orange-600 transition-all hover:scale-[1.02] group"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center text-3xl">
                🎭
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-white">Story Settings</h3>
                <p className="text-amber-100 text-sm mt-1">
                  Genre, characters, intensity & more
                </p>
              </div>
              <svg className="w-6 h-6 text-white/70 group-hover:text-white group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </button>

          {/* Read Stories */}
          <button
            onClick={() => navigate('/stories')}
            className="bg-white rounded-2xl shadow-lg p-6 text-left hover:bg-stone-50 transition-all hover:scale-[1.02] group border-2 border-stone-100 hover:border-amber-200"
          >
            <div className="flex items-center gap-4">
              <div className="w-14 h-14 bg-amber-100 rounded-xl flex items-center justify-center text-3xl">
                📚
              </div>
              <div className="flex-1">
                <h3 className="text-xl font-bold text-stone-800">Your Stories</h3>
                <p className="text-stone-500 text-sm mt-1">
                  {totalStories > 0 ? `${totalStories} stories to read` : 'Stories will appear here'}
                </p>
              </div>
              <svg className="w-6 h-6 text-stone-300 group-hover:text-amber-500 group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </div>
          </button>

          {/* Subscription / Upgrade */}
          {user.subscription_status === 'trial' ? (
            <button
              onClick={handleUpgrade}
              disabled={isUpgrading}
              className="bg-gradient-to-br from-emerald-500 to-teal-600 rounded-2xl shadow-lg p-6 text-left hover:from-emerald-600 hover:to-teal-700 transition-all hover:scale-[1.02] group disabled:opacity-50 disabled:cursor-not-allowed"
            >
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-white/20 rounded-xl flex items-center justify-center text-3xl">
                  {isUpgrading ? (
                    <div className="w-6 h-6 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  ) : (
                    '✨'
                  )}
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-white">Upgrade to Premium</h3>
                  <p className="text-emerald-100 text-sm mt-1">
                    {user.credits} trial credits left - Go unlimited!
                  </p>
                </div>
                <svg className="w-6 h-6 text-white/70 group-hover:text-white group-hover:translate-x-1 transition-all" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            </button>
          ) : (
            <div className="bg-white rounded-2xl shadow-lg p-6 text-left border-2 border-emerald-200">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 bg-emerald-100 rounded-xl flex items-center justify-center text-3xl">
                  💎
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-emerald-700">Premium Active</h3>
                  <p className="text-stone-500 text-sm mt-1">
                    {user.credits} credits this month
                  </p>
                </div>
              </div>
            </div>
          )}
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

        {/* Activity Log */}
        <div className="mt-8 bg-white rounded-2xl shadow-lg p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xl font-bold text-stone-800">Job Activity Log</h3>
            <button
              onClick={() => {
                setShowActivity(!showActivity);
                if (!showActivity) fetchActivity();
              }}
              className="text-sm text-amber-600 hover:text-amber-700 font-medium"
            >
              {showActivity ? 'Hide' : 'Show'} Activity →
            </button>
          </div>

          {showActivity && (
            <div className="space-y-2 max-h-96 overflow-y-auto">
              {activity.length === 0 ? (
                <p className="text-stone-500 text-center py-4">No recent activity</p>
              ) : (
                activity.map((job) => (
                  <div
                    key={job.job_id}
                    className={`p-3 rounded-lg border ${
                      job.status === 'completed'
                        ? 'bg-green-50 border-green-200'
                        : job.status === 'failed'
                        ? 'bg-red-50 border-red-200'
                        : job.status === 'running'
                        ? 'bg-blue-50 border-blue-200'
                        : 'bg-stone-50 border-stone-200'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-lg">
                          {job.status === 'completed' ? '✅' :
                           job.status === 'failed' ? '❌' :
                           job.status === 'running' ? '⏳' : '📋'}
                        </span>
                        <div>
                          <span className="font-medium text-stone-800">
                            {job.title || job.genre || 'Story'}
                          </span>
                          <span className={`ml-2 text-xs px-2 py-0.5 rounded-full ${
                            job.is_daily
                              ? 'bg-blue-100 text-blue-700'
                              : 'bg-amber-100 text-amber-700'
                          }`}>
                            {job.is_daily ? 'Daily' : 'Manual'}
                          </span>
                        </div>
                      </div>
                      <span className="text-xs text-stone-500">
                        {formatDate(job.created_at)}
                      </span>
                    </div>

                    <div className="mt-1 text-sm text-stone-600">
                      <span className="capitalize">{job.status}</span>
                      {job.current_step && job.status === 'running' && (
                        <span> - {STEP_LABELS[job.current_step] || job.current_step}</span>
                      )}
                      {job.generation_time_seconds && (
                        <span className="text-stone-400 ml-2">
                          ({Math.round(job.generation_time_seconds)}s)
                        </span>
                      )}
                    </div>

                    {job.error_message && (
                      <div className="mt-1 text-xs text-red-600 bg-red-100 p-2 rounded">
                        {job.error_message}
                      </div>
                    )}

                    {job.status === 'running' && (
                      <div className="mt-2 bg-white/50 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="bg-blue-500 h-full rounded-full transition-all duration-500"
                          style={{ width: `${job.progress_percent}%` }}
                        />
                      </div>
                    )}
                  </div>
                ))
              )}
            </div>
          )}

          {!showActivity && (
            <p className="text-stone-500 text-sm">
              Click "Show Activity" to see recent story generation jobs and their status.
            </p>
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
