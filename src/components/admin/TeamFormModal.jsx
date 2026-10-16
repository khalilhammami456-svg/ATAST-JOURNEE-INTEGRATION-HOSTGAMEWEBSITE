import { useEffect, useState } from 'react';
import { Plus, Users, X } from 'lucide-react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import Field from '../ui/Field';
import ColorPicker from '../ui/ColorPicker';
import AvatarPicker from '../ui/AvatarPicker';
import TeamAvatar from '../ui/TeamAvatar';
import { addTeam, updateTeam } from '../../store/actions';
import { useAppState } from '../../store/hooks';
import { TEAM_COLOR_PRESETS } from '../../utils/color';
import { randomAvatarId } from '../../data/avatars';

const emptyForm = (colorIndex = 0, takenAvatars = []) => ({
  name: '',
  color: TEAM_COLOR_PRESETS[colorIndex % TEAM_COLOR_PRESETS.length],
  avatar: randomAvatarId(takenAvatars),
  logo: null,
  participantNames: ['', '', '', '', ''],
});

/** Create a team (with its first participants) or edit an existing one. */
export default function TeamFormModal({ open, onClose, team = null, onSaved }) {
  const { teams } = useAppState();
  const [form, setForm] = useState(emptyForm());
  const [error, setError] = useState('');
  const takenAvatars = teams.filter((other) => other.id !== team?.id && other.avatar).map((other) => other.avatar);

  useEffect(() => {
    if (!open) return;
    setError('');
    setForm(
      team
        ? { name: team.name, color: team.color, avatar: team.avatar ?? null, logo: team.logo, participantNames: [] }
        : emptyForm(teams.length, takenAvatars),
    );
  }, [open, team]); // eslint-disable-line react-hooks/exhaustive-deps

  const setField = (key, value) => setForm((current) => ({ ...current, [key]: value }));
  const setParticipant = (index, value) =>
    setForm((current) => ({
      ...current,
      participantNames: current.participantNames.map((name, i) => (i === index ? value : name)),
    }));

  const submit = (event) => {
    event.preventDefault();
    try {
      if (team) {
        // Choosing an avatar replaces any image imported in an older version.
        updateTeam(team.id, {
          name: form.name,
          color: form.color,
          avatar: form.avatar,
          logo: form.avatar ? null : form.logo,
        });
        onSaved?.(team, 'updated');
      } else {
        const created = addTeam(form);
        onSaved?.(created, 'created');
      }
      onClose();
    } catch (submitError) {
      setError(submitError.message);
    }
  };

  const preview = { name: form.name || 'Équipe', color: form.color, avatar: form.avatar, logo: form.logo };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={team ? "Modifier l'équipe" : 'Nouvelle équipe'}
      icon={Users}
      size="lg"
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button type="submit" form="team-form">
            {team ? 'Enregistrer' : "Créer l'équipe"}
          </Button>
        </>
      }
    >
      <form id="team-form" onSubmit={submit} className="grid gap-6 md:grid-cols-[1fr_15rem]" noValidate>
        <div className="space-y-5">
          <Field
            label="Nom de l'équipe"
            placeholder="Ex. Team Phoenix"
            value={form.name}
            maxLength={32}
            onChange={(event) => {
              setField('name', event.target.value);
              setError('');
            }}
            error={error}
            data-autofocus
          />
          <ColorPicker value={form.color} onChange={(color) => setField('color', color)} />
          <AvatarPicker
            value={form.avatar}
            onChange={(avatar) => setField('avatar', avatar)}
            color={form.color}
            teamName={form.name}
            takenIds={takenAvatars}
          />

          {!team && (
            <fieldset>
              <legend className="label">Participants</legend>
              <ol className="space-y-2">
                {form.participantNames.map((name, index) => (
                  <li key={index} className="flex items-center gap-2">
                    <span className="w-6 text-right font-bold text-ink-faint">{index + 1}.</span>
                    <input
                      className="field py-2.5"
                      value={name}
                      placeholder="Nom et prénom"
                      aria-label={`Participant ${index + 1}`}
                      onChange={(event) => setParticipant(index, event.target.value)}
                    />
                    <button
                      type="button"
                      onClick={() =>
                        setField(
                          'participantNames',
                          form.participantNames.filter((_, i) => i !== index),
                        )
                      }
                      className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-ink-faint hover:bg-ink/5 hover:text-brand"
                      aria-label={`Retirer la ligne ${index + 1}`}
                    >
                      <X size={18} />
                    </button>
                  </li>
                ))}
              </ol>
              <Button
                variant="ghost"
                size="sm"
                icon={Plus}
                className="mt-2"
                onClick={() => setField('participantNames', [...form.participantNames, ''])}
              >
                Ajouter un participant
              </Button>
            </fieldset>
          )}
        </div>

        <aside className="hidden md:block">
          <div className="sticky top-0">
            <span className="label">Aperçu</span>
            <div
              className="flex flex-col items-center gap-3 rounded-3xl p-6 text-center"
              style={{
                background: `linear-gradient(160deg, ${form.color}22, transparent 70%)`,
                border: `2px solid ${form.color}55`,
              }}
            >
              <TeamAvatar team={preview} size="xl" ring />
              <p className="w-full truncate text-xl font-extrabold uppercase">{preview.name}</p>
              <p className="text-4xl font-extrabold">{team?.score ?? 0}</p>
              <p className="text-xs font-bold uppercase tracking-[0.3em] text-ink-faint">points</p>
            </div>
          </div>
        </aside>
      </form>
    </Modal>
  );
}
