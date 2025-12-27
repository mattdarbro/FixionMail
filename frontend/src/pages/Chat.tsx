/**
 * Chat Page
 *
 * Full-page chat interface for talking with Fixion.
 * Accessible after onboarding is complete.
 */

import { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { FixionChat } from '../components/FixionChat';
import { ChatMessage } from '../types/chat';

interface LocationState {
  storyId?: string;
  storyTitle?: string;
  storyGenre?: string;
}

export function ChatPage() {
  const { user, session } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const locationState = location.state as LocationState | null;

  // Extract story context from navigation state
  const storyContext = locationState?.storyId ? {
    storyId: locationState.storyId,
    storyTitle: locationState.storyTitle,
    storyGenre: locationState.storyGenre,
  } : null;

  const [conversationId, setConversationId] = useState<string | undefined>();
  const [initialMessages, setInitialMessages] = useState<ChatMessage[]>([]);
  const [isLoadingHistory, setIsLoadingHistory] = useState(true);

  // Load conversation history or start fresh
  useEffect(() => {
    async function loadOrStartConversation() {
      if (!session?.access_token) return;

      // If we have story context, start a fresh story discussion
      if (storyContext) {
        const storyTitle = storyContext.storyTitle || 'this story';
        setInitialMessages([
          {
            role: 'assistant',
            content: `I see you've been reading "${storyTitle}"! What did you think? I'd love to hear your thoughts, answer questions about the plot, discuss character motivations, or help you explore what happens next.\n\nWhat's on your mind?`,
            timestamp: new Date().toISOString(),
          },
        ]);
        setIsLoadingHistory(false);
        return;
      }

      try {
        // Try to get recent conversations
        const response = await fetch('/api/chat/conversations?limit=1', {
          headers: {
            'Authorization': `Bearer ${session.access_token}`,
          },
        });

        if (response.ok) {
          const data = await response.json();
          if (data.conversations && data.conversations.length > 0) {
            const lastConvo = data.conversations[0];
            // Only resume if it's a general chat (not onboarding)
            if (lastConvo.context_type === 'general') {
              setConversationId(lastConvo.id);

              // Load messages from this conversation
              const messagesRes = await fetch(`/api/chat/conversations/${lastConvo.id}/messages`, {
                headers: {
                  'Authorization': `Bearer ${session.access_token}`,
                },
              });

              if (messagesRes.ok) {
                const messagesData = await messagesRes.json();
                if (messagesData.messages) {
                  setInitialMessages(messagesData.messages.map((m: any) => ({
                    role: m.role,
                    content: m.content,
                    timestamp: m.created_at,
                  })));
                }
              }
            }
          }
        }
      } catch (error) {
        console.error('Error loading conversation:', error);
      } finally {
        setIsLoadingHistory(false);
      }
    }

    loadOrStartConversation();
  }, [session?.access_token, storyContext]);

  // Add welcome message if starting fresh (and no story context)
  useEffect(() => {
    if (!isLoadingHistory && initialMessages.length === 0 && !storyContext) {
      const genre = user?.current_genre || 'mystery';
      setInitialMessages([
        {
          role: 'assistant',
          content: `Welcome back! I'm Fixion, your personal story curator. We're currently exploring ${genre} stories together.\n\nWhat's on your mind? We can chat about your recent stories, discuss what you'd like to see next, or just talk about anything story-related.`,
          timestamp: new Date().toISOString(),
        },
      ]);
    }
  }, [isLoadingHistory, initialMessages.length, user?.current_genre, storyContext]);

  if (!user) {
    return (
      <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex items-center justify-center">
        <div className="text-center">
          <div className="text-5xl mb-4 animate-bounce">🎭</div>
          <p className="text-stone-600">Loading...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100 flex flex-col">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-amber-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
                title="Back to Dashboard"
              >
                <svg className="w-5 h-5 text-stone-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div className="flex items-center gap-2">
                <span className="text-3xl">🎭</span>
                <div>
                  <h1 className="text-xl font-bold text-amber-800">Chat with Fixion</h1>
                  <p className="text-xs text-stone-500">Your personal story curator</p>
                </div>
              </div>
            </div>
            <div className="flex items-center gap-3">
              {storyContext ? (
                <span className="text-sm text-stone-500">
                  Discussing: <span className="font-medium text-amber-700">{storyContext.storyTitle}</span>
                </span>
              ) : (
                <span className="text-sm text-stone-500 capitalize">
                  {user.current_genre || 'Mystery'} mode
                </span>
              )}
              <button
                onClick={() => {
                  // Clear story context by navigating without state
                  navigate('/chat', { replace: true, state: null });
                  setConversationId(undefined);
                  setInitialMessages([{
                    role: 'assistant',
                    content: "Fresh start! What would you like to chat about?",
                    timestamp: new Date().toISOString(),
                  }]);
                }}
                className="px-3 py-1.5 text-sm text-amber-600 hover:text-amber-700 hover:bg-amber-50 rounded-lg transition-colors"
              >
                New Chat
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* Chat Area */}
      <main className="flex-1 max-w-4xl w-full mx-auto flex flex-col">
        {isLoadingHistory ? (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <div className="text-4xl mb-3 animate-pulse">🎭</div>
              <p className="text-stone-500">Loading conversation...</p>
            </div>
          </div>
        ) : (
          <FixionChat
            conversationId={conversationId}
            onConversationIdChange={setConversationId}
            context={{
              genre: user.current_genre,
              storyId: storyContext?.storyId,
              contextType: storyContext ? 'story_discussion' : 'general',
            }}
            initialMessages={initialMessages}
            placeholder={storyContext
              ? `Share your thoughts on "${storyContext.storyTitle}"...`
              : "Ask Fixion anything about your stories..."
            }
            className="flex-1"
          />
        )}
      </main>

      {/* Quick Actions Footer */}
      <footer className="bg-white/80 backdrop-blur-sm border-t border-amber-200">
        <div className="max-w-4xl mx-auto px-4 py-3">
          <div className="flex items-center justify-center gap-4 text-sm">
            <button
              onClick={() => navigate('/dashboard')}
              className="text-stone-500 hover:text-amber-600 transition-colors"
            >
              Back to Dashboard
            </button>
            <span className="text-stone-300">•</span>
            <button
              onClick={() => navigate('/stories')}
              className="text-stone-500 hover:text-amber-600 transition-colors"
            >
              View Stories
            </button>
          </div>
        </div>
      </footer>
    </div>
  );
}
