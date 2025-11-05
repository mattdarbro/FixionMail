import { AudioPlayer } from './AudioPlayer';
import { AnimatedNarrative } from './AnimatedNarrative';

interface NarrativeCardProps {
  narrative: string;
  currentBeat: number;
  imageUrl?: string;
  audioUrl?: string;
  isGeneratingAudio?: boolean;
  isGeneratingImage?: boolean;
  isStreaming?: boolean;
  className?: string;
}

// Helper to get full media URLs from backend
const getMediaUrl = (url?: string) => {
  if (!url) return undefined;
  // If URL is already absolute, return as-is
  if (url.startsWith('http')) return url;
  // Otherwise prepend backend URL
  const backendUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
  return `${backendUrl}${url}`;
};

export function NarrativeCard({
  narrative,
  currentBeat,
  imageUrl,
  audioUrl,
  isGeneratingAudio = false,
  isGeneratingImage = false,
  isStreaming = false,
  className = ''
}: NarrativeCardProps) {
  return (
    <div className={`relative ${className}`}>
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-dark-900 via-dark-800 to-primary-950 rounded-xl opacity-50"></div>
      
      {/* Main card */}
      <div className="relative bg-dark-800/80 backdrop-blur-sm border border-primary-500/20 rounded-xl p-6 shadow-xl">
        {/* Beat indicator */}
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-accent-500 rounded-full animate-pulse"></div>
            <span className="text-sm font-medium text-accent-400">
              Beat {currentBeat}
            </span>
          </div>
          <div className="text-xs text-dark-400 font-fantasy">
            The Forgotten One Who Fell
          </div>
        </div>
        
        {/* Image display with loading states */}
        <div className="mb-6">
          {imageUrl ? (
            <div className="relative rounded-lg overflow-hidden group">
              <img
                src={getMediaUrl(imageUrl)}
                alt="Story scene"
                className="w-full h-48 object-cover transition-all duration-300 group-hover:scale-105"
                onLoad={() => console.log('Image loaded successfully')}
                onError={(e) => console.log('Image failed to load:', e)}
              />
              {/* Hover overlay for zoom effect */}
              <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-all duration-300 flex items-center justify-center">
                <div className="opacity-0 group-hover:opacity-100 transition-opacity duration-300">
                  <svg className="w-8 h-8 text-white" fill="currentColor" viewBox="0 0 24 24">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                  </svg>
                </div>
              </div>
            </div>
          ) : isGeneratingImage ? (
            <div className="rounded-lg bg-gradient-to-br from-dark-700 to-dark-600 h-48 flex items-center justify-center border border-primary-500/20 relative overflow-hidden">
              {/* Loading animation */}
              <div className="text-center">
                <div className="w-12 h-12 mx-auto mb-3 relative">
                  <div className="absolute inset-0 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
                  <div className="absolute inset-2 border-2 border-accent-200 border-t-accent-500 rounded-full animate-spin" style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
                </div>
                <p className="text-sm text-primary-300 font-medium">Generating scene image...</p>
                <p className="text-xs text-dark-400 mt-1">This may take 10-15 seconds</p>
              </div>
            </div>
          ) : (
            <div className="rounded-lg bg-gradient-to-br from-dark-700 to-dark-600 h-48 flex items-center justify-center border border-primary-500/20 relative overflow-hidden">
              {/* Animated background pattern */}
              <div className="absolute inset-0 opacity-10">
                <div className="absolute top-4 left-4 w-8 h-8 border border-primary-400 rounded-full animate-pulse"></div>
                <div className="absolute top-8 right-8 w-6 h-6 border border-accent-400 rounded-full animate-pulse" style={{ animationDelay: '0.5s' }}></div>
                <div className="absolute bottom-6 left-8 w-4 h-4 border border-secondary-400 rounded-full animate-pulse" style={{ animationDelay: '1s' }}></div>
                <div className="absolute bottom-8 right-6 w-10 h-10 border border-primary-300 rounded-full animate-pulse" style={{ animationDelay: '1.5s' }}></div>
              </div>
              
              <div className="text-center relative z-10">
                <div className="w-12 h-12 mx-auto mb-2 opacity-50">
                  <svg fill="currentColor" viewBox="0 0 24 24" className="w-full h-full text-primary-400">
                    <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
                  </svg>
                </div>
                <p className="text-sm text-dark-400">Scene visualization coming soon</p>
                <p className="text-xs text-dark-500 mt-1">AI-generated images will appear here</p>
              </div>
            </div>
          )}
        </div>
        
        {/* Narrative text */}
        <AnimatedNarrative
          narrative={narrative}
          isStreaming={isStreaming}
        />
        
        {/* Audio player */}
        {(audioUrl || isGeneratingAudio) && (
          <div className="mt-6">
            <AudioPlayer
              audioUrl={getMediaUrl(audioUrl)}
              isLoading={isGeneratingAudio}
              autoPlay={false}
            />
          </div>
        )}
        
        {/* Decorative elements */}
        <div className="absolute top-4 right-4 w-8 h-8 opacity-10">
          <svg fill="currentColor" viewBox="0 0 24 24" className="w-full h-full text-accent-500">
            <path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>
          </svg>
        </div>
      </div>
    </div>
  );
}
