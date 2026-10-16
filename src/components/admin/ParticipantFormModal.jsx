import { useEffect, useState } from 'react';
import { UserRound } from 'lucide-react';
import Modal from '../ui/Modal';
import Button from '../ui/Button';
import Field from '../ui/Field';
import ImageUpload from '../ui/ImageUpload';
import { addParticipant, updateParticipant } from '../../store/actions';
import { useAppState } from '../../store/hooks';

export default function ParticipantFormModal({ open, onClose, participant = null, defaultTeamId = '', onSaved }) {
  const { teams } = useAppState();
  const [form, setForm] = useState({ name: '', teamId: '', studentId: '', avatar: null });
  const [error, setError] = useState('');

  useEffect(() => {
    if (!open) return;
    setError('');
    setForm(
      participant
        ? {
            name: participant.name,
            teamId: participant.teamId,
            studentId: participant.studentId ?? '',
            avatar: participant.avatar,
          }
        : { name: '', teamId: defaultTeamId || teams[0]?.id || '', studentId: '', avatar: null },
    );
  }, [open, participant]); // eslint-disable-line react-hooks/exhaustive-deps

  const setField = (key) => (event) => setForm((current) => ({ ...current, [key]: event.target.value }));

  const submit = (event) => {
    event.preventDefault();
    try {
      if (participant) updateParticipant(participant.id, form);
      else addParticipant(form);
      onSaved?.(form, participant ? 'updated' : 'created');
      onClose();
    } catch (submitError) {
      setError(submitError.message);
    }
  };

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={participant ? 'Modifier le participant' : 'Nouveau participant'}
      icon={UserRound}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Annuler
          </Button>
          <Button type="submit" form="participant-form">
            {participant ? 'Enregistrer' : 'Ajouter'}
          </Button>
        </>
      }
    >
      <form id="participant-form" onSubmit={submit} className="space-y-5" noValidate>
        <Field
          label="Nom complet"
          placeholder="Ex. Mariem Gharbi"
          value={form.name}
          onChange={setField('name')}
          data-autofocus
        />
        <Field label="Équipe">
          {(props) => (
            <select {...props} className="field" value={form.teamId} onChange={setField('teamId')}>
              {teams.length === 0 && <option value="">Aucune équipe — créez-en une d'abord</option>}
              {teams.map((team) => (
                <option key={team.id} value={team.id}>
                  {team.name}
                </option>
              ))}
            </select>
          )}
        </Field>
        <Field
          label="Numéro étudiant / identifiant"
          placeholder="Facultatif"
          value={form.studentId}
          onChange={setField('studentId')}
        />
        <ImageUpload
          label="Photo"
          size={160}
          value={form.avatar}
          onChange={(avatar) => setForm((current) => ({ ...current, avatar }))}
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
