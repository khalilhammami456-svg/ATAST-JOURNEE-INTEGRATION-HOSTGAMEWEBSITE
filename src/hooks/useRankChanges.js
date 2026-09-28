import { useEffect, useRef, useState } from 'react';

/**
 * Remembers each team's previous rank and returns, for a few seconds,
 * how many positions it moved: { [teamId]: +2 | -1 }.
 */
export function useRankChanges(rankedTeams, visibleMs = 5000) {
  const previousRanks = useRef(null);
  const [changes, setChanges] = useState({});

  useEffect(() => {
    const currentRanks = Object.fromEntries(rankedTeams.map((team, index) => [team.id, index]));
    const previous = previousRanks.current;
    previousRanks.current = currentRanks;
    if (!previous) return undefined;

    const moved = {};
    Object.entries(currentRanks).forEach(([teamId, position]) => {
      if (previous[teamId] !== undefined && previous[teamId] !== position) {
        moved[teamId] = previous[teamId] - position;
      }
    });
    if (Object.keys(moved).length === 0) return undefined;

    setChanges((current) => ({ ...current, ...moved }));
    const timer = setTimeout(() => {
      setChanges((current) => {
        const next = { ...current };
        Object.keys(moved).forEach((teamId) => delete next[teamId]);
        return next;
      });
    }, visibleMs);
    return () => clearTimeout(timer);
  }, [rankedTeams, visibleMs]);

  return changes;
}
