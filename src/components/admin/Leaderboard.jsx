import { AnimatePresence } from 'framer-motion';
import { Plus, Trophy } from 'lucide-react';
import QuickScoreRow from './QuickScoreRow';
import EmptyState from '../ui/EmptyState';
import Button from '../ui/Button';
import { useRankedTeams } from '../../store/hooks';
import { useRankChanges } from '../../hooks/useRankChanges';

export default function Leaderboard({ limit, showButtons = true }) {
  const rankedTeams = useRankedTeams();
  const rankChanges = useRankChanges(rankedTeams);
  const visible = limit ? rankedTeams.slice(0, limit) : rankedTeams;

  if (rankedTeams.length === 0) {
    return (
      <EmptyState
        icon={Trophy}
        title="Aucune équipe"
        message="Créez votre première équipe pour commencer la compétition."
        action={
          <Button to="/admin/teams?new=1" icon={Plus}>
            Créer une équipe
          </Button>
        }
      />
    );
  }

  return (
    <ol className="space-y-2">
      <AnimatePresence initial={false}>
        {visible.map((team) => (
          <QuickScoreRow key={team.id} team={team} rankChange={rankChanges[team.id]} showButtons={showButtons} />
        ))}
      </AnimatePresence>
    </ol>
  );
}
