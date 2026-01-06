/**
 * Story Settings Page
 *
 * Configure your story preferences: genre, intensity, characters, and more.
 * Designed to be fun and make the customization process engaging.
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

// Genre configuration with icons and descriptions
const GENRES = [
  { id: 'mystery', icon: '🔍', name: 'Mystery', desc: 'Whodunits and puzzles', category: 'recurring' },
  { id: 'romance', icon: '💕', name: 'Romance', desc: 'Love stories', category: 'fresh' },
  { id: 'comedy', icon: '😂', name: 'Comedy', desc: 'Laughs and sitcom vibes', category: 'recurring' },
  { id: 'fantasy', icon: '🧙', name: 'Fantasy', desc: 'Magic and adventure', category: 'fresh' },
  { id: 'scifi', icon: '🚀', name: 'Sci-Fi', desc: 'Future and space', category: 'fresh' },
  { id: 'cozy', icon: '☕', name: 'Cozy', desc: 'Warm and comforting', category: 'fresh' },
  { id: 'western', icon: '🤠', name: 'Western', desc: 'Frontier tales', category: 'fresh' },
  { id: 'action', icon: '💥', name: 'Action', desc: 'Thrills and excitement', category: 'recurring' },
  { id: 'historical', icon: '📜', name: 'Historical', desc: 'Tales from the past', category: 'fresh' },
  { id: 'strange_fables', icon: '🌀', name: 'Strange Fables', desc: 'Twist endings', category: 'fresh' },
];

const INTENSITY_LEVELS = [
  { value: 1, label: 'Cozy', desc: 'Feel-good vibes, no stress', color: 'bg-green-100 text-green-700' },
  { value: 2, label: 'Light', desc: 'Easy reading, gentle tension', color: 'bg-lime-100 text-lime-700' },
  { value: 3, label: 'Moderate', desc: 'Some stakes, balanced drama', color: 'bg-amber-100 text-amber-700' },
  { value: 4, label: 'Dramatic', desc: 'Real consequences, tension', color: 'bg-orange-100 text-orange-700' },
  { value: 5, label: 'Intense', desc: 'Dark themes, high stakes', color: 'bg-red-100 text-red-700' },
];

const STORY_LENGTHS = [
  { value: 'short', label: 'Quick Read', desc: '~1,500 words (5 min)', icon: '⚡' },
  { value: 'medium', label: 'Standard', desc: '~3,000 words (12 min)', icon: '📖' },
];

const VOICES = [
  { value: 'nova', label: 'Nova', desc: 'Female, warm' },
  { value: 'alloy', label: 'Alloy', desc: 'Neutral, clear' },
  { value: 'echo', label: 'Echo', desc: 'Male, smooth' },
  { value: 'fable', label: 'Fable', desc: 'Expressive, dynamic' },
  { value: 'onyx', label: 'Onyx', desc: 'Male, deep' },
  { value: 'shimmer', label: 'Shimmer', desc: 'Female, light' },
];

// Undercurrent (Deeper Meanings) modes
const UNDERCURRENT_MODES = [
  {
    id: 'off',
    name: 'Just Fun Fiction',
    icon: '🎉',
    desc: 'Pure entertainment - engaging stories without deeper themes',
  },
  {
    id: 'surprise',
    name: 'Surprise Me',
    icon: '✨',
    desc: 'AI selects resonant themes that fit each story naturally',
  },
  {
    id: 'custom',
    name: 'Custom Theme',
    icon: '🎯',
    desc: 'You define the deeper meaning woven into your stories',
  },
];

interface Character {
  name: string;
  description: string;
}

interface CameoCharacter {
  name: string;
  description: string;
  frequency: 'rarely' | 'sometimes' | 'often';
}

const CAMEO_FREQUENCIES = [
  { value: 'rarely', label: 'Rarely', desc: '~15% of stories', icon: '🌟' },
  { value: 'sometimes', label: 'Sometimes', desc: '~30% of stories', icon: '✨' },
  { value: 'often', label: 'Often', desc: '~60% of stories', icon: '🌠' },
] as const;

export function StorySettingsPage() {
  const { user, session, refreshUser } = useAuth();
  const navigate = useNavigate();

  // Form state
  const [selectedGenre, setSelectedGenre] = useState<string>('mystery');
  const [intensity, setIntensity] = useState(3);
  const [storyLength, setStoryLength] = useState('short');
  const [deliveryTime, setDeliveryTime] = useState('08:00');
  const [voiceId, setVoiceId] = useState('nova');
  const [setting, setSetting] = useState('');
  const [characters, setCharacters] = useState<Character[]>([]);
  const [newCharName, setNewCharName] = useState('');
  const [newCharDesc, setNewCharDesc] = useState('');

  // Cameo characters
  const [cameoCharacters, setCameoCharacters] = useState<CameoCharacter[]>([]);
  const [newCameoName, setNewCameoName] = useState('');
  const [newCameoDesc, setNewCameoDesc] = useState('');
  const [newCameoFreq, setNewCameoFreq] = useState<'rarely' | 'sometimes' | 'often'>('sometimes');

  // Story themes
  const [undercurrentMode, setUndercurrentMode] = useState('off');
  const [undercurrentCustom, setUndercurrentCustom] = useState('');

  // UI state
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [activeSection, setActiveSection] = useState<'genre' | 'story' | 'delivery'>('genre');

  // Generate story now state
  const [isGenerating, setIsGenerating] = useState(false);
  const [generateMessage, setGenerateMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  // Load user preferences
  useEffect(() => {
    if (user) {
      setSelectedGenre(user.current_genre || 'mystery');
      if (user.preferences) {
        setDeliveryTime(user.preferences.delivery_time || '08:00');
        setStoryLength(user.preferences.story_length || 'short');
        setVoiceId(user.preferences.voice_id || 'nova');
      }
      if (user.story_bible) {
        setIntensity(user.story_bible.intensity || 3);
        setSetting(user.story_bible.setting?.description || '');
        if (user.story_bible.main_characters) {
          setCharacters(user.story_bible.main_characters);
        }
        // Load theme settings
        if (user.story_bible.story_settings) {
          setUndercurrentMode(user.story_bible.story_settings.undercurrent_mode || 'off');
          setUndercurrentCustom(user.story_bible.story_settings.undercurrent_custom || '');
        }
        // Load cameo characters
        if (user.story_bible.cameo_characters) {
          setCameoCharacters(user.story_bible.cameo_characters as CameoCharacter[]);
        }
      }
    }
  }, [user]);

  const addCharacter = () => {
    if (!newCharName.trim()) return;
    if (characters.length >= 2) {
      setSaveMessage({ type: 'error', text: 'Maximum 2 main characters allowed' });
      return;
    }
    setCharacters([...characters, { name: newCharName, description: newCharDesc }]);
    setNewCharName('');
    setNewCharDesc('');
  };

  const removeCharacter = (index: number) => {
    setCharacters(characters.filter((_, i) => i !== index));
  };

  const addCameo = () => {
    if (!newCameoName.trim()) return;
    if (cameoCharacters.length >= 5) {
      setSaveMessage({ type: 'error', text: 'Maximum 5 cameo characters allowed' });
      return;
    }
    setCameoCharacters([...cameoCharacters, {
      name: newCameoName,
      description: newCameoDesc,
      frequency: newCameoFreq
    }]);
    setNewCameoName('');
    setNewCameoDesc('');
    setNewCameoFreq('sometimes');
  };

  const removeCameo = (index: number) => {
    setCameoCharacters(cameoCharacters.filter((_, i) => i !== index));
  };

  const updateCameoFrequency = (index: number, frequency: 'rarely' | 'sometimes' | 'often') => {
    setCameoCharacters(cameoCharacters.map((cameo, i) =>
      i === index ? { ...cameo, frequency } : cameo
    ));
  };

  const handleSave = async () => {
    if (!session?.access_token) return;

    setIsSaving(true);
    setSaveMessage(null);

    try {
      // Update genre
      await fetch('/api/users/genre', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ genre: selectedGenre }),
      });

      // Update preferences
      await fetch('/api/users/preferences', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          story_length: storyLength,
          delivery_time: deliveryTime,
          voice_id: voiceId,
        }),
      });

      // Update story bible
      // Note: beat_structure is "auto" - the backend automatically rotates
      // between different story structures for variety
      const storyBible = {
        genre: selectedGenre,
        intensity,
        setting: { description: setting, name: setting.slice(0, 50) },
        main_characters: characters,
        cameo_characters: cameoCharacters.map(c => ({
          name: c.name,
          description: c.description,
          frequency: c.frequency,
          appearances: 0,
        })),
        beat_structure: 'auto',
        story_settings: {
          intensity_label: INTENSITY_LEVELS.find(l => l.value === intensity)?.label,
          story_length: storyLength,
          beat_structure: 'auto',
          undercurrent_mode: undercurrentMode,
          undercurrent_custom: undercurrentMode === 'custom' ? undercurrentCustom : null,
          undercurrent_match_intensity: true,
        },
      };

      await fetch('/api/users/story-bible', {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ story_bible: storyBible }),
      });

      // Refresh user data
      if (refreshUser) {
        await refreshUser();
      }

      setSaveMessage({ type: 'success', text: 'Settings saved! Your stories will reflect these changes.' });
    } catch (error) {
      console.error('Failed to save settings:', error);
      setSaveMessage({ type: 'error', text: 'Failed to save settings. Please try again.' });
    } finally {
      setIsSaving(false);
    }
  };

  const handleGenerateNow = async () => {
    if (!session?.access_token) return;

    setIsGenerating(true);
    setGenerateMessage(null);

    try {
      const response = await fetch('/api/stories/generate', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          genre: selectedGenre,
          intensity: intensity,
        }),
      });

      if (!response.ok) {
        const error = await response.json();
        throw new Error(error.detail || 'Failed to generate story');
      }

      const result = await response.json();
      setGenerateMessage({
        type: 'success',
        text: `Story generation started! Check your email shortly. (Job ID: ${result.job_id.slice(0, 8)}...)`,
      });
    } catch (error) {
      console.error('Failed to generate story:', error);
      setGenerateMessage({
        type: 'error',
        text: error instanceof Error ? error.message : 'Failed to generate story. Please try again.',
      });
    } finally {
      setIsGenerating(false);
    }
  };

  const selectedGenreInfo = GENRES.find(g => g.id === selectedGenre);
  const isRecurringGenre = selectedGenreInfo?.category === 'recurring';

  return (
    <div className="min-h-screen bg-gradient-to-b from-amber-50 to-stone-100">
      {/* Header */}
      <header className="bg-white/80 backdrop-blur-sm border-b border-amber-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <button
                onClick={() => navigate('/dashboard')}
                className="p-2 hover:bg-amber-100 rounded-lg transition-colors"
              >
                <svg className="w-5 h-5 text-stone-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
                </svg>
              </button>
              <div>
                <h1 className="text-xl font-bold text-amber-800">Story Settings</h1>
                <p className="text-xs text-stone-500">Customize your reading experience</p>
              </div>
            </div>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-5 py-2 bg-amber-600 text-white rounded-lg font-semibold hover:bg-amber-700 transition-colors disabled:bg-stone-300"
            >
              {isSaving ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8">
        {/* Save Message */}
        {saveMessage && (
          <div className={`mb-6 p-4 rounded-xl ${
            saveMessage.type === 'success' ? 'bg-green-50 text-green-700 border border-green-200' : 'bg-red-50 text-red-700 border border-red-200'
          }`}>
            {saveMessage.text}
          </div>
        )}

        {/* Section Tabs */}
        <div className="flex gap-2 mb-6">
          {[
            { id: 'genre', label: 'Genre & Style', icon: '🎭' },
            { id: 'story', label: 'Story Details', icon: '📖' },
            { id: 'delivery', label: 'Delivery', icon: '📬' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveSection(tab.id as any)}
              className={`flex-1 px-4 py-3 rounded-xl font-medium transition-all ${
                activeSection === tab.id
                  ? 'bg-amber-600 text-white shadow-lg'
                  : 'bg-white text-stone-600 hover:bg-amber-50'
              }`}
            >
              <span className="mr-2">{tab.icon}</span>
              {tab.label}
            </button>
          ))}
        </div>

        {/* Genre & Style Section */}
        {activeSection === 'genre' && (
          <div className="space-y-6">
            {/* Genre Selection */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-4">Choose Your Genre</h2>
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {GENRES.map((genre) => (
                  <button
                    key={genre.id}
                    onClick={() => setSelectedGenre(genre.id)}
                    className={`p-4 rounded-xl text-center transition-all ${
                      selectedGenre === genre.id
                        ? 'bg-amber-600 text-white shadow-lg scale-105'
                        : 'bg-stone-50 hover:bg-amber-50 text-stone-700'
                    }`}
                  >
                    <div className="text-3xl mb-2">{genre.icon}</div>
                    <div className="font-medium text-sm">{genre.name}</div>
                    <div className={`text-xs mt-1 ${selectedGenre === genre.id ? 'text-amber-100' : 'text-stone-400'}`}>
                      {genre.desc}
                    </div>
                  </button>
                ))}
              </div>
              <p className="mt-4 text-sm text-stone-500 text-center">
                {isRecurringGenre
                  ? '🔄 This genre uses recurring characters across stories'
                  : '✨ Each story features fresh characters'
                }
              </p>
            </div>

            {/* Intensity Slider */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-4">Story Intensity</h2>
              <div className="space-y-4">
                <input
                  type="range"
                  min="1"
                  max="5"
                  value={intensity}
                  onChange={(e) => setIntensity(parseInt(e.target.value))}
                  className="w-full h-3 rounded-full appearance-none bg-gradient-to-r from-green-200 via-amber-200 to-red-200 cursor-pointer"
                />
                <div className="flex justify-between text-xs text-stone-400">
                  {INTENSITY_LEVELS.map((level) => (
                    <span key={level.value} className={intensity === level.value ? 'font-bold text-amber-600' : ''}>
                      {level.label}
                    </span>
                  ))}
                </div>
                <div className={`text-center py-3 rounded-xl ${INTENSITY_LEVELS[intensity - 1].color}`}>
                  <span className="font-semibold">{INTENSITY_LEVELS[intensity - 1].label}</span>
                  <span className="mx-2">—</span>
                  <span>{INTENSITY_LEVELS[intensity - 1].desc}</span>
                </div>
              </div>
            </div>

            {/* Deeper Meanings (Undercurrent) */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-2">Deeper Meanings</h2>
              <p className="text-sm text-stone-500 mb-4">Add thematic depth to your stories</p>
              <div className="space-y-3">
                {UNDERCURRENT_MODES.map((mode) => (
                  <button
                    key={mode.id}
                    onClick={() => setUndercurrentMode(mode.id)}
                    className={`w-full p-4 rounded-xl text-left transition-all ${
                      undercurrentMode === mode.id
                        ? 'bg-amber-600 text-white shadow-lg ring-2 ring-amber-400'
                        : 'bg-stone-50 hover:bg-amber-50 text-stone-700'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <span className="text-2xl">{mode.icon}</span>
                      <div className="flex-1">
                        <div className="font-semibold">{mode.name}</div>
                        <div className={`text-sm ${undercurrentMode === mode.id ? 'text-amber-100' : 'text-stone-500'}`}>
                          {mode.desc}
                        </div>
                      </div>
                      {undercurrentMode === mode.id && (
                        <svg className="w-5 h-5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clipRule="evenodd" />
                        </svg>
                      )}
                    </div>
                  </button>
                ))}

                {/* Custom theme input */}
                {undercurrentMode === 'custom' && (
                  <div className="mt-4 p-4 bg-amber-50 rounded-xl border border-amber-200">
                    <label className="block text-sm font-medium text-stone-700 mb-2">
                      Your Custom Theme
                    </label>
                    <textarea
                      value={undercurrentCustom}
                      onChange={(e) => setUndercurrentCustom(e.target.value)}
                      placeholder="Describe the deeper meaning you want woven into your stories... (e.g., 'The importance of forgiveness' or 'Finding courage in unexpected places')"
                      className="w-full px-4 py-3 border border-stone-300 rounded-xl bg-white text-stone-800 placeholder:text-stone-400 focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none"
                      rows={3}
                    />
                    <p className="mt-2 text-xs text-stone-500">
                      This theme will be subtly woven throughout your stories without being heavy-handed.
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* Story Details Section */}
        {activeSection === 'story' && (
          <div className="space-y-6">
            {/* Setting */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-4">Story World</h2>
              <textarea
                value={setting}
                onChange={(e) => setSetting(e.target.value)}
                placeholder="Describe your story world in 1-2 sentences... (e.g., 'A small coastal town in Maine where everyone knows everyone's secrets')"
                className="w-full px-4 py-3 border border-stone-300 rounded-xl bg-white text-stone-800 placeholder:text-stone-400 focus:ring-2 focus:ring-amber-500 focus:border-transparent resize-none"
                rows={3}
              />
            </div>

            {/* Characters (for recurring genres) */}
            {isRecurringGenre && (
              <div className="bg-white rounded-2xl shadow-lg p-6">
                <h2 className="text-xl font-bold text-stone-800 mb-2">Main Characters</h2>
                <p className="text-sm text-stone-500 mb-4">These characters will appear in every story (max 2)</p>

                {/* Existing characters */}
                <div className="space-y-2 mb-4">
                  {characters.map((char, idx) => (
                    <div key={idx} className="flex items-center justify-between p-3 bg-amber-50 rounded-lg">
                      <div>
                        <span className="font-medium text-stone-800">{char.name}</span>
                        {char.description && (
                          <span className="text-stone-500 ml-2">— {char.description}</span>
                        )}
                      </div>
                      <button
                        onClick={() => removeCharacter(idx)}
                        className="text-red-500 hover:text-red-700 text-xl"
                      >
                        ×
                      </button>
                    </div>
                  ))}
                </div>

                {/* Add character form */}
                {characters.length < 2 && (
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newCharName}
                      onChange={(e) => setNewCharName(e.target.value)}
                      placeholder="Name"
                      className="w-1/3 px-3 py-2 border border-stone-300 rounded-lg bg-white text-stone-800 placeholder:text-stone-400"
                    />
                    <input
                      type="text"
                      value={newCharDesc}
                      onChange={(e) => setNewCharDesc(e.target.value)}
                      placeholder="Brief description"
                      className="flex-1 px-3 py-2 border border-stone-300 rounded-lg bg-white text-stone-800 placeholder:text-stone-400"
                    />
                    <button
                      onClick={addCharacter}
                      className="px-4 py-2 bg-amber-600 text-white rounded-lg hover:bg-amber-700"
                    >
                      Add
                    </button>
                  </div>
                )}
              </div>
            )}

            {/* Cameo Characters */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-2">Cameo Characters</h2>
              <p className="text-sm text-stone-500 mb-4">
                Add yourself, friends, or anyone you'd like to occasionally appear in your stories (max 5)
              </p>

              {/* Existing cameos */}
              <div className="space-y-3 mb-4">
                {cameoCharacters.map((cameo, idx) => (
                  <div key={idx} className="p-4 bg-purple-50 rounded-xl border border-purple-100">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <span className="font-semibold text-stone-800">{cameo.name}</span>
                        {cameo.description && (
                          <p className="text-sm text-stone-500 mt-1">{cameo.description}</p>
                        )}
                      </div>
                      <button
                        onClick={() => removeCameo(idx)}
                        className="text-red-400 hover:text-red-600 text-xl ml-2"
                      >
                        ×
                      </button>
                    </div>
                    <div className="flex gap-2 mt-3">
                      {CAMEO_FREQUENCIES.map((freq) => (
                        <button
                          key={freq.value}
                          onClick={() => updateCameoFrequency(idx, freq.value)}
                          className={`flex-1 px-2 py-1.5 rounded-lg text-xs font-medium transition-all ${
                            cameo.frequency === freq.value
                              ? 'bg-purple-600 text-white'
                              : 'bg-white text-stone-600 hover:bg-purple-100 border border-stone-200'
                          }`}
                        >
                          <span className="mr-1">{freq.icon}</span>
                          {freq.label}
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Add cameo form */}
              {cameoCharacters.length < 5 && (
                <div className="space-y-3 p-4 bg-stone-50 rounded-xl">
                  <div className="flex gap-2">
                    <input
                      type="text"
                      value={newCameoName}
                      onChange={(e) => setNewCameoName(e.target.value)}
                      placeholder="Name (e.g., 'Mom', 'Best Friend Jake')"
                      className="flex-1 px-3 py-2 border border-stone-300 rounded-lg bg-white text-stone-800 placeholder:text-stone-400"
                    />
                  </div>
                  <input
                    type="text"
                    value={newCameoDesc}
                    onChange={(e) => setNewCameoDesc(e.target.value)}
                    placeholder="Brief description (e.g., 'Loves gardening and always has good advice')"
                    className="w-full px-3 py-2 border border-stone-300 rounded-lg bg-white text-stone-800 placeholder:text-stone-400"
                  />
                  <div className="flex gap-2 items-center">
                    <span className="text-sm text-stone-500">Appears:</span>
                    {CAMEO_FREQUENCIES.map((freq) => (
                      <button
                        key={freq.value}
                        onClick={() => setNewCameoFreq(freq.value)}
                        className={`px-3 py-1.5 rounded-lg text-sm font-medium transition-all ${
                          newCameoFreq === freq.value
                            ? 'bg-purple-600 text-white'
                            : 'bg-white text-stone-600 hover:bg-purple-100 border border-stone-200'
                        }`}
                      >
                        {freq.icon} {freq.label}
                      </button>
                    ))}
                    <button
                      onClick={addCameo}
                      disabled={!newCameoName.trim()}
                      className="ml-auto px-4 py-1.5 bg-purple-600 text-white rounded-lg hover:bg-purple-700 disabled:bg-stone-300 disabled:cursor-not-allowed font-medium"
                    >
                      Add Cameo
                    </button>
                  </div>
                </div>
              )}

              {cameoCharacters.length === 0 && (
                <p className="text-center text-stone-400 text-sm py-2">
                  No cameos yet. Add someone special to occasionally appear in your stories!
                </p>
              )}
            </div>

            {/* Story Length */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-4">Story Length</h2>
              <div className="grid grid-cols-2 gap-4">
                {STORY_LENGTHS.map((length) => (
                  <button
                    key={length.value}
                    onClick={() => setStoryLength(length.value)}
                    className={`p-4 rounded-xl text-left transition-all ${
                      storyLength === length.value
                        ? 'bg-amber-600 text-white shadow-lg'
                        : 'bg-stone-50 hover:bg-amber-50 text-stone-700'
                    }`}
                  >
                    <span className="text-2xl mr-2">{length.icon}</span>
                    <span className="font-medium">{length.label}</span>
                    <div className={`text-sm mt-1 ${storyLength === length.value ? 'text-amber-100' : 'text-stone-400'}`}>
                      {length.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Delivery Section */}
        {activeSection === 'delivery' && (
          <div className="space-y-6">
            {/* Delivery Time */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-4">Delivery Time</h2>
              <p className="text-sm text-stone-500 mb-4">When should your daily story arrive?</p>
              <div className="flex items-center gap-4">
                <input
                  type="time"
                  value={deliveryTime}
                  onChange={(e) => setDeliveryTime(e.target.value)}
                  className="px-4 py-3 border border-stone-300 rounded-xl bg-white text-stone-800 text-lg font-medium focus:ring-2 focus:ring-amber-500 focus:border-transparent"
                />
                <span className="text-stone-500">Your local time</span>
              </div>
            </div>

            {/* Narrator Voice */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-4">Narrator Voice</h2>
              <p className="text-sm text-stone-500 mb-4">Choose a voice for audio narration</p>
              <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
                {VOICES.map((voice) => (
                  <button
                    key={voice.value}
                    onClick={() => setVoiceId(voice.value)}
                    className={`p-4 rounded-xl text-left transition-all ${
                      voiceId === voice.value
                        ? 'bg-amber-600 text-white shadow-lg'
                        : 'bg-stone-50 hover:bg-amber-50 text-stone-700'
                    }`}
                  >
                    <div className="font-medium">{voice.label}</div>
                    <div className={`text-sm ${voiceId === voice.value ? 'text-amber-100' : 'text-stone-400'}`}>
                      {voice.desc}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Generate Story Now */}
            <div className="bg-white rounded-2xl shadow-lg p-6">
              <h2 className="text-xl font-bold text-stone-800 mb-2">Generate Story Now</h2>
              <p className="text-sm text-stone-500 mb-4">
                Can't wait for your next scheduled story? Generate one immediately!
              </p>

              {generateMessage && (
                <div className={`mb-4 p-3 rounded-lg text-sm ${
                  generateMessage.type === 'success'
                    ? 'bg-green-50 text-green-700 border border-green-200'
                    : 'bg-red-50 text-red-700 border border-red-200'
                }`}>
                  {generateMessage.text}
                </div>
              )}

              <div className="flex items-center gap-4">
                <button
                  onClick={handleGenerateNow}
                  disabled={isGenerating}
                  className="px-6 py-3 bg-gradient-to-r from-amber-500 to-orange-500 text-white rounded-xl font-semibold hover:from-amber-600 hover:to-orange-600 transition-all disabled:from-stone-300 disabled:to-stone-400 shadow-lg hover:shadow-xl disabled:shadow-none"
                >
                  {isGenerating ? (
                    <span className="flex items-center gap-2">
                      <svg className="animate-spin h-5 w-5" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                      </svg>
                      Generating...
                    </span>
                  ) : (
                    'Generate Story Now'
                  )}
                </button>
                <span className="text-sm text-stone-400">Uses 1 credit</span>
              </div>

              <p className="mt-4 text-xs text-stone-400">
                Your story will be generated with your current settings and delivered to your email.
              </p>
            </div>
          </div>
        )}

        {/* Bottom Save Button */}
        <div className="mt-8 text-center">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className="px-8 py-3 bg-amber-600 text-white rounded-xl font-semibold hover:bg-amber-700 transition-colors disabled:bg-stone-300 shadow-lg"
          >
            {isSaving ? 'Saving...' : 'Save All Changes'}
          </button>
        </div>
      </main>
    </div>
  );
}
