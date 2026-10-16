import { History } from 'lucide-react';
import { useAppState, useTeamsById } from '../../store/hooks';
import { formatDelta, formatTime } from '../../utils/format';
import TeamAvatar from '../ui/TeamAvatar';

const KIND_LABELS = { game: 'Mini-jeu', set: 'Score fixé', adjust: 'Ajustement' };

/** Score change log, newest first. Pass `teamId` to show a single team. */
export default function HistoryList({
  teamId,
  limit,
  compact = false,
  emptyMessage = 'Aucune modification de score pour le moment.',
}) {
  const { history } = useAppState();
  const teamsById = useTeamsById();
  const entries = history
    .filter((entry) => !teamId || entry.teamId === teamId)
    .slice()
    .reverse()
    .slice(0, limit ?? Infinity);

  if (entries.length === 0) {
    return (
      <div className="flex flex-col items-center gap-2 rounded-2xl bg-surface-sunken/70 px-4 py-8 text-center text-ink-faint">
        <History size={28} />
        <p className="font-medium">{emptyMessage}</p>
      </div>
    );
  }

  return (
    <ol className="relative space-y-1">
      {entries.map((entry) => {
        const team = teamsById[entry.teamId];
        const positive = entry.delta > 0;
        return (
          <li key={entry.id} className="flex items-center gap-3 rounded-xl px-2 py-2 hover:bg-surface-sunken/60">
            <time className="w-12 shrink-0 text-sm font-bold text-ink-faint tabular">{formatTime(entry.at)}</time>
            {!teamId && team && <TeamAvatar team={team} size="xs" />}
            <div className="min-w-0 flex-1">
              {!teamId && <p className="truncate text-sm font-bold uppercase">{team?.name ?? 'Équipe supprimée'}</p>}
              <p className="truncate text-ink-soft">{entry.reason}</p>
            </div>
            {!compact && (
              <span className="hidden text-xs font-bold uppercase tracking-wider text-ink-faint sm:inline">
                {KIND_LABELS[entry.kind] ?? ''}
              </span>
            )}
            <span
              className={`w-16 shrink-0 rounded-lg py-1 text-center font-extrabold tabular ${
                positive
                  ? 'bg-[#12B886]/15 text-[#0b8a63] dark:text-[#3ddba6]'
                  : 'bg-orbit/15 text-[#b25e00] dark:text-orbit-soft'
              }`}
            >
              {formatDelta(entry.delta)}
            </span>
            {!compact && (
              <span className="w-12 shrink-0 text-right text-sm font-semibold text-ink-faint tabular">
                {entry.newScore}
              </span>
            )}
          </li>
        );
      })}
    </ol>
  );
}
