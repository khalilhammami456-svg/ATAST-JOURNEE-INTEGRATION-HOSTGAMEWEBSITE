import { useEffect, useMemo, useState } from 'react';
import { Trophy } from 'lucide-react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import TeamAvatar from '../ui/TeamAvatar';
import { awardGamePoints } from '../../store/actions';
import { useAppState, useRankedTeams } from '../../store/hooks';
import { useConfirm } from '../ui/ConfirmDialog';
import { useNotify } from '../ui/Notification';

/** Enter every team's result for one mini-game, then save them in a single batch. */
export default function AwardPointsModal({ open, onClose, game }) {
  const { history } = useAppState();
  const rankedTeams = useRankedTeams();
  const teams = useMemo(() => [...rankedTeams].sort((a, b) => a.name.localeCompare(b.name, 'fr')), [rankedTeams]);
  const confirm = useConfirm();
  const notify = useNotify();
  const [points, setPoints] = useState({});
  const [error, setError] = useState('');

  useEffect(() => {
    if (open) {
      setPoints({});
      setError('');
    }
  }, [open]);

  if (!game) return null;

  const alreadyPlayed = history.some((entry) => entry.gameId === game.id);
  const filledCount = Object.values(points).filter((value) => value !== '' && Number(value) !== 0).length;
  const roundToFive = (value) => Math.max(1, Math.round(value / 5) * 5);
  const quickValues = game.maxPoints
    ? [...new Set([game.maxPoints, roundToFive(game.maxPoints * 0.66), roundToFive(game.maxPoints * 0.33)])]
    : [30, 20, 10, 5];

  const submit = async (event) => {
    event.preventDefault();
    if (alreadyPlayed) {
      const ok = await confirm({
        title: 'Mini-jeu déjà noté',
        message: `Des points ont déjà été attribués pour « ${game.name} ». Les nouveaux points s'ajouteront aux précédents.`,
        confirmLabel: 'Ajouter quand même',
      });
      if (!ok) return;
    }
    try {
      const entries = awardGamePoints(game.id, points);
      notify(`${game.name} : scores enregistrés pour ${entries.length} équipe${entries.length > 1 ? 's' : ''}.`);
      onClose();
    } catch (submitError) {
      setError(submitError.message);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`${game.emoji ?? '🎮'} ${game.name}`}
      description={
        game.maxPoints
          ? `Jusqu'à ${game.maxPoints} points par équipe. Laissez vide les équipes qui ne marquent pas.`
          : 'Laissez vide les équipes qui ne marquent pas.'
      }
      size="lg"
      footer={
        <>
          <span className="mr-auto text-sm font-semibold text-ink-soft">
            {filledCount} équipe{filledCount > 1 ? 's' : ''} notée{filledCount > 1 ? 's' : ''}
          </span>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button type="submit" form="award-form" icon={Trophy} disabled={filledCount === 0}>
            Enregistrer les scores
          </Button>
        </>
      }
    >
      <form id="award-form" onSubmit={submit} noValidate>
        <ul className="divide-y divide-line">
          {teams.map((team) => (
            <li key={team.id} className="flex flex-wrap items-center gap-3 py-2.5">
              <TeamAvatar team={team} size="sm" />
              <div className="min-w-[8rem] flex-1">
                <p className="font-bold uppercase">{team.name}</p>
                <p className="text-sm text-ink-faint">{team.score} pts actuellement</p>
              </div>
              <div className="flex gap-1">
                {quickValues.map((value) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => setPoints((current) => ({ ...current, [team.id]: String(value) }))}
                    className="h-10 min-w-[2.75rem] rounded-lg border-2 border-line px-2 text-sm font-bold hover:border-brand hover:text-brand"
                  >
                    {value}
                  </button>
                ))}
              </div>
              <label className="flex items-center gap-2">
                <span className="text-xl font-extrabold text-brand">+</span>
                <input
                  type="number"
                  inputMode="numeric"
                  min="0"
                  max={game.maxPoints ?? undefined}
                  className="field w-24 py-2 text-center text-xl font-extrabold"
                  value={points[team.id] ?? ''}
                  onChange={(event) => {
                    setError('');
                    setPoints((current) => ({ ...current, [team.id]: event.target.value }));
                  }}
                  aria-label={`Points pour ${team.name}`}
                />
              </label>
            </li>
          ))}
        </ul>
        {error && (
          <p className="mt-3 rounded-xl bg-brand/10 px-4 py-3 font-semibold text-brand" role="alert">
            {error}
          </p>
        )}
      </form>
    </Modal>
  );
}
