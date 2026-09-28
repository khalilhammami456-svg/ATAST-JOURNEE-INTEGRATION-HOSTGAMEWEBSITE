import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { ArrowDown, ArrowUp } from 'lucide-react';
import TeamAvatar from '../ui/TeamAvatar';
import AnimatedNumber from '../ui/AnimatedNumber';
import ScoreButtons from './ScoreButtons';
import { MEDALS } from '../../utils/ranking';

/** One leaderboard line for the admin: rank, team, live score and the quick +/- buttons. */
export default function QuickScoreRow({ team, rankChange, showButtons = true }) {
  const medal = MEDALS[team.rank];
  return (
    <motion.li
      layout="position"
      transition={{ type: 'spring', stiffness: 420, damping: 38 }}
      className="flex flex-wrap items-center gap-x-4 gap-y-3 rounded-2xl border border-line bg-surface-raised p-3 pr-4"
      style={{ borderLeft: `6px solid ${team.color}` }}
    >
      <span className="w-10 text-center text-2xl font-extrabold tabular" aria-label={`Rang ${team.rank}`}>
        {medal ?? team.rank}
      </span>
      <TeamAvatar team={team} size="sm" />
      <Link
        to={`/admin/teams/${team.id}`}
        className="min-w-[8rem] flex-1 truncate text-lg font-bold uppercase hover:text-brand"
      >
        {team.name}
      </Link>
      {rankChange ? (
        <span
          className={`inline-flex items-center gap-0.5 rounded-full px-2 py-0.5 text-sm font-bold ${
            rankChange > 0 ? 'bg-[#12B886]/15 text-[#0b8a63]' : 'bg-orbit/15 text-[#b25e00]'
          }`}
        >
          {rankChange > 0 ? <ArrowUp size={14} /> : <ArrowDown size={14} />}
          {Math.abs(rankChange)}
        </span>
      ) : null}
      {showButtons ? (
        <ScoreButtons team={team}>
          <span className="w-20 text-center text-2xl font-extrabold">
            <AnimatedNumber value={team.score} />
          </span>
        </ScoreButtons>
      ) : (
        <span className="text-2xl font-extrabold">
          <AnimatedNumber value={team.score} /> <span className="text-sm font-bold text-ink-faint">PTS</span>
        </span>
      )}
    </motion.li>
  );
}
