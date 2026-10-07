'use strict';
/** Membership review (FR-02..FR-04) and member management (FR-05, FR-06, FR-19..FR-23). */
const repo = require('../repositories');
const { transaction } = require('../db/database');
const { errors, uuid, now, paged } = require('../utils');
const audit = require('./audit');
const { currentSeason } = require('../validators');
const files = require('./files');
const dto = require('./dto');
const sync = require('./sync');

// ------------------------------------------------------------ requests
function listRequests({ status, q }, page) {
  const { rows, total } = repo.requests.list({ status, q, ...page });
  return paged(rows.map((r) => ({
    id: r.id, name: r.name, email: r.email, phone: r.phone, status: r.status,
    rejectionReason: r.rejection_reason, createdAt: r.created_at, reviewedAt: r.reviewed_at,
    reviewerName: r.reviewer_name, autoAccepted: r.auto_accepted === 1, onPaidList: r.on_paid_list === 1,
  })), total, page);
}

function pendingOrThrow(id) {
  const r = repo.requests.findById(id);
  if (!r) throw errors.notFound('Demande');
  if (r.status !== 'PENDING') throw errors.conflict('Cette demande a déjà été traitée.', 'ALREADY_REVIEWED');
  return r;
}

/**
 * Creates the MEMBER account of a pending request (inside the caller's transaction).
 * An unclaimed paid subscription for the same email (`subscription`, or found here) is attached to the new member.
 * `reviewerId` is null when the system accepts from the paid list.
 */
function activateRequest(r, { reviewerId = null, auto = false, subscription = null } = {}) {
  if (repo.users.findActiveByEmail(r.email)) {
    throw errors.conflict('Un compte actif utilise déjà cette adresse email.', 'EMAIL_TAKEN');
  }
  const at = now();
  const userId = uuid();
  repo.users.insert({
    id: userId, name: r.name, email: r.email, password_hash: r.password_hash, phone: r.phone,
    role: 'MEMBER', status: 'ACTIVE', created_at: at, updated_at: at,
  });
  repo.requests.markAccepted(r.id, userId, reviewerId, at, auto ? 1 : 0);
  const paid = subscription || repo.subscriptions.findAvailableByEmail(r.email);
  if (paid) repo.subscriptions.claim(paid.id, userId, at);
  audit.log(reviewerId, auto ? 'MEMBERSHIP_AUTO_ACCEPTED' : 'MEMBERSHIP_ACCEPTED', 'membership_request', r.id,
    { userId, email: r.email, subscriptionSeason: paid?.season ?? null });
  sync.publish('admins', ['requests', 'members', 'stats', 'subscriptions']);
  sync.publish('all', ['members', 'scoreboard']);
  return { userId, subscriptionSeason: paid?.season ?? null };
}

/** FR-03: activates the account with role MEMBER, inside one transaction. */
function acceptRequest(id, admin) {
  return transaction(() => {
    const r = pendingOrThrow(id);
    const { userId, subscriptionSeason } = activateRequest(r, { reviewerId: admin.id });
    return { id, status: 'ACCEPTED', userId, subscriptionSeason };
  });
}

/** FR-04: rejected requests never become active members; the reason is kept. */
function rejectRequest(id, reason, admin) {
  return transaction(() => {
    const r = pendingOrThrow(id);
    repo.requests.markRejected(id, reason, admin.id, now());
    audit.log(admin.id, 'MEMBERSHIP_REJECTED', 'membership_request', id, { email: r.email, reason });
    sync.publish('admins', ['requests', 'stats']);
    return { id, status: 'REJECTED' };
  });
}

// ------------------------------------------------------------ members
function listPublicMembers(q, page) {
  const { rows, total } = repo.users.listMembers({ q, ...page });
  return paged(rows.map(dto.publicMember), total, page);
}

function getPublicMember(id) {
  const u = repo.users.findMemberWithScore(id);
  if (!u || u.role !== 'MEMBER' || u.status !== 'ACTIVE') throw errors.notFound('Membre');
  return dto.publicMember(u);
}

function listAdminMembers({ q, status, subscription, season }, page) {
  const s = season || currentSeason();
  const { rows, total } = repo.users.listMembers({
    q, ...page, includeEmail: true, status: status || 'ACTIVE', season: s, subscription,
  });
  return { ...paged(rows.map((r) => dto.adminMember(r, s)), total, page), season: s };
}

function getAdminMember(id) {
  const u = repo.users.findMemberWithScore(id);
  if (!u || u.role !== 'MEMBER') throw errors.notFound('Membre');
  const history = repo.participations.listForMember(id).map((p) => ({
    id: p.id, status: p.status, pointsAwarded: p.points_awarded, createdAt: p.created_at, validatedAt: p.validated_at,
    event: { id: p.event_id, title: p.title, type: p.type, date: p.date, time: p.time, location: p.location, status: p.event_status },
  }));
  const season = currentSeason();
  const subs = repo.subscriptions.listForMember(id).map(dto.subscription);
  const current = subs.find((x) => x.season === season);
  return {
    ...dto.adminMember(u),
    subscription: { season, paid: Boolean(current), paidAt: current?.paidAt ?? null, amount: current?.amount ?? null },
    subscriptions: subs,
    participations: history,
    rank: repo.users.rankOf(id),
  };
}

