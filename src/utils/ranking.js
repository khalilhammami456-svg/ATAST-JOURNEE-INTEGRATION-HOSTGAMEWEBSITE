/**
 * Standard competition ranking: equal scores share a rank, the next rank skips.
 * 250, 250, 220 → 1, 1, 3
 */
export function rankTeams(teams) {
  const sorted = [...teams].sort(
    (a, b) => b.score - a.score || a.name.localeCompare(b.name, 'fr', { sensitivity: 'base' }),
  );
  let previousScore = null;
  let previousRank = 0;
  return sorted.map((team, index) => {
    const rank = team.score === previousScore ? previousRank : index + 1;
    previousScore = team.score;
    previousRank = rank;
    return { ...team, rank };
  });
}

export const leaderIds = (rankedTeams) =>
  rankedTeams.filter((team) => team.rank === 1 && team.score > 0).map((team) => team.id);

export const MEDALS = { 1: '🥇', 2: '🥈', 3: '🥉' };

export const PLACE_LABELS = {
  1: 'Première place',
  2: 'Deuxième place',
  3: 'Troisième place',
};

export const PLACE_COLORS = { 1: '#FFC83D', 2: '#D9DEE8', 3: '#E08A4F' };
