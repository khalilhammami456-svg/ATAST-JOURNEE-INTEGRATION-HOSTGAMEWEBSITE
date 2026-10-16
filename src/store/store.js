import { isFirebaseConfigured } from './firebaseConfig';
import * as local from './localStore';
import * as firestoreImpl from './firestoreStore';

/**
 * Picks the sync engine: Firestore (multi-device, real-time) once a real
 * Firebase project is configured in firebaseConfig.js, otherwise the
 * original single-device localStorage engine — so the app never breaks
 * while Firebase hasn't been set up yet. Both engines share the exact same
 * shape and `update()` contract; nothing outside this file needs to know
 * which one is active.
 */
const impl = isFirebaseConfigured ? firestoreImpl : local;

export const getState = impl.getState;
export const subscribe = impl.subscribe;
export const update = impl.update;
export const onStorageError = impl.onStorageError;
export const createBaseState = impl.createBaseState;
export const DEFAULT_DISPLAY = impl.DEFAULT_DISPLAY;
