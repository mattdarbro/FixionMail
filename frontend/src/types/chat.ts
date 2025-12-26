/**
 * Fixion Chat type definitions
 */

export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

export interface ChatResponse {
  response: string;
  conversation_id: string;
  message_id?: string;
}

export interface OnboardingStartResponse {
  response: string;
  conversation_id: string;
  available_genres: Genre[];
}

export interface Genre {
  id: string;
  name: string;
  description: string;
  icon: string;
}

export interface GenreSelectionResponse {
  response: string;
  conversation_id: string;
  genre: string;
  persona: string;
  next_step: string;
}

export interface StoryDiscussResponse {
  response: string;
  story_id: string;
  conversation_id: string;
}

export interface RetellAnalysis {
  revision_type: 'surface' | 'prose' | 'structure';
  credit_cost: number;
  writers_room_story: string;
  confirmation_needed: boolean;
}

export interface RetellRequestResponse {
  response: string;
  analysis?: RetellAnalysis;
  confirmation_needed: boolean;
}

export interface ConfirmationCard {
  id: string;
  type: 'genre' | 'protagonist' | 'setting' | 'preferences';
  title: string;
  summary: string;
  details: Record<string, string | string[]>;
  confirmed: boolean;
}

export interface OnboardingState {
  step: 'welcome' | 'genre' | 'protagonist' | 'preferences' | 'complete';
  conversationId?: string;
  selectedGenre?: string;
  confirmationCards: ConfirmationCard[];
  storyBible: Record<string, unknown>;
}
