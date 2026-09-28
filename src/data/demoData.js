import { createId } from '../utils/id';

export const DEFAULT_SETTINGS = {
  eventName: "Journée d'Intégration",
  year: 2026,
  organizer: 'ATAST Student Section · ISIMM',
  logo: null,
  primaryColor: '#C4073D',
  darkMode: false,
  animations: true,
  confetti: true,
  sound: true,
};

const DEMO_TEAMS = [
  {
    name: 'Team Phoenix',
    avatar: 'flame',
    color: '#F5921E',
    members: ['Ahmed Ben Ali', 'Yassine Trabelsi', 'Mariem Gharbi', 'Ines Jaziri', 'Mohamed Ayari', 'Rania Chaabane'],
  },
  {
    name: 'Team Titans',
    avatar: 'mountain',
    color: '#1F6FE0',
    members: ['Oussema Mejri', 'Salma Ferchichi', 'Hamza Bouzid', 'Nour Hammami', 'Aziz Khelifi'],
  },
  {
    name: 'Team Wolves',
    avatar: 'moon',
    color: '#2E3A59',
    members: ['Karim Saidi', 'Emna Dridi', 'Wassim Rekik', 'Chaima Mabrouk', 'Firas Jlassi', 'Lina Oueslati'],
  },
  {
    name: 'Team Eagles',
    avatar: 'bird',
    color: '#8B3DFF',
    members: ['Skander Mansouri', 'Molka Brahmi', 'Iheb Sassi', 'Farah Kallel', 'Bilel Nasri'],
  },
  {
    name: 'Team Cobras',
    avatar: 'zap',
    color: '#12B886',
    members: ['Achref Guesmi', 'Syrine Hadded', 'Mehdi Zouari', 'Asma Hamdi', 'Rayen Belhadj', 'Eya Toumi'],
  },
  {
    name: 'Team Dragons',
    avatar: 'castle',
    color: '#E03131',
    members: ['Taha Boughanmi', 'Yasmine Chebbi', 'Houssem Arfaoui', 'Dorsaf Laabidi', 'Ghassen Kacem'],
  },
  {
    name: 'Team Stars',
    avatar: 'star',
    color: '#FFC83D',
    members: ['Amine Jebali', 'Rahma Ghanmi', 'Nader Ouni', 'Sirine Belaid', 'Malek Chouchane', 'Hiba Nefzi'],
  },
  {
    name: 'Team Falcons',
    avatar: 'feather',
    color: '#00B4D8',
    members: ['Seif Mahjoub', 'Meriem Baccouche', 'Anis Hlaoui', 'Olfa Jouini', 'Zied Ben Amor'],
  },
];

const DEMO_GAMES = [
  {
    name: 'Quiz musical',
    emoji: '🎵',
    description: 'Un quiz de 20 questions sur les tubes d’hier et d’aujourd’hui.',
    maxPoints: 50,
  },
  { name: 'Course relais', emoji: '🏃', description: 'Relais à 4 dans la cour, chrono officiel.', maxPoints: 40 },
  {
    name: 'Blind test',
    emoji: '🎧',
    description: 'Reconnaître le titre et l’artiste en moins de 10 secondes.',
    maxPoints: 40,
  },
  {
    name: 'Défi sportif',
    emoji: '⚽',
    description: 'Penalties, tir à la corde et parcours d’obstacles.',
    maxPoints: 60,
  },
  { name: 'Memory', emoji: '🧠', description: 'Memory géant aux couleurs de l’ISIMM.', maxPoints: 30 },
  {
    name: 'Challenge photo',
    emoji: '📸',
    description: 'La photo d’équipe la plus créative, votée par le jury.',
    maxPoints: 30,
  },
];

// Points per team for the games already played in the demo (same order as DEMO_TEAMS).
const DEMO_RESULTS = [
  { game: 0, points: [45, 38, 30, 25, 20, 35, 15, 28], minutesAgo: 150 },
  { game: 1, points: [30, 40, 35, 20, 25, 15, 10, 30], minutesAgo: 110 },
  { game: 2, points: [40, 25, 30, 35, 20, 30, 25, 15], minutesAgo: 70 },
];

export function createDemoState() {
  const now = Date.now();
  const teams = DEMO_TEAMS.map(({ name, color, avatar }, index) => ({
    id: createId('team'),
    name,
    color,
    avatar,
    logo: null,
    score: 0,
    createdAt: now - 4 * 3600_000 + index,
  }));

  const participants = DEMO_TEAMS.flatMap(({ members }, teamIndex) =>
    members.map((name, memberIndex) => ({
      id: createId('p'),
      name,
      teamId: teams[teamIndex].id,
      studentId: `ISIMM-${String(2600 + teamIndex * 10 + memberIndex).padStart(4, '0')}`,
      avatar: null,
    })),
  );

  const games = DEMO_GAMES.map((game) => ({ id: createId('game'), ...game, createdAt: now - 5 * 3600_000 }));

  const history = [];
  const push = (team, delta, reason, at, extra = {}) => {
    const prevScore = team.score;
    team.score = Math.max(0, prevScore + delta);
    history.push({
      id: createId('h'),
      teamId: team.id,
      delta: team.score - prevScore,
      prevScore,
      newScore: team.score,
      reason,
      gameId: null,
      kind: 'adjust',
      batchId: null,
      at,
      ...extra,
    });
  };

  DEMO_RESULTS.forEach(({ game, points, minutesAgo }) => {
    const batchId = createId('batch');
    points.forEach((value, teamIndex) =>
      push(teams[teamIndex], value, `Mini-jeu : ${games[game].name}`, now - minutesAgo * 60_000 + teamIndex, {
        gameId: games[game].id,
        kind: 'game',
        batchId,
      }),
    );
  });
  push(teams[3], 15, 'Bonus fair-play', now - 45 * 60_000);
  push(teams[2], -5, 'Pénalité : retard', now - 30 * 60_000);
  push(teams[6], 10, 'Bonus ambiance', now - 12 * 60_000);

  return { teams, participants, games, history };
}
