import { useState, useEffect, useRef, useMemo } from 'react';

interface AnimatedNarrativeProps {
  narrative: string;
  isStreaming?: boolean;
  className?: string;
}

export function AnimatedNarrative({
  narrative,
  isStreaming = false,
  className = ''
}: AnimatedNarrativeProps) {
  const [displayedWords, setDisplayedWords] = useState<string[]>([]);
  const [isSkipped, setIsSkipped] = useState(false);
  const previousNarrativeRef = useRef('');
  const wordsLengthRef = useRef(0);

  // Split narrative into words (memoized to prevent unnecessary recalculation)
  const words = useMemo(() => {
    return narrative.trim().split(/\s+/).filter(word => word.length > 0);
  }, [narrative]);

  useEffect(() => {
    // Detect if this is a completely new narrative (new beat/story)
    const isNewNarrative = previousNarrativeRef.current.length > 0 &&
                          !narrative.startsWith(previousNarrativeRef.current);

    if (isNewNarrative) {
      // Reset for new narrative
      setDisplayedWords([]);
      setIsSkipped(false);
      wordsLengthRef.current = 0;
    }

    // Update displayed words based on streaming state
    if (isStreaming && !isSkipped) {
      // Streaming: show words progressively
      if (words.length > wordsLengthRef.current) {
        setDisplayedWords(words);
        wordsLengthRef.current = words.length;
      }
    } else {
      // Not streaming or skipped: show all words immediately
      setDisplayedWords(words);
      wordsLengthRef.current = words.length;
    }

    previousNarrativeRef.current = narrative;
  }, [narrative, words, isStreaming, isSkipped]);

  const handleSkip = () => {
    setIsSkipped(true);
    setDisplayedWords(words);
    wordsLengthRef.current = words.length;
  };

  // Show skip button only during active streaming
  const showSkipButton = isStreaming && !isSkipped;

  return (
    <div className={`relative ${className}`}>
      <div className="prose prose-invert max-w-none">
        <p className="text-lg leading-relaxed text-dark-100 font-sans mb-0">
          {displayedWords.map((word, index) => (
            <span
              key={`${index}-${word}`}
              className="inline-block word-fade-in mr-[0.25em]"
              style={{
                // No delay if skipped, otherwise stagger by 50ms per word
                animationDelay: isSkipped ? '0ms' : `${index * 50}ms`
              }}
            >
              {word}
            </span>
          ))}
        </p>
      </div>

      {/* Skip button - subtle, at bottom */}
      {showSkipButton && (
        <div className="mt-6 flex justify-center">
          <button
            onClick={handleSkip}
            className="text-xs text-dark-500 hover:text-dark-300 transition-colors duration-200 opacity-40 hover:opacity-100 px-3 py-1.5 rounded border border-dark-600 hover:border-dark-500"
            aria-label="Skip animation"
          >
            Skip
          </button>
        </div>
      )}
    </div>
  );
}
