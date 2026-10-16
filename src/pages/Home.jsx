import { motion } from 'framer-motion';
import { Rocket, Trophy, Tv } from 'lucide-react';
import BrandMark from '../components/ui/BrandMark';
import Button from '../components/ui/Button';
import TeamAvatar from '../components/ui/TeamAvatar';
import { useRankedTeams, useSettings } from '../store/hooks';
import { setDisplayView } from '../store/actions';

const lineVariants = {
  hidden: { y: '110%' },
  visible: (index) => ({ y: 0, transition: { delay: 0.25 + index * 0.18, duration: 0.9, ease: [0.2, 0.9, 0.2, 1] } }),
};

export default function Home() {
  const { organizer } = useSettings();
  const teams = useRankedTeams();
  const leader = teams.find((team) => team.rank === 1 && team.score > 0);
  const lines = ['ATAST', 'Student Section', 'Academy 7.0'];
  const brandText = 'ATAST Student Section Academy 7.0';

  const openScreen = (view) => {
    if (view) setDisplayView(view);
    window.open(`${import.meta.env.BASE_URL}display`, 'journee-integration-display');
  };

  return (
    <div className="relative min-h-screen overflow-hidden bg-[#f8efe6] text-brand-night">
      <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_15%_18%,rgba(244,175,98,0.30),transparent_18%),radial-gradient(circle_at_78%_20%,rgba(98,181,165,0.24),transparent_18%),radial-gradient(circle_at_55%_80%,rgba(214,88,70,0.16),transparent_24%)]" />
      <div className="pointer-events-none absolute -left-12 top-10 h-40 w-40 rounded-full bg-[#f0c26e]/35 blur-3xl" />
      <div className="pointer-events-none absolute -right-8 bottom-10 h-52 w-52 rounded-full bg-[#73bca8]/25 blur-3xl" />

      <main className="relative z-10 mx-auto grid min-h-screen max-w-7xl items-center gap-10 px-6 py-10 lg:grid-cols-[1.05fr_1.2fr] lg:px-10">
        <div className="order-2 flex justify-center lg:order-1 lg:justify-start">
          <div className="orbital-scene">
            <span className="orbit orbit-one" aria-hidden="true" />
            <span className="orbit orbit-two" aria-hidden="true" />
            <span className="orbit orbit-three" aria-hidden="true" />
            <div className="red-sphere">
              <BrandMark className="h-72 w-72 drop-shadow-[0_0_28px_rgba(118,48,30,0.55)] sm:h-80 sm:w-80" />
            </div>
          </div>
        </div>

        <div className="order-1 flex flex-col items-center text-center lg:order-2 lg:items-start lg:text-left">
          <div className="mb-5 inline-flex items-center gap-2 rounded-full border border-[#d8a06d] bg-[#fff7f0]/80 px-4 py-2 text-[0.65rem] font-black uppercase tracking-[0.38em] text-brand-night/80 backdrop-blur-sm">
            {organizer}
          </div>

          <h1 className="display-title max-w-[18ch] text-[clamp(3rem,6vw,7rem)] leading-[0.9] tracking-[-0.06em] text-[#3d1f16]">
            {lines.map((line, index) => (
              <span key={line} className="block overflow-hidden pb-[0.06em]">
                <motion.span className="block" variants={lineVariants} initial="hidden" animate="visible" custom={index}>
                  {line}
                </motion.span>
              </span>
            ))}
          </h1>

          <motion.div
            className="mt-5 flex flex-wrap items-center gap-3"
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.8, duration: 0.5 }}
          >
            <span className="rounded-full border border-[#efb380] bg-[#fff3e8] px-4 py-2 text-xs font-bold uppercase tracking-[0.28em] text-[#8f3a24] shadow-[0_8px_20px_rgba(209,108,68,0.12)]">
              {brandText}
            </span>
          </motion.div>

          <motion.div
            className="mt-8 flex flex-wrap justify-center gap-4 lg:justify-start"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 1.1, duration: 0.6 }}
          >
            <Button variant="primary" size="xl" icon={Rocket} to="/admin">
              Commencer
            </Button>
            <Button variant="secondary" size="xl" icon={Trophy} onClick={() => openScreen('leaderboard')}>
              Classement
            </Button>
            <Button variant="secondary" size="xl" icon={Tv} onClick={() => openScreen()}>
              Mode écran
            </Button>
          </motion.div>
        </div>
      </main>

      {leader && (
        <motion.footer
          className="relative z-10 mx-auto mb-8 flex max-w-3xl items-center gap-3 rounded-2xl border border-[#edcdb2] bg-[#fffaf6]/85 px-5 py-3 shadow-[0_18px_35px_rgba(72,48,35,0.08)] backdrop-blur-md"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 1.5 }}
        >
          <TeamAvatar team={leader} size="sm" />
          <p className="text-left leading-tight">
            <span className="block text-[0.64rem] font-bold uppercase tracking-[0.32em] text-brand-night/70">En tête</span>
            <span className="text-lg font-extrabold uppercase text-brand-night">
              {leader.name} · {leader.score} pts
            </span>
          </p>
        </motion.footer>
      )}
    </div>
  );
}
