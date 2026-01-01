/**
 * Stories Page
 *
 * Displays user's story library with the ability to read, rate, and
 * request new stories.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { Story, StoryListResponse, StoryStats } from '../types/story';

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

export function StoriesPage() {
  const { session } = useAuth();
  const navigate = useNavigate();

  const [stories, setStories] = useState<Story[]>([]);
  const [stats, setStats] = useState<StoryStats | null>(null);
  const [selectedStory, setSelectedStory] = useState<Story | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(0);
  const [total, setTotal] = useState(0);
  const [isGenerating, setIsGenerating] = useState(false);

  const limit = 12;

  useEffect(() => {
    if (session?.access_token) {
      fetchStories();
      fetchStats();
    }
  }, [session, page]);

  const fetchStories = async () => {
    if (!session?.access_token) return;

    try {
      const response = await fetch(
        `/api/stories?limit=${limit}&offset=${page * limit}`,
        {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        }
      );

      if (!response.ok) throw new Error('Failed to fetch stories');

      const data: StoryListResponse = await response.json();
      setStories(data.stories);
      setTotal(data.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load stories');
    } finally {
      setIsLoading(false);
    }
  };

  const fetchStats = async () => {
    if (!session?.access_token) return;

    try {
      const response = await fetch('/api/stories/stats', {
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data: StoryStats = await response.json();
        setStats(data);
      }
    } catch {
      // Stats are optional, don't show error
    }
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

      // Navigate to dashboard to show generation progress
      navigate('/dashboard');
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to generate story');
      setIsGenerating(false);
    }
  };

  const handleRateStory = async (storyId: string, rating: number) => {
    if (!session?.access_token) return;

    try {
      await fetch(`/api/stories/${storyId}/rate?rating=${rating}`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
        },
      });

      // Update local state
      setStories(stories.map(s =>
        s.id === storyId ? { ...s, rating } : s
      ));

      if (selectedStory?.id === storyId) {
        setSelectedStory({ ...selectedStory, rating });
      }
    } catch {
      // Silent fail for ratings
    }
  };

  const formatDate = (dateString: string) => {
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  const formatReadTime = (wordCount: number) => {
    const minutes = Math.ceil(wordCount / 200);
    return `${minutes} min read`;
  };

  if (isLoading) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-amber-600 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-stone-600">Loading your stories...</p>
        </div>
      </div>
    );
  }

  // Story Reader Modal
  if (selectedStory) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100">
        <header className="bg-white/80 backdrop-blur-sm border-b border-amber-200 sticky top-0 z-10">
          <div className="max-w-4xl mx-auto px-4 py-4">
            <div className="flex items-center justify-between">
              <button
                onClick={() => setSelectedStory(null)}
                className="flex items-center gap-2 text-stone-600 hover:text-amber-700"
              >
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
                Back to Library
              </button>

              {/* Rating */}
              <div className="flex items-center gap-2">
                <span className="text-sm text-stone-500">Rate:</span>
                <div className="flex gap-1">
                  {[1, 2, 3, 4, 5].map((star) => (
                    <button
                      key={star}
                      onClick={() => handleRateStory(selectedStory.id, star)}
                      className={`text-xl transition-transform hover:scale-110 ${
                        selectedStory.rating && star <= selectedStory.rating
                          ? 'text-amber-500'
                          : 'text-stone-300'
                      }`}
                    >
                      ★
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>
        </header>

        <main className="max-w-3xl mx-auto px-4 py-8">
          {/* Story Header */}
          <div className="mb-8 text-center">
            <div className="text-4xl mb-4">
              {GENRE_ICONS[selectedStory.genre] || '📖'}
            </div>
            <h1 className="text-3xl font-bold text-stone-800 mb-2">
              {selectedStory.title}
            </h1>
            <p className="text-stone-500">
              {formatDate(selectedStory.created_at)} · {formatReadTime(selectedStory.word_count)} · {selectedStory.genre}
            </p>
          </div>

          {/* Cover Image */}
          {selectedStory.image_url && (
            <div className="mb-8 rounded-2xl overflow-hidden shadow-lg">
              <img
                src={selectedStory.image_url}
                alt={selectedStory.title}
                className="w-full h-64 object-cover"
              />
            </div>
          )}

          {/* Audio Player */}
          {selectedStory.audio_url && (
            <div className="mb-8 bg-white rounded-xl p-4 shadow-md">
              <div className="flex items-center gap-3 mb-2">
                <span className="text-lg">🎧</span>
                <span className="font-medium text-stone-700">Listen to this story</span>
              </div>
              <audio
                controls
                className="w-full"
                src={selectedStory.audio_url}
              >
                Your browser does not support the audio element.
              </audio>
            </div>
          )}

          {/* Story Content */}
          <article className="bg-white rounded-2xl shadow-lg p-8">
            <div className="prose prose-stone prose-lg max-w-none">
              {selectedStory.narrative.split('\n\n').map((paragraph, idx) => (
                <p key={idx} className="mb-4 leading-relaxed text-stone-700">
                  {paragraph}
                </p>
              ))}
            </div>
          </article>

          {/* Story Footer */}
          <div className="mt-8 text-center">
            <p className="text-stone-500 mb-4">
              {selectedStory.word_count.toLocaleString()} words
            </p>
            <button
              onClick={() => navigate('/chat', {
                state: {
                  storyId: selectedStory.id,
                  storyTitle: selectedStory.title,
                  storyGenre: selectedStory.genre
                }
              })}
              className="px-6 py-3 bg-amber-600 text-white rounded-xl font-medium hover:bg-amber-700 transition-colors"
            >
              💬 Discuss with Fixion
            </button>
          </div>
        </main>
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
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-stone-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-xl font-bold text-amber-800">Your Story Library</h1>
                <p className="text-xs text-stone-500">
                  {total} {total === 1 ? 'story' : 'stories'} in your collection
                </p>
              </div>
            </div>
            <button
              onClick={handleGenerateStory}
              disabled={isGenerating}
              className="px-4 py-2 bg-amber-600 text-white rounded-lg font-medium hover:bg-amber-700 transition-colors disabled:bg-stone-300 flex items-center gap-2"
            >
              {isGenerating ? (
                <>
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Generating...
                </>
              ) : (
                <>
                  ✨ New Story
                </>
              )}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-8">
        {/* Stats Banner */}
        {stats && stats.total_stories > 0 && (
          <div className="bg-white rounded-2xl shadow-md p-6 mb-8">
            <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
              <div>
                <div className="text-3xl font-bold text-amber-600">{stats.total_stories}</div>
                <div className="text-sm text-stone-500">Total Stories</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-amber-600">
                  {(stats.total_words / 1000).toFixed(1)}k
                </div>
                <div className="text-sm text-stone-500">Words Read</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-amber-600">
                  {Object.keys(stats.genres).length}
                </div>
                <div className="text-sm text-stone-500">Genres Explored</div>
              </div>
              <div>
                <div className="text-3xl font-bold text-amber-600">
                  {stats.average_rating > 0 ? stats.average_rating.toFixed(1) : '—'}
                </div>
                <div className="text-sm text-stone-500">Avg Rating</div>
              </div>
            </div>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 text-red-700 p-4 rounded-xl mb-6">
            {error}
          </div>
        )}

        {/* Empty State */}
        {stories.length === 0 && !error && (
          <div className="text-center py-16">
            <div className="text-6xl mb-4">📚</div>
            <h2 className="text-2xl font-bold text-stone-800 mb-2">
              Your library is empty
            </h2>
            <p className="text-stone-500 mb-6">
              Stories you receive will appear here. Generate your first story to get started!
            </p>
            <button
              onClick={handleGenerateStory}
              disabled={isGenerating}
              className="px-6 py-3 bg-amber-600 text-white rounded-xl font-medium hover:bg-amber-700 transition-colors disabled:bg-stone-300"
            >
              {isGenerating ? 'Generating...' : '✨ Generate Your First Story'}
            </button>
          </div>
        )}

        {/* Story Grid */}
        {stories.length > 0 && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {stories.map((story) => (
              <button
                key={story.id}
                onClick={() => setSelectedStory(story)}
                className="bg-white rounded-2xl shadow-md overflow-hidden hover:shadow-lg transition-shadow text-left group"
              >
                {/* Cover Image or Gradient */}
                <div className="h-32 relative">
                  {story.image_url ? (
                    <img
                      src={story.image_url}
                      alt={story.title}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-gradient-to-br from-amber-100 to-amber-200 flex items-center justify-center">
                      <span className="text-5xl">
                        {GENRE_ICONS[story.genre] || '📖'}
                      </span>
                    </div>
                  )}
                  {/* Genre Badge */}
                  <div className="absolute top-2 right-2 px-2 py-1 bg-black/50 backdrop-blur-sm rounded-full text-xs text-white">
                    {story.genre}
                  </div>
                  {/* Audio indicator */}
                  {story.audio_url && (
                    <div className="absolute bottom-2 left-2 w-8 h-8 bg-black/50 backdrop-blur-sm rounded-full flex items-center justify-center">
                      <span className="text-white text-sm">🎧</span>
                    </div>
                  )}
                </div>

                {/* Content */}
                <div className="p-4">
                  <h3 className="font-semibold text-stone-800 mb-1 line-clamp-1 group-hover:text-amber-700 transition-colors">
                    {story.title}
                  </h3>
                  <p className="text-sm text-stone-500 line-clamp-2 mb-3">
                    {story.narrative.slice(0, 120)}...
                  </p>
                  <div className="flex items-center justify-between text-xs text-stone-400">
                    <span>{formatDate(story.created_at)}</span>
                    <span>{formatReadTime(story.word_count)}</span>
                  </div>
                  {/* Rating */}
                  {story.rating && (
                    <div className="mt-2 text-amber-500">
                      {'★'.repeat(story.rating)}
                      {'☆'.repeat(5 - story.rating)}
                    </div>
                  )}
                </div>
              </button>
            ))}
          </div>
        )}

        {/* Pagination */}
        {total > limit && (
          <div className="flex justify-center gap-4 mt-8">
            <button
              onClick={() => setPage(p => Math.max(0, p - 1))}
              disabled={page === 0}
              className="px-4 py-2 bg-white rounded-lg shadow-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-amber-50 transition-colors"
            >
              ← Previous
            </button>
            <span className="px-4 py-2 text-stone-600">
              Page {page + 1} of {Math.ceil(total / limit)}
            </span>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={(page + 1) * limit >= total}
              className="px-4 py-2 bg-white rounded-lg shadow-md disabled:opacity-50 disabled:cursor-not-allowed hover:bg-amber-50 transition-colors"
            >
              Next →
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
