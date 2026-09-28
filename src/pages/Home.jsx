import { motion } from 'framer-motion';
import { Rocket, Trophy, Tv } from 'lucide-react';
import StageBackground from '../components/display/StageBackground';
import OrbitRings from '../components/ui/OrbitRings';
import BrandMark from '../components/ui/BrandMark';
import Button from '../components/ui/Button';
import TeamAvatar from '../components/ui/TeamAvatar';
import { useRankedTeams, useSettings } from '../store/hooks';
import { setDisplayView } from '../store/actions';

function splitTitle(name) {
  const [first, ...rest] = name.trim().split(/\s+/);
  return rest.length ? [first, rest.join(' ')] : [first];
}

const lineVariants = {
  hidden: { y: '110%' },
  visible: (index) => ({ y: 0, transition: { delay: 0.25 + index * 0.18, duration: 0.9, ease: [0.2, 0.9, 0.2, 1] } }),
};

export default function Home() {
  const { eventName, year, organizer } = useSettings();
  const teams = useRankedTeams();
  const leader = teams.find((team) => team.rank === 1 && team.score > 0);
  const lines = splitTitle(eventName);

  const openScreen = (view) => {
    if (view) setDisplayView(view);
    window.open('/display', 'journee-integration-display');
  };

  return (
    <div className="on-brand relative flex min-h-screen flex-col overflow-hidden text-cream">
      <StageBackground intensity="strong" />

      <header className="relative z-10 flex items-center justify-end gap-3 px-6 pt-6 sm:px-10">
        <p className="text-right text-sm font-bold uppercase tracking-[0.3em] text-cream/85">{organizer}</p>
        <BrandMark className="h-14 w-14" />
      </header>

      <main className="relative z-10 flex flex-1 flex-col items-center justify-center px-6 py-12 text-center">
        <h1 className="display-title" style={{ fontSize: 'clamp(3.2rem, 12vw, 11.5rem)' }}>
          {lines.map((line, index) => (
            <span key={line} className="block overflow-hidden pb-[0.06em]">
              <motion.span className="block" variants={lineVariants} initial="hidden" animate="visible" custom={index}>
                {line}
              </motion.span>
            </span>
          ))}
        </h1>

        <motion.div
          className="relative mt-4 grid place-items-center"
          initial={{ opacity: 0, scale: 0.7 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.8, type: 'spring', stiffness: 120, damping: 14 }}
        >
          <OrbitRings className="absolute -inset-x-[45%] -inset-y-[120%]" />
          <span
            className="relative flex items-center gap-3 rounded-full bg-cream px-6 py-1 font-extrabold tracking-[0.15em] text-brand shadow-lift sm:px-8 sm:gap-4"
            style={{ fontSize: 'clamp(2rem, 6vw, 5rem)' }}
          >
            <img
              src="/brand/atast-emblem.png"
              alt="ATAST"
              className="h-[1.15em] w-[1.15em] shrink-0 object-contain"
            />
            {year}
          </span>
        </motion.div>

        <motion.div
          className="mt-14 flex flex-wrap justify-center gap-4"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.1, duration: 0.6 }}
        >
          <Button variant="light" size="xl" icon={Rocket} to="/admin">
            Commencer
          </Button>
          <Button variant="outlineLight" size="xl" icon={Trophy} onClick={() => openScreen('leaderboard')}>
            Classement
          </Button>
          <Button variant="outlineLight" size="xl" icon={Tv} onClick={() => openScreen()}>
            Mode écran
          </Button>
        </motion.div>
      </main>

      {leader && (
        <motion.footer
          className="relative z-10 mx-auto mb-8 flex items-center gap-3 rounded-2xl bg-[#1D0F14]/40 px-5 py-3 backdrop-blur"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.5 }}
        >
          <TeamAvatar team={leader} size="sm" />
          <p className="text-left leading-tight">
            <span className="block text-xs font-bold uppercase tracking-[0.3em] text-cream/70">En tête</span>
            <span className="text-lg font-extrabold uppercase">
              {leader.name} · {leader.score} pts
            </span>
          </p>
        </motion.footer>
      )}
    </div>
  );
}
