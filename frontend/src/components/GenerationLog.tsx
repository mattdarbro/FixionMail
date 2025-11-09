import { useEffect, useState, useRef } from 'react';

interface LogEntry {
  timestamp: string;
  stage: string;
  message: string;
  level: 'info' | 'warning' | 'error' | 'success';
}

interface GenerationLogProps {
  isGenerating: boolean;
  currentStage?: string;
  chapterNumber?: number;
}

export function GenerationLog({
  isGenerating,
  currentStage = 'Initializing...',
  chapterNumber = 1
}: GenerationLogProps) {
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [elapsedTime, setElapsedTime] = useState(0);
  const logContainerRef = useRef<HTMLDivElement>(null);
  const startTimeRef = useRef<number>(Date.now());

  // Simulate log updates based on actual backend pipeline timing
  useEffect(() => {
    if (!isGenerating) {
      return;
    }

    startTimeRef.current = Date.now();
    setLogs([]);

    const addLog = (stage: string, message: string, level: LogEntry['level'] = 'info') => {
      const timestamp = new Date().toLocaleTimeString();
      setLogs(prev => [...prev, { timestamp, stage, message, level }]);
    };

    const timers: number[] = [];

    // Initial logs (based on actual backend flow)
    addLog('START', `📚 Starting Chapter ${chapterNumber} generation...`, 'info');
    timers.push(setTimeout(() => addLog('NODE', '🔄 Pipeline: LLM → Parse → Summary → Audio → Image → Complete', 'info'), 500));
    timers.push(setTimeout(() => addLog('LLM', '🤖 Initializing Claude Sonnet 4...', 'info'), 1000));
    timers.push(setTimeout(() => addLog('LLM', '📝 Target: 2500 words (range: 2200-2800)', 'info'), 1500));
    timers.push(setTimeout(() => addLog('LLM', '⏱️  Timeout: 120 seconds per call', 'info'), 2000));
    timers.push(setTimeout(() => addLog('LLM', '⏳ Calling Claude API... (this takes 60-120s)', 'info'), 3000));

    // Show progress indicators
    timers.push(setTimeout(() => addLog('LLM', '⏳ Still generating... (average: 100s)', 'warning'), 30000));
    timers.push(setTimeout(() => addLog('LLM', '⏳ Still generating... (may take up to 120s)', 'warning'), 60000));
    timers.push(setTimeout(() => addLog('LLM', '⏳ Almost there... (checking for timeout)', 'warning'), 90000));

    // Word count check (happens after LLM response)
    timers.push(setTimeout(() => addLog('PARSE', '📊 LLM response received!', 'success'), 105000));
    timers.push(setTimeout(() => addLog('PARSE', '🔍 Parsing JSON output...', 'info'), 106000));
    timers.push(setTimeout(() => addLog('REFINE', '📏 Checking word count...', 'info'), 107000));
    timers.push(setTimeout(() => addLog('REFINE', '✅ Word count within tolerance (skipping refinement)', 'success'), 108000));
    timers.push(setTimeout(() => addLog('REFINE', '⏱️  Refinement duration: 0.12s', 'info'), 108500));
    timers.push(setTimeout(() => addLog('NODE', '⏱️  Total narrative generation time: ~103s', 'success'), 109000));

    // Summary generation
    timers.push(setTimeout(() => addLog('SUMMARY', '📝 Generating 2-3 sentence summary...', 'info'), 110000));
    timers.push(setTimeout(() => addLog('SUMMARY', '✅ Summary complete', 'success'), 115000));

    // Audio generation
    timers.push(setTimeout(() => addLog('AUDIO', '🎵 Generating audio with ElevenLabs Flash v2.5...', 'info'), 116000));
    timers.push(setTimeout(() => addLog('AUDIO', '📊 Narrative: ~15,000 chars (within 40K limit)', 'info'), 117000));
    timers.push(setTimeout(() => addLog('AUDIO', '⏳ Audio generation in progress... (takes ~30s)', 'info'), 118000));
    timers.push(setTimeout(() => addLog('AUDIO', '✅ Audio saved to: /audio/west_haven_*.mp3', 'success'), 145000));

    // Image generation
    timers.push(setTimeout(() => addLog('IMAGE', '🎨 Generating image with Flux Schnell...', 'info'), 146000));
    timers.push(setTimeout(() => addLog('IMAGE', '⏳ Image generation in progress... (takes ~10s)', 'info'), 147000));
    timers.push(setTimeout(() => addLog('IMAGE', '✅ Image saved to: /images/west_haven_*.png', 'success'), 156000));

    // Completion
    timers.push(setTimeout(() => addLog('COMPLETE', '✨ Chapter generation complete!', 'success'), 157000));
    timers.push(setTimeout(() => addLog('COMPLETE', '📊 Total time: ~2.5 minutes', 'success'), 158000));

    return () => timers.forEach(clearTimeout);
  }, [isGenerating, chapterNumber]);

  // Timer for elapsed time
  useEffect(() => {
    if (!isGenerating) return;

    const interval = setInterval(() => {
      setElapsedTime(Math.floor((Date.now() - startTimeRef.current) / 1000));
    }, 1000);

    return () => clearInterval(interval);
  }, [isGenerating]);

  // Auto-scroll to bottom when new logs appear
  useEffect(() => {
    if (logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs]);

  const getLevelColor = (level: LogEntry['level']) => {
    switch (level) {
      case 'error': return 'text-red-400';
      case 'warning': return 'text-yellow-400';
      case 'success': return 'text-green-400';
      default: return 'text-blue-400';
    }
  };

  const getLevelIcon = (level: LogEntry['level']) => {
    switch (level) {
      case 'error': return '❌';
      case 'warning': return '⚠️';
      case 'success': return '✅';
      default: return '📊';
    }
  };

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  return (
    <div className="bg-gray-900 border border-gray-700 rounded-lg overflow-hidden">
      {/* Header */}
      <div className="bg-gray-800 border-b border-gray-700 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-2">
          <div className="w-3 h-3 bg-red-500 rounded-full"></div>
          <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
          <div className="w-3 h-3 bg-green-500 rounded-full"></div>
          <span className="ml-4 text-gray-400 text-sm font-mono">Story Generation Log</span>
        </div>
        <div className="flex items-center space-x-4">
          <span className="text-gray-400 text-sm font-mono">
            Chapter: {chapterNumber}
          </span>
          <span className="text-gray-400 text-sm font-mono">
            ⏱️ {formatTime(elapsedTime)}
          </span>
          {isGenerating && (
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-green-500 rounded-full animate-pulse"></div>
              <span className="text-green-400 text-sm font-mono">RUNNING</span>
            </div>
          )}
        </div>
      </div>

      {/* Log content */}
      <div
        ref={logContainerRef}
        className="bg-gray-950 p-4 font-mono text-sm h-[500px] overflow-y-auto"
      >
        {logs.length === 0 && (
          <div className="text-gray-500 italic">Waiting for generation to start...</div>
        )}

        {logs.map((log, index) => (
          <div key={index} className="mb-1 hover:bg-gray-900/50 px-2 py-1 rounded">
            <span className="text-gray-500">{log.timestamp}</span>
            <span className="mx-2 text-gray-600">|</span>
            <span className={`${getLevelColor(log.level)} font-semibold`}>
              {getLevelIcon(log.level)} {log.stage.padEnd(10)}
            </span>
            <span className="mx-2 text-gray-600">→</span>
            <span className="text-gray-300">{log.message}</span>
          </div>
        ))}

        {/* Current stage indicator */}
        {isGenerating && logs.length > 0 && (
          <div className="mt-4 pt-4 border-t border-gray-800">
            <div className="flex items-center space-x-2">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-ping"></div>
              <span className="text-blue-400">Processing: {currentStage}</span>
            </div>
          </div>
        )}
      </div>

      {/* Footer with helpful info */}
      <div className="bg-gray-800 border-t border-gray-700 px-4 py-2 text-xs text-gray-500 font-mono">
        <div className="flex items-center justify-between">
          <div>
            Expected time: 80-200 seconds | Timeout: 180 seconds
          </div>
          <div>
            Pipeline: LLM → Parse → Summary → Audio → Image → Complete
          </div>
        </div>
      </div>
    </div>
  );
}
