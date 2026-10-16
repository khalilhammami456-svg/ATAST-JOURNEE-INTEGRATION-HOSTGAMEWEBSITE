import { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { Crown } from 'lucide-react';
import TeamAvatar from '../ui/TeamAvatar';
import OrbitRings from '../ui/OrbitRings';
import { useAnimatedNumber } from '../../hooks/useAnimatedNumber';
import { useRankedTeams, useSettings } from '../../store/hooks';
import { PLACE_COLORS, PLACE_LABELS } from '../../utils/ranking';
import { formatPoints } from '../../utils/format';
import { celebrationConfetti } from '../../utils/confetti';
import { playSound } from '../../utils/sound';
import DisplayEmpty from './DisplayEmpty';

/*
 * Ceremony phases:
 *   0 intro → 1 third place → 2 second place → 3 suspense → 4 champion + confetti
 */
const PHASE_DELAYS = [1900, 2000, 2000, 2300];
const FINAL_PHASE = 4;

const BLOCK_HEIGHTS = { 1: '36vh', 2: '26vh', 3: '19vh' };
const NUMBER_SIZES = { 1: '18vh', 2: '13vh', 3: '10vh' };
const REVEAL_PHASE = { 3: 1, 2: 2, 1: 4 };

function useCeremony(runKey, animations) {
  const [phase, setPhase] = useState(animations ? 0 : FINAL_PHASE);

  useEffect(() => {
    if (!animations) {
      setPhase(FINAL_PHASE);
      return undefined;
    }
    setPhase(0);
    let elapsed = 0;
    const timers = PHASE_DELAYS.map((delay, index) => {
      elapsed += delay;
      return setTimeout(() => setPhase(index + 1), elapsed);
    });
    return () => timers.forEach(clearTimeout);
  }, [runKey, animations]);

  return phase;
}

function CountUp({ value, active }) {
  const displayed = useAnimatedNumber(active ? value : 0, 1400);
  return <span className="tabular">{formatPoints(displayed)}</span>;
}

function PodiumColumn({ place, team, revealed, champion }) {
  const color = PLACE_COLORS[place];
  const height = BLOCK_HEIGHTS[place];

  return (
    <div
      className={`relative flex h-full flex-col items-center justify-end ${place === 1 ? 'w-[30vw] z-10' : 'w-[24vw]'}`}
    >
      <AnimatePresence>
        {revealed && team && (
          <motion.div
            key={team.id}
            className="relative mb-[2.4vh] flex w-full flex-col items-center text-center text-cream"
            initial={{ opacity: 0, y: 60, scale: 0.6 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ type: 'spring', stiffness: 160, damping: 16, delay: 0.35 }}
          >
            {champion && (
              <motion.p
                className="display-title mb-[1.4vh] flex items-center gap-[0.8vw] bg-[linear-gradient(90deg,#FFC83D,#FFF3C4,#FFC83D)] bg-[length:200%_100%] bg-clip-text text-transparent animate-shine"
                style={{ fontSize: 'min(7.5vh, 6.5vw)' }}
                initial={{ opacity: 0, scale: 2.2, letterSpacing: '0.4em' }}
                animate={{ opacity: 1, scale: 1, letterSpacing: '0.02em' }}
                transition={{ duration: 0.9, ease: [0.2, 0.9, 0.3, 1.2], delay: 0.6 }}
              >
                <Crown className="h-[0.8em] w-[0.8em] text-gold" strokeWidth={2.4} />
                {team.rank === 1 ? 'Champion' : PLACE_LABELS[place]}
              </motion.p>
            )}
            <div className="relative grid place-items-center">
              {champion && (
                <>
                  <OrbitRings className="absolute -inset-[42%]" color="#FFC83D" />
                  <span className="absolute inset-0 rounded-[2.5rem] bg-gold/60 animate-pulse-ring" />
                </>
              )}
              <TeamAvatar
                team={team}
                size={champion ? '2xl' : 'xl'}
                ring
                className={
                  champion
                    ? '!h-[min(17vh,22vw)] !w-[min(17vh,22vw)] !text-[min(6vh,8vw)]'
                    : '!h-[min(12vh,16vw)] !w-[min(12vh,16vw)] !text-[min(4.2vh,5.5vw)]'
                }
              />
            </div>
            <p
              className="mt-[1.8vh] w-full truncate px-[0.5vw] font-extrabold uppercase leading-none tracking-tight drop-shadow-[0_4px_10px_rgba(0,0,0,.35)]"
              style={{ fontSize: champion ? 'min(7vh, 5vw)' : 'min(4.4vh, 3.4vw)' }}
            >
              {team.name}
            </p>
            <p
              className="mt-[0.8vh] font-extrabold leading-none"
              style={{ fontSize: champion ? 'min(6vh, 5vw)' : 'min(4vh, 3.4vw)', color }}
            >
              <CountUp value={team.score} active={revealed} />
              <span className="ml-[0.5vw] text-[0.45em] tracking-[0.2em] text-cream/80">POINTS</span>
            </p>
            {team.rank < place && (
              <span
                className="mt-[1vh] rounded-full bg-gold px-[0.8vw] py-[0.3vh] font-extrabold uppercase text-[#1D0F14]"
                style={{ fontSize: 'clamp(0.8rem, 2vh, 1.5rem)' }}
              >
                Ex æquo · {team.rank === 1 ? '1er' : `${team.rank}e`}
              </span>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.div
        className="relative w-full overflow-hidden rounded-t-[2vh]"
        style={{
          height,
          transformOrigin: 'bottom',
          background: `linear-gradient(180deg, #FFFFFF 0%, #F8F3EC 60%, #E9DED2 100%)`,
          boxShadow: `inset 0 1.2vh 0 0 ${color}, 0 -10px 60px -20px ${revealed ? color : 'transparent'}`,
        }}
        initial={{ scaleY: 0 }}
        animate={{ scaleY: revealed ? 1 : 0.12 }}
        transition={{ type: 'spring', stiffness: 120, damping: 18 }}
      >
        <span
          className={`absolute inset-x-0 top-[2vh] text-center font-extrabold leading-none transition-opacity duration-500 ${revealed ? 'opacity-100' : 'opacity-0'}`}
          style={{
            fontSize: `min(${NUMBER_SIZES[place]}, ${parseFloat(NUMBER_SIZES[place]) * 0.9}vw)`,
            color: 'rgb(var(--brand))',
          }}
        >
          {place}
        </span>
        <span
          className={`absolute inset-x-0 bottom-[2vh] text-center font-bold uppercase tracking-[0.3em] text-[#1D0F14]/55 transition-opacity duration-500 ${revealed ? 'opacity-100' : 'opacity-0'}`}
          style={{ fontSize: 'clamp(0.7rem, 1.8vh, 1.4rem)' }}
        >
          {PLACE_LABELS[place]}
        </span>
      </motion.div>
    </div>
  );
}

export default function Podium({ runKey }) {
  const teams = useRankedTeams();
  const { animations, confetti, sound, eventName, year } = useSettings();
  const phase = useCeremony(runKey, animations);
  const [first, second, third] = teams;

  useEffect(() => {
    if (sound && (phase === 1 || phase === 2)) playSound('reveal');
    if (phase === FINAL_PHASE) {
      if (sound && animations) playSound('victory');
      if (confetti) {
        const timer = setTimeout(() => celebrationConfetti(3600), animations ? 500 : 0);
        return () => clearTimeout(timer);
      }
    }
    return undefined;
  }, [phase]); // eslint-disable-line react-hooks/exhaustive-deps

  if (teams.length === 0) return <DisplayEmpty />;

  const revealed = (place) => phase >= REVEAL_PHASE[place];
  const championPhase = phase === FINAL_PHASE;

  return (
    <div className="relative flex h-full flex-col">
      {/* spotlight beams behind the champion */}
      <motion.div
        className="pointer-events-none absolute inset-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: championPhase ? 1 : phase >= 1 ? 0.35 : 0 }}
        transition={{ duration: 1.2 }}
        style={{
          background:
            'conic-gradient(from 180deg at 50% -10%, transparent 160deg, rgba(255,243,196,.28) 172deg, transparent 180deg, rgba(255,243,196,.22) 188deg, transparent 200deg)',
        }}
        aria-hidden="true"
      />
      <motion.div
        className="pointer-events-none absolute left-1/2 top-[18%] h-[60vh] w-[60vh] -translate-x-1/2 rounded-full"
        style={{ background: 'radial-gradient(circle, rgba(255,200,61,.35), transparent 65%)' }}
        initial={{ opacity: 0, scale: 0.5 }}
        animate={{ opacity: championPhase ? 1 : 0, scale: championPhase ? 1 : 0.5 }}
        transition={{ duration: 1.4 }}
        aria-hidden="true"
      />

      <AnimatePresence mode="wait">
        {phase === 0 && (
          <motion.div
            key="intro"
            className="absolute inset-0 z-20 flex flex-col items-center justify-center text-center text-cream"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0, scale: 1.1 }}
          >
            <motion.p
              className="font-bold uppercase tracking-[0.5em] text-cream/80"
              style={{ fontSize: 'clamp(1rem, 3vh, 2.4rem)' }}
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
            >
              {eventName} {year}
            </motion.p>
            <motion.h1
              className="display-title mt-[2vh]"
              style={{ fontSize: 'clamp(3rem, 16vh, 14rem)' }}
              initial={{ scale: 0.6, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ type: 'spring', stiffness: 140, damping: 14, delay: 0.2 }}
            >
              Le podium
            </motion.h1>
          </motion.div>
        )}
        {phase === 3 && (
          <motion.div
            key="suspense"
            className="absolute inset-x-0 top-[22%] z-20 flex justify-center text-center text-cream"
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: [1, 1.06, 1, 1.06, 1] }}
            exit={{ opacity: 0, scale: 1.3 }}
            transition={{ scale: { duration: 2.2, ease: 'easeInOut' } }}
          >
            <p className="display-title" style={{ fontSize: 'clamp(2.4rem, 9vh, 8rem)' }}>
              Et le champion est…
            </p>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="relative z-10 mt-auto flex h-full items-end justify-center gap-[1.2vw] px-[4vw]">
        <PodiumColumn place={2} team={second} revealed={revealed(2)} />
        <PodiumColumn place={1} team={first} revealed={revealed(1)} champion />
        <PodiumColumn place={3} team={third} revealed={revealed(3)} />
      </div>
    </div>
  );
}
