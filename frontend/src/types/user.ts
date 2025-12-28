/**
 * User-related type definitions
 */

export interface UserPreferences {
  story_length?: 'short' | 'medium' | 'long';
  delivery_time?: string; // HH:MM format
  timezone?: string;
  voice_id?: string;
  model_preference?: 'sonnet' | 'opus';
}

export interface StoryBible {
  protagonist?: {
    name?: string;
    age?: string;
    occupation?: string;
    personality?: string[];
    goals?: string[];
    backstory?: string;
  };
  setting?: {
    time_period?: string;
    location?: string;
    atmosphere?: string;
    description?: string;
    name?: string;
  };
  themes?: string[];
  tone?: string;
  genre?: string;
  intensity?: number;
  main_characters?: Array<{ name: string; description: string }>;
  story_settings?: {
    intensity_label?: string;
    story_length?: string;
    beat_structure?: string;
    undercurrent_mode?: string;
    undercurrent_custom?: string | null;
    undercurrent_match_intensity?: boolean;
  };
  beat_structure?: string;
  [key: string]: unknown;
}

export interface User {
  id: string;
  email: string;
  credits: number;
  subscription_status: 'trial' | 'active' | 'past_due' | 'cancelled' | 'expired';
  subscription_tier?: 'monthly' | 'annual';
  current_period_end?: string;
  onboarding_completed: boolean;
  onboarding_step?: string;
  current_genre?: string;
  preferences: UserPreferences;
  story_bible: StoryBible;
  created_at: string;
}

export interface CreditBalance {
  credits: number;
  subscription_status: string;
  subscription_tier?: string;
}

export interface UserStats {
  total_stories: number;
  original_stories: number;
  retells: number;
  genres: Record<string, number>;
  total_words: number;
  average_rating: number;
}
