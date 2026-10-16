import { motion } from 'framer-motion';
import { Users } from 'lucide-react';
import TeamAvatar from '../ui/TeamAvatar';
import AnimatedNumber from '../ui/AnimatedNumber';
import { useRankedTeams } from '../../store/hooks';
import { PLACE_COLORS } from '../../utils/ranking';
import DisplayEmpty from './DisplayEmpty';
import { useIsCompactScreen } from '../../hooks/useMediaQuery';

function columnsFor(count) {
  if (count <= 3) return count;
  if (count <= 4) return 4;
  if (count <= 8) return 4;
  if (count <= 10) return 5;
  if (count <= 12) return 4;
  return 6;
}

/** "Tous les groupes": one card per team, ordered by rank. */
export default function DisplayTeams() {
  const teams = useRankedTeams();
  const compact = useIsCompactScreen();
  if (teams.length === 0) return <DisplayEmpty />;

  const columns = compact ? 2 : columnsFor(teams.length);
  const rows = Math.ceil(teams.length / columns);

  return (
    <div className={`flex h-full flex-col px-[4vw] pb-[3vh] ${compact ? 'overflow-y-auto pb-24' : ''}`}>
      <h1 className="display-title mb-[2.5vh] text-center text-cream" style={{ fontSize: 'clamp(2.5rem, 8vh, 7rem)' }}>
        Les équipes
      </h1>
      <div
        className={`grid gap-[1.6vw] ${compact ? 'gap-3' : 'min-h-0 flex-1'}`}
        style={{
          gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
          gridTemplateRows: compact ? `repeat(${rows}, 15rem)` : `repeat(${rows}, minmax(0, 1fr))`,
        }}
      >
        {teams.map((team, index) => {
          const podium = PLACE_COLORS[team.rank];
          return (
            <motion.article
              key={team.id}
              layout
              initial={{ opacity: 0, y: 40, scale: 0.9 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              transition={{
                layout: { type: 'spring', stiffness: 160, damping: 22 },
                delay: index * 0.05,
                type: 'spring',
                stiffness: 220,
                damping: 22,
              }}
              className="relative flex min-h-0 flex-col items-center justify-center overflow-hidden rounded-[2.2vh] bg-cream px-[1vw] py-[1.5vh] text-center text-[#1D0F14]"
              style={{ boxShadow: `0 16px 40px -18px rgba(0,0,0,.6), inset 0 0.8vh 0 0 ${team.color}` }}
            >
              <svg
                className="pointer-events-none absolute -right-[20%] -top-[25%] h-[80%] w-[80%] opacity-[0.12]"
                viewBox="0 0 100 100"
                aria-hidden="true"
              >
                <path
                  d="M0 70 C 30 70, 55 50, 60 0"
                  stroke={team.color}
                  strokeWidth="12"
                  fill="none"
                  strokeLinecap="round"
                />
              </svg>
              <span
                className="absolute left-[1vw] top-[1.6vh] rounded-full px-[0.7vw] py-[0.2vh] font-extrabold tabular"
                style={{
                  fontSize: 'clamp(0.8rem, 2vh, 1.6rem)',
                  backgroundColor: podium ?? 'rgb(var(--brand) / 0.1)',
                  color: podium ? '#1D0F14' : 'rgb(var(--brand))',
                }}
              >
                #{String(team.rank).padStart(2, '0')}
              </span>
              <TeamAvatar team={team} size="lg" className="!h-[28%] !w-auto aspect-square !text-[3.2vh]" />
              <h2
                className="mt-[1vh] w-full truncate font-extrabold uppercase leading-none"
                style={{ fontSize: 'clamp(1rem, 3.2vh, 2.6rem)' }}
              >
                {team.name}
              </h2>
              <p
                className="mt-[0.6vh] font-extrabold leading-none"
                style={{ fontSize: 'clamp(1.8rem, 7vh, 6rem)', color: team.color }}
              >
                <AnimatedNumber value={team.score} flash={false} />
              </p>
              <p
                className="font-bold tracking-[0.35em] text-[#1D0F14]/55"
                style={{ fontSize: 'clamp(0.7rem, 1.6vh, 1.2rem)' }}
              >
                POINTS
              </p>
              <p
                className="mt-[0.8vh] flex items-center gap-[0.4vw] font-bold text-[#1D0F14]/60"
                style={{ fontSize: 'clamp(0.8rem, 1.9vh, 1.4rem)' }}
              >
                <Users className="h-[1em] w-[1em]" /> {team.participantCount} participants
              </p>
            </motion.article>
          );
        })}
      </div>
    </div>
  );
}
