import { useEffect, useState } from 'react';
import { Zap } from 'lucide-react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import Field from '../ui/Field';
import TeamAvatar from '../ui/TeamAvatar';
import { addScoreEvent } from '../../store/actions';
import { useAppState, useRankedTeams } from '../../store/hooks';

const PRESETS = [5, 10, 20, 30, 50, -5, -10];

/** Fast "add points" dialog: pick a team, a value, optionally a reason — done. */
export default function AddPointsModal({ open, onClose, defaultTeamId = '' }) {
  const { games } = useAppState();
  const teams = useRankedTeams();
  const [teamId, setTeamId] = useState('');
  const [points, setPoints] = useState('');
  const [gameId, setGameId] = useState('');
  const [reason, setReason] = useState('');
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setTeamId(defaultTeamId);
    setPoints('');
    setGameId('');
    setReason('');
    setError('');
  }, [open, defaultTeamId]);

  const submit = (event) => {
    event.preventDefault();
    if (!teamId) {
      setError('Choisissez une équipe.');
      return;
    }
    try {
      const label = reason.trim() || (Number(points) < 0 ? 'Pénalité' : 'Bonus');
      addScoreEvent(teamId, points, { reason: gameId ? reason : label, gameId: gameId || null });
      onClose();
    } catch (submitError) {
      setError(submitError.message);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title="Ajouter des points"
      icon={Zap}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button type="submit" form="add-points-form" icon={Zap}>
            Valider
          </Button>
        </>
      }
    >
      <form id="add-points-form" onSubmit={submit} className="space-y-5" noValidate>
        <fieldset>
          <legend className="label">Équipe</legend>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-4">
            {teams.map((team) => (
              <button
                key={team.id}
                type="button"
                onClick={() => {
                  setTeamId(team.id);
                  setError('');
                }}
                aria-pressed={teamId === team.id}
                className={`flex items-center gap-2 rounded-xl border-2 p-2 text-left transition ${
                  teamId === team.id ? 'border-brand bg-brand/10' : 'border-line hover:border-ink/30'
                }`}
              >
                <TeamAvatar team={team} size="xs" />
                <span className="truncate text-sm font-bold uppercase">{team.name.replace(/^team\s+/i, '')}</span>
              </button>
            ))}
          </div>
        </fieldset>

        <fieldset>
          <legend className="label">Points</legend>
          <div className="flex flex-wrap items-center gap-2">
            {PRESETS.map((value) => (
              <button
                key={value}
                type="button"
                onClick={() => setPoints(String(value))}
                aria-pressed={points === String(value)}
                className={`h-12 min-w-[3.5rem] rounded-xl px-3 text-lg font-extrabold transition ${
                  points === String(value)
                    ? 'bg-brand text-cream'
                    : value < 0
                      ? 'border-2 border-line text-ink-soft hover:border-ink/40'
                      : 'border-2 border-brand/40 text-brand hover:bg-brand/10'
                }`}
              >
                {value > 0 ? `+${value}` : value}
              </button>
            ))}
            <input
              type="number"
              inputMode="numeric"
              className="field h-12 w-28 py-0 text-center text-lg font-extrabold"
              placeholder="Autre"
              value={points}
              onChange={(event) => setPoints(event.target.value)}
              aria-label="Nombre de points"
            />
          </div>
        </fieldset>

        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Mini-jeu">
            {(props) => (
              <select {...props} className="field" value={gameId} onChange={(event) => setGameId(event.target.value)}>
                <option value="">— Aucun —</option>
                {games.map((game) => (
                  <option key={game.id} value={game.id}>
                    {game.emoji} {game.name}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <Field
            label="Motif"
            placeholder="Ex. Bonus ambiance"
            value={reason}
            onChange={(event) => setReason(event.target.value)}
          />
        </div>

        {error && (
          <p className="rounded-xl bg-brand/10 px-4 py-3 font-semibold text-brand" role="alert">
            {error}
          </p>
        )}
      </form>
    </Modal>
  );
}
