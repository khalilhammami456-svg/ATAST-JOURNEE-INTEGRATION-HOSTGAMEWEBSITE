/** History-API router with role guards (UX only — the API enforces permissions). */
import { h, replace } from '../components/dom.js';
import { session } from '../state/session.js';
import { errorState, skeletons, toast } from '../components/ui.js';

let routes = [];
let layouts = {};
let currentLayoutKey = null;
let currentLayout = null;
let renderToken = 0;
let current = null; // { page, ctx, title }
// Live-update handlers registered by the page currently displayed.
let scope = { handlers: [], warned: false };
const appRoot = () => document.getElementById('app');

function compile(path) {
  const keys = [];
  const re = new RegExp(`^${path.replace(/:([a-z]+)/g, (_, k) => { keys.push(k); return '([0-9a-f-]{36})'; })}/?$`);
  return { re, keys };
}

export function defineRoutes(list, layoutFactories) {
  routes = list.map((r) => ({ ...r, ...compile(r.path) }));
  layouts = layoutFactories;
}

export function navigate(to, { replace: rep = false } = {}) {
  const url = new URL(to, location.origin);
  if (url.pathname + url.search === location.pathname + location.search && !rep) {
    render();
    return;
  }
  history[rep ? 'replaceState' : 'pushState']({}, '', url.pathname + url.search + url.hash);
  render();
}

function match(pathname) {
  for (const r of routes) {
    const m = r.re.exec(pathname);
    if (m) return { route: r, params: Object.fromEntries(r.keys.map((k, i) => [k, m[i + 1]])) };
  }
  return null;
}

function layoutFor(route) {
  if (!route || route.guard === 'guest') return route ? 'bare' : (session.user ? (session.isAdmin ? 'admin' : 'member') : 'bare');
  return session.isAdmin ? 'admin' : 'member';
}

export async function render() {
  const token = ++renderToken;
  const { pathname, search } = location;
  const found = match(pathname);
  const route = found?.route;

  // ---- Guards
  if (route?.redirect) return navigate(route.redirect(), { replace: true });
  if (route && route.guard !== 'guest' && route.guard !== 'public' && !session.user) {
    const next = encodeURIComponent(pathname + search);
    return navigate(`/login?next=${next}`, { replace: true });
  }
  if (route?.guard === 'guest' && session.user) return navigate(session.homePath(), { replace: true });
  if (route?.guard === 'member' && session.isAdmin && route.adminRedirect) return navigate(route.adminRedirect, { replace: true });

  // ---- Layout (kept between navigations when unchanged)
  const key = layoutFor(route);
  if (key !== currentLayoutKey) {
    currentLayout = layouts[key]();
    currentLayoutKey = key;
    replace(appRoot(), currentLayout.root);
  }
  currentLayout.update?.(pathname);
  const main = currentLayout.main;

  let page;
  let title;
  if (!route) {
    page = layouts.notFound;
    title = 'Page introuvable';
  } else if (route.guard === 'admin' && !session.isAdmin) {
    page = layouts.forbidden;
    title = 'Accès réservé';
  } else {
    page = route.page;
    title = route.title;
  }

  scope = { handlers: [], warned: false };
  if (route?.live && page === route.page) onLive(route.live, () => softRender(), { page: true });
  replace(main, skeletons('row', 4));
  main.setAttribute('aria-busy', 'true');
  const ctx = {
    params: found?.params || {},
    query: Object.fromEntries(new URLSearchParams(search)),
    setTitle: (t) => { document.title = `${t} | ATAST`; },
  };
  document.title = `${title} | ATAST`;
  let content;
  try {
    content = await page(ctx);
  } catch (err) {
    if (token !== renderToken) return;
    if (err.status === 401) return;
    content = err.status === 404 ? layouts.notFound() : h('div', { class: 'page-wrap' }, errorState(err, () => render()));
  }
  if (token !== renderToken) return;
  current = { page, ctx, title, route };
  main.removeAttribute('aria-busy');
  replace(main, content);
  window.scrollTo(0, 0);
  const heading = main.querySelector('[data-page-title]') || main.querySelector('h1');
  if (heading) {
    if (!heading.hasAttribute('tabindex')) heading.setAttribute('tabindex', '-1');
    heading.focus({ preventScroll: true });
  }
}

