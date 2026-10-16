/**
 * Real-time synchronisation client.
 *
 * Keeps one Server-Sent Events stream open while signed in. The server only
 * says *what* changed (topics); pages re-read their data through the API.
 * EventSource reconnects by itself; after any reconnection every page area is
 * refreshed so nothing missed while offline or asleep stays stale.
 * Tabs of the same browser also share sign-in / sign-out through BroadcastChannel.
 */
import { session } from '../state/session.js';

export const ALL_TOPICS = ['events', 'scoreboard', 'members', 'messages', 'suggestions', 'profile', 'requests', 'stats'];

let source = null;
let status = 'off'; // off | connecting | live | reconnecting | offline
let hadError = false;
let retryTimer = null;
const changeListeners = new Set();
const statusListeners = new Set();
let revokedHandler = () => {};
let authCheck = async () => true;

const channel = 'BroadcastChannel' in window ? new BroadcastChannel('atast-auth') : null;
const tabListeners = new Set();
channel?.addEventListener('message', (e) => {
  for (const fn of tabListeners) fn(e.data);
});

function setStatus(next) {
  if (status === next) return;
  status = next;
  for (const fn of statusListeners) fn(status);
}

function emit(change) {
  for (const fn of changeListeners) {
    try {
      fn(change);
    } catch (err) {
      console.error(err);
    }
  }
}

export function startSync() {
  if (source || !session.user || !('EventSource' in window)) return;
  clearTimeout(retryTimer);
  setStatus(hadError ? 'reconnecting' : 'connecting');
  source = new EventSource('/api/sync', { withCredentials: true });

  source.addEventListener('ready', () => {
    const resume = hadError;
    hadError = false;
    attempts = 0;
    setStatus('live');
    // Back after a disconnection: refresh everything that might have changed meanwhile.
    if (resume) emit({ topics: ALL_TOPICS, resync: true });
  });
  source.addEventListener('change', (e) => {
    try {
      emit(JSON.parse(e.data));
    } catch {
      /* ignore malformed frame */
    }
  });
  source.addEventListener('session', (e) => {
    let reason = 'LOGOUT';
    try {
      reason = JSON.parse(e.data).reason;
    } catch {
      /* keep default */
    }
    stopSync();
    revokedHandler(reason);
  });
  source.onerror = () => {
    hadError = true;
    setStatus(navigator.onLine === false ? 'offline' : 'reconnecting');
    if (source && source.readyState === EventSource.CLOSED) {
      // The browser gave up (server unreachable or session expired): retry ourselves.
      source = null;
      scheduleRetry();
    }
  };
}

let attempts = 0;
/** Retries with a growing delay (2 s → 15 s) until the server answers. */
function scheduleRetry() {
  clearTimeout(retryTimer);
  const delay = Math.min(2000 * 2 ** attempts, 15000);
  attempts += 1;
  retryTimer = setTimeout(async () => {
    if (!session.user || source) return;
    const state = await authCheck(); // 'ok' | 'unauthenticated' | 'unreachable'
    if (state === 'ok') startSync();
    else if (state === 'unreachable') scheduleRetry();
    // 'unauthenticated': the app signs the person out, nothing to retry.
  }, delay);
}

export function stopSync() {
  clearTimeout(retryTimer);
  if (source) source.close();
  source = null;
  hadError = false;
  setStatus('off');
}

export function syncStatus() {
  return status;
}

export function onChange(fn) {
  changeListeners.add(fn);
  return () => changeListeners.delete(fn);
}

export function onStatus(fn) {
  statusListeners.add(fn);
  fn(status);
  return () => statusListeners.delete(fn);
}

export function setRevokedHandler(fn) {
  revokedHandler = fn;
}

export function setAuthCheck(fn) {
  authCheck = fn;
}

/** Tells the other tabs of this browser that the user signed in or out. */
export function tellOtherTabs(type) {
  channel?.postMessage({ type });
}

export function onOtherTab(fn) {
  tabListeners.add(fn);
}

/** Reconnects at once instead of waiting for the browser's own retry delay. */
function reconnectNow() {
  if (!session.user) return;
  if (source && source.readyState === EventSource.OPEN) {
    // The stream survived the interruption: just catch up in case something was missed.
    if (status !== 'live') {
      setStatus('live');
      emit({ topics: ALL_TOPICS, resync: true });
    }
    return;
  }
  if (source) source.close();
  source = null;
  hadError = true;
  startSync();
}
window.addEventListener('online', reconnectNow);
// Phones suspend background tabs: reconnect (and resync) as soon as the page is visible again.
document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') reconnectNow();
});
window.addEventListener('offline', () => {
  if (session.user) setStatus('offline');
});
