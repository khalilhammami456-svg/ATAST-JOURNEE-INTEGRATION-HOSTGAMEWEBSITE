/** Formatting helpers and French labels for enums. */
export const TYPE_LABELS = {
  SMALL: 'Petit événement',
  MEDIUM: 'Événement moyen',
  BIG: 'Grand événement',
  MEETING: 'Réunion',
};
export const TYPE_SHORT = { SMALL: 'Petit', MEDIUM: 'Moyen', BIG: 'Grand', MEETING: 'Réunion' };
export const TYPE_POINTS = { SMALL: 10, MEDIUM: 20, BIG: 30, MEETING: 0 };
export const EVENT_TYPES = ['SMALL', 'MEDIUM', 'BIG', 'MEETING'];

export const EVENT_STATUS = {
  DRAFT: 'Brouillon',
  PUBLISHED: 'Publié',
  COMPLETED: 'Terminé',
  ARCHIVED: 'Archivé',
};
export const REQUEST_STATUS = { PENDING: 'En attente', ACCEPTED: 'Acceptée', REJECTED: 'Refusée' };
export const SUGGESTION_STATUS = { NEW: 'Nouvelle', READ: 'Lue', IN_REVIEW: 'En cours d’étude', RESOLVED: 'Traitée' };
export const SUBSCRIPTION_STATUS = { AVAILABLE: 'Payée, pas encore inscrite', CLAIMED: 'Membre inscrit', REVOKED: 'Annulée' };
export const IMPORT_ROW_STATUS = {
  NEW: 'À ajouter',
  AUTO_ACCEPT: 'Acceptée automatiquement',
  RENEWAL: 'Déjà membre',
  ALREADY_LISTED: 'Déjà enregistrée',
  DUPLICATE: 'Doublon',
  BLOCKED: 'À traiter à la main',
  INVALID: 'Erreur',
};
export const MEMBER_STATUS = { ACTIVE: 'Actif', SUSPENDED: 'Suspendu', DEACTIVATED: 'Désactivé' };
export const PARTICIPATION_STATUS = { REGISTERED: 'Inscrit', VALIDATED: 'Participation validée' };

const TZ = 'Africa/Tunis';

/** "YYYY-MM-DD" → Date at noon UTC (no day shift whatever the browser zone). */
const dayDate = (ymd) => new Date(`${ymd}T12:00:00Z`);

export function formatDay(ymd, opts = { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' }) {
  return new Intl.DateTimeFormat('fr-FR', { ...opts, timeZone: 'UTC' }).format(dayDate(ymd));
}
export function dayParts(ymd) {
  const d = dayDate(ymd);
  return {
    day: new Intl.DateTimeFormat('fr-FR', { day: 'numeric', timeZone: 'UTC' }).format(d),
    month: new Intl.DateTimeFormat('fr-FR', { month: 'short', timeZone: 'UTC' }).format(d).replace('.', ''),
    year: d.getUTCFullYear(),
  };
}
export function formatTime(hhmm) {
  const [h, m] = hhmm.split(':');
  return `${Number(h)} h ${m}`;
}
export function formatDateTime(iso) {
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit', timeZone: TZ }).format(new Date(iso));
}
export function formatDate(iso) {
  return new Intl.DateTimeFormat('fr-FR', { day: 'numeric', month: 'long', year: 'numeric', timeZone: TZ }).format(new Date(iso));
}
export function relative(iso) {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  const rtf = new Intl.RelativeTimeFormat('fr', { numeric: 'auto' });
  if (diff < 60) return 'à l’instant';
  if (diff < 3600) return rtf.format(-Math.round(diff / 60), 'minute');
  if (diff < 86400) return rtf.format(-Math.round(diff / 3600), 'hour');
  if (diff < 86400 * 30) return rtf.format(-Math.round(diff / 86400), 'day');
  return formatDate(iso);
}
export function todayYmd() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: TZ }).format(new Date());
}
export function isPast(ymd) {
  return ymd < todayYmd();
}
export function formatPrice(event) {
  if (event.isFree) return 'Gratuit';
  const [int, dec] = event.price.split('.');
  const intFmt = Number(int).toLocaleString('fr-FR');
  const decimals = dec.replace(/0+$/, '');
  return decimals ? `${intFmt},${dec.slice(0, Math.max(decimals.length, 2))} ${event.currency}` : `${intFmt} ${event.currency}`;
}
export function pointsLabel(n) {
  return n === 0 ? '0 point' : `+${n} pts`;
}
export function plural(n, one, many) {
  return `${n.toLocaleString('fr-FR')} ${n > 1 ? many : one}`;
}
export function ordinal(n) {
  return n === 1 ? '1er' : `${n}e`;
}
export function firstName(name) {
  return String(name || '').split(' ')[0];
}

/** Academic year containing today: September starts a new season (2025-09..2026-08 = 2025-2026). */
export function currentSeason() {
  const [y, m] = todayYmd().split('-').map(Number);
  return m >= 9 ? `${y}-${y + 1}` : `${y - 1}-${y}`;
}
export function seasonOptions() {
  const start = Number(currentSeason().slice(0, 4));
  return [start + 1, start, start - 1, start - 2].map((y) => `${y}-${y + 1}`);
}
export function formatAmount(amount) {
  if (amount === null || amount === undefined) return '—';
  const [int, dec] = String(amount).split('.');
  return `${Number(int).toLocaleString('fr-FR')},${dec} DT`;
}