// ------------------------------------------------------------------ live updates
/**
 * Registers a refresh for the page on screen. It runs when the server reports a
 * change on one of `topics` (from any device), and is forgotten on navigation.
 * `container` limits the "is the person busy here?" check to one region.
 */
export function onLive(topics, fn, { container = null, page = false } = {}) {
  const owner = scope;
  owner.handlers.push({ topics, fn, container, page, timer: null, owner });
}

const EDITABLE = 'input, textarea, select, [contenteditable="true"]';

function busyIn(region) {
  if (document.querySelector('.modal-backdrop')) return 'modal';
  const active = document.activeElement;
  const root = region || currentLayout?.main;
  if (root && root.querySelector('form[data-dirty]')) return 'dirty';
  if (root && active && root.contains(active) && active.matches(EDITABLE)) return 'typing';
  return null;
}

function run(handler) {
  clearTimeout(handler.timer);
  handler.timer = setTimeout(() => {
    if (handler.owner !== scope) return; // page changed meanwhile
    const busy = busyIn(handler.container);
    if (busy) {
      if (busy === 'dirty' && handler.page && !scope.warned) {
        scope.warned = true;
        toast('Des informations de cette page ont changé ailleurs. Vos saisies en cours sont conservées.', 'info', {
          timeout: 0,
          action: { label: 'Actualiser', onClick: () => { currentLayout?.main.querySelectorAll('form[data-dirty]').forEach((f) => delete f.dataset.dirty); run(handler); } },
        });
      }
      handler.timer = setTimeout(() => run(handler), 1500);
      return;
    }
    handler.fn();
  }, 250);
}

/** Called by the sync client for every change notice. */
export function dispatchChange(change) {
  for (const handler of scope.handlers) {
    if (handler.topics.some((t) => change.topics.includes(t))) run(handler);
  }
}

/** Re-renders the current page in place: same scroll position, no loading state. */
async function softRender() {
  if (!current || !currentLayout) return;
  const token = renderToken;
  const main = currentLayout.main;
  const previous = scope;
  scope = { handlers: [], warned: previous.warned };
  if (current.route?.live) onLive(current.route.live, () => softRender(), { page: true });
  let content;
  try {
    content = await current.page(current.ctx);
  } catch (err) {
    if (token !== renderToken) return;
    if (err.status === 404) {
      content = layouts.notFound();
    } else {
      scope = previous; // keep the page as it is and its live handlers
      return;
    }
  }
  if (token !== renderToken) return;
  const y = window.scrollY;
  const hadFocus = main.contains(document.activeElement);
  replace(main, content);
  window.scrollTo(0, y);
  if (hadFocus) main.focus({ preventScroll: true });
}

export function startRouter() {
  // Track forms with unsaved input so a live refresh never wipes them.
  const markDirty = (e) => {
    const form = e.target.closest?.('form');
    if (form) form.dataset.dirty = '1';
  };
  document.addEventListener('input', markDirty, true);
  document.addEventListener('change', markDirty, true);
  document.addEventListener('reset', (e) => { delete e.target.dataset.dirty; }, true);

  window.addEventListener('popstate', render);
  document.addEventListener('click', (e) => {
    if (e.defaultPrevented || e.button !== 0 || e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
    const a = e.target.closest('a[data-link]');
    if (!a || a.target === '_blank') return;
    const url = new URL(a.href, location.origin);
    if (url.origin !== location.origin) return;
    e.preventDefault();
    navigate(url.pathname + url.search);
  });
  render();
}
