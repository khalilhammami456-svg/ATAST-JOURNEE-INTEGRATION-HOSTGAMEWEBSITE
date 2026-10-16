'use strict';
/** Events (FR-07..FR-12) and participations (FR-13, FR-14). */
const config = require('../config');
const repo = require('../repositories');
const { transaction } = require('../db/database');
const { errors, uuid, now, paged } = require('../utils');
const { pointsFor } = require('./points');
const audit = require('./audit');
const files = require('./files');
const dto = require('./dto');
const sync = require('./sync');

/** Every device showing events (and admin counters) refreshes. */
function announceEvent(eventId, extraTopics = []) {
  sync.publish('all', ['events', ...extraTopics], { eventId });
  sync.publish('admins', ['stats'], { eventId });
}

const MEMBER_VISIBLE = ['PUBLISHED', 'COMPLETED'];

/** Today's date in the club's time zone (YYYY-MM-DD). */
function today() {
  return new Intl.DateTimeFormat('en-CA', { timeZone: config.timezone }).format(new Date());
}

// ------------------------------------------------------------ reading
function listForMember(user, { q, type, when }, page) {
  const { rows, total } = repo.events.list({ statuses: MEMBER_VISIBLE, q, type, when, today: today(), ...page });
  const mine = repo.participations.statusesForMember(user.id, rows.map((r) => r.id));
  return paged(rows.map((e) => dto.event(e, { myParticipation: mine.get(e.id) || null })), total, page);
}

function getForMember(user, id) {
  const e = repo.events.findById(id);
  if (!e || !MEMBER_VISIBLE.includes(e.status)) throw errors.notFound('Événement');
  const mine = repo.participations.findActive(id, user.id);
  return dto.event(e, { myParticipation: mine ? mine.status : null, canRegister: canRegister(e) });
}

function canRegister(e) {
  return e.status === 'PUBLISHED' && e.date >= today();
}

function listForAdmin({ q, type, status, when }, page) {
  let statuses;
  if (status === 'ALL') statuses = null;
  else if (status) statuses = [status];
  else statuses = ['DRAFT', 'PUBLISHED', 'COMPLETED'];
  const { rows, total } = repo.events.list({ statuses, q, type, when, today: today(), ...page });
  return paged(rows.map((e) => dto.event(e)), total, page);
}

function getForAdmin(id) {
  const e = repo.events.findById(id);
  if (!e) throw errors.notFound('Événement');
  const participants = repo.participations.listForEvent(id).map((p) => ({
    id: p.id, status: p.status, pointsAwarded: p.points_awarded, createdAt: p.created_at, validatedAt: p.validated_at,
    member: { id: p.member_id, name: p.name, email: p.email, avatarUrl: files.publicUrl(p.profile_photo), status: p.member_status },
  }));
  return { ...dto.event(e), participants };
}

// ------------------------------------------------------------ writing
function create(input, admin) {
  return transaction(() => {
    const id = uuid();
    const at = now();
    repo.events.insert({ ...input, id, createdBy: admin.id, createdAt: at, updatedAt: at });
    audit.log(admin.id, 'EVENT_CREATED', 'event', id, { title: input.title, type: input.type, status: input.status });
    announceEvent(id);
    return dto.event(repo.events.findById(id));
  });
}

/** FR-11: editing never deletes participations; a type change recalculates points. */
function update(id, input, admin) {
  return transaction(() => {
    const before = repo.events.findById(id);
    if (!before) throw errors.notFound('Événement');
    const at = now();
    repo.events.update(id, input, at);
    let recalculated = 0;
    if (before.type !== input.type) {
      recalculated = repo.participations.recalcForEvent(id, pointsFor(input.type), at);
    }
    audit.log(admin.id, input.status === 'ARCHIVED' && before.status !== 'ARCHIVED' ? 'EVENT_ARCHIVED' : 'EVENT_UPDATED',
      'event', id, {
        title: input.title,
        ...(before.type !== input.type ? { typeFrom: before.type, typeTo: input.type, recalculated } : {}),
        ...(before.status !== input.status ? { statusFrom: before.status, statusTo: input.status } : {}),
      });
    // A type change moves scores: members' own score and the ranking refresh too.
    announceEvent(id, before.type !== input.type && recalculated ? ['scoreboard', 'profile'] : []);
    return { ...dto.event(repo.events.findById(id)), recalculatedParticipations: recalculated };
  });
}

/** FR-12: logical archiving — history and scores are preserved. */
function archive(id, admin) {
  return transaction(() => {
    const e = repo.events.findById(id);
    if (!e) throw errors.notFound('Événement');
    if (e.status !== 'ARCHIVED') {
      repo.events.setStatus(id, 'ARCHIVED', now());
      audit.log(admin.id, 'EVENT_ARCHIVED', 'event', id, { title: e.title, previousStatus: e.status });
      announceEvent(id);
    }
    return dto.event(repo.events.findById(id));
  });
}

function setImage(id, file, admin) {
  const e = repo.events.findById(id);
  if (!e) throw errors.notFound('Événement');
  const name = files.saveImage(file);
  repo.events.setImage(id, name, now());
  files.removeImage(e.image_url);
  audit.log(admin.id, 'EVENT_IMAGE_UPDATED', 'event', id);
  announceEvent(id);
  return dto.event(repo.events.findById(id));
}

function removeImage(id, admin) {
  const e = repo.events.findById(id);
  if (!e) throw errors.notFound('Événement');
  repo.events.setImage(id, null, now());
  files.removeImage(e.image_url);
  audit.log(admin.id, 'EVENT_IMAGE_REMOVED', 'event', id);
  announceEvent(id);
  return dto.event(repo.events.findById(id));
}

