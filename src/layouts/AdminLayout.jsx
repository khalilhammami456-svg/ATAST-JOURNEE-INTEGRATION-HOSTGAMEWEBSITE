import { useCallback, useState } from 'react';
import { Outlet, useLocation } from 'react-router-dom';
import { motion } from 'framer-motion';
import Sidebar from '../components/admin/Sidebar';
import Navbar from '../components/admin/Navbar';
import AddPointsModal from '../components/admin/AddPointsModal';
import { useNotify } from '../components/ui/Notification';
import { useScoreEvents } from '../hooks/useScoreEvents';
import { useSettings, useTeamsById } from '../store/hooks';
import { playSound } from '../utils/sound';
import { formatDelta } from '../utils/format';

const COLLAPSE_KEY = 'journee-integration:sidebar-collapsed';

function readCollapsed() {
  try {
    return localStorage.getItem(COLLAPSE_KEY) === '1';
  } catch {
    return false;
  }
}

/** Toasts + discreet sounds for every score change, including leader changes. */
function useScoreFeedback() {
  const notify = useNotify();
  const teamsById = useTeamsById();
  const { sound } = useSettings();

  useScoreEvents((event) => {
    if (event.type === 'reset') {
      notify('Tous les scores ont été remis à zéro.', { type: 'info' });
      return;
    }
    if (event.type === 'undo') {
      notify('Modification annulée.', { type: 'info' });
    } else if (event.changes.length === 1) {
      const [{ teamId, delta }] = event.changes;
      const name = teamsById[teamId]?.name ?? 'Équipe';
      notify(
        delta > 0
          ? `${name} a gagné ${formatDelta(delta)} point${delta > 1 ? 's' : ''}`
          : `${name} perd ${Math.abs(delta)} point${delta < -1 ? 's' : ''}`,
        { type: delta > 0 ? 'gain' : 'loss', duration: 2400 },
      );
    }
    if (event.leaderChanged) {
      const names = event.leaderIds.map((id) => teamsById[id]?.name).filter(Boolean);
      notify(
        names.length > 1 ? `🏆 Égalité en tête : ${names.join(' & ')} !` : `🏆 ${names[0]} prend la première place !`,
        { type: 'leader', duration: 4200 },
      );
    }
    if (sound) {
      const gained = event.changes.some((change) => change.delta > 0);
      playSound(event.leaderChanged ? 'leader' : gained ? 'gain' : 'loss');
    }
  });
}

export default function AdminLayout() {
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(readCollapsed);
  const [addPoints, setAddPoints] = useState({ open: false, teamId: '' });

  useScoreFeedback();

  const toggleCollapsed = () =>
    setCollapsed((value) => {
      try {
        localStorage.setItem(COLLAPSE_KEY, value ? '0' : '1');
      } catch {
        /* per-viewer convenience only */
      }
      return !value;
    });

  const openAddPoints = useCallback((teamId = '') => setAddPoints({ open: true, teamId }), []);
  const closeAddPoints = useCallback(() => setAddPoints((current) => ({ ...current, open: false })), []);

  return (
    <div className="flex min-h-screen">
      <Sidebar collapsed={collapsed} onToggle={toggleCollapsed} onAddPoints={() => openAddPoints()} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Navbar onAddPoints={() => openAddPoints()} />
        <main className="mx-auto w-full max-w-[1500px] flex-1 px-4 py-6 sm:px-8 lg:py-10">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 12 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.25, ease: 'easeOut' }}
          >
            <Outlet context={{ openAddPoints }} />
          </motion.div>
        </main>
      </div>
      <AddPointsModal open={addPoints.open} defaultTeamId={addPoints.teamId} onClose={closeAddPoints} />
    </div>
  );
}
