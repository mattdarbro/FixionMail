/**
 * Fixion Chat Component
 *
 * The main chat interface for talking with Fixion during onboarding
 * and story discussions.
 */

import { useState, useRef, useEffect, KeyboardEvent } from 'react';
import { ChatMessage } from '../types/chat';
import { useAuth } from '../contexts/AuthContext';
import { chatApi } from '../services/chatApi';

interface FixionChatProps {
  conversationId?: string;
  onConversationIdChange?: (id: string) => void;
  context?: {
    genre?: string;
    onboarding_step?: string;
  };
  initialMessages?: ChatMessage[];
  placeholder?: string;
  className?: string;
}

export function FixionChat({
  conversationId,
  onConversationIdChange,
  context,
  initialMessages = [],
  placeholder = "Type a message to Fixion...",
  className = "",
}: FixionChatProps) {
  const { session } = useAuth();
  const [messages, setMessages] = useState<ChatMessage[]>(initialMessages);
  const [input, setInput] = useState('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 150)}px`;
    }
  }, [input]);

  const handleSend = async () => {
    if (!input.trim() || isStreaming || !session?.access_token) return;

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
      timestamp: new Date().toISOString(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsStreaming(true);
    setStreamingContent('');

    // Use streaming API
    chatApi.streamMessage(
      session.access_token,
      userMessage.content,
      conversationId,
      context,
      // onToken
      (token) => {
        setStreamingContent((prev) => prev + token);
      },
      // onComplete
      (response) => {
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: response.response,
            timestamp: new Date().toISOString(),
          },
        ]);
        setStreamingContent('');
        setIsStreaming(false);

        if (response.conversation_id && onConversationIdChange) {
          onConversationIdChange(response.conversation_id);
        }
      },
      // onError
      (error) => {
        console.error('Chat error:', error);
        setMessages((prev) => [
          ...prev,
          {
            role: 'assistant',
            content: "Oh dear, something went wrong on my end. The writers room is having... technical difficulties. Give me a moment and try again?",
            timestamp: new Date().toISOString(),
          },
        ]);
        setStreamingContent('');
        setIsStreaming(false);
      }
    );
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className={`flex flex-col h-full ${className}`}>
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.map((message, index) => (
          <div
            key={index}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                message.role === 'user'
                  ? 'bg-amber-600 text-white rounded-br-md'
                  : 'bg-stone-100 text-stone-800 rounded-bl-md'
              }`}
            >
              {message.role === 'assistant' && (
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-lg">🎭</span>
                  <span className="font-medium text-amber-700">Fixion</span>
                </div>
              )}
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {message.content}
              </p>
            </div>
          </div>
        ))}

        {/* Streaming message */}
        {isStreaming && streamingContent && (
          <div className="flex justify-start">
            <div className="max-w-[80%] rounded-2xl rounded-bl-md px-4 py-3 bg-stone-100 text-stone-800">
              <div className="flex items-center gap-2 mb-1">
                <span className="text-lg">🎭</span>
                <span className="font-medium text-amber-700">Fixion</span>
              </div>
              <p className="whitespace-pre-wrap text-sm leading-relaxed">
                {streamingContent}
                <span className="inline-block w-2 h-4 bg-amber-600 animate-pulse ml-0.5" />
              </p>
            </div>
          </div>
        )}

        {/* Typing indicator */}
        {isStreaming && !streamingContent && (
          <div className="flex justify-start">
            <div className="rounded-2xl rounded-bl-md px-4 py-3 bg-stone-100">
              <div className="flex items-center gap-2">
                <span className="text-lg">🎭</span>
                <div className="flex gap-1">
                  <div className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <div className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <div className="w-2 h-2 bg-stone-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t border-stone-200 p-4 bg-white">
        <div className="flex gap-3 items-end">
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={placeholder}
            disabled={isStreaming || !session}
            rows={1}
            className="flex-1 resize-none rounded-xl border border-stone-300 px-4 py-3 text-sm
                       bg-white text-stone-800
                       focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent
                       disabled:bg-stone-50 disabled:text-stone-400
                       placeholder:text-stone-400"
          />
          <button
            onClick={handleSend}
            disabled={!input.trim() || isStreaming || !session}
            className="px-4 py-3 bg-amber-600 text-white rounded-xl font-medium
                       hover:bg-amber-700 transition-colors
                       disabled:bg-stone-300 disabled:cursor-not-allowed"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
            </svg>
          </button>
        </div>
        <p className="text-xs text-stone-400 mt-2 text-center">
          Shift + Enter for new line
        </p>
      </div>
    </div>
  );
}
