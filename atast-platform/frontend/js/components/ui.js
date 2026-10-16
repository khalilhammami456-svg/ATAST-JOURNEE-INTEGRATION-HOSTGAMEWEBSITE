/** Reusable UI components (chapter "Components"). */
import { h, replace, clear, nextId } from './dom.js';
import { icon } from './icons.js';
import { emptyArt } from './brand.js';
import {
  TYPE_LABELS, TYPE_SHORT, EVENT_STATUS, REQUEST_STATUS, SUGGESTION_STATUS, MEMBER_STATUS,
  PARTICIPATION_STATUS, SUBSCRIPTION_STATUS, IMPORT_ROW_STATUS, dayParts, formatTime, formatPrice, pointsLabel, isPast,
} from '../services/format.js';

// ------------------------------------------------------------------ Toast
export function toast(message, kind = 'success', { timeout = 5000, action } = {}) {
  const host = document.getElementById('toasts');
  const close = () => {
    el.remove();
  };
  const actionBtn = action ? h('button', { class: 'toast__action', type: 'button', onClick: () => { close(); action.onClick(); } }, action.label) : null;
  const el = h('div', { class: ['toast', `toast--${kind}`], role: kind === 'error' ? 'alert' : undefined },
    icon(kind === 'error' ? 'alert' : kind === 'info' ? 'info' : 'check'),
    h('div', { class: 'toast__body' }, h('span', message), actionBtn),
    h('button', { class: 'icon-btn toast__close', type: 'button', 'aria-label': 'Fermer la notification', onClick: close }, icon('close')));
  host.append(el);
  if (timeout) setTimeout(close, kind === 'error' ? timeout * 1.6 : timeout);
}

// ------------------------------------------------------------------ Modal & dialogs
const FOCUSABLE = 'a[href], button:not([disabled]), input:not([disabled]):not([type="hidden"]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export function openModal({ title, description, body, actions = [], onClose, size } = {}) {
  const titleId = nextId('mt');
  const descId = description ? nextId('md') : undefined;
  const previous = document.activeElement;
  const dialog = h('div', { class: 'modal', role: 'dialog', 'aria-modal': 'true', 'aria-labelledby': titleId, 'aria-describedby': descId },
    h('div', { class: 'modal__head' },
      h('h2', { id: titleId }, title),
      h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Fermer', onClick: () => close() }, icon('close'))),
    h('div', { class: 'modal__body' }, description ? h('p', { id: descId, class: 'muted' }, description) : null, body),
    actions.length ? h('div', { class: 'modal__foot' }, actions) : null);
  if (size === 'lg') dialog.style.setProperty('width', 'min(680px, 100%)');
  const backdrop = h('div', { class: 'modal-backdrop', onMousedown: (e) => { if (e.target === backdrop) close(); } }, dialog);

  function onKey(e) {
    if (e.key === 'Escape') { e.preventDefault(); close(); }
    if (e.key === 'Tab') {
      const items = [...dialog.querySelectorAll(FOCUSABLE)];
      if (!items.length) return;
      const first = items[0]; const last = items[items.length - 1];
      if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
      else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
    }
  }
  let closed = false;
  function close(result) {
    if (closed) return;
    closed = true;
    document.removeEventListener('keydown', onKey);
    backdrop.remove();
    document.body.classList.remove('no-scroll');
    if (previous && previous.isConnected) previous.focus();
    onClose?.(result);
  }
  document.addEventListener('keydown', onKey);
  document.body.append(backdrop);
  document.body.classList.add('no-scroll');
  const autofocus = dialog.querySelector('[autofocus]') || dialog.querySelector('.modal__body ' + FOCUSABLE) || dialog.querySelector('.modal__foot .btn:last-child');
  (autofocus || dialog).focus();
  return { close, dialog };
}

/** Confirmation dialog — resolves true/false. */
export function confirmDialog({ title, message, confirmLabel, danger = false, cancelLabel = 'Annuler' }) {
  return new Promise((resolve) => {
    let result = false;
    const m = openModal({
      title,
      body: h('p', message),
      actions: [
        h('button', { class: 'btn btn--secondary', type: 'button', onClick: () => m.close() }, cancelLabel),
        h('button', { class: ['btn', danger ? 'btn--danger' : ''], type: 'button', onClick: () => { result = true; m.close(); } }, confirmLabel),
      ],
      onClose: () => resolve(result),
    });
  });
}

