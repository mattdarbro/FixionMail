/**
 * Confirmation Card Component
 *
 * Used during onboarding to confirm user decisions.
 * Each card summarizes a choice and allows the user to confirm or edit.
 */

import { ReactNode } from 'react';

interface ConfirmationCardProps {
  title: string;
  icon?: string;
  confirmed: boolean;
  onConfirm: () => void;
  onEdit: () => void;
  children: ReactNode;
  className?: string;
}

export function ConfirmationCard({
  title,
  icon,
  confirmed,
  onConfirm,
  onEdit,
  children,
  className = '',
}: ConfirmationCardProps) {
  return (
    <div
      className={`
        rounded-xl border-2 overflow-hidden transition-all duration-200
        ${confirmed
          ? 'border-green-500 bg-green-50'
          : 'border-amber-300 bg-amber-50'
        }
        ${className}
      `}
    >
      {/* Header */}
      <div
        className={`
          px-4 py-3 flex items-center justify-between
          ${confirmed ? 'bg-green-100' : 'bg-amber-100'}
        `}
      >
        <div className="flex items-center gap-2">
          {icon && <span className="text-xl">{icon}</span>}
          <h3 className={`font-semibold ${confirmed ? 'text-green-800' : 'text-amber-800'}`}>
            {title}
          </h3>
        </div>
        {confirmed && (
          <div className="flex items-center gap-1 text-green-600">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
            </svg>
            <span className="text-sm font-medium">Confirmed</span>
          </div>
        )}
      </div>

      {/* Content */}
      <div className="p-4">
        {children}
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 flex gap-3">
        {!confirmed ? (
          <>
            <button
              onClick={onConfirm}
              className="flex-1 px-4 py-2 bg-amber-600 text-white rounded-lg font-medium
                         hover:bg-amber-700 transition-colors"
            >
              Confirm
            </button>
            <button
              onClick={onEdit}
              className="px-4 py-2 border border-stone-300 text-stone-600 rounded-lg
                         hover:bg-stone-50 transition-colors"
            >
              Edit
            </button>
          </>
        ) : (
          <button
            onClick={onEdit}
            className="px-4 py-2 text-stone-500 hover:text-stone-700 text-sm transition-colors"
          >
            Change this
          </button>
        )}
      </div>
    </div>
  );
}

// Detail row for displaying key-value pairs in cards
interface DetailRowProps {
  label: string;
  value: string | string[];
}

export function DetailRow({ label, value }: DetailRowProps) {
  return (
    <div className="flex items-start gap-2 py-1">
      <span className="text-stone-500 text-sm min-w-[100px]">{label}:</span>
      <span className="text-stone-800 text-sm font-medium">
        {Array.isArray(value) ? value.join(', ') : value}
      </span>
    </div>
  );
}

// Genre confirmation card
interface GenreConfirmationProps {
  genre: string;
  genreName: string;
  genreDescription: string;
  confirmed: boolean;
  onConfirm: () => void;
  onEdit: () => void;
}

export function GenreConfirmation({
  genreName,
  genreDescription,
  confirmed,
  onConfirm,
  onEdit,
}: GenreConfirmationProps) {
  return (
    <ConfirmationCard
      title="Your Genre"
      icon="🎭"
      confirmed={confirmed}
      onConfirm={onConfirm}
      onEdit={onEdit}
    >
      <div className="space-y-2">
        <p className="text-lg font-semibold text-stone-800">{genreName}</p>
        <p className="text-sm text-stone-600">{genreDescription}</p>
      </div>
    </ConfirmationCard>
  );
}

// Protagonist confirmation card
interface ProtagonistConfirmationProps {
  protagonist: {
    name?: string;
    age?: string;
    occupation?: string;
    personality?: string[];
  };
  confirmed: boolean;
  onConfirm: () => void;
  onEdit: () => void;
}

export function ProtagonistConfirmation({
  protagonist,
  confirmed,
  onConfirm,
  onEdit,
}: ProtagonistConfirmationProps) {
  return (
    <ConfirmationCard
      title="Your Protagonist"
      icon="👤"
      confirmed={confirmed}
      onConfirm={onConfirm}
      onEdit={onEdit}
    >
      <div className="space-y-1">
        {protagonist.name && <DetailRow label="Name" value={protagonist.name} />}
        {protagonist.age && <DetailRow label="Age" value={protagonist.age} />}
        {protagonist.occupation && <DetailRow label="Occupation" value={protagonist.occupation} />}
        {protagonist.personality && protagonist.personality.length > 0 && (
          <DetailRow label="Personality" value={protagonist.personality} />
        )}
      </div>
    </ConfirmationCard>
  );
}

// Preferences confirmation card
interface PreferencesConfirmationProps {
  preferences: {
    story_length?: string;
    delivery_time?: string;
    timezone?: string;
  };
  confirmed: boolean;
  onConfirm: () => void;
  onEdit: () => void;
}

export function PreferencesConfirmation({
  preferences,
  confirmed,
  onConfirm,
  onEdit,
}: PreferencesConfirmationProps) {
  const lengthLabels: Record<string, string> = {
    short: 'Short (~1,000 words)',
    medium: 'Medium (~2,000 words)',
    long: 'Long (~3,500 words)',
  };

  return (
    <ConfirmationCard
      title="Your Preferences"
      icon="⚙️"
      confirmed={confirmed}
      onConfirm={onConfirm}
      onEdit={onEdit}
    >
      <div className="space-y-1">
        {preferences.story_length && (
          <DetailRow
            label="Story Length"
            value={lengthLabels[preferences.story_length] || preferences.story_length}
          />
        )}
        {preferences.delivery_time && (
          <DetailRow label="Delivery Time" value={preferences.delivery_time} />
        )}
        {preferences.timezone && (
          <DetailRow label="Timezone" value={preferences.timezone} />
        )}
      </div>
    </ConfirmationCard>
  );
}
