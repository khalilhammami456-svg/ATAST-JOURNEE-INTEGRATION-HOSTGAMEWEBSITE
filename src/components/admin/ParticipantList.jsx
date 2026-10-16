import { useMemo, useState } from 'react';
import { Pencil, Search, Trash2, UserPlus, UsersRound } from 'lucide-react';
import { useAppState, useTeamsById } from '../../store/hooks';
import { deleteParticipant, updateParticipant } from '../../store/actions';
import { normalize } from '../../utils/format';
import { useConfirm } from '../ui/ConfirmDialog';
import { useNotify } from '../ui/Notification';
import Button from '../ui/Button';
import EmptyState from '../ui/EmptyState';
import ParticipantFormModal from './ParticipantFormModal';

function ParticipantAvatar({ participant, color }) {
  if (participant.avatar) {
    return <img src={participant.avatar} alt="" className="h-10 w-10 shrink-0 rounded-full object-cover" />;
  }
  const letters = participant.name
    .split(/\s+/)
    .slice(0, 2)
    .map((word) => word[0])
    .join('')
    .toUpperCase();
  return (
    <span
      className="grid h-10 w-10 shrink-0 place-items-center rounded-full text-sm font-extrabold text-white"
      style={{ backgroundColor: color ?? '#888' }}
      aria-hidden="true"
    >
      {letters}
    </span>
  );
}

