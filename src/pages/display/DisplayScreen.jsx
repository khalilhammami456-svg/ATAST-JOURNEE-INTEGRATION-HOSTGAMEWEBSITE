import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Gamepad2, LayoutGrid, ListOrdered, Maximize, Minimize, Trophy } from 'lucide-react';
import StageBackground from '../../components/display/StageBackground';
import Podium from '../../components/display/Podium';
import DisplayLeaderboard from '../../components/display/DisplayLeaderboard';
import DisplayTeams from '../../components/display/DisplayTeams';
import DisplayGames from '../../components/display/DisplayGames';
import LiveEventOverlay from '../../components/display/LiveEventOverlay';
import BrandMark from '../../components/ui/BrandMark';
import { useAppState } from '../../store/hooks';
import { setDisplayView, startPodiumCeremony } from '../../store/actions';
import { useFullscreen } from '../../hooks/useFullscreen';
import { useKeyboardShortcuts } from '../../hooks/useKeyboardShortcuts';

const VIEWS = [
  { id: 'podium', label: 'Podium', icon: Trophy, key: 'P' },
  { id: 'leaderboard', label: 'Classement', icon: ListOrdered, key: 'L' },
  { id: 'teams', label: 'Équipes', icon: LayoutGrid, key: 'E' },
  { id: 'games', label: 'Mini-jeux', icon: Gamepad2, key: 'G' },
];

/** Hides the cursor and controls after a few seconds without mouse movement. */
function useIdle(timeoutMs = 3000) {
  const [idle, setIdle] = useState(false);
  useEffect(() => {
    let timer;
    const wake = () => {
      setIdle(false);
      clearTimeout(timer);
      timer = setTimeout(() => setIdle(true), timeoutMs);
    };
    wake();
    window.addEventListener('mousemove', wake);
    window.addEventListener('touchstart', wake);
    window.addEventListener('keydown', wake);
    return () => {
      clearTimeout(timer);
      window.removeEventListener('mousemove', wake);
      window.removeEventListener('touchstart', wake);
      window.removeEventListener('keydown', wake);
    };
  }, [timeoutMs]);
  return idle;
}

function Clock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = setInterval(() => setNow(new Date()), 15_000);
    return () => clearInterval(timer);
  }, []);
  return <span className="tabular">{now.toLocaleTimeString('fr-FR', { hour: '2-digit', minute: '2-digit' })}</span>;
}

export default function DisplayScreen() {
  const { display, settings } = useAppState();
  const { isFullscreen, toggle: toggleFullscreen } = useFullscreen();
  const idle = useIdle();
  const view = VIEWS.some((item) => item.id === display.view) ? display.view : 'leaderboard';

  const selectView = (id) => (id === 'podium' ? startPodiumCeremony() : setDisplayView(id));

  useKeyboardShortcuts({
    p: () => startPodiumCeremony(),
    r: () => startPodiumCeremony(),
    l: () => setDisplayView('leaderboard'),
    e: () => setDisplayView('teams'),
    g: () => setDisplayView('games'),
    f: toggleFullscreen,
  });

  return (
    <div
      className={`on-brand relative h-screen w-screen overflow-hidden font-sans text-cream ${idle ? 'cursor-none' : ''}`}
    >
      <StageBackground dramatic={view === 'podium'} />

      <header className="relative z-20 flex h-[11vh] items-center justify-between px-[3vw]">
        <div className="flex items-center gap-[1vw]">
          <BrandMark className="h-[7vh] w-[7vh]" padding="p-[0.6vh]" />
          <div className="leading-none">
            <p className="font-extrabold uppercase" style={{ fontSize: 'clamp(1rem, 3vh, 2.4rem)' }}>
              {settings.eventName}
            </p>
            <p
              className="mt-[0.5vh] hidden font-bold uppercase tracking-[0.3em] text-cream/70 sm:block"
              style={{ fontSize: 'clamp(0.7rem, 1.7vh, 1.3rem)' }}
            >
              {settings.organizer} · {settings.year}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-[1.2vw] font-bold" style={{ fontSize: 'clamp(0.9rem, 2.4vh, 1.9rem)' }}>
          <span className="flex items-center gap-[0.5vw] whitespace-nowrap rounded-full bg-cream/15 px-[1vw] py-[0.5vh] uppercase tracking-widest">
            <span className="relative flex h-[1.2vh] w-[1.2vh] min-h-[8px] min-w-[8px]">
              <span className="absolute inset-0 animate-ping rounded-full bg-cream opacity-70" />
              <span className="relative h-full w-full rounded-full bg-cream" />
            </span>
            En direct
          </span>
          <span className="hidden sm:inline">
            <Clock />
          </span>
        </div>
      </header>

      <main className="relative z-10 h-[89vh]">
        <AnimatePresence mode="wait">
          <motion.div
            key={view}
            className="h-full"
            initial={{ opacity: 0, y: 30 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -30 }}
            transition={{ duration: 0.45, ease: [0.3, 0.7, 0.2, 1] }}
          >
            {view === 'podium' && <Podium runKey={display.podiumRun} />}
            {view === 'leaderboard' && <DisplayLeaderboard />}
            {view === 'teams' && <DisplayTeams />}
            {view === 'games' && <DisplayGames />}
          </motion.div>
        </AnimatePresence>
      </main>

      <LiveEventOverlay enabled={view !== 'podium'} />

      <nav
        className={`absolute inset-x-0 bottom-[2vh] z-30 flex justify-center transition-all duration-500 ${
          idle ? 'pointer-events-none translate-y-6 opacity-0' : 'opacity-100'
        }`}
        aria-label="Vues de l'écran public"
      >
        <div className="flex items-center gap-1 rounded-2xl bg-[#1D0F14]/75 p-1.5 shadow-lift backdrop-blur">
          {VIEWS.map(({ id, label, icon: Icon, key }) => (
            <button
              key={id}
              type="button"
              onClick={() => selectView(id)}
              aria-pressed={view === id}
              className={`flex h-12 items-center gap-2 rounded-xl px-5 font-extrabold uppercase tracking-wide transition ${
                view === id ? 'bg-cream text-brand' : 'text-cream/80 hover:bg-cream/10 hover:text-cream'
              }`}
            >
              <Icon size={20} />
              <span className="hidden sm:inline">{label}</span>
              <kbd className="ml-1 hidden rounded bg-black/15 px-1.5 text-xs opacity-70 md:inline">{key}</kbd>
            </button>
          ))}
          <span className="mx-1 h-8 w-px bg-cream/20" />
          <button
            type="button"
            onClick={toggleFullscreen}
            className="grid h-12 w-12 place-items-center rounded-xl text-cream/80 hover:bg-cream/10 hover:text-cream"
            aria-label={isFullscreen ? 'Quitter le plein écran' : 'Plein écran'}
            title="Plein écran (F)"
          >
            {isFullscreen ? <Minimize size={20} /> : <Maximize size={20} />}
          </button>
        </div>
      </nav>
    </div>
  );
}
