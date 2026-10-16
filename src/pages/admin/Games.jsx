import { useMemo, useState } from 'react';
import { Gamepad2, Plus } from 'lucide-react';
import PageHeader from '../../components/admin/PageHeader';
import GameCard from '../../components/admin/GameCard';
import GameFormModal from '../../components/admin/GameFormModal';
import AwardPointsModal from '../../components/admin/AwardPointsModal';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import { useConfirm } from '../../components/ui/ConfirmDialog';
import { useNotify } from '../../components/ui/Notification';
import { useAppState } from '../../store/hooks';
import { deleteGame } from '../../store/actions';

export default function Games() {
  const { games, history } = useAppState();
  const confirm = useConfirm();
  const notify = useNotify();
  const [formState, setFormState] = useState({ open: false, game: null });
  const [awardGame, setAwardGame] = useState(null);

  const statsByGame = useMemo(() => {
    const stats = {};
    history.forEach(({ gameId, teamId, delta }) => {
      if (!gameId) return;
      stats[gameId] ??= { teams: new Set(), total: 0 };
      stats[gameId].teams.add(teamId);
      stats[gameId].total += delta;
    });
    return stats;
  }, [history]);

  const remove = async (game) => {
    const ok = await confirm({
      title: `Supprimer « ${game.name} » ?`,
      message: 'Le mini-jeu disparaît de la liste. Les points déjà attribués restent dans les scores et l’historique.',
      confirmLabel: 'Supprimer',
      danger: true,
    });
    if (!ok) return;
    deleteGame(game.id);
    notify(`« ${game.name} » supprimé.`, { type: 'info' });
  };

  return (
    <>
      <PageHeader
        eyebrow="Compétition"
        title="Mini-jeux"
        description="Créez les épreuves de la journée puis attribuez les points de toutes les équipes en une seule fois."
        actions={
          games.length > 0 && (
            <Button icon={Plus} onClick={() => setFormState({ open: true, game: null })}>
              Nouveau mini-jeu
            </Button>
          )
        }
      />

      {games.length === 0 ? (
        <EmptyState
          icon={Gamepad2}
          title="Aucun mini-jeu"
          message="Ajoutez les épreuves de la journée : quiz, relais, blind test…"
          action={
            <Button icon={Plus} size="lg" onClick={() => setFormState({ open: true, game: null })}>
              Créer un mini-jeu
            </Button>
          }
        />
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3">
          {games.map((game) => (
            <GameCard
              key={game.id}
              game={game}
              stats={{ teamCount: statsByGame[game.id]?.teams.size ?? 0, total: statsByGame[game.id]?.total ?? 0 }}
              onAward={() => setAwardGame(game)}
              onEdit={() => setFormState({ open: true, game })}
              onDelete={() => remove(game)}
            />
          ))}
        </div>
      )}

      <GameFormModal
        open={formState.open}
        game={formState.game}
        onClose={() => setFormState({ open: false, game: null })}
        onSaved={(name, mode) =>
          notify(mode === 'created' ? `« ${name} » ajouté aux mini-jeux.` : 'Mini-jeu mis à jour.')
        }
      />
      <AwardPointsModal open={Boolean(awardGame)} game={awardGame} onClose={() => setAwardGame(null)} />
    </>
  );
}
