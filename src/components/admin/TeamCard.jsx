import { Link } from 'react-router-dom';
import { motion } from 'framer-motion';
import { Users } from 'lucide-react';
import TeamAvatar from '../ui/TeamAvatar';
import AnimatedNumber from '../ui/AnimatedNumber';
import ScoreButtons from './ScoreButtons';

/** Admin team card: identity, live score and quick buttons; the whole header links to the team page. */
export default function TeamCard({ team }) {
  return (
    <motion.article
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      className="card relative overflow-hidden"
      style={{ borderTop: `6px solid ${team.color}` }}
    >
      <Link to={`/admin/teams/${team.id}`} className="block p-5 pb-3 transition hover:bg-surface-sunken/40">
        <div className="flex items-start justify-between">
          <span className="text-sm font-extrabold tracking-widest text-ink-faint tabular">
            #{String(team.rank).padStart(2, '0')}
          </span>
          <span className="inline-flex items-center gap-1 text-sm font-bold text-ink-soft">
            <Users size={15} /> {team.participantCount}
          </span>
        </div>
        <div className="mt-2 flex flex-col items-center text-center">
          <TeamAvatar team={team} size="lg" />
          <h3 className="mt-3 w-full truncate text-xl font-extrabold uppercase">{team.name}</h3>
          <p className="mt-1 text-5xl font-extrabold leading-none" style={{ color: team.color }}>
            <AnimatedNumber value={team.score} flash={false} />
          </p>
          <p className="text-xs font-bold uppercase tracking-[0.3em] text-ink-faint">points</p>
        </div>
      </Link>
      <div className="flex justify-center overflow-x-auto border-t border-line bg-surface-sunken/50 px-2 py-3">
        <ScoreButtons team={team} size="sm" />
      </div>
    </motion.article>
  );
}
