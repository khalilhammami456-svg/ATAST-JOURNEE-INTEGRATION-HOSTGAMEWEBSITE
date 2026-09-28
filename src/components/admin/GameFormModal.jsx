import { useEffect, useState } from 'react';
import { Gamepad2 } from 'lucide-react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import Field from '../ui/Field';
import { addGame, updateGame } from '../../store/actions';

const EMOJIS = ['🎮', '🎵', '🏃', '🎧', '⚽', '🧠', '📸', '🎯', '🧩', '🎤', '🏀', '🎲', '🔥', '💡'];

export default function GameFormModal({ open, onClose, game = null, onSaved }) {
  const [form, setForm] = useState({ name: '', description: '', maxPoints: '', emoji: '🎮' });
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setError('');
    setForm(
      game
        ? {
            name: game.name,
            description: game.description ?? '',
            maxPoints: game.maxPoints ?? '',
            emoji: game.emoji ?? '🎮',
          }
        : { name: '', description: '', maxPoints: '', emoji: '🎮' },
    );
  }, [open, game]);

  const setField = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const submit = (event) => {
    event.preventDefault();
    try {
      if (game) updateGame(game.id, form);
      else addGame(form);
      onSaved?.(form.name.trim(), game ? 'updated' : 'created');
      onClose();
    } catch (submitError) {
      setError(submitError.message);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={game ? 'Modifier le mini-jeu' : 'Nouveau mini-jeu'}
      icon={Gamepad2}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button type="submit" form="game-form">
            {game ? 'Enregistrer' : 'Créer le mini-jeu'}
          </Button>
        </>
      }
    >
      <form id="game-form" onSubmit={submit} className="space-y-5" noValidate>
        <fieldset>
          <legend className="label">Icône</legend>
          <div className="flex flex-wrap gap-1.5">
            {EMOJIS.map((emoji) => (
              <button
                key={emoji}
                type="button"
                onClick={() => setForm((current) => ({ ...current, emoji }))}
                aria-pressed={form.emoji === emoji}
                className={`grid h-11 w-11 place-items-center rounded-xl text-2xl transition ${
                  form.emoji === emoji ? 'bg-brand/15 ring-2 ring-brand' : 'hover:bg-ink/5'
                }`}
              >
                {emoji}
              </button>
            ))}
          </div>
        </fieldset>
        <Field
          label="Nom"
          placeholder="Ex. Quiz musical"
          value={form.name}
          onChange={setField('name')}
          data-autofocus
        />
        <Field label="Description">
          {(props) => (
            <textarea
              {...props}
              rows={3}
              className="field resize-none"
              placeholder="Ex. Un quiz de 20 questions."
              value={form.description}
              onChange={setField('description')}
            />
          )}
        </Field>
        <Field
          label="Points maximum par équipe"
          type="number"
          min="1"
          inputMode="numeric"
          placeholder="Ex. 50 (facultatif)"
          value={form.maxPoints}
          onChange={setField('maxPoints')}
        />
        {error && (
          <p className="text-sm font-semibold text-brand" role="alert">
            {error}
          </p>
        )}
      </form>
    </Modal>
  );
}