/** Searchable participant table. With `teamId`, only that team's members are listed. */
export default function ParticipantList({ teamId = null }) {
  const { participants, teams } = useAppState();
  const teamsById = useTeamsById();
  const confirm = useConfirm();
  const notify = useNotify();
  const [query, setQuery] = useState('');
  const [teamFilter, setTeamFilter] = useState('');
  const [editing, setEditing] = useState(null);
  const [creating, setCreating] = useState(false);

  const filtered = useMemo(() => {
    const needle = normalize(query);
    const activeTeam = teamId ?? teamFilter;
    return participants
      .filter((p) => !activeTeam || p.teamId === activeTeam)
      .filter(
        (p) =>
          !needle ||
          normalize(p.name).includes(needle) ||
          normalize(p.studentId ?? '').includes(needle) ||
          normalize(teamsById[p.teamId]?.name ?? '').includes(needle),
      )
      .sort((a, b) => a.name.localeCompare(b.name, 'fr'));
  }, [participants, query, teamFilter, teamId, teamsById]);

  const remove = async (participant) => {
    const ok = await confirm({
      title: 'Supprimer ce participant ?',
      message: `${participant.name} sera retiré(e) de ${teamsById[participant.teamId]?.name ?? "l'équipe"}. Cette action est définitive.`,
      confirmLabel: 'Supprimer',
      danger: true,
    });
    if (!ok) return;
    deleteParticipant(participant.id);
    notify(`${participant.name} a été supprimé(e).`, { type: 'info' });
  };

  const move = (participant, newTeamId) => {
    updateParticipant(participant.id, { teamId: newTeamId });
    notify(`${participant.name} → ${teamsById[newTeamId]?.name}`, { type: 'info' });
  };

  const header = (
    <div className="flex flex-wrap items-center gap-3">
      <label className="relative min-w-[14rem] flex-1">
        <span className="sr-only">Rechercher un participant</span>
        <Search size={19} className="pointer-events-none absolute left-4 top-1/2 -translate-y-1/2 text-ink-faint" />
        <input
          type="search"
          className="field pl-11"
          placeholder="Rechercher un nom, un identifiant, une équipe…"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
        />
      </label>
      {!teamId && (
        <select
          className="field w-auto min-w-[12rem]"
          value={teamFilter}
          onChange={(event) => setTeamFilter(event.target.value)}
          aria-label="Filtrer par équipe"
        >
          <option value="">Toutes les équipes</option>
          {teams.map((team) => (
            <option key={team.id} value={team.id}>
              {team.name}
            </option>
          ))}
        </select>
      )}
      <Button icon={UserPlus} onClick={() => setCreating(true)} disabled={teams.length === 0}>
        Ajouter
      </Button>
    </div>
  );

  const modals = (
    <ParticipantFormModal
      open={creating || Boolean(editing)}
      participant={editing}
      defaultTeamId={teamId ?? teamFilter}
      onClose={() => {
        setCreating(false);
        setEditing(null);
      }}
      onSaved={(form, mode) =>
        notify(mode === 'created' ? `${form.name.trim()} a rejoint l'équipe !` : 'Participant mis à jour.')
      }
    />
  );

  const isEmpty = participants.filter((p) => !teamId || p.teamId === teamId).length === 0;
  if (isEmpty) {
    return (
      <>
        <EmptyState
          icon={UsersRound}
          title="Aucun participant"
          message={
            teams.length
              ? 'Ajoutez les étudiants pour composer les équipes.'
              : "Créez d'abord une équipe, puis ajoutez ses participants."
          }
          action={
            teams.length ? (
              <Button icon={UserPlus} onClick={() => setCreating(true)}>
                Ajouter un participant
              </Button>
            ) : (
              <Button to="/admin/teams?new=1">Créer une équipe</Button>
            )
          }
        />
        {modals}
      </>
    );
  }

  return (
    <div className="space-y-4">
      {header}
      <div className="card overflow-hidden">
        <div className="scrollbar-thin overflow-x-auto">
          <table className="w-full min-w-[40rem] text-left">
            <thead className="bg-surface-sunken/70 text-xs font-bold uppercase tracking-widest text-ink-soft">
              <tr>
                <th scope="col" className="px-4 py-3">
                  Nom
                </th>
                <th scope="col" className="px-4 py-3">
                  Équipe
                </th>
                <th scope="col" className="px-4 py-3">
                  ID
                </th>
                <th scope="col" className="px-4 py-3 text-right">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-line">
              {filtered.map((participant) => {
                const team = teamsById[participant.teamId];
                return (
                  <tr key={participant.id} className="hover:bg-surface-sunken/40">
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-3">
                        <ParticipantAvatar participant={participant} color={team?.color} />
                        <span className="font-semibold">{participant.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-2.5">
                      <div className="flex items-center gap-2">
                        <span className="h-3 w-3 shrink-0 rounded-full" style={{ backgroundColor: team?.color }} />
                        <select
                          className="rounded-lg border border-transparent bg-transparent py-1 pr-6 font-semibold hover:border-line focus:border-brand focus:outline-none"
                          value={participant.teamId}
                          onChange={(event) => move(participant, event.target.value)}
                          aria-label={`Déplacer ${participant.name} vers une autre équipe`}
                        >
                          {teams.map((option) => (
                            <option key={option.id} value={option.id}>
                              {option.name}
                            </option>
                          ))}
                        </select>
                      </div>
                    </td>
                    <td className="px-4 py-2.5 font-mono text-sm text-ink-soft">{participant.studentId || '—'}</td>
                    <td className="px-4 py-2.5">
                      <div className="flex justify-end gap-1">
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => setEditing(participant)}
                          aria-label={`Modifier ${participant.name}`}
                        >
                          <Pencil size={17} />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon-sm"
                          onClick={() => remove(participant)}
                          aria-label={`Supprimer ${participant.name}`}
                          className="hover:!text-brand"
                        >
                          <Trash2 size={17} />
                        </Button>
                      </div>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        {filtered.length === 0 && (
          <p className="px-4 py-10 text-center text-lg text-ink-faint">
            Aucun participant ne correspond à « {query} ».
          </p>
        )}
        <p className="border-t border-line px-4 py-2.5 text-sm font-semibold text-ink-faint">
          {filtered.length} participant{filtered.length > 1 ? 's' : ''} affiché{filtered.length > 1 ? 's' : ''}
        </p>
      </div>
      {modals}
    </div>
  );
}
