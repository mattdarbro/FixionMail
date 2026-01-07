/**
 * Genre Selection Card
 *
 * A clickable card for selecting a story genre during onboarding.
 */

interface GenreCardProps {
  id: string;
  name: string;
  description: string;
  icon: string;
  selected?: boolean;
  onClick: (id: string) => void;
}

export function GenreCard({
  id,
  name,
  description,
  icon,
  selected = false,
  onClick,
}: GenreCardProps) {
  return (
    <button
      onClick={() => onClick(id)}
      className={`
        w-full p-4 rounded-xl text-left transition-all duration-200
        border-2 hover:scale-[1.02]
        ${selected
          ? 'border-amber-500 bg-amber-50 shadow-lg shadow-amber-500/20'
          : 'border-stone-200 bg-white hover:border-amber-300 hover:bg-amber-50/50'
        }
      `}
    >
      <div className="flex items-start gap-3">
        <span className="text-3xl" role="img" aria-label={name}>
          {icon}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className={`font-semibold text-lg ${selected ? 'text-amber-700' : 'text-stone-800'}`}>
            {name}
          </h3>
          <p className="text-sm text-stone-600 mt-1 leading-relaxed">
            {description}
          </p>
        </div>
        {selected && (
          <div className="flex-shrink-0">
            <div className="w-6 h-6 bg-amber-500 rounded-full flex items-center justify-center">
              <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
            </div>
          </div>
        )}
      </div>
    </button>
  );
}

// Genre data for the selection screen - matches StorySettings.tsx
export const GENRES = [
  {
    id: 'mystery',
    name: 'Mystery',
    description: 'Whodunits, detective stories, and puzzles to solve. Recurring characters.',
    icon: '🔍',
    category: 'recurring',
  },
  {
    id: 'romance',
    name: 'Romance',
    description: 'Love stories, meet-cutes, and happily ever afters. Fresh characters each story.',
    icon: '💕',
    category: 'fresh',
  },
  {
    id: 'comedy',
    name: 'Comedy',
    description: 'Laughs, sitcom vibes, and feel-good humor. Recurring characters.',
    icon: '😂',
    category: 'recurring',
  },
  {
    id: 'fantasy',
    name: 'Fantasy',
    description: 'Magic, mythical creatures, and epic quests. Fresh characters each story.',
    icon: '🧙',
    category: 'fresh',
  },
  {
    id: 'scifi',
    name: 'Sci-Fi',
    description: 'Future worlds, space adventures, and technology dreams. Fresh characters each story.',
    icon: '🚀',
    category: 'fresh',
  },
  {
    id: 'cozy',
    name: 'Cozy',
    description: 'Warm, comforting tales perfect for relaxing. Fresh characters each story.',
    icon: '☕',
    category: 'fresh',
  },
  {
    id: 'western',
    name: 'Western',
    description: 'Frontier tales, cowboys, and the wild west. Fresh characters each story.',
    icon: '🤠',
    category: 'fresh',
  },
  {
    id: 'action',
    name: 'Action',
    description: 'Thrills, excitement, and high-stakes adventure. Recurring characters.',
    icon: '💥',
    category: 'recurring',
  },
  {
    id: 'historical',
    name: 'Historical',
    description: 'Tales from the past, bringing history to life. Fresh characters each story.',
    icon: '📜',
    category: 'fresh',
  },
  {
    id: 'strange_fables',
    name: 'Strange Fables',
    description: 'Twist endings and unexpected turns. Fresh characters each story.',
    icon: '🌀',
    category: 'fresh',
  },
];

interface GenreGridProps {
  selectedGenre?: string;
  onSelect: (genreId: string) => void;
}

export function GenreGrid({ selectedGenre, onSelect }: GenreGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {GENRES.map((genre) => (
        <GenreCard
          key={genre.id}
          {...genre}
          selected={selectedGenre === genre.id}
          onClick={onSelect}
        />
      ))}
    </div>
  );
}
