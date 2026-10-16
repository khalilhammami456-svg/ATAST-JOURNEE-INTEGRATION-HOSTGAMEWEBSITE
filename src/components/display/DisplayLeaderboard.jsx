import { useEffect, useRef, useState } from 'react';
import { motion } from 'framer-motion';
import { ArrowDown, ArrowUp, Trophy } from 'lucide-react';
import TeamAvatar from '../ui/TeamAvatar';
import AnimatedNumber from '../ui/AnimatedNumber';
import { useRankedTeams } from '../../store/hooks';
import { useRankChanges } from '../../hooks/useRankChanges';
import { PLACE_COLORS } from '../../utils/ranking';
import DisplayEmpty from './DisplayEmpty';
import { useIsCompactScreen } from '../../hooks/useMediaQuery';

/** Briefly returns true for teams whose score just changed, to trigger a glow. */
function useRecentlyChanged(teams, durationMs = 2200) {
  const previousScores = useRef(null);
  const [changed, setChanged] = useState({});

  useEffect(() => {
    const scores = Object.fromEntries(teams.map((team) => [team.id, team.score]));
    const previous = previousScores.current;
    previousScores.current = scores;
    if (!previous) return undefined;
    const ids = teams
      .filter((team) => previous[team.id] !== undefined && previous[team.id] !== team.score)
      .map((team) => team.id);
    if (ids.length === 0) return undefined;
    setChanged((current) => ({ ...current, ...Object.fromEntries(ids.map((id) => [id, Date.now()])) }));
    const timer = setTimeout(
      () =>
        setChanged((current) => {
          const next = { ...current };
          ids.forEach((id) => delete next[id]);
          return next;
        }),
      durationMs,
    );
    return () => clearTimeout(timer);
  }, [teams, durationMs]);

  return changed;
}

function RankBadge({ rank }) {
  const podiumColor = PLACE_COLORS[rank];
  return (
    <span
      className="grid aspect-square h-[78%] shrink-0 place-items-center rounded-[28%] font-extrabold tabular"
      style={{
        backgroundColor: podiumColor ?? 'rgb(var(--brand) / 0.12)',
        color: podiumColor ? '#1D0F14' : 'rgb(var(--brand))',
        fontSize: 'clamp(1.1rem, 3.4vh, 2.6rem)',
      }}
    >
      {rank}
    </span>
  );
}

export default function DisplayLeaderboard() {
  const teams = useRankedTeams();
  const rankChanges = useRankChanges(teams);
  const recentlyChanged = useRecentlyChanged(teams);
  const compact = useIsCompactScreen();

  if (teams.length === 0) return <DisplayEmpty />;

  const twoColumns = !compact && teams.length > 10;
  const rowsPerColumn = twoColumns ? Math.ceil(teams.length / 2) : teams.length;
  const topScore = Math.max(1, teams[0].score);

  return (
    <div className={`flex h-full flex-col px-[4vw] pb-[3vh] ${compact ? 'overflow-y-auto pb-24' : ''}`}>
      <h1
        className="display-title mb-[2.5vh] flex items-center justify-center gap-[1.5vw] text-cream"
        style={{ fontSize: 'clamp(2.5rem, 8vh, 7rem)' }}
      >
        <Trophy className="h-[0.8em] w-[0.8em] text-gold" strokeWidth={2.4} />
        Classement
      </h1>

      <ol
        className={`grid gap-x-[2vw] ${compact ? '' : 'min-h-0 flex-1'}`}
        style={{
          gridTemplateRows: compact ? `repeat(${rowsPerColumn}, 4.5rem)` : `repeat(${rowsPerColumn}, minmax(0, 1fr))`,
          gridAutoFlow: 'column',
          gridTemplateColumns: twoColumns ? 'repeat(2, minmax(0, 1fr))' : 'minmax(0, 1fr)',
          rowGap: teams.length > 8 ? '1vh' : '1.4vh',
          maxHeight: compact || twoColumns || teams.length > 6 ? undefined : `${teams.length * 13}vh`,
        }}
      >
        {teams.map((team, index) => {
          const change = rankChanges[team.id];
          const glowing = Boolean(recentlyChanged[team.id]);
          const isLeader = team.rank === 1 && team.score > 0;
          return (
            <motion.li
              key={team.id}
              layout
              initial={{ opacity: 0, x: -60 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{
                layout: { type: 'spring', stiffness: 170, damping: 24 },
                opacity: { delay: index * 0.06 },
                x: { delay: index * 0.06, type: 'spring', stiffness: 200, damping: 24 },
              }}
              className="relative flex min-h-0 items-center gap-[1.4vw] overflow-hidden rounded-[1.4vh] bg-cream px-[1.2vw] text-[#1D0F14]"
              style={{
                boxShadow: glowing
                  ? `0 0 0 4px ${team.color}, 0 0 48px 8px ${team.color}aa`
                  : isLeader
                    ? '0 0 0 4px #FFC83D, 0 12px 30px -12px rgba(0,0,0,.5)'
                    : '0 10px 26px -14px rgba(0,0,0,.55)',
                transition: 'box-shadow .6s ease',
              }}
            >
              <span
                className="absolute inset-y-0 left-0 w-[0.6vw] min-w-[6px]"
                style={{ backgroundColor: team.color }}
              />
              <RankBadge rank={team.rank} />
              <TeamAvatar team={team} size="sm" className="!h-[70%] !w-auto aspect-square !text-[2.2vh]" />
              <div className="flex min-w-0 flex-1 flex-col justify-center gap-[0.6vh]">
                <p
                  className="truncate font-extrabold uppercase leading-none tracking-tight"
                  style={{ fontSize: 'clamp(1.1rem, 3.6vh, 3rem)' }}
                >
                  {team.name}
                </p>
                <div className="h-[0.9vh] min-h-[5px] w-full max-w-[40vw] overflow-hidden rounded-full bg-[#1D0F14]/10">
                  <motion.div
                    className="h-full rounded-full"
                    style={{ backgroundColor: team.color }}
                    initial={{ width: 0 }}
                    animate={{ width: `${(team.score / topScore) * 100}%` }}
                    transition={{ duration: 1, ease: 'easeOut' }}
                  />
                </div>
              </div>
              {change ? (
                <motion.span
                  initial={{ scale: 0, opacity: 0 }}
                  animate={{ scale: 1, opacity: 1 }}
                  className={`flex items-center gap-1 rounded-full px-[0.9vw] py-[0.4vh] font-extrabold text-white ${change > 0 ? 'bg-[#12B886]' : 'bg-orbit'}`}
                  style={{ fontSize: 'clamp(0.9rem, 2.2vh, 1.7rem)' }}
                >
                  {change > 0 ? (
                    <ArrowUp className="h-[1em] w-[1em]" strokeWidth={3} />
                  ) : (
                    <ArrowDown className="h-[1em] w-[1em]" strokeWidth={3} />
                  )}
                  {change > 0 ? `+${change}` : change} position{Math.abs(change) > 1 ? 's' : ''}
                </motion.span>
              ) : null}
              <p
                className="shrink-0 text-right font-extrabold leading-none tabular"
                style={{ fontSize: 'clamp(1.4rem, 5vh, 4.2rem)' }}
              >
                <AnimatedNumber value={team.score} />
                <span className="ml-[0.4vw] align-middle text-[0.4em] font-bold tracking-widest text-[#1D0F14]/50">
                  PTS
                </span>
              </p>
            </motion.li>
          );
        })}
      </ol>
    </div>
  );
}
