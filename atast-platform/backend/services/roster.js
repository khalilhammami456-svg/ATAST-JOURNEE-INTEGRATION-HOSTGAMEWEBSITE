'use strict';
/**
 * Paid-subscription roster (cotisations).
 *
 * The treasurer's Excel/CSV list of people who paid is imported here. Each listed person gets a
 * subscription record (status AVAILABLE). When that person registers with the same email (and
 * the same phone number), the membership request is accepted automatically — no administrator
 * needed — and the subscription becomes CLAIMED by the new member. People who are already members
 * simply get their payment recorded (renewal).
 *
 * Preview and import share one code path (`run`), so what the administrator reviews is exactly
 * what gets written.
 */
const config = require('../config');
const repo = require('../repositories');
const { transaction } = require('../db/database');
const { errors, uuid, now, paged } = require('../utils');
const v = require('../validators');
const audit = require('./audit');
const dto = require('./dto');
const members = require('./members');
const sync = require('./sync');
const sheet = require('./spreadsheet');

// ---------------------------------------------------------------- columns
const strip = (s) => String(s ?? '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().replace(/[^a-z0-9]/g, '');

const ALIASES = {
  name: ['nomcomplet', 'nometprenom', 'prenomnom', 'nomprenom', 'name', 'fullname', 'membre', 'etudiant', 'adherent', 'nomdumembre'],
  firstName: ['prenom', 'firstname', 'givenname', 'prenoms'],
  lastName: ['lastname', 'familyname', 'surname'],
  email: ['email', 'mail', 'adresseemail', 'adressemail', 'courriel', 'emailaddress', 'adresseelectronique', 'emailetudiant'],
  phone: ['telephone', 'tel', 'phone', 'gsm', 'mobile', 'numero', 'numerotelephone', 'numtel', 'ntel', 'telephonemobile', 'numerodetelephone', 'numerotel'],
  amount: ['montant', 'amount', 'somme', 'cotisation', 'prix', 'montantpaye', 'montantdt', 'montanttnd'],
  paidAt: ['datedepaiement', 'datepaiement', 'paidat', 'date', 'payele', 'datedecotisation', 'datecotisation', 'datedupaiement'],
  reference: ['reference', 'ref', 'recu', 'numerorecu', 'nrecu', 'numrecu', 'receipt', 'numerodurecu', 'recunumero'],
};

/** Maps header cells to our fields. "Nom" alone is the full name; next to "Prénom" it is the last name. */
function mapHeader(cells) {
  const keys = cells.map(strip);
  const map = {};
  keys.forEach((k, i) => {
    for (const [field, names] of Object.entries(ALIASES)) if (map[field] === undefined && names.includes(k)) map[field] = i;
  });
  const nomIdx = keys.indexOf('nom');
  if (nomIdx !== -1) {
    if (map.firstName !== undefined) map.lastName ??= nomIdx;
    else map.name ??= nomIdx;
  }
  return map;
}

const MISSING_LABELS = { name: 'Nom', email: 'Email', phone: 'Téléphone' };

function locateTable(rows) {
  for (let i = 0; i < Math.min(rows.length, 15); i += 1) {
    const map = mapHeader(rows[i] || []);
    if (map.email !== undefined) return { map, headerIndex: i };
  }
  throw errors.validation({
    file: 'Colonne « Email » introuvable. La première ligne doit contenir les titres : Nom, Email, Téléphone (et facultativement Montant, Date de paiement, Référence).',
  });
}

const cellText = (c) => (c === null || c === undefined ? '' : c instanceof Date ? c.toISOString().slice(0, 10) : String(c).trim());

/** Turns the sheet into raw record objects (before validation). */
function extractRecords(rows) {
  const { map, headerIndex } = locateTable(rows);
  const missing = [];
  if (map.name === undefined && !(map.firstName !== undefined && map.lastName !== undefined)) missing.push(MISSING_LABELS.name);
  if (map.phone === undefined) missing.push(MISSING_LABELS.phone);
  if (missing.length) {
    throw errors.validation({ file: `Colonne${missing.length > 1 ? 's' : ''} obligatoire${missing.length > 1 ? 's' : ''} introuvable${missing.length > 1 ? 's' : ''} : ${missing.join(', ')}.` });
  }
  const records = [];
  for (let i = headerIndex + 1; i < rows.length; i += 1) {
    const r = rows[i] || [];
    if (r.every((c) => cellText(c) === '')) continue;
    const pick = (f) => (map[f] === undefined ? null : r[map[f]] ?? null);
    const name = map.name !== undefined ? cellText(pick('name')) : `${cellText(pick('firstName'))} ${cellText(pick('lastName'))}`.trim();
    records.push({
      line: i + 1,
      raw: { name, email: cellText(pick('email')), phone: pick('phone'), amount: pick('amount'), paidAt: pick('paidAt'), reference: pick('reference') },
    });
  }
  if (!records.length) throw errors.validation({ file: 'Aucune ligne de données trouvée sous les titres de colonnes.' });
  if (records.length > config.importMaxRows) throw errors.validation({ file: `Le fichier dépasse ${config.importMaxRows} lignes. Découpez-le en plusieurs fichiers.` });
  return records;
}

// ---------------------------------------------------------------- analysis
const STATUS = {
  NEW: 'NEW',                       // will be added to the paid list
  AUTO_ACCEPT: 'AUTO_ACCEPT',       // a pending request matches: accepted automatically
  RENEWAL: 'RENEWAL',               // already an active member: payment recorded on the account
  ALREADY_LISTED: 'ALREADY_LISTED',
  DUPLICATE: 'DUPLICATE',
  BLOCKED: 'BLOCKED',
  INVALID: 'INVALID',
};
const WILL_IMPORT = new Set([STATUS.NEW, STATUS.AUTO_ACCEPT, STATUS.RENEWAL]);

const samePhone = (a, b) => v.phoneKey(a) === v.phoneKey(b);

/** Decides what an import row would do, from the current state of the database. */
function classify(clean, season, seen) {
  const email = clean.email;
  if (seen.has(email)) return { status: STATUS.DUPLICATE, note: `Adresse déjà présente plus haut dans le fichier (ligne ${seen.get(email)}).` };
  const live = repo.subscriptions.findLive(email, season);
  if (live) {
    return { status: STATUS.ALREADY_LISTED, note: live.status === 'CLAIMED' ? 'Cotisation déjà enregistrée pour ce membre.' : 'Déjà dans la liste des cotisations de cette saison.' };
  }
  const active = repo.users.findActiveByEmail(email);
  if (active) {
    if (active.role !== 'MEMBER') return { status: STATUS.BLOCKED, note: 'Cette adresse appartient à un compte administrateur.' };
    return { status: STATUS.RENEWAL, note: `Déjà membre (${active.name}) : la cotisation sera enregistrée sur son compte.`, user: active };
  }
  if (repo.users.findAnyByEmail(email)) {
    return { status: STATUS.BLOCKED, note: 'Compte suspendu ou désactivé : à traiter manuellement depuis la fiche du membre.' };
  }
  const pending = repo.requests.findPendingByEmail(email);
  if (pending) {
    if (!config.autoAcceptRequirePhone || samePhone(pending.phone, clean.phone)) {
      return { status: STATUS.AUTO_ACCEPT, note: `La demande d’adhésion de ${pending.name} sera acceptée automatiquement.`, request: pending };
    }
    return { status: STATUS.NEW, note: 'Une demande existe avec un autre numéro de téléphone : elle restera à valider manuellement.' };
  }
  return { status: STATUS.NEW, note: null };
}

function analyse(records, season) {
  const seen = new Map();
  return records.map(({ line, raw }) => {
    let clean;
    try {
      clean = v.subscriptionInput(raw);
    } catch (err) {
      if (!err.fields) throw err;
      return { line, raw, status: STATUS.INVALID, note: Object.values(err.fields).join(' ') };
    }
    const verdict = classify(clean, season, seen);
    if (verdict.status !== STATUS.DUPLICATE) seen.set(clean.email, line);
    return { line, clean, ...verdict };
  });
}

function summarize(items) {
  const counts = Object.fromEntries(Object.values(STATUS).map((s) => [s, 0]));
  for (const it of items) counts[it.status] += 1;
  return { total: items.length, willImport: items.filter((i) => WILL_IMPORT.has(i.status)).length, counts };
}

const publicRow = (it) => ({
  line: it.line,
  name: it.clean?.name ?? (it.raw?.name || null),
  email: it.clean?.email ?? (it.raw?.email || null),
  phone: it.clean?.phone ?? (it.raw?.phone === null || it.raw?.phone === undefined ? null : String(it.raw.phone)),
  amount: it.clean ? dto.money(it.clean.amount) : null,
  paidAt: it.clean?.paidAt ?? null,
  reference: it.clean?.reference ?? null,
  status: it.status,
  note: it.note ?? null,
});

// ---------------------------------------------------------------- writing
/** Inserts the subscription of a classified row and applies its consequence. Returns the new row. */
function apply(it, season, { batchId, adminId, at }) {
  const sub = {
    id: uuid(), batch_id: batchId, season, name: it.clean.name, email: it.clean.email, phone: it.clean.phone,
    amount: it.clean.amount, paid_at: it.clean.paidAt, reference: it.clean.reference,
    status: 'AVAILABLE', created_by: adminId, created_at: at,
  };
  repo.subscriptions.insert(sub);
  if (it.status === STATUS.AUTO_ACCEPT) {
    members.activateRequest(it.request, { reviewerId: null, auto: true, subscription: sub });
  } else if (it.status === STATUS.RENEWAL) {
    repo.subscriptions.claim(sub.id, it.user.id, at);
  }
  return sub;
}

/**
 * Analyses `records` and, when `commit` is true, writes everything in one transaction
 * (all or nothing). `meta` = { filename } for imports, null for a single manual entry.
 */
function run(records, season, { commit, meta = null }, admin) {
  const exec = () => {
    const items = analyse(records, season);
    const summary = summarize(items);
    if (!commit) return { items, summary };
    const at = now();
    let batchId = null;
    if (meta) {
      batchId = uuid();
      repo.importBatches.insert({
        id: batchId, filename: meta.filename, season, rows_total: items.length, rows_imported: summary.willImport,
        rows_skipped: items.length - summary.willImport, auto_accepted: summary.counts.AUTO_ACCEPT, renewals: summary.counts.RENEWAL,
        created_by: admin.id, created_at: at,
      });
    }
    const created = [];
    for (const it of items) if (WILL_IMPORT.has(it.status)) created.push(apply(it, season, { batchId, adminId: admin.id, at }));
    if (meta) {
      audit.log(admin.id, 'SUBSCRIPTIONS_IMPORTED', 'import_batch', batchId, {
        filename: meta.filename, season, imported: summary.willImport, skipped: items.length - summary.willImport,
        autoAccepted: summary.counts.AUTO_ACCEPT, renewals: summary.counts.RENEWAL,
      });
    }
    sync.publish('admins', ['subscriptions', 'stats', 'requests', 'members']);
    return { items, summary, batchId, created };
  };
  return commit ? transaction(exec) : exec();
}

// ---------------------------------------------------------------- public API
/** Excel/CSV import. `dryRun` returns the preview without writing anything. */
async function importFile({ buffer, filename, season, dryRun }, admin) {
  const rows = await sheet.readRows(buffer, filename);
  const records = extractRecords(rows);
  const out = run(records, season, { commit: !dryRun, meta: { filename: String(filename || 'import').slice(0, 120) } }, admin);
  return {
    dryRun: Boolean(dryRun),
    season,
    batchId: out.batchId ?? null,
    summary: out.summary,
    rows: out.items.map(publicRow),
  };
}

/** One person added by hand. Throws a readable error when the row cannot be added. */
function addOne(input, admin) {
  const out = run([{ line: 1, raw: input }], input.season, { commit: false }, admin);
  const [it] = out.items;
  if (!WILL_IMPORT.has(it.status)) {
    throw errors.conflict(it.note || 'Cette cotisation ne peut pas être ajoutée.', it.status === STATUS.ALREADY_LISTED ? 'ALREADY_LISTED' : 'NOT_ADDABLE');
  }
  const done = run([{ line: 1, raw: input }], input.season, { commit: true }, admin);
  audit.log(admin.id, 'SUBSCRIPTION_ADDED', 'subscription', done.created[0].id, { season: input.season, email: input.email, result: it.status });
  return { ...dto.subscription(repo.subscriptions.findById(done.created[0].id)), result: it.status, note: it.note };
}

/** Records the payment of an existing member directly on their account. */
function recordMemberPayment(memberId, payment, admin) {
  return transaction(() => {
    const u = repo.users.findById(memberId);
    if (!u || u.role !== 'MEMBER') throw errors.notFound('Membre');
    if (repo.subscriptions.findLive(u.email, payment.season)) {
      throw errors.conflict(`La cotisation ${payment.season} est déjà enregistrée pour ce membre.`, 'ALREADY_LISTED');
    }
    const at = now();
    const id = uuid();
    repo.subscriptions.insert({
      id, season: payment.season, name: u.name, email: u.email, phone: u.phone, amount: payment.amount, paid_at: payment.paidAt,
      reference: payment.reference, status: 'CLAIMED', user_id: u.id, claimed_at: at, created_by: admin.id, created_at: at,
    });
    audit.log(admin.id, 'SUBSCRIPTION_ADDED', 'subscription', id, { season: payment.season, email: u.email, result: 'MEMBER_PAYMENT' });
    sync.publish('admins', ['subscriptions', 'stats', 'members'], { memberId });
    return dto.subscription(repo.subscriptions.findById(id));
  });
}

function revokeSubscription(id, admin) {
  return transaction(() => {
    const s = repo.subscriptions.findById(id);
    if (!s) throw errors.notFound('Cotisation');
    if (s.status !== 'AVAILABLE') {
      throw errors.conflict(s.status === 'CLAIMED' ? 'Cette personne est déjà membre : la cotisation ne peut plus être retirée de la liste.' : 'Cotisation déjà annulée.', 'NOT_REVOCABLE');
    }
    repo.subscriptions.revoke(id, now());
    audit.log(admin.id, 'SUBSCRIPTION_REVOKED', 'subscription', id, { season: s.season, email: s.email });
    sync.publish('admins', ['subscriptions', 'stats']);
    return { id, status: 'REVOKED' };
  });
}

/** Undo an import: people not yet registered leave the list; members already created stay members. */
function revertBatch(id, admin) {
  return transaction(() => {
    const b = repo.importBatches.findById(id);
    if (!b) throw errors.notFound('Import');
    if (b.reverted_at) throw errors.conflict('Cet import a déjà été annulé.', 'ALREADY_REVERTED');
    const at = now();
    const revoked = repo.subscriptions.revokeBatch(id, at);
    repo.importBatches.markReverted(id, admin.id, at);
    audit.log(admin.id, 'IMPORT_REVERTED', 'import_batch', id, { filename: b.filename, revoked });
    sync.publish('admins', ['subscriptions', 'stats']);
    return { id, revoked, kept: b.rows_imported - revoked };
  });
}

function listSubscriptions({ status, season, q }, page) {
  const { rows, total } = repo.subscriptions.list({ status, season, q, ...page });
  return paged(rows.map((r) => ({ ...dto.subscription(r), memberName: r.member_name || null })), total, page);
}

function listBatches(page) {
  const { rows, total } = repo.importBatches.list(page);
  return paged(rows.map((b) => ({
    id: b.id, filename: b.filename, season: b.season, rowsTotal: b.rows_total, rowsImported: b.rows_imported, rowsSkipped: b.rows_skipped,
    autoAccepted: b.auto_accepted, renewals: b.renewals, stillAvailable: b.still_available, author: b.author_name || null,
    createdAt: b.created_at, revertedAt: b.reverted_at || null,
  })), total, page);
}

/**
 * Called inside the registration transaction. Accepts the new request on the spot when the person
 * is on the paid list (same email and, by default, same phone number). Returns the result or null.
 */
function tryAutoAccept(request) {
  const sub = repo.subscriptions.findAvailableByEmail(request.email);
  if (!sub) return null;
  if (config.autoAcceptRequirePhone && !samePhone(sub.phone, request.phone)) return null;
  // A suspended or deactivated account is a decision of the administration: never bypassed.
  if (repo.users.findAnyByEmail(request.email)) return null;
  const { userId } = members.activateRequest(request, { reviewerId: null, auto: true, subscription: sub });
  return { userId, season: sub.season };
}

// ---------------------------------------------------------------- stats & files
function subscriptionStats() {
  const season = v.currentSeason();
  const byStatus = Object.fromEntries(repo.subscriptions.countByStatus(season).map((r) => [r.status, r.n]));
  const active = repo.users.countActiveMembers();
  const paid = repo.users.countActiveByPaid(season);
  return { season, paidMembers: paid, unpaidMembers: Math.max(0, active - paid), awaitingRegistration: byStatus.AVAILABLE || 0 };
}

const FILE_TYPE = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet';

async function templateFile() {
  const buffer = await sheet.writeWorkbook('Cotisations', [
    { title: 'Nom complet', width: 28 }, { title: 'Email', width: 32 }, { title: 'Téléphone', width: 18 },
    { title: 'Montant (DT)', width: 14 }, { title: 'Date de paiement', width: 18 }, { title: 'Référence', width: 18 },
  ], []);
  return { buffer, type: FILE_TYPE, filename: 'modele-import-cotisations.xlsx' };
}

const asDate = (ymd) => (ymd ? new Date(`${ymd}T00:00:00Z`) : null);
const asNumber = (minor) => (minor === null || minor === undefined ? null : minor / 1000);
const MEMBER_STATUS_FR = { ACTIVE: 'Actif', SUSPENDED: 'Suspendu', DEACTIVATED: 'Désactivé' };
const SUB_STATUS_FR = { AVAILABLE: 'Payée, pas encore inscrite', CLAIMED: 'Membre inscrit', REVOKED: 'Annulée' };

async function membersFile({ status = 'ANY', season }) {
  const rows = repo.users.listForExport({ status, season });
  const buffer = await sheet.writeWorkbook('Membres', [
    { title: 'Nom', width: 28 }, { title: 'Email', width: 32 }, { title: 'Téléphone', width: 18 }, { title: 'Date de naissance', width: 18 },
    { title: 'Statut', width: 12 }, { title: 'Score', width: 8 }, { title: 'Membre depuis', width: 16 },
    { title: `Cotisation ${season}`, width: 18 }, { title: 'Date de paiement', width: 18, format: 'yyyy-mm-dd' },
    { title: 'Montant (DT)', width: 14, format: '0.000' }, { title: 'Référence', width: 16 },
  ], rows.map((r) => [
    r.name, r.email, r.phone, asDate(r.birthday), MEMBER_STATUS_FR[r.status] || r.status, r.score, asDate(r.created_at.slice(0, 10)),
    r.sub_paid ? 'Payée' : 'Non payée', asDate(r.sub_paid_at), asNumber(r.sub_amount), r.sub_reference,
  ]));
  return { buffer, type: FILE_TYPE, filename: `membres-${season}.xlsx` };
}

async function subscriptionsFile({ status, season }) {
  const rows = repo.subscriptions.listForExport({ status, season });
  const buffer = await sheet.writeWorkbook('Cotisations', [
    { title: 'Saison', width: 12 }, { title: 'Nom', width: 28 }, { title: 'Email', width: 32 }, { title: 'Téléphone', width: 18 },
    { title: 'Montant (DT)', width: 14, format: '0.000' }, { title: 'Date de paiement', width: 18, format: 'yyyy-mm-dd' },
    { title: 'Référence', width: 16 }, { title: 'Statut', width: 26 },
  ], rows.map((r) => [r.season, r.name, r.email, r.phone, asNumber(r.amount), asDate(r.paid_at), r.reference, SUB_STATUS_FR[r.status] || r.status]));
  return { buffer, type: FILE_TYPE, filename: `cotisations${season ? `-${season}` : ''}.xlsx` };
}

module.exports = {
  STATUS, importFile, addOne, recordMemberPayment, revokeSubscription, revertBatch, listSubscriptions, listBatches,
  tryAutoAccept, subscriptionStats, templateFile, membersFile, subscriptionsFile, mapHeader, extractRecords,
};
