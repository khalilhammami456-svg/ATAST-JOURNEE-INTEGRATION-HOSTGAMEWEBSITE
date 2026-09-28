import { rankTeams } from './ranking';
import { formatDateTime } from './format';

function downloadFile(filename, content, mimeType) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}

const stamp = () => {
  const now = new Date();
  const pad = (value) => String(value).padStart(2, '0');
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}_${pad(now.getHours())}h${pad(now.getMinutes())}`;
};

const csvCell = (value) => {
  const text = String(value ?? '');
  return /[";\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
};

// Semicolons + BOM so Excel (FR locale) opens the file with columns and accents intact.
const toCsv = (rows) => '\uFEFF' + rows.map((row) => row.map(csvCell).join(';')).join('\n');

export function exportJson(state) {
  const { rev, ...data } = state;
  const payload = { app: 'journee-integration', exportedAt: new Date().toISOString(), data };
  downloadFile(`journee-integration-sauvegarde-${stamp()}.json`, JSON.stringify(payload, null, 2), 'application/json');
}

export function exportCsv(state) {
  const teamName = Object.fromEntries(state.teams.map((team) => [team.id, team.name]));
  const participantCount = (teamId) => state.participants.filter((p) => p.teamId === teamId).length;

  const ranking = [
    ['Rang', 'Équipe', 'Score', 'Participants'],
    ...rankTeams(state.teams).map((team) => [team.rank, team.name, team.score, participantCount(team.id)]),
  ];
  const participants = [
    ['Nom', 'Équipe', 'Identifiant'],
    ...state.participants.map((p) => [p.name, teamName[p.teamId] ?? '', p.studentId]),
  ];
  const gameName = Object.fromEntries(state.games.map((game) => [game.id, game.name]));
  const history = [
    ['Date', 'Équipe', 'Points', 'Motif', 'Mini-jeu', 'Score après'],
    ...state.history.map((entry) => [
      formatDateTime(entry.at),
      teamName[entry.teamId] ?? 'Équipe supprimée',
      entry.delta,
      entry.reason,
      gameName[entry.gameId] ?? '',
      entry.newScore,
    ]),
  ];

  const time = stamp();
  downloadFile(`classement-${time}.csv`, toCsv(ranking), 'text/csv;charset=utf-8');
  downloadFile(`participants-${time}.csv`, toCsv(participants), 'text/csv;charset=utf-8');
  downloadFile(`historique-scores-${time}.csv`, toCsv(history), 'text/csv;charset=utf-8');
}

export function parseBackup(text) {
  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    throw new Error("Le fichier n'est pas un JSON valide.");
  }
  const data = parsed?.data ?? parsed;
  const required = ['teams', 'participants', 'games', 'history', 'settings'];
  const missing = required.filter((key) => !(key in (data ?? {})));
  if (missing.length) {
    throw new Error(`Sauvegarde incomplète : il manque ${missing.join(', ')}.`);
  }
  if (!Array.isArray(data.teams) || !Array.isArray(data.participants)) {
    throw new Error('Sauvegarde invalide : les équipes ou participants sont mal formés.');
  }
  return data;
}