// ------------------------------------------------------------------ Badges
export function typeBadge(type, { short = false } = {}) {
  return h('span', { class: ['badge', `badge--${type}`] }, short ? TYPE_SHORT[type] : TYPE_LABELS[type]);
}
export function pointsChip(points, { withSign = true } = {}) {
  return h('span', { class: ['points', points === 0 && 'points--zero'] }, withSign ? pointsLabel(points) : `${points} pts`);
}
const STATUS_MAPS = { event: EVENT_STATUS, request: REQUEST_STATUS, suggestion: SUGGESTION_STATUS, member: MEMBER_STATUS, participation: PARTICIPATION_STATUS, subscription: SUBSCRIPTION_STATUS };
export function statusPill(kind, status) {
  return h('span', { class: ['status', `status--${status}`] }, STATUS_MAPS[kind][status] || status);
}
/** Outcome of one imported spreadsheet row. */
export function rowPill(status) {
  return h('span', { class: ['status', `status--ROW_${status}`] }, IMPORT_ROW_STATUS[status] || status);
}
/** Paid / unpaid badge for the subscription of a season. */
export function paidPill(paid) {
  return h('span', { class: ['status', paid ? 'status--CLAIMED' : 'status--UNPAID'] }, paid ? 'Payée' : 'Non payée');
}

// ------------------------------------------------------------------ Avatar
export function avatar(person, { size = '', decorative = true } = {}) {
  return h('img', {
    class: ['avatar', size && `avatar--${size}`],
    src: person?.avatarUrl || '/assets/default-avatar.svg',
    alt: decorative ? '' : (person?.avatarUrl ? `Photo de ${person.name}` : `${person?.name || 'Membre'} n'a pas encore de photo`),
    loading: 'lazy',
    decoding: 'async',
    width: 40,
    height: 40,
  });
}

// ------------------------------------------------------------------ States
export function emptyState({ title, text, action }) {
  return h('div', { class: 'empty' }, emptyArt(), h('h3', title), text ? h('p', text) : null, action || null);
}
export function errorState(err, retry) {
  return h('div', { class: 'error-state', role: 'alert' },
    h('div', { class: 'row' }, icon('alert'), h('b', err?.message || 'Une erreur est survenue.')),
    retry ? h('button', { class: 'btn btn--secondary btn--sm', type: 'button', onClick: retry }, 'Réessayer') : null);
}
export function skeletons(kind = 'card', count = 3) {
  return h('div', { class: kind === 'card' ? 'event-grid' : 'stack', 'aria-busy': 'true' },
    h('span', { class: 'sr-only', role: 'status' }, 'Chargement…'),
    Array.from({ length: count }, () => h('div', { class: ['skeleton', `skeleton--${kind}`] })));
}

/** Loads data into a container with loading / error / retry states. */
let quietDepth = 0;
/** Runs a list refresh without the loading skeleton (used by live updates). */
export function quietly(fn) {
  quietDepth += 1;
  try {
    return fn();
  } finally {
    quietDepth -= 1;
  }
}

export async function load(container, fetcher, render, { skeleton = 'card', count = 3, quiet = quietDepth > 0 } = {}) {
  // quiet: live refresh — keep the current content until the new data arrives, no skeleton flash.
  if (!quiet) replace(container, skeletons(skeleton, count));
  try {
    const data = await fetcher();
    replace(container, render(data));
    return data;
  } catch (err) {
    if (err.status === 401 || quiet) return null;
    replace(container, errorState(err, () => load(container, fetcher, render, { skeleton, count })));
    return null;
  }
}

// ------------------------------------------------------------------ Pagination
export function pagination({ page, totalPages, total }, onPage, noun = ['élément', 'éléments']) {
  if (totalPages <= 1) return null;
  return h('nav', { class: 'pagination', 'aria-label': 'Pagination' },
    h('button', { class: 'btn btn--secondary btn--sm', type: 'button', disabled: page <= 1, onClick: () => onPage(page - 1) }, icon('left'), 'Précédent'),
    h('span', { class: 'pagination__info' }, `Page ${page} sur ${totalPages}`, h('span', { class: 'sr-only' }, ` (${total} ${total > 1 ? noun[1] : noun[0]})`)),
    h('button', { class: 'btn btn--secondary btn--sm', type: 'button', disabled: page >= totalPages, onClick: () => onPage(page + 1) }, 'Suivant', icon('right')));
}

