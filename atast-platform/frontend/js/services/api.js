/**
 * HTTP client for the ATAST REST API. Maps every failure to an ApiError
 * with a readable French message (chapter "Error States").
 */
import { session } from '../state/session.js';

export class ApiError extends Error {
  constructor(status, code, message, fields) {
    super(message);
    this.status = status;
    this.code = code;
    this.fields = fields || null;
  }
}

const MESSAGES = {
  NETWORK: 'Connexion au serveur impossible. Vérifiez votre connexion internet puis réessayez.',
  SERVER: 'Le service est momentanément indisponible. Réessayez dans quelques instants.',
};

let onUnauthorized = () => {};
export function setUnauthorizedHandler(fn) {
  onUnauthorized = fn;
}

export async function api(path, { method = 'GET', body, form, query, silent401 = false } = {}) {
  let url = `/api${path}`;
  if (query) {
    const params = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) if (v !== undefined && v !== null && v !== '') params.set(k, v);
    const qs = params.toString();
    if (qs) url += `?${qs}`;
  }
  const headers = { 'X-Requested-With': 'fetch', Accept: 'application/json' };
  if (method !== 'GET' && session.csrf) headers['X-CSRF-Token'] = session.csrf;
  let payload;
  if (form) payload = form;
  else if (body !== undefined) {
    headers['Content-Type'] = 'application/json';
    payload = JSON.stringify(body);
  }

  let res;
  try {
    res = await fetch(url, { method, headers, body: payload, credentials: 'same-origin' });
  } catch {
    throw new ApiError(0, 'NETWORK', MESSAGES.NETWORK);
  }
  if (res.status === 204) return null;

  let data = null;
  try {
    data = await res.json();
  } catch {
    data = null;
  }
  if (res.ok) return data;

  const err = data?.error;
  if (res.status >= 500 || !err) {
    throw new ApiError(res.status, err?.code || 'SERVER_ERROR', res.status >= 500 ? MESSAGES.SERVER : (err?.message || MESSAGES.SERVER));
  }
  const apiError = new ApiError(res.status, err.code, err.message, err.fields);
  if (res.status === 401 && err.code === 'UNAUTHENTICATED' && !silent401) onUnauthorized(apiError);
  throw apiError;
}
