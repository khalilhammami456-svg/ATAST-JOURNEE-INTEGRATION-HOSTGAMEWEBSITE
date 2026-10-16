import { motion } from 'framer-motion';
import { Gamepad2 } from 'lucide-react';
import { useAppState } from '../../store/hooks';
import { useIsCompactScreen } from '../../hooks/useMediaQuery';

function columnsFor(count) {
  if (count <= 2) return count;
  if (count <= 6) return 3;
  if (count <= 8) return 4;
  return 5;
}

/** "Mini-jeux": every game from the admin Mini-jeux list, so participants can pick one themselves. */
export default function DisplayGames() {
  const { games } = useAppState();
  const compact = useIsCompactScreen();

  if (games.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center gap-[2vh] text-center text-cream">
        <Gamepad2 className="h-[10vh] w-[10vh] opacity-80" strokeWidth={1.8} />
        <p className="display-title" style={{ fontSize: 'clamp(2rem, 7vh, 6rem)' }}>
          Mini-jeux
        </p>
        <p className="font-semibold text-cream/80" style={{ fontSize: 'clamp(1rem, 3vh, 2rem)' }}>
          Les épreuves arrivent bientôt…
        </p>
      </div>
    );
  }

  const columns = compact ? 2 : columnsFor(games.length);
  const rows = Math.ceil(games.length / columns);

  return (
    <div className={`flex h-full flex-col px-[4vw] pb-[3vh] ${compact ? 'overflow-y-auto pb-24' : ''}`}>
      <h1 className="display-title mb-[2.5vh] text-center text-cream" style={{ fontSize: 'clamp(2.5rem, 8vh, 7rem)' }}>
        Mini-jeux
      </h1>
      <div
        className={`grid gap-[1.6vw] ${compact ? 'gap-3' : 'min-h-0 flex-1'}`}
        style={{
          gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))`,
          gridTemplateRows: compact ? `repeat(${rows}, auto)` : `repeat(${rows}, minmax(0, 1fr))`,
        }}
      >
        {games.map((game, index) => (
          <motion.article
            key={game.id}
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
            className="relative flex min-h-0 flex-col items-center justify-center overflow-hidden rounded-[2.2vh] bg-cream px-[1.2vw] py-[2vh] text-center text-[#1D0F14]"
            style={{ boxShadow: '0 16px 40px -18px rgba(0,0,0,.6)' }}
          >
            <span style={{ fontSize: 'clamp(2rem, 6vh, 4.5rem)' }}>{game.emoji ?? '🎮'}</span>
            <h2
              className="mt-[1vh] w-full font-extrabold uppercase leading-tight"
              style={{ fontSize: 'clamp(1rem, 2.8vh, 2rem)' }}
            >
              {game.name}
            </h2>
            {game.description && (
              <p
                className="mt-[0.8vh] line-clamp-3 font-semibold text-[#1D0F14]/70"
                style={{ fontSize: 'clamp(0.75rem, 1.7vh, 1.2rem)' }}
              >
                {game.description}
              </p>
            )}
            {game.maxPoints && (
              <p
                className="mt-[1vh] rounded-full bg-brand/10 px-[1vw] py-[0.4vh] font-extrabold uppercase tracking-wider text-brand"
                style={{ fontSize: 'clamp(0.7rem, 1.5vh, 1.1rem)' }}
              >
                Max {game.maxPoints} pts
              </p>
            )}
          </motion.article>
        ))}
      </div>
    </div>
  );
}
