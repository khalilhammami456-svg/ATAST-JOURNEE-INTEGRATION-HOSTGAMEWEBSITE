'use strict';
/** Repositories: the only layer that talks SQL. Prepared statements only. */
const { get } = require('../db/database');
const { pointsSql } = require('../services/points');
const { likeTerm } = require('../utils');

const SCORE_SQL = `(SELECT COALESCE(SUM(${pointsSql('e.type')}), 0)
  FROM event_participations p JOIN events e ON e.id = p.event_id
  WHERE p.member_id = u.id AND p.status = 'VALIDATED')`;

// ---------------------------------------------------------------- users
const users = {
  findById(id) {
    return get().prepare('SELECT * FROM users WHERE id = ?').get(id);
  },
  findActiveByEmail(email) {
    return get().prepare(`SELECT * FROM users WHERE lower(email) = lower(?) AND status = 'ACTIVE'`).get(email);
  },
  findAnyByEmail(email) {
    return get().prepare(`SELECT * FROM users WHERE lower(email) = lower(?) ORDER BY created_at DESC`).get(email);
  },
  insert(u) {
    get().prepare(`INSERT INTO users (id, name, email, password_hash, phone, role, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .run(u.id, u.name, u.email, u.password_hash, u.phone, u.role, u.status, u.created_at, u.updated_at);
  },
  updateProfile(id, p, at) {
    get().prepare(`UPDATE users SET name = ?, phone = ?, description = ?, birthday = ?, instagram = ?,
      facebook = ?, github = ?, linkedin = ?, updated_at = ? WHERE id = ?`)
      .run(p.name, p.phone, p.description, p.birthday, p.instagram, p.facebook, p.github, p.linkedin, at, id);
  },
  setPhoto(id, file, at) {
    get().prepare('UPDATE users SET profile_photo = ?, updated_at = ? WHERE id = ?').run(file, at, id);
  },
  setPassword(id, hash, at) {
    get().prepare('UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?').run(hash, at, id);
  },
  setStatus(id, status, at) {
    get().prepare('UPDATE users SET status = ?, updated_at = ? WHERE id = ?').run(status, at, id);
  },
  score(id) {
    return get().prepare(`SELECT ${SCORE_SQL} AS score FROM users u WHERE u.id = ?`).get(id)?.score ?? 0;
  },
  /** Administrator correction of identity details (not the password, role or status). */
  updateIdentity(id, p, at) {
    get().prepare('UPDATE users SET name = ?, email = ?, phone = ?, birthday = ?, updated_at = ? WHERE id = ?')
      .run(p.name, p.email, p.phone, p.birthday, at, id);
  },
  /**
   * Members (role MEMBER) with derived score. With `season`, also tells whether the member
   * paid it (sub_paid_at / sub_amount are set when a CLAIMED subscription exists) and
   * `subscription: 'paid' | 'unpaid'` filters on it.
   */
  listMembers({ q, offset, pageSize, includeEmail = false, status = 'ACTIVE', season = null, subscription = null }) {
    const where = [`u.role = 'MEMBER'`];
    const args = [];
    if (status !== 'ANY') { where.push('u.status = ?'); args.push(status); }
    if (q) {
      if (includeEmail) {
        where.push(`(u.name LIKE ? ESCAPE '\\' OR u.email LIKE ? ESCAPE '\\')`);
        args.push(likeTerm(q), likeTerm(q));
      } else {
        where.push(`u.name LIKE ? ESCAPE '\\'`);
        args.push(likeTerm(q));
      }
    }
    const paidExists = `EXISTS (SELECT 1 FROM subscriptions s WHERE s.user_id = u.id AND s.status = 'CLAIMED' AND s.season = ?)`;
    if (season && subscription === 'paid') { where.push(paidExists); args.push(season); }
    if (season && subscription === 'unpaid') { where.push(`NOT ${paidExists}`); args.push(season); }
    const w = where.join(' AND ');
    const total = get().prepare(`SELECT COUNT(*) AS n FROM users u WHERE ${w}`).get(...args).n;
    const subCols = season
      ? `, (SELECT s.paid_at FROM subscriptions s WHERE s.user_id = u.id AND s.status = 'CLAIMED' AND s.season = ?) AS sub_paid_at,
          (SELECT s.amount FROM subscriptions s WHERE s.user_id = u.id AND s.status = 'CLAIMED' AND s.season = ?) AS sub_amount,
          ${paidExists} AS sub_paid`
      : '';
    const subArgs = season ? [season, season, season] : [];
    const rows = get().prepare(`SELECT u.*, ${SCORE_SQL} AS score${subCols} FROM users u WHERE ${w}
      ORDER BY u.name COLLATE NOCASE ASC, u.created_at ASC LIMIT ? OFFSET ?`).all(...subArgs, ...args, pageSize, offset);
    return { rows, total };
  },
  /** Every member for the Excel export, with the subscription of `season` when there is one. */
  listForExport({ status = 'ANY', season }) {
    const where = [`u.role = 'MEMBER'`];
    const args = [season];
    if (status !== 'ANY') { where.push('u.status = ?'); args.push(status); }
    return get().prepare(`SELECT u.name, u.email, u.phone, u.birthday, u.status, u.created_at, ${SCORE_SQL} AS score,
        s.paid_at AS sub_paid_at, s.amount AS sub_amount, s.reference AS sub_reference,
        CASE WHEN s.id IS NULL THEN 0 ELSE 1 END AS sub_paid
      FROM users u
      LEFT JOIN subscriptions s ON s.user_id = u.id AND s.status = 'CLAIMED' AND s.season = ?
      WHERE ${where.join(' AND ')}
      ORDER BY u.name COLLATE NOCASE ASC LIMIT 10000`).all(...args);
  },
  countActiveByPaid(season) {
    return get().prepare(`SELECT COUNT(*) AS n FROM users u WHERE u.role = 'MEMBER' AND u.status = 'ACTIVE'
      AND EXISTS (SELECT 1 FROM subscriptions s WHERE s.user_id = u.id AND s.status = 'CLAIMED' AND s.season = ?)`).get(season).n;
  },
  findMemberWithScore(id) {
    return get().prepare(`SELECT u.*, ${SCORE_SQL} AS score FROM users u WHERE u.id = ?`).get(id);
  },
  /**
   * FR-24: active members by score desc; ties broken by a stable secondary
   * criterion (name, then account creation date, then id).
   */
  scoreboard({ offset, pageSize }) {
    const total = get().prepare(`SELECT COUNT(*) AS n FROM users WHERE role = 'MEMBER' AND status = 'ACTIVE'`).get().n;
    const rows = get().prepare(`SELECT * FROM (
        SELECT u.id, u.name, u.profile_photo, ${SCORE_SQL} AS score, u.created_at
        FROM users u WHERE u.role = 'MEMBER' AND u.status = 'ACTIVE')
      ORDER BY score DESC, name COLLATE NOCASE ASC, created_at ASC, id ASC
      LIMIT ? OFFSET ?`).all(pageSize, offset);
    return { rows, total };
  },
  rankOf(id) {
    const rows = get().prepare(`SELECT id FROM (
        SELECT u.id, u.name, ${SCORE_SQL} AS score, u.created_at
        FROM users u WHERE u.role = 'MEMBER' AND u.status = 'ACTIVE')
      ORDER BY score DESC, name COLLATE NOCASE ASC, created_at ASC, id ASC`).all();
    const i = rows.findIndex((r) => r.id === id);
    return i === -1 ? null : { rank: i + 1, total: rows.length };
  },
  countActiveMembers() {
    return get().prepare(`SELECT COUNT(*) AS n FROM users WHERE role = 'MEMBER' AND status = 'ACTIVE'`).get().n;
  },
};

// ---------------------------------------------------------------- membership requests
const requests = {
  findById(id) {
    return get().prepare('SELECT * FROM membership_requests WHERE id = ?').get(id);
  },
  findPendingByEmail(email) {
    return get().prepare(`SELECT * FROM membership_requests WHERE lower(email) = lower(?) AND status = 'PENDING'`).get(email);
  },
  findLatestRejectedByEmail(email) {
    return get().prepare(`SELECT * FROM membership_requests WHERE lower(email) = lower(?) AND status = 'REJECTED'
      ORDER BY reviewed_at DESC LIMIT 1`).get(email);
  },
  insert(r) {
    get().prepare(`INSERT INTO membership_requests (id, name, email, phone, password_hash, status, created_at)
      VALUES (?, ?, ?, ?, ?, 'PENDING', ?)`).run(r.id, r.name, r.email, r.phone, r.password_hash, r.created_at);
  },
  /** `reviewer` is null (and `auto` 1) when the system accepted it from the paid list. */
  markAccepted(id, userId, reviewer, at, auto = 0) {
    get().prepare(`UPDATE membership_requests SET status = 'ACCEPTED', user_id = ?, password_hash = NULL,
      reviewed_by = ?, reviewed_at = ?, auto_accepted = ? WHERE id = ? AND status = 'PENDING'`).run(userId, reviewer, at, auto, id);
  },
  markRejected(id, reason, reviewer, at) {
    get().prepare(`UPDATE membership_requests SET status = 'REJECTED', rejection_reason = ?, reviewed_by = ?,
      reviewed_at = ? WHERE id = ? AND status = 'PENDING'`).run(reason, reviewer, at, id);
  },
  list({ status, q, offset, pageSize }) {
    const where = [];
    const args = [];
    if (status) { where.push('r.status = ?'); args.push(status); }
    if (q) {
      where.push(`(r.name LIKE ? ESCAPE '\\' OR r.email LIKE ? ESCAPE '\\')`);
      args.push(likeTerm(q), likeTerm(q));
    }
    const w = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const total = get().prepare(`SELECT COUNT(*) AS n FROM membership_requests r ${w}`).get(...args).n;
    const rows = get().prepare(`SELECT r.id, r.name, r.email, r.phone, r.status, r.rejection_reason, r.created_at,
        r.reviewed_at, r.auto_accepted, rv.name AS reviewer_name,
        EXISTS (SELECT 1 FROM subscriptions s WHERE lower(s.email) = lower(r.email) AND s.status = 'AVAILABLE') AS on_paid_list
      FROM membership_requests r LEFT JOIN users rv ON rv.id = r.reviewed_by ${w}
      ORDER BY CASE r.status WHEN 'PENDING' THEN 0 ELSE 1 END, r.created_at DESC
      LIMIT ? OFFSET ?`).all(...args, pageSize, offset);
    return { rows, total };
  },
  countPending() {
    return get().prepare(`SELECT COUNT(*) AS n FROM membership_requests WHERE status = 'PENDING'`).get().n;
  },
};

// ---------------------------------------------------------------- events
const EVENT_COLS = `e.*, (SELECT COUNT(*) FROM event_participations p WHERE p.event_id = e.id AND p.status = 'VALIDATED') AS validated_count,
  (SELECT COUNT(*) FROM event_participations p WHERE p.event_id = e.id AND p.status = 'REGISTERED') AS registered_count`;

const events = {
  findById(id) {
    return get().prepare(`SELECT ${EVENT_COLS} FROM events e WHERE e.id = ?`).get(id);
  },
  insert(e) {
    get().prepare(`INSERT INTO events (id, title, description, type, date, time, location, is_free, price, currency,
        image_url, additional_info, status, created_by, created_at, updated_at)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .run(e.id, e.title, e.description, e.type, e.date, e.time, e.location, e.isFree ? 1 : 0, e.price, e.currency,
        e.imageUrl ?? null, e.additionalInfo, e.status, e.createdBy, e.createdAt, e.updatedAt);
  },
  update(id, e, at) {
    get().prepare(`UPDATE events SET title = ?, description = ?, type = ?, date = ?, time = ?, location = ?,
        is_free = ?, price = ?, currency = ?, additional_info = ?, status = ?, updated_at = ? WHERE id = ?`)
      .run(e.title, e.description, e.type, e.date, e.time, e.location, e.isFree ? 1 : 0, e.price, e.currency,
        e.additionalInfo, e.status, at, id);
  },
  setImage(id, file, at) {
    get().prepare('UPDATE events SET image_url = ?, updated_at = ? WHERE id = ?').run(file, at, id);
  },
  setStatus(id, status, at) {
    get().prepare('UPDATE events SET status = ?, updated_at = ? WHERE id = ?').run(status, at, id);
  },
  list({ statuses, type, q, when, offset, pageSize, today }) {
    const where = [];
    const args = [];
    if (statuses?.length) {
      where.push(`e.status IN (${statuses.map(() => '?').join(',')})`);
      args.push(...statuses);
    }
    if (type) { where.push('e.type = ?'); args.push(type); }
    if (q) {
      where.push(`(e.title LIKE ? ESCAPE '\\' OR e.location LIKE ? ESCAPE '\\')`);
      args.push(likeTerm(q), likeTerm(q));
    }
    if (when === 'upcoming') { where.push('e.date >= ?'); args.push(today); }
    if (when === 'past') { where.push('e.date < ?'); args.push(today); }
    const w = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const order = when === 'upcoming' ? 'e.date ASC, e.time ASC' : 'e.date DESC, e.time DESC';
    const total = get().prepare(`SELECT COUNT(*) AS n FROM events e ${w}`).get(...args).n;
    const rows = get().prepare(`SELECT ${EVENT_COLS} FROM events e ${w} ORDER BY ${order} LIMIT ? OFFSET ?`)
      .all(...args, pageSize, offset);
    return { rows, total };
  },
  count() {
    return get().prepare(`SELECT COUNT(*) AS n FROM events WHERE status != 'ARCHIVED'`).get().n;
  },
  countUpcoming(today) {
    return get().prepare(`SELECT COUNT(*) AS n FROM events WHERE status = 'PUBLISHED' AND date >= ?`).get(today).n;
  },
};

// ---------------------------------------------------------------- participations
const participations = {
  findById(id) {
    return get().prepare('SELECT * FROM event_participations WHERE id = ?').get(id);
  },
  findActive(eventId, memberId) {
    return get().prepare(`SELECT * FROM event_participations WHERE event_id = ? AND member_id = ?
      AND status IN ('REGISTERED', 'VALIDATED')`).get(eventId, memberId);
  },
  insert(p) {
    get().prepare(`INSERT INTO event_participations (id, event_id, member_id, status, points_awarded, validated_at,
        validated_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .run(p.id, p.eventId, p.memberId, p.status, p.points, p.validatedAt ?? null, p.validatedBy ?? null, p.at, p.at);
  },
  validate(id, points, by, at) {
    get().prepare(`UPDATE event_participations SET status = 'VALIDATED', points_awarded = ?, validated_at = ?,
      validated_by = ?, updated_at = ? WHERE id = ? AND status = 'REGISTERED'`).run(points, at, by, at, id);
  },
  remove(id, at) {
    get().prepare(`UPDATE event_participations SET status = 'REMOVED', points_awarded = 0, updated_at = ?
      WHERE id = ?`).run(at, id);
  },
  /** FR-11: keep points_awarded in sync when an event's type changes. */
  recalcForEvent(eventId, points, at) {
    return get().prepare(`UPDATE event_participations SET points_awarded = ?, updated_at = ?
      WHERE event_id = ? AND status = 'VALIDATED'`).run(points, at, eventId).changes;
  },
  listForEvent(eventId) {
    return get().prepare(`SELECT p.id, p.status, p.points_awarded, p.created_at, p.validated_at,
        u.id AS member_id, u.name, u.email, u.profile_photo, u.status AS member_status
      FROM event_participations p JOIN users u ON u.id = p.member_id
      WHERE p.event_id = ? AND p.status IN ('REGISTERED', 'VALIDATED')
      ORDER BY CASE p.status WHEN 'REGISTERED' THEN 0 ELSE 1 END, u.name COLLATE NOCASE`).all(eventId);
  },
  listForMember(memberId) {
    return get().prepare(`SELECT p.id, p.status, p.points_awarded, p.created_at, p.validated_at,
        e.id AS event_id, e.title, e.type, e.date, e.time, e.location, e.status AS event_status
      FROM event_participations p JOIN events e ON e.id = p.event_id
      WHERE p.member_id = ? AND p.status IN ('REGISTERED', 'VALIDATED')
      ORDER BY e.date DESC, e.time DESC`).all(memberId);
  },
  /** For a member: map eventId -> own participation status. */
  statusesForMember(memberId, eventIds) {
    if (!eventIds.length) return new Map();
    const rows = get().prepare(`SELECT event_id, status FROM event_participations WHERE member_id = ?
      AND status IN ('REGISTERED', 'VALIDATED') AND event_id IN (${eventIds.map(() => '?').join(',')})`)
      .all(memberId, ...eventIds);
    return new Map(rows.map((r) => [r.event_id, r.status]));
  },
  countValidated() {
    return get().prepare(`SELECT COUNT(*) AS n FROM event_participations WHERE status = 'VALIDATED'`).get().n;
  },
};

// ---------------------------------------------------------------- messages
const messages = {
  insert(m) {
    get().prepare('INSERT INTO messages (id, title, content, sender_id, created_at) VALUES (?, ?, ?, ?, ?)')
      .run(m.id, m.title, m.content, m.senderId, m.createdAt);
  },
  list({ offset, pageSize }) {
    const total = get().prepare('SELECT COUNT(*) AS n FROM messages').get().n;
    const rows = get().prepare(`SELECT m.id, m.title, m.content, m.created_at, u.name AS author_name
      FROM messages m JOIN users u ON u.id = m.sender_id ORDER BY m.created_at DESC LIMIT ? OFFSET ?`)
      .all(pageSize, offset);
    return { rows, total };
  },
};

// ---------------------------------------------------------------- suggestions
const suggestions = {
  findById(id) {
    return get().prepare('SELECT * FROM suggestions WHERE id = ?').get(id);
  },
  insert(s) {
    get().prepare(`INSERT INTO suggestions (id, member_id, title, content, status, created_at, updated_at)
      VALUES (?, ?, ?, ?, 'NEW', ?, ?)`).run(s.id, s.memberId, s.title, s.content, s.at, s.at);
  },
  setStatus(id, status, at) {
    get().prepare('UPDATE suggestions SET status = ?, updated_at = ? WHERE id = ?').run(status, at, id);
  },
  list({ status, offset, pageSize }) {
    const w = status ? 'WHERE s.status = ?' : '';
    const args = status ? [status] : [];
    const total = get().prepare(`SELECT COUNT(*) AS n FROM suggestions s ${w}`).get(...args).n;
    const rows = get().prepare(`SELECT s.*, u.name AS author_name, u.profile_photo AS author_photo
      FROM suggestions s JOIN users u ON u.id = s.member_id ${w}
      ORDER BY CASE s.status WHEN 'NEW' THEN 0 WHEN 'READ' THEN 1 WHEN 'IN_REVIEW' THEN 2 ELSE 3 END,
        s.created_at DESC LIMIT ? OFFSET ?`).all(...args, pageSize, offset);
    return { rows, total };
  },
  listForMember(memberId) {
    return get().prepare(`SELECT id, title, content, status, created_at, updated_at FROM suggestions
      WHERE member_id = ? ORDER BY created_at DESC LIMIT 50`).all(memberId);
  },
  countNew() {
    return get().prepare(`SELECT COUNT(*) AS n FROM suggestions WHERE status = 'NEW'`).get().n;
  },
};

// ---------------------------------------------------------------- subscriptions (cotisations)
const subscriptions = {
  findById(id) {
    return get().prepare('SELECT * FROM subscriptions WHERE id = ?').get(id);
  },
  /** The live (not revoked) subscription of a person for a season. */
  findLive(email, season) {
    return get().prepare(`SELECT * FROM subscriptions WHERE lower(email) = lower(?) AND season = ?
      AND status IN ('AVAILABLE', 'CLAIMED')`).get(email, season);
  },
  /** Paid but not yet registered, newest season first. */
  findAvailableByEmail(email) {
    return get().prepare(`SELECT * FROM subscriptions WHERE lower(email) = lower(?) AND status = 'AVAILABLE'
      ORDER BY season DESC LIMIT 1`).get(email);
  },
  insert(s) {
    get().prepare(`INSERT INTO subscriptions (id, batch_id, season, name, email, phone, amount, paid_at, reference, status,
      user_id, claimed_at, created_by, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .run(s.id, s.batch_id ?? null, s.season, s.name, s.email, s.phone, s.amount ?? null, s.paid_at ?? null, s.reference ?? null,
        s.status, s.user_id ?? null, s.claimed_at ?? null, s.created_by ?? null, s.created_at, s.created_at);
  },
  claim(id, userId, at) {
    get().prepare(`UPDATE subscriptions SET status = 'CLAIMED', user_id = ?, claimed_at = ?, updated_at = ?
      WHERE id = ? AND status = 'AVAILABLE'`).run(userId, at, at, id);
  },
  revoke(id, at) {
    get().prepare(`UPDATE subscriptions SET status = 'REVOKED', updated_at = ? WHERE id = ? AND status = 'AVAILABLE'`).run(at, id);
  },
  revokeBatch(batchId, at) {
    return get().prepare(`UPDATE subscriptions SET status = 'REVOKED', updated_at = ? WHERE batch_id = ? AND status = 'AVAILABLE'`)
      .run(at, batchId).changes;
  },
  list({ status, season, q, offset, pageSize }) {
    const where = [];
    const args = [];
    if (status) { where.push('s.status = ?'); args.push(status); }
    if (season) { where.push('s.season = ?'); args.push(season); }
    if (q) {
      where.push(`(s.name LIKE ? ESCAPE '\\' OR s.email LIKE ? ESCAPE '\\')`);
      args.push(likeTerm(q), likeTerm(q));
    }
    const w = where.length ? `WHERE ${where.join(' AND ')}` : '';
    const total = get().prepare(`SELECT COUNT(*) AS n FROM subscriptions s ${w}`).get(...args).n;
    const rows = get().prepare(`SELECT s.*, u.name AS member_name FROM subscriptions s LEFT JOIN users u ON u.id = s.user_id ${w}
      ORDER BY s.created_at DESC, s.name COLLATE NOCASE ASC LIMIT ? OFFSET ?`).all(...args, pageSize, offset);
    return { rows, total };
  },
  listForExport({ status, season }) {
    const where = [];
    const args = [];
    if (status) { where.push('s.status = ?'); args.push(status); }
    if (season) { where.push('s.season = ?'); args.push(season); }
    return get().prepare(`SELECT s.* FROM subscriptions s ${where.length ? `WHERE ${where.join(' AND ')}` : ''}
      ORDER BY s.season DESC, s.name COLLATE NOCASE ASC LIMIT 20000`).all(...args);
  },
  listForMember(userId) {
    return get().prepare(`SELECT * FROM subscriptions WHERE user_id = ? AND status = 'CLAIMED' ORDER BY season DESC`).all(userId);
  },
  countByStatus(season) {
    return get().prepare(`SELECT status, COUNT(*) AS n FROM subscriptions WHERE season = ? GROUP BY status`).all(season);
  },
};

const importBatches = {
  insert(b) {
    get().prepare(`INSERT INTO import_batches (id, filename, season, rows_total, rows_imported, rows_skipped, auto_accepted,
      renewals, created_by, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`)
      .run(b.id, b.filename, b.season, b.rows_total, b.rows_imported, b.rows_skipped, b.auto_accepted, b.renewals, b.created_by, b.created_at);
  },
  findById(id) {
    return get().prepare('SELECT * FROM import_batches WHERE id = ?').get(id);
  },
  markReverted(id, by, at) {
    get().prepare('UPDATE import_batches SET reverted_at = ?, reverted_by = ? WHERE id = ?').run(at, by, id);
  },
  list({ offset, pageSize }) {
    const total = get().prepare('SELECT COUNT(*) AS n FROM import_batches').get().n;
    const rows = get().prepare(`SELECT b.*, u.name AS author_name,
        (SELECT COUNT(*) FROM subscriptions s WHERE s.batch_id = b.id AND s.status = 'AVAILABLE') AS still_available
      FROM import_batches b LEFT JOIN users u ON u.id = b.created_by
      ORDER BY b.created_at DESC LIMIT ? OFFSET ?`).all(pageSize, offset);
    return { rows, total };
  },
};

// ---------------------------------------------------------------- audit
const audit = {
  insert(a) {
    get().prepare(`INSERT INTO audit_logs (id, actor_id, action, entity_type, entity_id, metadata, created_at)
      VALUES (?, ?, ?, ?, ?, ?, ?)`)
      .run(a.id, a.actorId, a.action, a.entityType, a.entityId, a.metadata, a.createdAt);
  },
  recent(limit = 8) {
    return get().prepare(`SELECT a.action, a.entity_type, a.entity_id, a.metadata, a.created_at, u.name AS actor_name
      FROM audit_logs a LEFT JOIN users u ON u.id = a.actor_id ORDER BY a.created_at DESC LIMIT ?`).all(limit);
  },
};

// ---------------------------------------------------------------- sessions
const sessions = {
  insert(s) {
    get().prepare('INSERT INTO sessions (id_hash, user_id, csrf_token, created_at, expires_at) VALUES (?, ?, ?, ?, ?)')
      .run(s.idHash, s.userId, s.csrf, s.createdAt, s.expiresAt);
  },
  find(idHash) {
    return get().prepare('SELECT * FROM sessions WHERE id_hash = ?').get(idHash);
  },
  delete(idHash) {
    get().prepare('DELETE FROM sessions WHERE id_hash = ?').run(idHash);
  },
  deleteForUser(userId, exceptHash = '') {
    get().prepare('DELETE FROM sessions WHERE user_id = ? AND id_hash != ?').run(userId, exceptHash);
  },
  purgeExpired(at) {
    get().prepare('DELETE FROM sessions WHERE expires_at < ?').run(at);
  },
};

module.exports = { users, requests, events, participations, messages, suggestions, subscriptions, importBatches, audit, sessions };