// ------------------------------------------------------------------ Forms
/**
 * Builds a labelled control with hint and error slots wired for screen readers.
 * Returns the wrapper; the control is wrapper.control.
 */
export function field({ label, name, type = 'text', value = '', required = false, optional = false, hint, autocomplete, multiline = false, maxlength, options, placeholder, inputmode, min, max, rows, step, readonly, span }) {
  const id = nextId(name);
  const hintId = hint ? `${id}-hint` : null;
  const errId = `${id}-err`;
  const describedby = [hintId, errId].filter(Boolean).join(' ');
  let control;
  const common = { id, name, required, 'aria-describedby': describedby, autocomplete, placeholder, readonly };
  if (options) {
    control = h('select', { ...common, class: 'select' }, options.map(([v, l]) => h('option', { value: v, selected: String(v) === String(value) }, l)));
  } else if (multiline) {
    control = h('textarea', { ...common, class: 'textarea', maxlength, rows: rows || 5 }, value || '');
  } else {
    control = h('input', { ...common, class: 'input', type, value: value ?? '', maxlength, inputmode, min, max, step });
  }
  const wrap = h('div', { class: ['field', span && 'span-2'] },
    h('label', { for: id }, label, optional ? h('span', { class: 'optional' }, ' (facultatif)') : null),
    hint ? h('div', { id: hintId, class: 'hint' }, hint) : null,
    control,
    h('div', { id: errId, class: 'field-error', 'aria-live': 'polite' }));
  if (multiline && maxlength) {
    const counter = h('div', { class: 'counter', 'aria-hidden': 'true' });
    const upd = () => { counter.textContent = `${control.value.length} / ${maxlength}`; };
    control.addEventListener('input', upd);
    upd();
    wrap.append(counter);
  }
  wrap.control = control;
  // An error disappears as soon as the person edits the field.
  control.addEventListener('input', () => {
    if (control.getAttribute('aria-invalid') !== 'true') return;
    control.removeAttribute('aria-invalid');
    wrap.querySelector('.field-error').textContent = '';
  });
  return wrap;
}

export function passwordField(opts) {
  const wrap = field({ ...opts, type: 'password' });
  const input = wrap.control;
  const toggle = h('button', { class: 'icon-btn', type: 'button', 'aria-label': 'Afficher le mot de passe', 'aria-pressed': 'false' }, icon('eye'));
  toggle.addEventListener('click', () => {
    const show = input.type === 'password';
    input.type = show ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', String(show));
    toggle.setAttribute('aria-label', show ? 'Masquer le mot de passe' : 'Afficher le mot de passe');
    replace(toggle, icon(show ? 'eyeOff' : 'eye'));
  });
  const group = h('div', { class: 'input-group' });
  input.replaceWith(group);
  group.append(input, toggle);
  return wrap;
}

export function clearErrors(form) {
  form.querySelectorAll('[aria-invalid="true"]').forEach((el) => el.removeAttribute('aria-invalid'));
  form.querySelectorAll('.field-error').forEach((el) => clear(el));
  form.querySelector('.form-alert')?.remove();
}

/** Shows server/client validation errors next to the matching fields. */
export function showErrors(form, err) {
  clearErrors(form);
  const fields = err?.fields || {};
  let first = null;
  const orphan = [];
  for (const [name, message] of Object.entries(fields)) {
    const input = form.querySelector(`[name="${CSS.escape(name)}"]`);
    if (!input) { orphan.push(message); continue; }
    input.setAttribute('aria-invalid', 'true');
    const errEl = form.querySelector(`#${CSS.escape(input.id)}-err`) || input.closest('.field, fieldset')?.querySelector('.field-error');
    if (errEl) errEl.textContent = message;
    first ||= input;
  }
  if (!Object.keys(fields).length || orphan.length) {
    const msg = orphan.length ? orphan.join(' ') : (err?.message || 'Une erreur est survenue.');
    form.prepend(h('div', { class: 'alert alert--error form-alert', role: 'alert' }, icon('alert'), h('p', msg)));
    if (!first) form.querySelector('.form-alert')?.scrollIntoView({ block: 'nearest' });
  }
  first?.focus();
}

export async function withBusy(button, fn) {
  if (button.classList.contains('is-loading')) return undefined;
  button.classList.add('is-loading');
  button.setAttribute('aria-busy', 'true');
  try {
    return await fn();
  } finally {
    button.classList.remove('is-loading');
    button.removeAttribute('aria-busy');
  }
}

