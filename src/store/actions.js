import { update, getState, createBaseState } from './store';
import { createDemoState } from '../data/demoData';
import { createId } from '../utils/id';
import { normalize } from '../utils/format';
import { rankTeams, leaderIds } from '../utils/ranking';

/* ------------------------------------------------------------------ */
/* Validation                                                          */
/* ------------------------------------------------------------------ */

function assertTeamName(state, name, ignoreId = null) {
  const cleaned = name?.trim();
  if (!cleaned) throw new Error("Le nom de l'équipe est obligatoire.");
  if (cleaned.length > 32) throw new Error("Le nom de l'équipe ne doit pas dépasser 32 caractères.");
  const exists = state.teams.some((team) => team.id !== ignoreId && normalize(team.name) === normalize(cleaned));
  if (exists) throw new Error('Une équipe avec ce nom existe déjà.');
  return cleaned;
}

function assertParticipantName(name) {
  const cleaned = name?.trim();
  if (!cleaned) throw new Error('Le nom du participant est obligatoire.');
  return cleaned;
}

function assertTeamExists(state, teamId) {
  if (!state.teams.some((team) => team.id === teamId)) throw new Error('Choisissez une équipe valide.');
}

export function parseScoreInput(value, { allowNegative = true } = {}) {
  if (value === '' || value === null || value === undefined) throw new Error('Indiquez un nombre de points.');
  const number = Number(value);
  if (!Number.isInteger(number)) throw new Error('Le score doit être un nombre entier.');
  if (!allowNegative && number < 0) throw new Error('Le score doit être un nombre positif.');
  if (Math.abs(number) > 100000) throw new Error('Ce nombre de points est trop grand.');
  return number;
}

/* ------------------------------------------------------------------ */
/* Score engine                                                        */
/* ------------------------------------------------------------------ */

function buildScoreEvent(previousTeams, nextTeams, changes, type) {
  const previousLeaders = leaderIds(rankTeams(previousTeams));
  const nextLeaders = leaderIds(rankTeams(nextTeams));
  const leaderChanged = nextLeaders.length > 0 && nextLeaders.some((id) => !previousLeaders.includes(id));
  return { id: createId('ev'), type, changes, leaderChanged, leaderIds: nextLeaders, at: Date.now() };
}

/**
 * Applies point changes to one or more teams, records one history entry per team
 * and publishes a `lastEvent` used for toasts, sounds and on-screen effects.
 * Scores never go below 0; the recorded delta is the one actually applied.
 */
function applyScoreChanges(changes, { reason, gameId = null, kind = 'adjust' }) {
  let applied = [];
  update((state) => {
    const batchId = changes.length > 1 ? createId('batch') : null;
    const at = Date.now();
    const deltas = new Map();
    changes.forEach(({ teamId, delta }) => deltas.set(teamId, (deltas.get(teamId) ?? 0) + delta));

    const entries = [];
    const teams = state.teams.map((team) => {
      const delta = deltas.get(team.id);
      if (!delta) return team;
      const newScore = Math.max(0, team.score + delta);
      if (newScore === team.score) return team;
      entries.push({
        id: createId('h'),
        teamId: team.id,
        delta: newScore - team.score,
        prevScore: team.score,
        newScore,
        reason: reason?.trim() || (newScore > team.score ? 'Points ajoutés' : 'Points retirés'),
        gameId,
        kind,
        batchId,
        at,
      });
      return { ...team, score: newScore };
    });

    if (entries.length === 0) return state;
    applied = entries;
    const eventChanges = entries.map(({ teamId, delta, newScore }) => ({ teamId, delta, newScore }));
    return {
      ...state,
      teams,
      history: [...state.history, ...entries],
      lastEvent: buildScoreEvent(state.teams, teams, eventChanges, 'score'),
    };
  });
  return applied;
}

export const adjustScore = (teamId, delta, reason) =>
  applyScoreChanges([{ teamId, delta }], { reason, kind: 'adjust' });

export function setScore(teamId, rawValue, reason) {
  const value = parseScoreInput(rawValue, { allowNegative: false });
  const team = getState().teams.find((t) => t.id === teamId);
  if (!team) throw new Error('Équipe introuvable.');
  if (value === team.score) throw new Error('Le score est déjà à cette valeur.');
  return applyScoreChanges([{ teamId, delta: value - team.score }], {
    reason: reason?.trim() || 'Score modifié manuellement',
    kind: 'set',
  });
}

