/** Helpers shared by the layouts. */
import { h } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { api } from '../services/api.js';
import { session } from '../state/session.js';
import { navigate } from '../app/router.js';
import { toast } from '../components/ui.js';
import { stopSync, tellOtherTabs, onStatus } from '../services/sync.js';

export async function logout() {
  stopSync(); // this device closes its own stream before the server ends the session
  tellOtherTabs('logout');
  try {
    await api('/auth/logout', { method: 'POST', silent401: true });
  } catch {
    /* the local session is cleared anyway */
  }
  session.clear();
  navigate('/login', { replace: true });
  toast('Vous êtes déconnecté.', 'info');
}

const STATUS_TEXT = {
  live: 'Synchronisé en direct',
  connecting: 'Connexion…',
  reconnecting: 'Reconnexion…',
  offline: 'Hors ligne',
  off: 'Synchronisation arrêtée',
};

/** Pill shown only when live updates are interrupted. */
export function syncBadge() {
  const el = h('span', { class: 'sync-state', role: 'status', hidden: true });
  onStatus((s) => {
    const show = s === 'reconnecting' || s === 'offline';
    el.hidden = !show;
    el.className = `sync-state${s === 'offline' ? ' sync-state--offline' : ''}`;
    el.replaceChildren(h('span', { class: 'lbl' }, s === 'offline' ? 'Hors ligne' : 'Reconnexion…'));
    el.title = s === 'offline' ? 'Les modifications des autres appareils apparaîtront au retour de la connexion.' : 'La synchronisation reprend automatiquement.';
  });
  return el;
}

/** Discreet line saying whether this device receives live updates. */
export function syncNote() {
  const el = h('span', { class: 'sync-note' });
  onStatus((s) => {
    el.textContent = STATUS_TEXT[s] || '';
    el.className = `sync-note${s === 'live' ? '' : ' sync-note--off'}`;
  });
  return el;
}

export function bareLayout() {
  const main = h('main', { id: 'main', tabindex: '-1' });
  return { root: main, main };
}

export function notFound() {
  return h('section', { class: 'not-found' },
    h('span', { class: 'num', 'aria-hidden': 'true' }, '404'),
    h('h1', { 'data-page-title': '', tabindex: '-1' }, 'Cette page n’existe pas'),
    h('p', { class: 'muted' }, 'Le lien est peut-être incorrect, ou le contenu a été retiré.'),
    h('a', { class: 'btn', href: session.homePath(), 'data-link': '' }, session.user ? 'Retour à l’accueil' : 'Aller à la connexion'));
}

export function forbidden() {
  return h('section', { class: 'not-found' },
    h('span', { class: 'num', 'aria-hidden': 'true' }, '403'),
    h('h1', { 'data-page-title': '', tabindex: '-1' }, 'Accès réservé à l’administration'),
    h('p', { class: 'muted' }, 'Votre compte membre ne permet pas d’ouvrir cette page.'),
    h('a', { class: 'btn', href: session.homePath(), 'data-link': '' }, icon('home'), 'Retour à l’accueil'));
}
