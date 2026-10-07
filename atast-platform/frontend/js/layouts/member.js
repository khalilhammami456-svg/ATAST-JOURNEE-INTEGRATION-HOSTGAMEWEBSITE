/** Member interface shell: top bar + menu opened from the icon at top right (FR-18). */
import { h, replace } from '../components/dom.js';
import { icon } from '../components/icons.js';
import { brand } from '../components/brand.js';
import { avatar } from '../components/ui.js';
import { session } from '../state/session.js';
import { api } from '../services/api.js';
import { logout, syncBadge, syncNote } from './shared.js';

const LINKS = [
  ['/home', 'Accueil', 'home'],
  ['/events', 'Événements', 'calendar'],
  ['/members', 'Membres', 'users'],
  ['/suggestions', 'Boîte à suggestions', 'bulb'],
  ['/scoreboard', 'Classement', 'trophy'],
  ['/profile', 'Mon profil', 'user'],
];

export function memberLayout() {
  const menuId = 'member-menu';
  const note = syncNote();
  const scoreSlot = h('div', { class: 'row' });
  const whoSlot = h('div', { class: 'member-menu__who' });
  const links = LINKS.map(([href, label, ic]) => h('a', { class: 'menu-link', href, 'data-link': '' }, icon(ic), label));
  const menu = h('div', { id: menuId, class: 'member-menu', hidden: true },
    whoSlot,
    h('nav', { 'aria-label': 'Menu principal' },
      links,
      h('div', { class: 'menu-sep', role: 'separator' }),
      h('button', { class: 'menu-link menu-link--danger', type: 'button', onClick: () => { closeMenu(); logout(); } }, icon('logout'), 'Se déconnecter')));
  const btn = h('button', {
    class: 'icon-btn menu-btn', type: 'button', 'aria-label': 'Ouvrir le menu', 'aria-expanded': 'false', 'aria-controls': menuId,
    onClick: () => (menu.hidden ? openMenu() : closeMenu()),
  }, icon('menu'));

  function openMenu() {
    menu.hidden = false;
    btn.setAttribute('aria-expanded', 'true');
    btn.setAttribute('aria-label', 'Fermer le menu');
    replace(btn, icon('close'));
    (menu.querySelector('[aria-current="page"]') || menu.querySelector('.menu-link')).focus();
    document.addEventListener('keydown', onKey);
    document.addEventListener('mousedown', onOutside);
  }
  function closeMenu(returnFocus = false) {
    if (menu.hidden) return;
    menu.hidden = true;
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-label', 'Ouvrir le menu');
    replace(btn, icon('menu'));
    document.removeEventListener('keydown', onKey);
    document.removeEventListener('mousedown', onOutside);
    if (returnFocus) btn.focus();
  }
  function onKey(e) {
    if (e.key === 'Escape') closeMenu(true);
    if (e.key === 'ArrowDown' || e.key === 'ArrowUp') {
      const items = [...menu.querySelectorAll('.menu-link')];
      const i = items.indexOf(document.activeElement);
      e.preventDefault();
      items[(i + (e.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length].focus();
    }
  }
  function onOutside(e) {
    if (!menu.contains(e.target) && !btn.contains(e.target)) closeMenu();
  }

  function paintUser() {
    const u = session.user;
    if (!u) return;
    const p = session.profile;
    replace(whoSlot, avatar(u), h('div', {}, h('b', u.name), h('span', { class: 'small muted' }, p ? `${p.score} points` : 'Membre ATAST'), h('div', {}, note)));
    replace(scoreSlot, h('a', { class: 'score-chip', href: '/profile', 'data-link': '', 'aria-label': p ? `Mon profil, ${p.score} points` : 'Mon profil' },
      p ? h('span', { class: 'num' }, String(p.score)) : null,
      p ? h('span', { class: 'lbl' }, 'pts') : null,
      avatar(u, { size: 'sm' })));
  }
  session.subscribe(paintUser);
  paintUser();
  if (session.isMember && !session.profile) {
    api('/members/me').then((p) => session.setProfile(p)).catch(() => {});
  }

  const main = h('main', { id: 'main', class: 'page', tabindex: '-1' });
  const root = h('div', { class: 'member-shell' },
    h('header', { class: 'topbar' },
      h('div', { class: 'topbar__inner' },
        brand({ href: '/home' }),
        h('div', { class: 'topbar__right' }, syncBadge(), scoreSlot, btn))),
    menu,
    main);

  return {
    root,
    main,
    update(path) {
      closeMenu();
      for (const a of links) {
        const href = a.getAttribute('href');
        const active = path === href || (href !== '/home' && path.startsWith(`${href}/`));
        if (active) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
      }
    },
  };
}