export function addScoreEvent(teamId, rawPoints, { reason, gameId = null } = {}) {
  const points = parseScoreInput(rawPoints);
  if (points === 0) throw new Error('Indiquez un nombre de points différent de 0.');
  const game = gameId ? getState().games.find((g) => g.id === gameId) : null;
  const label = reason?.trim() || (game ? `Mini-jeu : ${game.name}` : '');
  if (!label) throw new Error('Indiquez un motif ou choisissez un mini-jeu.');
  return applyScoreChanges([{ teamId, delta: points }], { reason: label, gameId, kind: game ? 'game' : 'adjust' });
}

export function awardGamePoints(gameId, pointsByTeam) {
  const game = getState().games.find((g) => g.id === gameId);
  if (!game) throw new Error('Mini-jeu introuvable.');
  const changes = Object.entries(pointsByTeam)
    .filter(([, value]) => value !== '' && value !== null && value !== undefined)
    .map(([teamId, value]) => {
      const points = parseScoreInput(value);
      if (game.maxPoints && points > game.maxPoints) {
        throw new Error(`Maximum ${game.maxPoints} points par équipe pour « ${game.name} ».`);
      }
      return { teamId, delta: points };
    })
    .filter(({ delta }) => delta !== 0);
  if (changes.length === 0) throw new Error('Saisissez des points pour au moins une équipe.');
  return applyScoreChanges(changes, { reason: `Mini-jeu : ${game.name}`, gameId, kind: 'game' });
}

function revertEntries(predicate) {
  let reverted = [];
  update((state) => {
    const toRevert = state.history.filter(predicate);
    if (toRevert.length === 0) return state;
    const revertIds = new Set(toRevert.map((entry) => entry.id));
    const deltas = new Map();
    toRevert.forEach(({ teamId, delta }) => deltas.set(teamId, (deltas.get(teamId) ?? 0) + delta));

    const changes = [];
    const teams = state.teams.map((team) => {
      const delta = deltas.get(team.id);
      if (!delta) return team;
      const newScore = Math.max(0, team.score - delta);
      changes.push({ teamId: team.id, delta: newScore - team.score, newScore });
      return { ...team, score: newScore };
    });
    reverted = toRevert;
    return {
      ...state,
      teams,
      history: state.history.filter((entry) => !revertIds.has(entry.id)),
      lastEvent: buildScoreEvent(state.teams, teams, changes, 'undo'),
    };
  });
  return reverted;
}

/** Cancels the most recent change (a whole mini-game batch counts as one change). */
export function undoLastChange() {
  const last = getState().history.at(-1);
  if (!last) throw new Error('Aucune modification à annuler.');
  return revertEntries((entry) => (last.batchId ? entry.batchId === last.batchId : entry.id === last.id));
}

export function undoLastForTeam(teamId) {
  const last = getState().history.findLast((entry) => entry.teamId === teamId);
  if (!last) throw new Error('Aucune modification à annuler pour cette équipe.');
  return revertEntries((entry) => entry.id === last.id);
}

export function resetScores() {
  update((state) => ({
    ...state,
    teams: state.teams.map((team) => ({ ...team, score: 0 })),
    history: [],
    lastEvent: { id: createId('ev'), type: 'reset', changes: [], leaderChanged: false, leaderIds: [], at: Date.now() },
  }));
}

/* ------------------------------------------------------------------ */
/* Teams                                                               */
/* ------------------------------------------------------------------ */

export function addTeam({ name, color, avatar = null, logo = null, participantNames = [] }) {
  let created;
  update((state) => {
    const cleanName = assertTeamName(state, name);
    const team = { id: createId('team'), name: cleanName, color, avatar, logo, score: 0, createdAt: Date.now() };
    const participants = participantNames
      .map((participantName) => participantName.trim())
      .filter(Boolean)
      .map((participantName) => ({
        id: createId('p'),
        name: participantName,
        teamId: team.id,
        studentId: '',
        avatar: null,
      }));
    created = team;
    return { ...state, teams: [...state.teams, team], participants: [...state.participants, ...participants] };
  });
  return created;
}