export function formData(form) {
  const out = {};
  for (const [k, v] of new FormData(form).entries()) if (typeof v === 'string') out[k] = v;
  return out;
}

export function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

export function searchBox({ label, placeholder, value = '', onSearch }) {
  const id = nextId('search');
  const input = h('input', { id, class: 'input', type: 'search', placeholder, value, autocomplete: 'off' });
  input.addEventListener('input', debounce(() => onSearch(input.value.trim()), 300));
  return h('div', { class: 'input-icon', role: 'search' }, h('label', { for: id, class: 'sr-only' }, label), icon('search'), input);
}

export function chipGroup({ label, options, value, onChange }) {
  const group = h('div', { class: 'chips', role: 'group', 'aria-label': label });
  const render = (current) => {
    replace(group, options.map(([v, text]) => h('button', {
      class: 'chip', type: 'button', 'aria-pressed': String(v === current),
      onClick: () => { render(v); onChange(v); },
    }, text)));
  };
  render(value);
  return group;
}

// ------------------------------------------------------------------ Page chrome
export function pageHead({ title, lead, actions, back }) {
  return h('div', {},
    back ? h('a', { class: 'back-link', href: back.href, 'data-link': '' }, icon('left'), back.label) : null,
    h('header', { class: 'page-head' },
      h('div', {}, h('h1', { tabindex: '-1', 'data-page-title': '' }, title), lead ? h('p', lead) : null),
      actions ? h('div', { class: 'row' }, actions) : null));
}

// ------------------------------------------------------------------ Domain cards
export function dateBlock(ymd) {
  const p = dayParts(ymd);
  return h('div', { class: ['date-block', isPast(ymd) && 'date-block--past'], 'aria-hidden': 'true' },
    h('span', { class: 'd' }, p.day), h('span', { class: 'm' }, p.month));
}

export function eventCard(e, { href } = {}) {
  const meta = h('div', { class: 'event-card__meta' },
    h('span', icon('clock'), h('span', { class: 'truncate' }, `${new Intl.DateTimeFormat('fr-FR', { weekday: 'short', day: 'numeric', month: 'short', timeZone: 'UTC' }).format(new Date(`${e.date}T12:00:00Z`))}, ${formatTime(e.time)}`)),
    h('span', icon('pin'), h('span', { class: 'truncate' }, e.location)));
  const foot = h('div', { class: 'event-card__foot' },
    typeBadge(e.type), pointsChip(e.points),
    h('span', { class: 'small muted' }, formatPrice(e)),
    e.myParticipation ? statusPill('participation', e.myParticipation) : null);
  const body = h('div', { class: 'grow' }, h('h3', { class: 'event-card__title' }, e.title), meta, foot);
  const link = href || `/events/${e.id}`;
  if (e.imageUrl) {
    return h('a', { class: 'event-card event-card--image', href: link, 'data-link': '' },
      h('img', { class: 'event-card__img', src: e.imageUrl, alt: '', loading: 'lazy', decoding: 'async' }),
      h('div', { class: 'event-card__inner' }, dateBlock(e.date), body));
  }
  return h('a', { class: ['event-card', isPast(e.date) && 'event-card--muted'], href: link, 'data-link': '' }, dateBlock(e.date), body);
}

const SOCIAL_NAMES = { instagram: 'Instagram', facebook: 'Facebook', github: 'GitHub', linkedin: 'LinkedIn' };
export function socialLinks(socials) {
  const items = Object.entries(socials || {}).filter(([, url]) => url);
  if (!items.length) return null;
  return h('div', { class: 'socials' }, items.map(([k, url]) => h('a', {
    class: 'social-link', href: url, target: '_blank', rel: 'noopener noreferrer nofollow',
  }, icon('link'), SOCIAL_NAMES[k], h('span', { class: 'sr-only' }, ' (nouvel onglet)'))));
}

export function memberCard(m, { href, extra } = {}) {
  return h('a', { class: 'member-card', href: href || `/members/${m.id}`, 'data-link': '' },
    avatar(m, { size: 'lg' }),
    h('div', { class: 'grow' },
      h('div', { class: 'member-card__name' }, m.name),
      m.description ? h('div', { class: 'member-card__desc' }, m.description) : h('div', { class: 'member-card__desc' }, 'Membre ATAST'),
      extra || null));
}
