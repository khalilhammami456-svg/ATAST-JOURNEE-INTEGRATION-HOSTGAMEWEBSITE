'use strict';
/**
 * Server-side validation (NFR-01, chapter "Validation and Error Handling").
 * Every validator returns a *clean* object containing only allowed fields
 * (unknown fields are dropped => no mass-assignment of role, score, status…).
 */
const config = require('../config');
const { errors } = require('../utils');

const EVENT_TYPES = ['SMALL', 'MEDIUM', 'BIG', 'MEETING'];
const EVENT_STATUSES = ['DRAFT', 'PUBLISHED', 'COMPLETED', 'ARCHIVED'];
const SUGGESTION_STATUSES = ['NEW', 'READ', 'IN_REVIEW', 'RESOLVED'];

/** Collects field errors, throws a single 422 at the end. */
class Checker {
  constructor(body) {
    this.body = body && typeof body === 'object' ? body : {};
    this.out = {};
    this.fields = {};
  }
  fail(field, message) {
    if (!this.fields[field]) this.fields[field] = message;
  }
  raw(field) {
    const v = this.body[field];
    return v === undefined || v === null ? '' : v;
  }
  str(field, { required = false, min = 0, max = 255, label = 'Ce champ', multiline = false } = {}) {
    let v = this.raw(field);
    if (typeof v !== 'string') v = String(v);
    v = multiline ? v.replace(/\r\n/g, '\n').trim() : v.replace(/\s+/g, ' ').trim();
    // Strip control characters (except newlines/tabs in multiline text)
    v = v.replace(multiline ? /[\u0000-\u0008\u000B\u000C\u000E-\u001F\u007F]/g : /[\u0000-\u001F\u007F]/g, '');
    if (!v) {
      if (required) this.fail(field, `${label} est obligatoire.`);
      this.out[field] = null;
      return null;
    }
    if (v.length < min) this.fail(field, `${label} doit contenir au moins ${min} caractères.`);
    if (v.length > max) this.fail(field, `${label} ne doit pas dépasser ${max} caractères.`);
    this.out[field] = v;
    return v;
  }
  oneOf(field, values, { required = true, label = 'Ce champ', fallback } = {}) {
    const v = String(this.raw(field) || '').trim().toUpperCase();
    if (!v) {
      if (fallback !== undefined) return (this.out[field] = fallback);
      if (required) this.fail(field, `${label} est obligatoire.`);
      return (this.out[field] = null);
    }
    if (!values.includes(v)) this.fail(field, `${label} n'est pas une valeur autorisée.`);
    return (this.out[field] = v);
  }
  done() {
    if (Object.keys(this.fields).length) throw errors.validation(this.fields);
    return this.out;
  }
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;

function email(c, field = 'email') {
  const v = c.str(field, { required: true, max: 254, label: "L'adresse email" });
  if (v && !EMAIL_RE.test(v)) c.fail(field, "L'adresse email n'est pas valide.");
  if (v) c.out[field] = v.toLowerCase();
}

function password(c, field = 'password', label = 'Le mot de passe') {
  const v = typeof c.body[field] === 'string' ? c.body[field] : '';
  if (!v) return c.fail(field, `${label} est obligatoire.`);
  if (v.length < 8) return c.fail(field, `${label} doit contenir au moins 8 caractères.`);
  if (v.length > 128) return c.fail(field, `${label} ne doit pas dépasser 128 caractères.`);
  if (!/[A-Za-z]/.test(v) || !/[0-9]/.test(v)) {
    return c.fail(field, `${label} doit contenir au moins une lettre et un chiffre.`);
  }
  c.out[field] = v;
}

function phone(c, field = 'phone', { required = true } = {}) {
  const v = c.str(field, { required, max: 25, label: 'Le numéro de téléphone' });
  if (!v) return;
  const cleaned = v.replace(/[\s().-]/g, '');
  if (!/^\+?[0-9]{8,15}$/.test(cleaned)) {
    c.fail(field, 'Le numéro de téléphone doit contenir entre 8 et 15 chiffres (ex. +216 20 123 456).');
  } else {
    c.out[field] = cleaned;
  }
}

function name(c, field = 'name') {
  const v = c.str(field, { required: true, min: 2, max: 80, label: 'Le nom' });
  if (v && !/^[\p{L}\p{M}' .-]+$/u.test(v)) {
    c.fail(field, "Le nom ne peut contenir que des lettres, des espaces, des apostrophes et des tirets.");
  }
}

function isRealDate(s) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return false;
  const d = new Date(`${s}T00:00:00Z`);
  return !Number.isNaN(d.getTime()) && d.toISOString().slice(0, 10) === s;
}

// ---------- Auth ----------
function register(body) {
  const c = new Checker(body);
  name(c);
  email(c);
  password(c);
  phone(c);
  const confirm = typeof c.body.passwordConfirm === 'string' ? c.body.passwordConfirm : '';
  if (!confirm) c.fail('passwordConfirm', 'Confirmez le mot de passe.');
  else if (confirm !== c.body.password) c.fail('passwordConfirm', 'Les deux mots de passe ne correspondent pas.');
  return c.done();
}

function login(body) {
  const c = new Checker(body);
  email(c);
  const pw = typeof c.body.password === 'string' ? c.body.password : '';
  if (!pw) c.fail('password', 'Le mot de passe est obligatoire.');
  else if (pw.length > 128) c.fail('password', 'Mot de passe invalide.');
  c.out.password = pw;
  return c.done();
}

function changePassword(body) {
  const c = new Checker(body);
  const current = typeof c.body.currentPassword === 'string' ? c.body.currentPassword : '';
  if (!current) c.fail('currentPassword', 'Le mot de passe actuel est obligatoire.');
  c.out.currentPassword = current;
  password(c, 'newPassword', 'Le nouveau mot de passe');
  if (c.body.newPasswordConfirm !== c.body.newPassword) {
    c.fail('newPasswordConfirm', 'Les deux mots de passe ne correspondent pas.');
  }
  if (current && current === c.body.newPassword) {
    c.fail('newPassword', "Le nouveau mot de passe doit être différent de l'actuel.");
  }
  return c.done();
}

// ---------- Profile ----------
const SOCIAL_HOSTS = {
  instagram: ['instagram.com'],
  facebook: ['facebook.com', 'fb.com'],
  github: ['github.com'],
  linkedin: ['linkedin.com'],
};
const SOCIAL_LABELS = { instagram: 'Instagram', facebook: 'Facebook', github: 'GitHub', linkedin: 'LinkedIn' };

function social(c, field) {
  const v = c.str(field, { max: 200, label: `Le lien ${SOCIAL_LABELS[field]}` });
  if (!v) return;
  let url;
  try {
    url = new URL(/^https?:\/\//i.test(v) ? v : `https://${v}`);
  } catch {
    return c.fail(field, `Le lien ${SOCIAL_LABELS[field]} n'est pas une URL valide.`);
  }
  const host = url.hostname.toLowerCase().replace(/^(www\.|m\.|[a-z]{2}\.)/, '');
  const okHost = SOCIAL_HOSTS[field].some((h) => host === h || host.endsWith(`.${h}`));
  if (url.protocol !== 'https:' && url.protocol !== 'http:') {
    return c.fail(field, `Le lien ${SOCIAL_LABELS[field]} doit commencer par https://`);
  }
  if (!okHost || url.username || url.password || url.pathname.length < 2) {
    return c.fail(field, `Saisissez l'adresse de votre profil ${SOCIAL_LABELS[field]} (ex. https://${SOCIAL_HOSTS[field][0]}/votre-nom).`);
  }
  url.protocol = 'https:';
  url.hash = '';
  c.out[field] = url.toString();
}

function profileUpdate(body) {
  const c = new Checker(body);
  name(c);
  phone(c);
  c.str('description', { max: 600, label: 'La description', multiline: true });
  const b = c.str('birthday', { max: 10, label: 'La date de naissance' });
  if (b) {
    if (!isRealDate(b)) c.fail('birthday', 'La date de naissance doit être une date valide.');
    else {
      const today = new Date().toISOString().slice(0, 10);
      if (b >= today) c.fail('birthday', 'La date de naissance doit être dans le passé.');
      else if (b < '1900-01-01') c.fail('birthday', "La date de naissance n'est pas plausible.");
    }
  }
  for (const s of Object.keys(SOCIAL_HOSTS)) social(c, s);
  return c.done();
}

// ---------- Membership ----------
function rejection(body) {
  const c = new Checker(body);
  c.str('reason', { required: true, min: 3, max: 500, label: 'Le motif du refus', multiline: true });
  return c.done();
}

// ---------- Events ----------
/** Converts "12.500" / "12,5" into minor units (3 decimals for TND, 2 otherwise). */
function parsePrice(raw, currency) {
  const decimals = currency === 'TND' ? 3 : 2;
  const s = String(raw).trim().replace(',', '.');
  const re = new RegExp(`^\\d{1,6}(\\.\\d{1,${decimals}})?$`);
  if (!re.test(s)) return null;
  const [int, frac = ''] = s.split('.');
  return Number(int) * 10 ** decimals + Number(frac.padEnd(decimals, '0'));
}

function eventInput(body, { forUpdate = false } = {}) {
  const c = new Checker(body);
  c.str('title', { required: true, min: 3, max: 120, label: 'Le titre' });
  c.oneOf('type', EVENT_TYPES, { label: 'Le type' });
  c.str('description', { max: 5000, label: 'La description', multiline: true });
  c.out.description = c.out.description || '';
  const date = c.str('date', { required: true, max: 10, label: 'La date' });
  if (date && !isRealDate(date)) c.fail('date', 'La date doit être au format AAAA-MM-JJ.');
  const time = c.str('time', { required: true, max: 5, label: "L'heure" });
  if (time && !/^([01]\d|2[0-3]):[0-5]\d$/.test(time)) c.fail('time', "L'heure doit être au format HH:MM.");
  c.str('location', { required: true, min: 2, max: 200, label: 'Le lieu' });
  c.str('additionalInfo', { max: 2000, label: 'Les informations complémentaires', multiline: true });
  c.oneOf('status', forUpdate ? EVENT_STATUSES : ['DRAFT', 'PUBLISHED', 'COMPLETED'], {
    label: 'Le statut', fallback: 'DRAFT',
  });

  const rawFree = c.body.isFree;
  const isFree = rawFree === true || rawFree === 'true' || rawFree === '1' || rawFree === 1;
  const isPaid = rawFree === false || rawFree === 'false' || rawFree === '0' || rawFree === 0;
  if (!isFree && !isPaid) c.fail('isFree', "Indiquez si l'événement est gratuit ou payant.");
  c.out.isFree = isFree;

  const currency = String(c.body.currency || config.defaultCurrency).toUpperCase();
  if (!config.supportedCurrencies.includes(currency)) c.fail('currency', "Cette devise n'est pas prise en charge.");
  c.out.currency = currency;

  if (isFree) {
    // Edge case "Free Event With Price": normalised to 0.
    c.out.price = 0;
  } else if (isPaid) {
    const raw = c.body.price;
    if (raw === undefined || raw === null || String(raw).trim() === '') {
      c.fail('price', 'Un événement payant doit avoir un prix.');
    } else {
      const minor = parsePrice(raw, currency);
      if (minor === null) c.fail('price', `Le prix doit être un nombre positif (ex. 15${currency === 'TND' ? '.500' : '.50'}).`);
      else if (minor <= 0) c.fail('price', 'Le prix doit être supérieur à zéro.');
      else c.out.price = minor;
    }
  }
  return c.done();
}

function message(body) {
  const c = new Checker(body);
  c.str('title', { required: true, min: 3, max: 140, label: 'Le titre' });
  c.str('content', { required: true, min: 3, max: 5000, label: 'Le contenu', multiline: true });
  return c.done();
}

function suggestion(body) {
  const c = new Checker(body);
  c.str('title', { max: 140, label: 'Le titre' });
  c.str('content', { required: true, min: 5, max: 3000, label: 'Votre suggestion', multiline: true });
  return c.done();
}

function suggestionStatus(body) {
  const c = new Checker(body);
  c.oneOf('status', SUGGESTION_STATUSES, { label: 'Le statut' });
  return c.done();
}

function memberStatus(body) {
  const c = new Checker(body);
  c.oneOf('status', ['ACTIVE', 'SUSPENDED', 'DEACTIVATED'], { label: 'Le statut' });
  return c.done();
}

function participationAdd(body) {
  const c = new Checker(body);
  const id = c.str('memberId', { required: true, max: 64, label: 'Le membre' });
  if (id && !/^[0-9a-f-]{36}$/i.test(id)) c.fail('memberId', 'Membre invalide.');
  return c.done();
}


// ---------- Subscriptions (cotisations) ----------
const MAX_AMOUNT_MINOR = 100000 * 1000; // 100 000 TND

/** Academic year containing `date`: September starts a new season (2025-09 .. 2026-08 => "2025-2026"). */
function currentSeason(date = new Date()) {
  const y = date.getUTCFullYear();
  return date.getUTCMonth() >= 8 ? `${y}-${y + 1}` : `${y - 1}-${y}`;
}

function isSeason(s) {
  const m = /^(\d{4})-(\d{4})$/.exec(String(s || ''));
  return Boolean(m) && Number(m[2]) === Number(m[1]) + 1 && Number(m[1]) >= 2000 && Number(m[1]) < 2100;
}

function season(c, field = 'season') {
  const v = c.str(field, { max: 9, label: 'La saison' });
  if (!v) return (c.out[field] = currentSeason());
  if (!isSeason(v)) c.fail(field, 'La saison doit ressembler à 2025-2026.');
  return v;
}

const pad2 = (n) => String(n).padStart(2, '0');

/**
 * Accepts what treasurers actually type in Excel: a real date cell, 2026-01-31, 31/01/2026,
 * 31-01-26, or a raw Excel serial number. Returns YYYY-MM-DD or null when unreadable.
 */
function parseDateCell(raw) {
  if (raw === null || raw === undefined || raw === '') return null;
  let y; let m; let d;
  if (raw instanceof Date) {
    if (Number.isNaN(raw.getTime())) return undefined;
    [y, m, d] = [raw.getUTCFullYear(), raw.getUTCMonth() + 1, raw.getUTCDate()];
  } else if (typeof raw === 'number') {
    if (raw < 30000 || raw > 80000) return undefined;
    const dt = new Date(Math.round((raw - 25569) * 86400000));
    [y, m, d] = [dt.getUTCFullYear(), dt.getUTCMonth() + 1, dt.getUTCDate()];
  } else {
    const t = String(raw).trim();
    let r = /^(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})/.exec(t);
    if (r) [y, m, d] = [Number(r[1]), Number(r[2]), Number(r[3])];
    else if ((r = /^(\d{1,2})[-/.](\d{1,2})[-/.](\d{2}|\d{4})$/.exec(t))) {
      [d, m] = [Number(r[1]), Number(r[2])];
      y = r[3].length === 2 ? 2000 + Number(r[3]) : Number(r[3]);
    } else return undefined;
  }
  const iso = `${y}-${pad2(m)}-${pad2(d)}`;
  return isRealDate(iso) ? iso : undefined;
}

/** "25", "25,5", "25.500 DT", 25 => minor units (millimes). undefined when unreadable. */
function parseAmountCell(raw) {
  if (raw === null || raw === undefined || raw === '') return null;
  let n;
  if (typeof raw === 'number') n = raw;
  else {
    const t = String(raw).replace(/\s| /g, '').replace(/(dt|tnd|dinars?)$/i, '').replace(',', '.');
    if (!/^\d+(\.\d{1,3})?$/.test(t)) return undefined;
    n = Number(t);
  }
  const minor = Math.round(n * 1000);
  if (!Number.isFinite(minor) || minor <= 0 || minor > MAX_AMOUNT_MINOR) return undefined;
  return minor;
}

/** One paid-subscription record, from a form or from one Excel row. */
function subscriptionInput(body) {
  const c = new Checker(body);
  name(c);
  email(c);
  phone(c);
  const paid = parseDateCell(c.body.paidAt);
  if (paid === undefined) c.fail('paidAt', 'La date de paiement doit ressembler à 31/01/2026.');
  else if (paid && (paid > new Date(Date.now() + 86400000).toISOString().slice(0, 10) || paid < '2000-01-01')) {
    c.fail('paidAt', "La date de paiement n'est pas plausible.");
  }
  c.out.paidAt = paid || null;
  const amount = parseAmountCell(c.body.amount);
  if (amount === undefined) c.fail('amount', 'Le montant doit être un nombre positif (ex. 25 ou 25,500).');
  c.out.amount = amount ?? null;
  c.str('reference', { max: 60, label: 'La référence' });
  return c.done();
}

function subscriptionForm(body) {
  const c = new Checker(body);
  season(c);
  const inner = subscriptionInput(body);
  return { ...c.done(), ...inner };
}

/** Marking an existing member as paid: only the payment details are needed. */
function memberPayment(body) {
  const c = new Checker(body);
  season(c);
  const paid = parseDateCell(c.body.paidAt);
  if (paid === undefined) c.fail('paidAt', 'La date de paiement doit ressembler à 31/01/2026.');
  c.out.paidAt = paid || null;
  const amount = parseAmountCell(c.body.amount);
  if (amount === undefined) c.fail('amount', 'Le montant doit être un nombre positif (ex. 25 ou 25,500).');
  c.out.amount = amount ?? null;
  c.str('reference', { max: 60, label: 'La référence' });
  return c.done();
}

/** Administrator correcting a member's identity details (name, email, phone, birthday). */
function memberAdminUpdate(body) {
  const c = new Checker(body);
  name(c);
  email(c);
  phone(c);
  const b = c.str('birthday', { max: 10, label: 'La date de naissance' });
  if (b) {
    if (!isRealDate(b)) c.fail('birthday', 'La date de naissance doit être une date valide.');
    else if (b >= new Date().toISOString().slice(0, 10)) c.fail('birthday', 'La date de naissance doit être dans le passé.');
    else if (b < '1900-01-01') c.fail('birthday', "La date de naissance n'est pas plausible.");
  }
  return c.done();
}

/** Digits that identify a phone number whatever the formatting (+216 20 123 456 == 20123456). */
const phoneKey = (p) => String(p || '').replace(/\D/g, '').slice(-8);

function seasonParam(value) {
  if (value === undefined || value === '') return undefined;
  if (!isSeason(value)) throw errors.validation({ season: 'Saison invalide.' });
  return String(value);
}

module.exports = {
  EVENT_TYPES, EVENT_STATUSES, SUGGESTION_STATUSES,
  register, login, changePassword, profileUpdate, rejection, eventInput,
  message, suggestion, suggestionStatus, memberStatus, participationAdd,
  parsePrice, isRealDate,
  currentSeason, isSeason, seasonParam, phoneKey, subscriptionInput, subscriptionForm, memberPayment, memberAdminUpdate,
  parseDateCell, parseAmountCell,
};