export function updateTeam(teamId, patch) {
  update((state) => {
    const name = patch.name !== undefined ? assertTeamName(state, patch.name, teamId) : undefined;
    return {
      ...state,
      teams: state.teams.map((team) =>
        team.id === teamId ? { ...team, ...patch, ...(name !== undefined && { name }) } : team,
      ),
    };
  });
}

export function deleteTeam(teamId) {
  update((state) => ({
    ...state,
    teams: state.teams.filter((team) => team.id !== teamId),
    participants: state.participants.filter((participant) => participant.teamId !== teamId),
    history: state.history.filter((entry) => entry.teamId !== teamId),
  }));
}

/* ------------------------------------------------------------------ */
/* Participants                                                        */
/* ------------------------------------------------------------------ */

export function addParticipant({ name, teamId, studentId = '', avatar = null }) {
  update((state) => {
    const cleanName = assertParticipantName(name);
    assertTeamExists(state, teamId);
    const participant = { id: createId('p'), name: cleanName, teamId, studentId: studentId.trim(), avatar };
    return { ...state, participants: [...state.participants, participant] };
  });
}

export function updateParticipant(participantId, patch) {
  update((state) => {
    if (patch.name !== undefined) patch = { ...patch, name: assertParticipantName(patch.name) };
    if (patch.teamId !== undefined) assertTeamExists(state, patch.teamId);
    if (patch.studentId !== undefined) patch = { ...patch, studentId: patch.studentId.trim() };
    return {
      ...state,
      participants: state.participants.map((participant) =>
        participant.id === participantId ? { ...participant, ...patch } : participant,
      ),
    };
  });
}

export function deleteParticipant(participantId) {
  update((state) => ({
    ...state,
    participants: state.participants.filter((participant) => participant.id !== participantId),
  }));
}

/* ------------------------------------------------------------------ */
/* Mini-games                                                          */
/* ------------------------------------------------------------------ */

function validateGame(state, { name, maxPoints }, ignoreId = null) {
  const cleanName = name?.trim();
  if (!cleanName) throw new Error('Le nom du mini-jeu est obligatoire.');
  if (state.games.some((game) => game.id !== ignoreId && normalize(game.name) === normalize(cleanName))) {
    throw new Error('Un mini-jeu avec ce nom existe déjà.');
  }
  const max = maxPoints === '' || maxPoints === null ? null : Number(maxPoints);
  if (max !== null && (!Number.isInteger(max) || max <= 0)) {
    throw new Error('Les points maximum doivent être un nombre entier positif.');
  }
  return { name: cleanName, maxPoints: max };
}

export function addGame({ name, description = '', maxPoints, emoji = '🎮' }) {
  update((state) => {
    const valid = validateGame(state, { name, maxPoints });
    const game = { id: createId('game'), ...valid, description: description.trim(), emoji, createdAt: Date.now() };
    return { ...state, games: [...state.games, game] };
  });
}

export function updateGame(gameId, { name, description = '', maxPoints, emoji }) {
  update((state) => {
    const valid = validateGame(state, { name, maxPoints }, gameId);
    return {
      ...state,
      games: state.games.map((game) =>
        game.id === gameId ? { ...game, ...valid, description: description.trim(), emoji: emoji ?? game.emoji } : game,
      ),
    };
  });
}

export function deleteGame(gameId) {
  update((state) => ({ ...state, games: state.games.filter((game) => game.id !== gameId) }));
}

/* ------------------------------------------------------------------ */
/* Settings, public screen, data                                       */
/* ------------------------------------------------------------------ */

export function updateSettings(patch) {
  update((state) => ({ ...state, settings: { ...state.settings, ...patch } }));
}

export function setDisplayView(view) {
  update((state) => (state.display.view === view ? state : { ...state, display: { ...state.display, view } }));
}

/** Switches the public screen to the podium and (re)starts the reveal ceremony. */
export function startPodiumCeremony() {
  update((state) => ({ ...state, display: { view: 'podium', podiumRun: Date.now() } }));
}

export function importData(data) {
  update((state) => ({ ...createBaseState(data), rev: state.rev }));
}

export function loadDemoData() {
  update((state) => ({ ...createBaseState(createDemoState()), settings: state.settings, rev: state.rev }));
}

export function clearAllData() {
  update((state) => ({ ...createBaseState(), settings: state.settings, rev: state.rev }));
}
