import { useState } from 'react';
import { ListOrdered, Trophy, Tv } from 'lucide-react';
import PageHeader from '../../components/admin/PageHeader';
import Leaderboard from '../../components/admin/Leaderboard';
import Button from '../../components/ui/Button';
import { setDisplayView, startPodiumCeremony } from '../../store/actions';

export default function LeaderboardPage() {
  const [showButtons, setShowButtons] = useState(true);
  return (
    <>
      <PageHeader
        eyebrow="Compétition"
        title="Classement"
        description="Calculé automatiquement à chaque modification. Les équipes à égalité partagent le même rang."
        actions={
          <>
            <Button variant="secondary" onClick={() => setShowButtons((value) => !value)}>
              {showButtons ? 'Masquer les boutons' : 'Afficher les boutons'}
            </Button>
            <Button variant="secondary" icon={ListOrdered} onClick={() => setDisplayView('leaderboard')}>
              Sur l'écran public
            </Button>
            <Button icon={Trophy} onClick={startPodiumCeremony}>
              Lancer le podium
            </Button>
          </>
        }
      />
      <Leaderboard showButtons={showButtons} />
      <p className="mt-6 flex items-center gap-2 text-ink-faint">
        <Tv size={18} /> Les boutons « écran public » pilotent l'onglet ouvert via Mode écran.
      </p>
    </>
  );
}
