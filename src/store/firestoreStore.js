import { initializeApp } from 'firebase/app';
import {
  collection,
  doc,
  getFirestore,
  initializeFirestore,
  onSnapshot,
  orderBy,
  persistentLocalCache,
  persistentMultipleTabManager,
  query,
  writeBatch,
} from 'firebase/firestore';
import { DEFAULT_SETTINGS } from '../data/demoData';
import { firebaseConfig, isFirebaseConfigured } from './firebaseConfig';

/**
 * External store shared across every host's device through Firestore.
 * Same shape and `update()` contract as localStore.js, so actions.js and
 * every component that reads the store are unaware of which one is active.
 *
 * The whole event lives under a single `events/main` document, with teams,
 * participants, games and history as subcollections (each item = one small
 * document) so a single score tweak only writes the one team that changed,
 * not the entire event, and so no document ever approaches Firestore's
 * 1&nbsp;MiB per-document limit even with team/participant photos.
 */

export const DEFAULT_DISPLAY = { view: 'leaderboard', podiumRun: 0 };
const EVENT_ID = 'main';
const ARRAY_KEYS = ['teams', 'participants', 'games', 'history'];
const DOC_KEYS = ['settings', 'display', 'lastEvent'];

export function createBaseState(data = {}) {
  return {
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

let state = createBaseState();
const listeners = new Set();
const errorListeners = new Set();

function emit() {
  listeners.forEach((listener) => listener());
}

function reportError(message) {
  errorListeners.forEach((listener) => listener(message));
}

export const getState = () => state;

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function onStorageError(listener) {
  errorListeners.add(listener);
  return () => errorListeners.delete(listener);
}

/* Everything below only runs when a real Firebase project is configured —
   importing this module is otherwise a safe no-op. */

let db = null;
let eventRef = null;
let collections = null;

function describeError(error) {
  if (error?.code === 'unavailable') {
    return 'Connexion perdue : les changements seront synchronisés au retour du réseau.';
  }
  if (error?.code === 'permission-denied') {
    return 'Accès refusé à la base partagée — vérifiez firestore.rules dans la console Firebase.';
  }
  return `Erreur de synchronisation : ${error?.message || 'inconnue'}.`;
}

if (isFirebaseConfigured) {
  const app = initializeApp(firebaseConfig);

  try {
    db = initializeFirestore(app, {
      localCache: persistentLocalCache({ tabManager: persistentMultipleTabManager() }),
    });
  } catch (error) {
    // Offline persistence isn't available in this browser (e.g. private
    // browsing) — fall back to an in-memory-only Firestore client.
    console.warn('Firestore offline persistence unavailable, continuing without it.', error);
    db = getFirestore(app);
  }

  eventRef = doc(db, 'events', EVENT_ID);
  collections = {
    teams: collection(eventRef, 'teams'),
    participants: collection(eventRef, 'participants'),
    games: collection(eventRef, 'games'),
    history: collection(eventRef, 'history'),
  };

  const latest = { doc: {}, teams: [], participants: [], games: [], history: [] };
  const ready = { doc: false, teams: false, participants: false, games: false, history: false };

  function recompute() {
    state = createBaseState({
      ...latest.doc,
      teams: latest.teams,
      participants: latest.participants,
      games: latest.games,
      history: latest.history,
    });
    emit();
  }

  onSnapshot(
    eventRef,
    (snap) => {
      latest.doc = snap.exists() ? snap.data() : {};
      ready.doc = true;
      if (Object.values(ready).some(Boolean)) recompute();
    },
    (error) => reportError(describeError(error)),
  );

  const watch = (key, ref, sortBy) => {
    const target = sortBy ? query(ref, orderBy(sortBy)) : ref;
    onSnapshot(
      target,
      (snap) => {
        latest[key] = snap.docs.map((docSnap) => ({ id: docSnap.id, ...docSnap.data() }));
        ready[key] = true;
        recompute();
      },
      (error) => reportError(describeError(error)),
    );
  };

  watch('teams', collections.teams);
  watch('participants', collections.participants);
  watch('games', collections.games);
  watch('history', collections.history, 'at');
}

async function commitOps(ops) {
  const CHUNK = 400; // Firestore batches cap at 500 operations
  for (let i = 0; i < ops.length; i += CHUNK) {
    const batch = writeBatch(db);
    ops.slice(i, i + CHUNK).forEach((op) => {
      if (op.type === 'delete') batch.delete(op.ref);
      else batch.set(op.ref, op.data, op.merge ? { merge: true } : undefined);
    });
    // eslint-disable-next-line no-await-in-loop
    await batch.commit();
  }
}

/**
 * Applies an updater `(state) => nextState`, updates local state right away
 * (so the UI never waits on a round trip), then diffs the result against
 * what changed and writes only that to Firestore. Returning the same object
 * is a no-op.
 */
export function update(updater) {
  if (!isFirebaseConfigured) return state; // guarded no-op, see localStore.js

  const draft = updater(state);
  if (draft === state) return state;

  // Not re-wrapped through createBaseState: state (and therefore every
  // updater's spread of it) is always already well-formed, and re-wrapping
  // would allocate new settings/display objects on every call, breaking
  // the reference-equality diff below and writing the whole event doc on
  // every single score click instead of just what changed.
  const nextState = draft;
  const previous = state;
  state = nextState;
  emit();

  const ops = [];

  ARRAY_KEYS.forEach((key) => {
    if (nextState[key] === previous[key]) return;
    const prevById = new Map(previous[key].map((item) => [item.id, item]));
    const nextIds = new Set();
    nextState[key].forEach((item) => {
      nextIds.add(item.id);
      if (prevById.get(item.id) !== item) {
        const { id, ...rest } = item;
        ops.push({ type: 'set', ref: doc(collections[key], id), data: rest });
      }
    });
    prevById.forEach((_, id) => {
      if (!nextIds.has(id)) ops.push({ type: 'delete', ref: doc(collections[key], id) });
    });
  });

  const docPatch = {};
  DOC_KEYS.forEach((key) => {
    if (nextState[key] !== previous[key]) docPatch[key] = nextState[key];
  });
  if (Object.keys(docPatch).length > 0) {
    ops.push({ type: 'set', ref: eventRef, data: docPatch, merge: true });
  }

  if (ops.length > 0) {
    commitOps(ops).catch((error) => reportError(describeError(error)));
  }

  return state;
}
