import { adjustScore } from '../../store/actions';

const STEPS = [-10, -5, -1, 1, 5, 10];

/** The [-10] [-5] [-1] … [+1] [+5] [+10] strip. `children` is rendered in the middle (usually the score). */
export default function ScoreButtons({ team, children, size = 'md', reason }) {
  const sizeClass =
    size === 'lg'
      ? 'h-14 min-w-[3.75rem] text-xl'
      : size === 'sm'
        ? 'h-9 min-w-[2.6rem] text-sm'
        : 'h-11 min-w-[3rem] text-base';
  const renderStep = (step) => {
    const positive = step > 0;
    return (
      <button
        key={step}
        type="button"
        onClick={() => adjustScore(team.id, step, reason)}
        disabled={!positive && team.score === 0}
        className={`tabular rounded-xl px-2 font-extrabold transition active:scale-95 disabled:opacity-30 ${sizeClass} ${
          positive
            ? 'bg-brand text-cream hover:brightness-110'
            : 'border-2 border-line bg-surface-raised text-ink hover:border-ink/40'
        }`}
        aria-label={`${positive ? 'Ajouter' : 'Retirer'} ${Math.abs(step)} point${Math.abs(step) > 1 ? 's' : ''} à ${team.name}`}
      >
        {positive ? `+${step}` : step}
      </button>
    );
  };

  return (
    <div className="flex items-center gap-1.5">
      {STEPS.filter((step) => step < 0).map(renderStep)}
      {children}
      {STEPS.filter((step) => step > 0).map(renderStep)}
    </div>
  );
}
