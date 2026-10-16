import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Crown } from 'lucide-react';
import TeamAvatar from '../ui/TeamAvatar';
import { useScoreEvents } from '../../hooks/useScoreEvents';
import { useSettings, useTeamsById } from '../../store/hooks';
import { formatDelta } from '../../utils/format';
import { burstConfetti } from '../../utils/confetti';

/**
 * Live reactions on the public screen: a "+20" ribbon for each score change
 * and a full "Nouveau leader" moment when the first place changes hands.
 */
export default function LiveEventOverlay({ enabled }) {
  const teamsById = useTeamsById();
  const { confetti } = useSettings();
  const [gains, setGains] = useState([]);
  const [newLeader, setNewLeader] = useState(null);

  useScoreEvents((event) => {
    if (!enabled || event.type !== 'score') return;
    const items = event.changes.slice(0, 4).map((change) => ({ ...change, key: `${event.id}-${change.teamId}` }));
    setGains((current) => [...current, ...items].slice(-4));
    items.forEach((item) =>
      setTimeout(() => setGains((current) => current.filter((gain) => gain.key !== item.key)), 3200),
    );

    if (event.leaderChanged && event.leaderIds.length === 1) {
      setNewLeader({ teamId: event.leaderIds[0], key: event.id });
      if (confetti) burstConfetti();
    }
  });

  useEffect(() => {
    if (!newLeader) return undefined;
    const timer = setTimeout(() => setNewLeader(null), 3800);
    return () => clearTimeout(timer);
  }, [newLeader]);

  const leaderTeam = newLeader && teamsById[newLeader.teamId];

  return (
    <>
      <div className="pointer-events-none absolute right-[2vw] top-[12vh] z-30 flex flex-col items-end gap-[1vh]">
        <AnimatePresence>
          {gains.map((gain) => {
            const team = teamsById[gain.teamId];
            if (!team) return null;
            return (
              <motion.div
                key={gain.key}
                layout
                initial={{ x: '120%', opacity: 0 }}
                animate={{ x: 0, opacity: 1 }}
                exit={{ x: '120%', opacity: 0 }}
                transition={{ type: 'spring', stiffness: 260, damping: 26 }}
                className="flex items-center gap-[0.8vw] rounded-[1.4vh] bg-cream py-[0.8vh] pl-[0.8vh] pr-[1.4vw] text-[#1D0F14] shadow-lift"
                style={{ boxShadow: `0 0 0 3px ${team.color}, 0 18px 40px -16px rgba(0,0,0,.6)` }}
              >
                <TeamAvatar team={team} size="sm" className="!h-[6vh] !w-[6vh] !text-[2vh]" />
                <span className="font-extrabold uppercase" style={{ fontSize: 'clamp(1rem, 2.6vh, 2rem)' }}>
                  {team.name}
                </span>
                <span
                  className={`font-extrabold tabular ${gain.delta > 0 ? 'text-[#0b8a63]' : 'text-[#b25e00]'}`}
                  style={{ fontSize: 'clamp(1.3rem, 3.6vh, 2.8rem)' }}
                >
                  {formatDelta(gain.delta)}
                </span>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      <AnimatePresence>
        {enabled && leaderTeam && (
          <motion.div
            key={newLeader.key}
            className="pointer-events-none absolute inset-0 z-40 grid place-items-center bg-[rgb(var(--brand-night)/0.72)] backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
          >
            <motion.div
              className="flex flex-col items-center text-center text-cream"
              initial={{ scale: 0.5, y: 40 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 1.2, opacity: 0 }}
              transition={{ type: 'spring', stiffness: 180, damping: 14 }}
            >
              <p
                className="flex items-center gap-[1vw] font-bold uppercase tracking-[0.4em] text-gold"
                style={{ fontSize: 'clamp(1rem, 3.4vh, 2.6rem)' }}
              >
                <Crown className="h-[1.2em] w-[1.2em]" /> Nouveau leader
              </p>
              <TeamAvatar team={leaderTeam} size="2xl" ring className="mt-[3vh] !h-[20vh] !w-[20vh] !text-[7vh]" />
              <p className="display-title mt-[3vh]" style={{ fontSize: 'clamp(2.5rem, 11vh, 10rem)' }}>
                {leaderTeam.name}
              </p>
              <p className="mt-[1vh] font-extrabold" style={{ fontSize: 'clamp(1.5rem, 5vh, 4rem)' }}>
                {leaderTeam.score} <span className="text-[0.5em] tracking-[0.3em] text-cream/75">POINTS</span>
              </p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
