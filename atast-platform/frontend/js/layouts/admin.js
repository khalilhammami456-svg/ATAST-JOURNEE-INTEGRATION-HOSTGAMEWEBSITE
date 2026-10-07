/** Admin interface shell: navy sidebar (drawer on small screens). */
import { h, replace } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { brand } from '../components/brand.js';
import { avatar } from '../components/ui.js';
import { session } from '../state/session.js';
import { api } from '../services/api.js';
import { logout, syncBadge, syncNote } from './shared.js';

const counts = { requests: null, suggestions: null };
const countEls = { requests: [], suggestions: [] };

/** Re-reads the pending counters shown in the sidebar (called after reviews). */
export async function refreshAdminCounts() {
  try {
    const s = await api('/admin/stats');
    counts.requests = s.pendingRequests;
    counts.suggestions = s.newSuggestions;
    paintCounts();
    return s;
  } catch {
    return null;
  }
}
function paintCounts() {
  for (const key of Object.keys(countEls)) {
    for (const el of countEls[key]) {
      const n = counts[key];
      el.hidden = !n;
      el.textContent = n ? String(n) : '';
      el.setAttribute('aria-label', n ? `${n} en attente` : '');
    }
  }
}

const GROUPS = [
  ['Gestion du club', [
    ['/admin', 'Tableau de bord', 'dashboard'],
    ['/admin/requests', 'Demandes d’adhésion', 'inbox', 'requests'],
    ['/admin/members', 'Membres', 'users'],
    ['/admin/subscriptions', 'Cotisations', 'ticket'],
    ['/admin/events', 'Événements', 'calendar'],
    ['/admin/messages', 'Messages', 'send'],
    ['/admin/suggestions', 'Suggestions', 'bulb', 'suggestions'],
  ]],
  ['Espace club', [
    ['/scoreboard', 'Classement', 'trophy'],
    ['/profile', 'Mon profil', 'user'],
  ]],
];

export function adminLayout() {
  countEls.requests = [];
  countEls.suggestions = [];
  const links = [];
  const sidebarId = 'admin-sidebar';
  const closeBtn = h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fermer la navigation', onClick: () => close(true) }, icon('close'));
  closeBtn.style.setProperty('color', '#fff');
  const userSlot = h('div', { class: 'side-user' });
  const note = syncNote();

  const sidebar = h('aside', { id: sidebarId, class: 'sidebar', 'aria-label': 'Navigation administration' },
    h('div', { class: 'row row--between' }, brand({ href: '/admin', sub: 'Administration' }), closeBtn),
    h('nav', { 'aria-label': 'Administration' },
      GROUPS.map(([title, items]) => h('div', { class: 'side-group' },
        h('div', { class: 'side-title' }, title),
        items.map(([href, label, ic, countKey]) => {
          const count = countKey ? h('span', { class: 'count', hidden: true }) : null;
          if (countKey) countEls[countKey].push(count);
          const a = h('a', { class: 'side-link', href, 'data-link': '' }, icon(ic), label, count);
          links.push(a);
          return a;
        })))),
    h('div', { class: 'sidebar__foot' },
      userSlot,
      h('button', { class: 'side-link', type: 'button', onClick: logout }, icon('logout'), 'Se déconnecter')));

  const scrim = h('div', { class: 'sidebar-scrim', hidden: true, onClick: () => close() });
  const toggle = h('button', {
    class: 'icon-btn', type: 'button', 'aria-label': 'Ouvrir la navigation', 'aria-expanded': 'false', 'aria-controls': sidebarId,
    onClick: () => open(),
  }, icon('menu'));

  function open() {
    sidebar.classList.add('is-open');
    scrim.hidden = false;
    toggle.setAttribute('aria-expanded', 'true');
    sidebar.querySelector('.side-link').focus();
    document.addEventListener('keydown', onKey);
  }
  function close(returnFocus = false) {
    if (!sidebar.classList.contains('is-open')) return;
    sidebar.classList.remove('is-open');
    scrim.hidden = true;
    toggle.setAttribute('aria-expanded', 'false');
    document.removeEventListener('keydown', onKey);
    if (returnFocus) toggle.focus();
  }
  function onKey(e) {
    if (e.key === 'Escape') close(true);
  }

  function paintUser() {
    const u = session.user;
    if (!u) return;
    replace(userSlot, avatar(u), h('div', {}, h('b', u.name), h('small', 'Administrateur'), h('div', {}, note)));
  }
  session.subscribe(paintUser);
  paintUser();
  paintCounts();
  refreshAdminCounts();

  const main = h('main', { id: 'main', class: 'page', tabindex: '-1' });
  const root = h('div', { class: 'admin-shell' },
    sidebar, scrim,
    h('div', { class: 'admin-main' },
      h('header', { class: 'admin-top' }, toggle, brand({ href: '/admin', sub: 'Administration' }), h('span', { class: 'grow' }), syncBadge()),
      main));

  return {
    root,
    main,
    update(path) {
      close();
      for (const a of links) {
        const href = a.getAttribute('href');
        const active = path === href || (href !== '/admin' && path.startsWith(`${href}/`));
        if (active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
      }
    },
  };
}
