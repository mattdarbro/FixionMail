import { GenerationLog } from './GenerationLog';

interface LoadingStateProps {
  message?: string;
  chapterNumber?: number;
  showDebugLog?: boolean;
}

export function LoadingState({
  message = "The story is weaving...",
  chapterNumber = 1,
  showDebugLog = true // Default to true for development
}: LoadingStateProps) {
  // Show debug log view for development
  if (showDebugLog) {
    return (
      <div className="p-4">
        <GenerationLog
          isGenerating={true}
          currentStage={message}
          chapterNumber={chapterNumber}
        />
      </div>
    );
  }

  // Original loading animation (for production)
  return (
    <div className="flex flex-col items-center justify-center min-h-[400px] p-8">
      {/* Magical loading spinner */}
      <div className="relative mb-6">
        <div className="w-16 h-16 border-4 border-primary-200 border-t-primary-600 rounded-full animate-spin"></div>
        <div className="absolute inset-0 w-16 h-16 border-4 border-transparent border-t-accent-500 rounded-full animate-spin"
             style={{ animationDirection: 'reverse', animationDuration: '1.5s' }}></div>
        <div className="absolute inset-2 w-12 h-12 border-2 border-transparent border-t-secondary-500 rounded-full animate-spin"
             style={{ animationDuration: '2s' }}></div>
      </div>

      {/* Loading message */}
      <div className="text-center">
        <h3 className="text-lg font-fantasy text-primary-300 mb-2">
          {message}
        </h3>
        <p className="text-sm text-dark-400 animate-pulse">
          The ancient magic is at work...
        </p>
      </div>

      {/* Floating particles effect */}
      <div className="absolute inset-0 overflow-hidden pointer-events-none">
        {[...Array(6)].map((_, i) => (
          <div
            key={i}
            className="absolute w-1 h-1 bg-accent-400 rounded-full animate-pulse"
            style={{
              left: `${20 + i * 15}%`,
              top: `${30 + (i % 3) * 20}%`,
              animationDelay: `${i * 0.5}s`,
              animationDuration: '3s',
            }}
          />
        ))}
      </div>
    </div>
  );
}
