import { useOutletContext } from 'react-router-dom';
import { Crown, Gamepad2, Plus, Sparkles, Trophy, Tv, Undo2, Users, UsersRound, Zap } from 'lucide-react';
import PageHeader from '../../components/admin/PageHeader';
import Leaderboard from '../../components/admin/Leaderboard';
import HistoryList from '../../components/admin/HistoryList';
import StatsCard from '../../components/ui/StatsCard';
import Button from '../../components/ui/Button';
import TeamAvatar from '../../components/ui/TeamAvatar';
import AnimatedNumber from '../../components/ui/AnimatedNumber';
import { useConfirm } from '../../components/ui/ConfirmDialog';
import { useNotify } from '../../components/ui/Notification';
import { useAppState, useRankedTeams, useSettings, useTeamsById } from '../../store/hooks';
import { startPodiumCeremony, undoLastChange } from '../../store/actions';
import { formatDelta, relativeTime } from '../../utils/format';

function openDisplay(path = `${import.meta.env.BASE_URL}display`) {
  window.open(path, 'journee-integration-display');
}

function LeaderCard({ leaders }) {
  if (leaders.length === 0) {
    return <StatsCard tone="brand" icon={Crown} label="Leader" value="—" detail="Aucun point distribué" />;
  }
  const [leader] = leaders;
  return (
    <div className="on-brand relative overflow-hidden rounded-xl2 bg-brand p-5 text-cream shadow-lift">
      <svg className="absolute -right-8 -top-10 h-44 w-44 text-cream/15" viewBox="0 0 100 100" aria-hidden="true">
        <path d="M0 70 C 30 70, 55 50, 60 0" stroke="currentColor" strokeWidth="10" fill="none" strokeLinecap="round" />
      </svg>
      <p className="relative flex items-center gap-2 text-sm font-bold uppercase tracking-widest text-cream/80">
        <Crown size={18} strokeWidth={2.6} /> {leaders.length > 1 ? 'Leaders ex æquo' : 'Leader'}
      </p>
      <div className="relative mt-3 flex items-center gap-3">
        <TeamAvatar team={leader} size="md" ring />
        <div className="min-w-0">
          <p
            className={`line-clamp-2 font-extrabold uppercase leading-tight ${leaders.length > 1 ? 'text-lg' : 'text-2xl'}`}
          >
            {leaders.map((team) => team.name).join(' · ')}
          </p>
          <p className="text-3xl font-extrabold leading-none">
            <AnimatedNumber value={leader.score} flash={false} /> <span className="text-base text-cream/75">pts</span>
          </p>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { openAddPoints } = useOutletContext();
  const { participants, history, games } = useAppState();
  const { eventName, year } = useSettings();
  const rankedTeams = useRankedTeams();
  const teamsById = useTeamsById();
  const confirm = useConfirm();
  const notify = useNotify();

  const totalPoints = rankedTeams.reduce((sum, team) => sum + team.score, 0);
  const leaders = rankedTeams.filter((team) => team.rank === 1 && team.score > 0);
  const lastEntry = history.at(-1);
  const playedGames = new Set(history.map((entry) => entry.gameId).filter(Boolean)).size;

  const undo = async () => {
    const batchSize = lastEntry.batchId ? history.filter((entry) => entry.batchId === lastEntry.batchId).length : 1;
    const ok = await confirm({
      title: 'Annuler la dernière modification ?',
      message:
        batchSize > 1
          ? `« ${lastEntry.reason} » sera annulé pour les ${batchSize} équipes concernées.`
          : `« ${lastEntry.reason} » (${formatDelta(lastEntry.delta)} pts pour ${teamsById[lastEntry.teamId]?.name}) sera annulé.`,
      confirmLabel: 'Annuler la modification',
    });
    if (!ok) return;
    try {
      undoLastChange();
    } catch (error) {
      notify(error.message, { type: 'error' });
    }
  };

  return (
    <>
      <PageHeader
        eyebrow={`Tableau de bord · ${year}`}
        title={eventName}
        actions={
          <>
            <Button variant="secondary" icon={Tv} onClick={() => openDisplay()}>
              Mode écran
            </Button>
            <Button
              variant="secondary"
              icon={Trophy}
              onClick={() => {
                startPodiumCeremony();
                openDisplay();
              }}
            >
              Voir le podium
            </Button>
          </>
        }
      />

      <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Statistiques">
        <StatsCard
          icon={Users}
          label="Équipes"
          value={rankedTeams.length}
          detail={`${playedGames}/${games.length} mini-jeux joués`}
        />
        <StatsCard
          icon={UsersRound}
          label="Participants"
          value={participants.length}
          detail={rankedTeams.length ? `≈ ${Math.round(participants.length / rankedTeams.length)} par équipe` : '—'}
        />
        <StatsCard
          icon={Sparkles}
          label="Points distribués"
          value={<AnimatedNumber value={totalPoints} flash={false} />}
          detail={`${history.length} modification${history.length > 1 ? 's' : ''}`}
        />
        <LeaderCard leaders={leaders} />
      </section>

      <section className="mt-6 flex flex-wrap gap-3" aria-label="Actions rapides">
        <Button to="/admin/teams?new=1" icon={Plus} variant="secondary">
          Ajouter une équipe
        </Button>
        <Button icon={Zap} onClick={() => openAddPoints()}>
          Ajouter des points
        </Button>
        <Button to="/admin/games" icon={Gamepad2} variant="secondary">
          Noter un mini-jeu
        </Button>
        <Button to="/admin/participants" icon={UsersRound} variant="secondary">
          Participants
        </Button>
      </section>

      <div className="mt-8 grid gap-8 xl:grid-cols-[minmax(0,1fr)_26rem]">
        <section aria-labelledby="ranking-title">
          <div className="mb-3 flex items-baseline justify-between">
            <h2 id="ranking-title" className="text-2xl font-extrabold uppercase">
              Classement & scores rapides
            </h2>
            <span className="hidden text-sm font-semibold text-ink-faint md:inline">Un clic = points ajoutés</span>
          </div>
          <Leaderboard />
        </section>

        <aside className="space-y-6">
          <section className="card p-5" aria-labelledby="last-change-title">
            <h2 id="last-change-title" className="text-sm font-bold uppercase tracking-widest text-ink-soft">
              Dernière modification
            </h2>
            {lastEntry ? (
              <div className="mt-3 flex items-center gap-3">
                {teamsById[lastEntry.teamId] && <TeamAvatar team={teamsById[lastEntry.teamId]} size="sm" />}
                <div className="min-w-0 flex-1">
                  <p className="truncate font-extrabold uppercase">
                    {teamsById[lastEntry.teamId]?.name ?? 'Équipe supprimée'}
                  </p>
                  <p className="truncate text-sm text-ink-soft">
                    {lastEntry.reason} · {relativeTime(lastEntry.at)}
                  </p>
                </div>
                <span
                  className={`text-2xl font-extrabold ${lastEntry.delta > 0 ? 'text-[#0b8a63] dark:text-[#3ddba6]' : 'text-orbit'}`}
                >
                  {formatDelta(lastEntry.delta)}
                </span>
              </div>
            ) : (
              <p className="mt-3 text-ink-faint">Aucune modification pour le moment.</p>
            )}
            <Button
              variant="secondary"
              size="sm"
              icon={Undo2}
              className="mt-4 w-full"
              onClick={undo}
              disabled={!lastEntry}
            >
              Annuler la dernière modification
            </Button>
          </section>

          <section className="card p-5" aria-labelledby="history-title">
            <h2 id="history-title" className="mb-3 text-sm font-bold uppercase tracking-widest text-ink-soft">
              Historique récent
            </h2>
            <HistoryList limit={10} compact />
          </section>
        </aside>
      </div>
    </>
  );
}
