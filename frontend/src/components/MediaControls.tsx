import { useState } from 'react';

interface MediaControlsProps {
  onAudioToggle: (enabled: boolean) => void;
  onImageToggle: (enabled: boolean) => void;
  onVoiceChange: (voiceId: string) => void;
  audioEnabled: boolean;
  imageEnabled: boolean;
  selectedVoice: string;
}

export function MediaControls({
  onAudioToggle,
  onImageToggle,
  onVoiceChange,
  audioEnabled,
  imageEnabled,
  selectedVoice
}: MediaControlsProps) {
  // ElevenLabs voice options
  const voices = [
    { id: '21m00Tcm4TlvDq8ikWAM', name: 'Rachel (Default)' },
    { id: 'AZnzlk1XvdvUeBnXmlld', name: 'Domi' },
    { id: 'EXAVITQu4vr4xnSDxMaL', name: 'Bella' },
    { id: 'ErXwobaYiN019PkySvjV', name: 'Antoni' },
    { id: 'MF3mGyEYCl7XYWbV9V6O', name: 'Elli' },
    { id: 'TxGEqnHWrfWFTfGW9XjX', name: 'Josh' },
    { id: 'VR6AewLTigWG4xSOukaG', name: 'Arnold' },
    { id: 'pNInz6obpgDQGcFmaJgB', name: 'Adam' },
    { id: 'yoZ06aMxZJJ28mfd3POQ', name: 'Sam' },
  ];

  return (
    <div className="bg-dark-800/80 backdrop-blur-sm border border-primary-500/20 rounded-lg p-6 space-y-4">
      <h3 className="text-lg font-semibold text-primary-300 mb-4">Media Settings (Dev Mode)</h3>

      {/* Audio Toggle */}
      <label className="flex items-center gap-3 cursor-pointer group">
        <input
          type="checkbox"
          checked={audioEnabled}
          onChange={(e) => onAudioToggle(e.target.checked)}
          className="w-5 h-5 rounded border-2 border-primary-500/40 bg-dark-700 checked:bg-primary-600 checked:border-primary-600 focus:ring-2 focus:ring-primary-500/50 transition-all cursor-pointer"
        />
        <span className="text-dark-200 group-hover:text-dark-100 transition-colors">
          Generate Audio
          <span className="text-sm text-dark-400 ml-2">(saves ElevenLabs credits when off)</span>
        </span>
      </label>

      {/* Voice Selection - only show when audio is enabled */}
      {audioEnabled && (
        <div className="ml-8 space-y-2">
          <label className="block text-sm text-dark-300">
            Voice:
          </label>
          <select
            value={selectedVoice}
            onChange={(e) => onVoiceChange(e.target.value)}
            className="w-full max-w-xs px-4 py-2 bg-dark-700 border border-primary-500/30 rounded-lg text-dark-100 focus:border-primary-500 focus:ring-2 focus:ring-primary-500/50 outline-none transition-all"
          >
            {voices.map(voice => (
              <option key={voice.id} value={voice.id}>
                {voice.name}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Image Toggle */}
      <label className="flex items-center gap-3 cursor-pointer group">
        <input
          type="checkbox"
          checked={imageEnabled}
          onChange={(e) => onImageToggle(e.target.checked)}
          className="w-5 h-5 rounded border-2 border-primary-500/40 bg-dark-700 checked:bg-primary-600 checked:border-primary-600 focus:ring-2 focus:ring-primary-500/50 transition-all cursor-pointer"
        />
        <span className="text-dark-200 group-hover:text-dark-100 transition-colors">
          Generate Images
          <span className="text-sm text-dark-400 ml-2">(saves Replicate credits when off)</span>
        </span>
      </label>
    </div>
  );
}
