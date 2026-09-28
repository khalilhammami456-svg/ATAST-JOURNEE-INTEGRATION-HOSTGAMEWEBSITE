import { DEFAULT_SETTINGS, createDemoState } from '../data/demoData';

/**
 * Minimal external store persisted in localStorage.
 * Every tab of the same browser stays in sync through BroadcastChannel
 * (with the `storage` event as a fallback), so /admin and /display
 * always show the same data without any server.
 */
const STORAGE_KEY = 'journee-integration:state:v1';
const CHANNEL_NAME = 'journee-integration:sync';

export const DEFAULT_DISPLAY = { view: 'leaderboard', podiumRun: 0 };

export function createBaseState(data = {}) {
  return {
    rev: 0,
    updatedAt: Date.now(),
    teams: [],
    participants: [],
    games: [],
    history: [],
    lastEvent: null,
    ...data,
    settings: { ...DEFAULT_SETTINGS, ...(data.settings ?? {}) },
    display: { ...DEFAULT_DISPLAY, ...(data.display ?? {}) },
  };
}

function loadInitialState() {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return createBaseState(JSON.parse(raw));
  } catch (error) {
    console.error('Données locales illisibles, chargement de la démo.', error);
  }
  return createBaseState(createDemoState());
}

let state = loadInitialState();
const listeners = new Set();
const errorListeners = new Set();
const channel = typeof BroadcastChannel !== 'undefined' ? new BroadcastChannel(CHANNEL_NAME) : null;

function emit() {
  listeners.forEach((listener) => listener());
}

function persist(nextState) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(nextState));
  } catch (error) {
    const message =
      error?.name === 'QuotaExceededError'
        ? 'Stockage local plein : retirez quelques logos ou photos, puis réessayez.'
        : "Impossible d'enregistrer les données localement.";
    errorListeners.forEach((listener) => listener(message));
  }
}

function isNewer(incoming) {
  return incoming.rev > state.rev || (incoming.rev === state.rev && incoming.updatedAt > state.updatedAt);
}

function receive(incoming) {
  if (!incoming || !isNewer(incoming)) return;
  state = createBaseState(incoming);
  emit();
}

channel?.addEventListener('message', (event) => {
  if (event.data?.type === 'state') receive(event.data.state);
});

window.addEventListener('storage', (event) => {
  if (event.key !== STORAGE_KEY || !event.newValue) return;
  try {
    receive(JSON.parse(event.newValue));
  } catch {
    /* ignore malformed writes from other tabs */
  }
});

export const getState = () => state;

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function onStorageError(listener) {
  errorListeners.add(listener);
  return () => errorListeners.delete(listener);
}

/** Applies an updater `(state) => nextState`. Returning the same object is a no-op. */
export function update(updater) {
  const draft = updater(state);
  if (draft === state) return state;
  state = { ...draft, rev: state.rev + 1, updatedAt: Date.now() };
  persist(state);
  channel?.postMessage({ type: 'state', state });
  emit();
  return state;
}
