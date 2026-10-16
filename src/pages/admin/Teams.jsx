import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { AnimatePresence } from 'framer-motion';
import { Plus, Users } from 'lucide-react';
import PageHeader from '../../components/admin/PageHeader';
import TeamCard from '../../components/admin/TeamCard';
import TeamFormModal from '../../components/admin/TeamFormModal';
import Button from '../../components/ui/Button';
import EmptyState from '../../components/ui/EmptyState';
import { useNotify } from '../../components/ui/Notification';
import { useRankedTeams } from '../../store/hooks';

export default function Teams() {
  const teams = useRankedTeams();
  const notify = useNotify();
  const [searchParams, setSearchParams] = useSearchParams();
  const [creating, setCreating] = useState(false);

  useEffect(() => {
    if (searchParams.get('new')) {
      setCreating(true);
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams]);

  return (
    <>
      <PageHeader
        eyebrow="Gestion"
        title="Équipes"
        description={`${teams.length} équipe${teams.length > 1 ? 's' : ''} en compétition. Cliquez sur une carte pour gérer son score, son historique et ses membres.`}
        actions={
          teams.length > 0 && (
            <Button icon={Plus} onClick={() => setCreating(true)}>
              Nouvelle équipe
            </Button>
          )
        }
      />

      {teams.length === 0 ? (
        <EmptyState
          icon={Users}
          title="Aucune équipe"
          message="Créez votre première équipe pour commencer la compétition."
          action={
            <Button icon={Plus} size="lg" onClick={() => setCreating(true)}>
              Créer une équipe
            </Button>
          }
        />
      ) : (
        <div className="grid gap-5 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
          <AnimatePresence>
            {teams.map((team) => (
              <TeamCard key={team.id} team={team} />
            ))}
          </AnimatePresence>
        </div>
      )}

      <TeamFormModal
        open={creating}
        onClose={() => setCreating(false)}
        onSaved={(team) => notify(`${team.name} est prête pour la compétition !`)}
      />
    </>
  );
}
