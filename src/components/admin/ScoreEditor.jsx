import { useState } from 'react';
import { Plus, Save, Undo2 } from 'lucide-react';
import Button from '../ui/Button';
import Field from '../ui/Field';
import AnimatedNumber from '../ui/AnimatedNumber';
import ScoreButtons from './ScoreButtons';
import { useAppState } from '../../store/hooks';
import { addScoreEvent, setScore, undoLastForTeam } from '../../store/actions';
import { useNotify } from '../ui/Notification';
import { useConfirm } from '../ui/ConfirmDialog';
import { formatDelta } from '../../utils/format';

/** The three ways to change a score: quick buttons, direct value, or a scored event. */
export default function ScoreEditor({ team }) {
  const { games, history } = useAppState();
  const notify = useNotify();
  const confirm = useConfirm();
  const [directValue, setDirectValue] = useState('');
  const [directError, setDirectError] = useState('');
  const [eventForm, setEventForm] = useState({ gameId: '', reason: '', points: '' });
  const [eventError, setEventError] = useState('');

  const lastEntry = history.findLast((entry) => entry.teamId === team.id);

  const submitDirect = (event) => {
    event.preventDefault();
    try {
      setScore(team.id, directValue);
      setDirectValue('');
      setDirectError('');
    } catch (error) {
      setDirectError(error.message);
    }
  };

  const submitEvent = (event) => {
    event.preventDefault();
    try {
      addScoreEvent(team.id, eventForm.points, { reason: eventForm.reason, gameId: eventForm.gameId || null });
      setEventForm({ gameId: '', reason: '', points: '' });
      setEventError('');
    } catch (error) {
      setEventError(error.message);
    }
  };

  const undo = async () => {
    const ok = await confirm({
      title: 'Annuler la dernière modification ?',
      message: `« ${lastEntry.reason} » (${formatDelta(lastEntry.delta)} pts) sera retiré de l'historique de ${team.name}.`,
      confirmLabel: 'Annuler la modification',
    });
    if (!ok) return;
    try {
      undoLastForTeam(team.id);
      notify('Dernière modification annulée.', { type: 'info' });
    } catch (error) {
      notify(error.message, { type: 'error' });
    }
  };

  return (
    <div className="space-y-6">
      <section className="card flex flex-col items-center gap-5 p-6">
        <p className="text-sm font-bold uppercase tracking-[0.3em] text-ink-soft">Score actuel</p>
        <div className="text-8xl font-extrabold leading-none tracking-tight" style={{ color: team.color }}>
          <AnimatedNumber value={team.score} flash={false} />
        </div>
        <div className="max-w-full overflow-x-auto pb-1">
          <ScoreButtons team={team} size="lg">
            <span className="w-4" />
          </ScoreButtons>
        </div>
        <Button variant="ghost" size="sm" icon={Undo2} onClick={undo} disabled={!lastEntry}>
          Annuler la dernière modification
        </Button>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={submitDirect} className="card space-y-4 p-5" noValidate>
          <h3 className="text-lg font-extrabold uppercase">Fixer le score</h3>
          <Field
            label="Nouveau score"
            type="number"
            inputMode="numeric"
            min="0"
            placeholder={String(team.score)}
            value={directValue}
            onChange={(event) => setDirectValue(event.target.value)}
            error={directError}
          />
          <Button type="submit" icon={Save} className="w-full">
            Enregistrer
          </Button>
        </form>

        <form onSubmit={submitEvent} className="card space-y-4 p-5" noValidate>
          <h3 className="text-lg font-extrabold uppercase">Ajouter un événement</h3>
          <Field label="Mini-jeu">
            {(props) => (
              <select
                {...props}
                className="field"
                value={eventForm.gameId}
                onChange={(event) => setEventForm((form) => ({ ...form, gameId: event.target.value }))}
              >
                <option value="">— Autre (bonus, pénalité…) —</option>
                {games.map((game) => (
                  <option key={game.id} value={game.id}>
                    {game.emoji} {game.name}
                  </option>
                ))}
              </select>
            )}
          </Field>
          <div className="grid grid-cols-[1fr_8rem] gap-3">
            <Field
              label="Motif"
              placeholder={eventForm.gameId ? 'Facultatif' : 'Ex. Pénalité, Bonus…'}
              value={eventForm.reason}
              onChange={(event) => setEventForm((form) => ({ ...form, reason: event.target.value }))}
            />
            <Field
              label="Points"
              type="number"
              inputMode="numeric"
              placeholder="+30"
              value={eventForm.points}
              onChange={(event) => setEventForm((form) => ({ ...form, points: event.target.value }))}
            />
          </div>
          {eventError && (
            <p className="text-sm font-semibold text-brand" role="alert">
              {eventError}
            </p>
          )}
          <Button type="submit" icon={Plus} className="w-full">
            Ajouter
          </Button>
        </form>
      </div>
    </div>
  );
}
