import { useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Pencil, Trash2 } from 'lucide-react';
import ScoreEditor from '../../components/admin/ScoreEditor';
import HistoryList from '../../components/admin/HistoryList';
import ParticipantList from '../../components/admin/ParticipantList';
import TeamFormModal from '../../components/admin/TeamFormModal';
import TeamAvatar from '../../components/ui/TeamAvatar';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import { useConfirm } from '../../components/ui/ConfirmDialog';
import { useNotify } from '../../components/ui/Notification';
import { useRankedTeams } from '../../store/hooks';
import { deleteTeam } from '../../store/actions';
import { MEDALS } from '../../utils/ranking';
import { ordinalLabel } from '../../utils/format';

export default function TeamDetail() {
  const { teamId } = useParams();
  const navigate = useNavigate();
  const confirm = useConfirm();
  const notify = useNotify();
  const team = useRankedTeams().find((candidate) => candidate.id === teamId);
  const [editing, setEditing] = useState(false);

  if (!team) {
    return (
      <EmptyState
        title="Équipe introuvable"
        message="Elle a peut-être été supprimée."
        action={
          <Button to="/admin/teams" icon={ArrowLeft}>
            Retour aux équipes
          </Button>
        }
      />
    );
  }

  const remove = async () => {
    const ok = await confirm({
      title: `Supprimer ${team.name} ?`,
      message: (
        <p>
          L'équipe, ses <strong>{team.participantCount} participants</strong> et tout son historique de score seront
          définitivement supprimés.
        </p>
      ),
      confirmLabel: "Supprimer l'équipe",
      danger: true,
      typeToConfirm: 'SUPPRIMER',
    });
    if (!ok) return;
    deleteTeam(team.id);
    notify(`${team.name} a été supprimée.`, { type: 'info' });
    navigate('/admin/teams');
  };

  return (
    <>
      <Link
        to="/admin/teams"
        className="mb-4 inline-flex items-center gap-1.5 font-bold uppercase text-ink-soft hover:text-brand"
      >
        <ArrowLeft size={18} /> Équipes
      </Link>

      <header
        className="relative mb-8 flex flex-wrap items-center gap-5 overflow-hidden rounded-3xl p-6 text-white shadow-lift"
        style={{ background: `linear-gradient(120deg, ${team.color}, ${team.color}cc 55%, rgb(var(--brand-deep)))` }}
      >
        <svg
          className="pointer-events-none absolute -right-10 -top-16 h-72 w-72 text-white/15"
          viewBox="0 0 100 100"
          aria-hidden="true"
        >
          <path
            d="M0 80 C 30 80, 55 55, 62 0"
            stroke="currentColor"
            strokeWidth="9"
            fill="none"
            strokeLinecap="round"
          />
          <path
            d="M20 110 C 45 90, 80 80, 110 40"
            stroke="currentColor"
            strokeWidth="9"
            fill="none"
            strokeLinecap="round"
          />
        </svg>
        <TeamAvatar team={team} size="xl" ring />
        <div className="relative min-w-0 flex-1">
          <p className="text-sm font-bold uppercase tracking-[0.3em] text-white/80">
            {MEDALS[team.rank] ?? ''} {ordinalLabel(team.rank)} au classement
          </p>
          <h1 className="display-title truncate text-5xl drop-shadow-sm sm:text-6xl">{team.name}</h1>
          <p className="mt-1 text-lg font-semibold text-white/85">{team.participantCount} participants</p>
        </div>
        <div className="relative flex gap-2">
          <Button variant="light" icon={Pencil} onClick={() => setEditing(true)}>
            Modifier
          </Button>
          <Button variant="outlineLight" size="icon" onClick={remove} aria-label={`Supprimer ${team.name}`}>
            <Trash2 size={19} />
          </Button>
        </div>
      </header>

      <div className="grid gap-8 xl:grid-cols-[minmax(0,1fr)_28rem]">
        <ScoreEditor team={team} />
        <section className="card p-5" aria-labelledby="team-history">
          <h2 id="team-history" className="mb-3 text-lg font-extrabold uppercase">
            Historique des scores
          </h2>
          <HistoryList teamId={team.id} />
          <p className="mt-3 border-t border-line pt-3 text-right font-bold">
            Score actuel : <span className="text-brand">{team.score}</span>
          </p>
        </section>
      </div>

      <section className="mt-10" aria-labelledby="team-members">
        <h2 id="team-members" className="mb-4 text-2xl font-extrabold uppercase">
          Participants
        </h2>
        <ParticipantList teamId={team.id} />
      </section>

      <TeamFormModal
        open={editing}
        team={team}
        onClose={() => setEditing(false)}
        onSaved={() => notify('Équipe mise à jour.')}
      />
    </>
  );
}
