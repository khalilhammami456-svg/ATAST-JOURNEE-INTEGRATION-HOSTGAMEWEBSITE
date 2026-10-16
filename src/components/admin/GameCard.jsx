import { Pencil, Trash2, Trophy } from 'lucide-react';
import Button from '../ui/Button';

export default function GameCard({ game, stats, onAward, onEdit, onDelete }) {
  return (
    <article className="card group relative flex flex-col overflow-hidden p-5 transition hover:-translate-y-1 hover:shadow-lift">
      <div className="absolute -right-6 -top-6 grid h-24 w-24 place-items-center rounded-full bg-brand/10 text-5xl transition group-hover:scale-110">
        <span className="translate-x-[-6px] translate-y-[6px]">{game.emoji ?? '🎮'}</span>
      </div>
      <div className="pr-16">
        <h3 className="text-xl font-extrabold uppercase leading-tight">{game.name}</h3>
        {game.maxPoints && (
          <p className="mt-1 text-sm font-bold uppercase tracking-wider text-brand">
            Max {game.maxPoints} pts / équipe
          </p>
        )}
      </div>
      <p className="mt-3 flex-1 text-ink-soft">{game.description || 'Pas de description.'}</p>
      <p className="mt-4 text-sm font-semibold text-ink-faint">
        {stats.teamCount
          ? `Joué · ${stats.teamCount} équipe${stats.teamCount > 1 ? 's' : ''} notée${stats.teamCount > 1 ? 's' : ''} · ${stats.total} pts distribués`
          : 'Pas encore joué'}
      </p>
      <div className="mt-4 flex items-center gap-2">
        <Button icon={Trophy} className="flex-1" onClick={onAward}>
          Attribuer les points
        </Button>
        <Button variant="ghost" size="icon" onClick={onEdit} aria-label={`Modifier ${game.name}`}>
          <Pencil size={18} />
        </Button>
        <Button
          variant="ghost"
          size="icon"
          onClick={onDelete}
          aria-label={`Supprimer ${game.name}`}
          className="hover:!text-brand"
        >
          <Trash2 size={18} />
        </Button>
      </div>
    </article>
  );
}