/** Administrator corrects a member's identity details; the unique-active-email rule still holds. */
function updateMemberIdentity(id, input, admin) {
  return transaction(() => {
    const u = repo.users.findById(id);
    if (!u || u.role !== 'MEMBER') throw errors.notFound('Membre');
    const other = repo.users.findActiveByEmail(input.email);
    if (other && other.id !== id) {
      throw errors.validation({ email: 'Un autre compte actif utilise déjà cette adresse email.' });
    }
    repo.users.updateIdentity(id, input, now());
    const changed = ['name', 'email', 'phone', 'birthday'].filter((k) => (u[k] || null) !== (input[k] || null));
    audit.log(admin.id, 'MEMBER_UPDATED', 'user', id, { fields: changed });
    sync.publish('admins', ['members']);
    sync.publish({ userId: id }, ['profile']);
    sync.publish('all', ['members', 'scoreboard'], { memberId: id });
    return getAdminMember(id);
  });
}

function setMemberStatus(id, status, admin) {
  return transaction(() => {
    const u = repo.users.findById(id);
    if (!u || u.role !== 'MEMBER') throw errors.notFound('Membre');
    if (u.status === status) return dto.adminMember({ ...u, score: repo.users.score(id) });
    if (status === 'ACTIVE' && repo.users.findActiveByEmail(u.email)) {
      throw errors.conflict('Un autre compte actif utilise déjà cette adresse email.', 'EMAIL_TAKEN');
    }
    repo.users.setStatus(id, status, now());
    // Logical deactivation: participations are preserved; sessions are revoked.
    if (status !== 'ACTIVE') repo.sessions.deleteForUser(id);
    audit.log(admin.id, 'MEMBER_STATUS_CHANGED', 'user', id, { from: u.status, to: status });
    sync.publish('admins', ['members', 'stats'], { memberId: id });
    sync.publish('all', ['members', 'scoreboard']);
    if (status !== 'ACTIVE') sync.revoke({ userId: id, reason: 'ACCOUNT_INACTIVE' });
    return dto.adminMember({ ...repo.users.findById(id), score: repo.users.score(id) });
  });
}

// ------------------------------------------------------------ own profile
function getOwnProfile(user) {
  const fresh = repo.users.findById(user.id);
  const profile = dto.selfProfile(fresh, repo.users.score(user.id));
  if (fresh.role === 'MEMBER') {
    profile.rank = repo.users.rankOf(user.id);
    profile.participations = repo.participations.listForMember(user.id).map((p) => ({
      id: p.id, status: p.status, pointsAwarded: p.points_awarded,
      event: { id: p.event_id, title: p.title, type: p.type, date: p.date, status: p.event_status },
    }));
  }
  return profile;
}

/** Tells the user's other devices, and everyone showing this person, to refresh. */
function announceProfile(user) {
  sync.publish({ userId: user.id }, ['profile']);
  if (user.role === 'MEMBER') {
    sync.publish('all', ['members', 'scoreboard'], { memberId: user.id });
  }
}

function updateOwnProfile(user, input) {
  repo.users.updateProfile(user.id, input, now());
  announceProfile(user);
  return getOwnProfile(user);
}

function setOwnPhoto(user, file) {
  const name = files.saveImage(file);
  const previous = repo.users.findById(user.id).profile_photo;
  repo.users.setPhoto(user.id, name, now());
  files.removeImage(previous);
  announceProfile(user);
  return getOwnProfile(user);
}

function removeOwnPhoto(user) {
  const previous = repo.users.findById(user.id).profile_photo;
  repo.users.setPhoto(user.id, null, now());
  files.removeImage(previous);
  announceProfile(user);
  return getOwnProfile(user);
}

// ------------------------------------------------------------ scoreboard
function scoreboard(page) {
  const { rows, total } = repo.users.scoreboard(page);
  return paged(rows.map((r, i) => ({
    rank: page.offset + i + 1,
    memberId: r.id,
    name: r.name,
    avatarUrl: files.publicUrl(r.profile_photo),
    score: r.score,
  })), total, page);
}

module.exports = {
  listRequests, acceptRequest, rejectRequest, activateRequest,
  listPublicMembers, getPublicMember, listAdminMembers, getAdminMember, updateMemberIdentity, setMemberStatus,
  getOwnProfile, updateOwnProfile, setOwnPhoto, removeOwnPhoto, scoreboard,
};
