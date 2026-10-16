import PageHeader from '../../components/admin/PageHeader';
import ParticipantList from '../../components/admin/ParticipantList';
import { useAppState } from '../../store/hooks';

export default function Participants() {
  const { participants, teams } = useAppState();
  return (
    <>
      <PageHeader
        eyebrow="Gestion"
        title="Participants"
        description={`${participants.length} étudiants répartis dans ${teams.length} équipes. Changez l'équipe d'un participant directement dans le tableau.`}
      />
      <ParticipantList />
    </>
  );
}
