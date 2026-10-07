'use strict';
/** Message Sandbox (FR-15), Suggestion Box (FR-16) and admin dashboard stats. */
const repo = require('../repositories');
const { transaction } = require('../db/database');
const { errors, uuid, now, paged } = require('../utils');
const audit = require('./audit');
const files = require('./files');
const { today } = require('./events');
const sync = require('./sync');
const roster = require('./roster');

/**
 * A global announcement is stored once and read by every active member
 * (no per-recipient duplication).
 */
function sendMessage(input, admin) {
  return transaction(() => {
    const id = uuid();
    repo.messages.insert({ id, title: input.title, content: input.content, senderId: admin.id, createdAt: now() });
    audit.log(admin.id, 'MESSAGE_SENT', 'message', id, { title: input.title, recipients: repo.users.countActiveMembers() });
    sync.publish('members', ['messages'], { notice: `Nouvelle annonce du bureau : « ${input.title} »` });
    sync.publish('admins', ['messages']);
    return { id };
  });
}

function listMessages(page) {
  const { rows, total } = repo.messages.list(page);
  return paged(rows.map((m) => ({
    id: m.id, title: m.title, content: m.content, createdAt: m.created_at, author: m.author_name,
  })), total, page);
}

function sendSuggestion(input, user) {
  const id = uuid();
  repo.suggestions.insert({ id, memberId: user.id, title: input.title, content: input.content, at: now() });
  sync.publish('admins', ['suggestions', 'stats']);
  sync.publish({ userId: user.id }, ['suggestions']);
  return { id, status: 'NEW' };
}

const mapSuggestion = (s) => ({
  id: s.id, title: s.title, content: s.content, status: s.status, createdAt: s.created_at, updatedAt: s.updated_at,
  ...(s.author_name ? { author: { id: s.member_id, name: s.author_name, avatarUrl: files.publicUrl(s.author_photo) } } : {}),
});

function listOwnSuggestions(user) {
  return repo.suggestions.listForMember(user.id).map(mapSuggestion);
}

function listSuggestions(status, page) {
  const { rows, total } = repo.suggestions.list({ status, ...page });
  return paged(rows.map(mapSuggestion), total, page);
}

function setSuggestionStatus(id, status, admin) {
  return transaction(() => {
    const s = repo.suggestions.findById(id);
    if (!s) throw errors.notFound('Suggestion');
    repo.suggestions.setStatus(id, status, now());
    audit.log(admin.id, 'SUGGESTION_STATUS_CHANGED', 'suggestion', id, { from: s.status, to: status });
    sync.publish('admins', ['suggestions', 'stats']);
    if (s.status !== status) {
      const label = { NEW: 'nouvelle', READ: 'lue', IN_REVIEW: 'en cours d’étude', RESOLVED: 'traitée' }[status];
      sync.publish({ userId: s.member_id }, ['suggestions'], { notice: `Votre suggestion${s.title ? ` « ${s.title} »` : ''} est maintenant ${label}.` });
    }
    return { id, status };
  });
}

function dashboard() {
  return {
    subscriptions: roster.subscriptionStats(),
    activeMembers: repo.users.countActiveMembers(),
    pendingRequests: repo.requests.countPending(),
    totalEvents: repo.events.count(),
    upcomingEvents: repo.events.countUpcoming(today()),
    validatedParticipations: repo.participations.countValidated(),
    newSuggestions: repo.suggestions.countNew(),
    recentActivity: repo.audit.recent(8).map((a) => ({
      action: a.action, entityType: a.entity_type, actor: a.actor_name, createdAt: a.created_at,
      metadata: a.metadata ? JSON.parse(a.metadata) : null,
    })),
  };
}

module.exports = {
  sendMessage, listMessages, sendSuggestion, listOwnSuggestions, listSuggestions, setSuggestionStatus, dashboard,
};