// ------------------------------------------------------------ participations
/** Member signs up for an upcoming published event (no points until validated). */
function register(user, eventId) {
  return transaction(() => {
    const e = repo.events.findById(eventId);
    if (!e || !MEMBER_VISIBLE.includes(e.status)) throw errors.notFound('Événement');
    if (!canRegister(e)) throw errors.conflict("Les inscriptions sont fermées pour cet événement.", 'REGISTRATION_CLOSED');
    if (repo.participations.findActive(eventId, user.id)) {
      throw errors.conflict('Vous êtes déjà inscrit à cet événement.', 'DUPLICATE_PARTICIPATION');
    }
    repo.participations.insert({ id: uuid(), eventId, memberId: user.id, status: 'REGISTERED', points: 0, at: now() });
    announceRegistration(user.id, eventId);
    return { status: 'REGISTERED' };
  });
}

/** Member withdraws a registration that has not been validated yet. */
function withdraw(user, eventId) {
  return transaction(() => {
    const p = repo.participations.findActive(eventId, user.id);
    if (!p) throw errors.notFound('Inscription');
    if (p.status === 'VALIDATED') {
      throw errors.conflict("Votre participation a déjà été validée. Contactez l'administration pour la modifier.", 'ALREADY_VALIDATED');
    }
    repo.participations.remove(p.id, now());
    announceRegistration(user.id, eventId);
    return { status: null };
  });
}

function announceRegistration(userId, eventId) {
  sync.publish({ userId }, ['profile', 'events'], { eventId });
  sync.publish('admins', ['events', 'stats'], { eventId });
}

/** The member gets a personal notice; everyone's ranking and event pages refresh. */
function announceParticipation(memberId, e, notice) {
  sync.publish({ userId: memberId }, ['profile'], { eventId: e.id, notice });
  sync.publish('all', ['scoreboard', 'events'], { eventId: e.id });
  sync.publish('admins', ['stats', 'members'], { eventId: e.id, memberId });
}

const validatedNotice = (e, points) => (points
  ? `Votre participation à « ${e.title} » a été validée : +${points} pts.`
  : `Votre présence à « ${e.title} » a été validée.`);

function assertCanValidate(e) {
  if (e.status !== 'PUBLISHED' && e.status !== 'COMPLETED') {
    throw errors.conflict('Les participations ne peuvent être validées que pour un événement publié ou terminé.', 'EVENT_NOT_OPEN');
  }
}

/** Admin records attendance directly (validated => points awarded once). */
function adminAdd(eventId, memberId, admin) {
  return transaction(() => {
    const e = repo.events.findById(eventId);
    if (!e) throw errors.notFound('Événement');
    assertCanValidate(e);
    const m = repo.users.findById(memberId);
    if (!m || m.role !== 'MEMBER' || m.status !== 'ACTIVE') throw errors.notFound('Membre');
    const existing = repo.participations.findActive(eventId, memberId);
    const at = now();
    const points = pointsFor(e.type);
    if (existing?.status === 'VALIDATED') {
      throw errors.conflict(`La participation de ${m.name} est déjà validée.`, 'DUPLICATE_PARTICIPATION');
    }
    let id;
    if (existing) {
      id = existing.id;
      repo.participations.validate(id, points, admin.id, at);
    } else {
      id = uuid();
      repo.participations.insert({
        id, eventId, memberId, status: 'VALIDATED', points, validatedAt: at, validatedBy: admin.id, at,
      });
    }
    audit.log(admin.id, 'PARTICIPATION_VALIDATED', 'event_participation', id, { eventId, memberId, points });
    announceParticipation(memberId, e, validatedNotice(e, points));
    return getForAdmin(eventId);
  });
}

function adminValidate(participationId, admin) {
  return transaction(() => {
    const p = repo.participations.findById(participationId);
    if (!p || p.status === 'REMOVED') throw errors.notFound('Participation');
    if (p.status === 'VALIDATED') throw errors.conflict('Cette participation est déjà validée.', 'DUPLICATE_PARTICIPATION');
    const e = repo.events.findById(p.event_id);
    assertCanValidate(e);
    const points = pointsFor(e.type);
    repo.participations.validate(p.id, points, admin.id, now());
    audit.log(admin.id, 'PARTICIPATION_VALIDATED', 'event_participation', p.id, { eventId: e.id, memberId: p.member_id, points });
    announceParticipation(p.member_id, e, validatedNotice(e, points));
    return getForAdmin(e.id);
  });
}

function adminRemove(participationId, admin) {
  return transaction(() => {
    const p = repo.participations.findById(participationId);
    if (!p || p.status === 'REMOVED') throw errors.notFound('Participation');
    repo.participations.remove(p.id, now());
    audit.log(admin.id, 'PARTICIPATION_REMOVED', 'event_participation', p.id, {
      eventId: p.event_id, memberId: p.member_id, previousStatus: p.status, pointsRemoved: p.points_awarded,
    });
    const e = repo.events.findById(p.event_id);
    announceParticipation(p.member_id, e, p.status === 'VALIDATED'
      ? `Votre participation à « ${e.title} » a été retirée par le bureau.`
      : `Votre inscription à « ${e.title} » a été annulée par le bureau.`);
    return getForAdmin(p.event_id);
  });
}

module.exports = {
  today, listForMember, getForMember, listForAdmin, getForAdmin, create, update, archive, setImage, removeImage,
  register, withdraw, adminAdd, adminValidate, adminRemove,
};
