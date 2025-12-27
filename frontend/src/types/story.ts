export interface Choice {
  id: number;
  text: string;
  consequence_hint: string;
}

export interface StoryResponse {
  session_id: string;
  narrative: string;
  choices: Choice[];
  current_beat: number;
  credits_remaining: number;
  image_url?: string;
  audio_url?: string;
}

export interface StartStoryRequest {
  world_id: string;
  user_id?: string;
  generate_audio?: boolean;  // Optional: control audio generation (default: from config)
  generate_image?: boolean;  // Optional: control image generation (default: from config)
  voice_id?: string;         // Optional: OpenAI TTS voice (default: from config)
}

export interface ContinueStoryRequest {
  session_id: string;
  choice_id: number;
  generate_audio?: boolean;  // Optional: control audio generation (default: from config)
  generate_image?: boolean;  // Optional: control image generation (default: from config)
  voice_id?: string;         // Optional: OpenAI TTS voice (default: from config)
}

export interface StoryState {
  sessionId: string | null;
  narrative: string;
  choices: Choice[];
  currentBeat: number;
  creditsRemaining: number;
  isLoading: boolean;
  error: string | null;
  imageUrl?: string;
  audioUrl?: string;
}

// FixionMail standalone story types
export interface Story {
  id: string;
  title: string;
  narrative: string;
  genre: string;
  word_count: number;
  audio_url?: string;
  image_url?: string;
  rating?: number;
  is_retell: boolean;
  created_at: string;
}

export interface StoryListResponse {
  stories: Story[];
  total: number;
  limit: number;
  offset: number;
}

export interface StoryStats {
  total_stories: number;
  original_stories: number;
  retells: number;
  genres: Record<string, number>;
  total_words: number;
  average_rating: number;
}

export interface GenerateStoryRequest {
  genre?: string;
  intensity?: number;
}

export interface GenerateStoryResponse {
  job_id: string;
  message: string;
  status: string;
}

export interface JobStatus {
  job_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  current_step?: string;
  progress_percent: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}
