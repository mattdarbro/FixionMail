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

// Genre data for the selection screen
export const GENRES = [
  {
    id: 'mystery',
    name: 'Mystery',
    description: 'Whodunits, detective stories, and puzzles to solve. Perfect for analytical minds.',
    icon: '🔍',
  },
  {
    id: 'romance',
    name: 'Romance',
    description: 'Love stories, meet-cutes, and happily ever afters. Heart-warming tales.',
    icon: '💕',
  },
  {
    id: 'thriller',
    name: 'Thriller',
    description: 'Edge-of-your-seat suspense, danger, and high stakes. Not for the faint of heart.',
    icon: '😰',
  },
  {
    id: 'scifi',
    name: 'Science Fiction',
    description: 'Future worlds, space adventures, and technology dreams. Boldly go where no story has gone.',
    icon: '🚀',
  },
  {
    id: 'fantasy',
    name: 'Fantasy',
    description: 'Magic, mythical creatures, and epic quests. Escape to extraordinary realms.',
    icon: '🐉',
  },
  {
    id: 'horror',
    name: 'Horror',
    description: 'Chills, thrills, and things that go bump in the night. Sleep with the lights on.',
    icon: '👻',
  },
  {
    id: 'literary',
    name: 'Literary Fiction',
    description: 'Character-driven stories with depth and meaning. For the thoughtful reader.',
    icon: '📚',
  },
  {
    id: 'adventure',
    name: 'Adventure',
    description: 'Action-packed journeys, treasure hunts, and daring exploits. Fortune favors the bold.',
    icon: '⚔️',
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
