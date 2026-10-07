'use strict';
/**
 * Controllers: translate HTTP <-> services. No business rules live here;
 * every input goes through a validator before reaching a service.
 */
const v = require('../validators');
const authService = require('../services/auth');
const members = require('../services/members');
const events = require('../services/events');
const comm = require('../services/communication');
const roster = require('../services/roster');
const dto = require('../services/dto');
const { setSessionCookie, clearSessionCookie } = require('../middleware/auth');
const { pagination, errors } = require('../utils');

const enumQuery = (value, allowed) => {
  if (value === undefined || value === '') return undefined;
  const up = String(value).toUpperCase();
  if (!allowed.includes(up)) throw errors.validation({ filter: 'Filtre invalide.' });
  return up;
};
const searchQuery = (q) => (typeof q === 'string' && q.trim() ? q.trim().slice(0, 80) : undefined);
const whenQuery = (w) => (w === 'upcoming' || w === 'past' ? w : undefined);

// ------------------------------------------------------------ auth
const auth = {
  async register(req, res) {
    const input = v.register(req.body);
    const result = await authService.register(input);
    res.status(201).json({
      ...result,
      message: result.autoAccepted
        ? 'Votre cotisation est confirmée : votre adhésion est acceptée. Vous pouvez vous connecter.'
        : "Votre demande d'adhésion a été envoyée. L'administration du club va l'examiner.",
    });
  },
  async login(req, res) {
    const input = v.login(req.body);
    const { user, session } = await authService.login(input);
    if (req.authSession) authService.logout(req.authSession.idHash);
    setSessionCookie(res, session);
    res.json({ user, csrfToken: session.csrf });
  },
  logout(req, res) {
    authService.logout(req.authSession?.idHash);
    clearSessionCookie(res);
    res.status(204).end();
  },
  me(req, res) {
    res.json({ user: dto.sessionUser(req.user), csrfToken: req.authSession.csrf });
  },
  async changePassword(req, res) {
    const input = v.changePassword(req.body);
    await authService.changePassword(req.user, req.authSession.idHash, input);
    res.json({ message: 'Mot de passe modifié. Vos autres appareils ont été déconnectés.' });
  },
};

// ------------------------------------------------------------ members
const memberCtl = {
  list(req, res) {
    res.json(members.listPublicMembers(searchQuery(req.query.q), pagination(req.query, { defaultSize: 24 })));
  },
  get(req, res) {
    res.json(members.getPublicMember(req.params.id));
  },
  me(req, res) {
    res.json(members.getOwnProfile(req.user));
  },
  updateMe(req, res) {
    res.json(members.updateOwnProfile(req.user, v.profileUpdate(req.body)));
  },
  setPhoto(req, res) {
    res.json(members.setOwnPhoto(req.user, req.file));
  },
  removePhoto(req, res) {
    res.json(members.removeOwnPhoto(req.user));
  },
  scoreboard(req, res) {
    res.json(members.scoreboard(pagination(req.query, { defaultSize: 50 })));
  },
};

// ------------------------------------------------------------ events (member side)
const eventCtl = {
  list(req, res) {
    const filters = {
      q: searchQuery(req.query.q),
      type: enumQuery(req.query.type, v.EVENT_TYPES),
      when: whenQuery(req.query.when),
    };
    res.json(events.listForMember(req.user, filters, pagination(req.query, { defaultSize: 12 })));
  },
  get(req, res) {
    res.json(events.getForMember(req.user, req.params.id));
  },
  register(req, res) {
    res.status(201).json(events.register(req.user, req.params.id));
  },
  withdraw(req, res) {
    res.json(events.withdraw(req.user, req.params.id));
  },
};

// ------------------------------------------------------------ communication
const commCtl = {
  messages(req, res) {
    res.json(comm.listMessages(pagination(req.query, { defaultSize: 10 })));
  },
  sendSuggestion(req, res) {
    res.status(201).json(comm.sendSuggestion(v.suggestion(req.body), req.user));
  },
  mySuggestions(req, res) {
    res.json({ items: comm.listOwnSuggestions(req.user) });
  },
};

// ------------------------------------------------------------ admin
const admin = {
  stats(_req, res) {
    res.json(comm.dashboard());
  },
  requests(req, res) {
    const filters = {
      status: enumQuery(req.query.status, ['PENDING', 'ACCEPTED', 'REJECTED']),
      q: searchQuery(req.query.q),
    };
    res.json(members.listRequests(filters, pagination(req.query)));
  },
  accept(req, res) {
    res.json(members.acceptRequest(req.params.id, req.user));
  },
  reject(req, res) {
    res.json(members.rejectRequest(req.params.id, v.rejection(req.body).reason, req.user));
  },
  members(req, res) {
    const filters = {
      q: searchQuery(req.query.q),
      status: enumQuery(req.query.status, ['ACTIVE', 'SUSPENDED', 'DEACTIVATED', 'ANY']),
      subscription: enumQuery(req.query.subscription, ['PAID', 'UNPAID'])?.toLowerCase(),
      season: v.seasonParam(req.query.season),
    };
    res.json(members.listAdminMembers(filters, pagination(req.query, { defaultSize: 24 })));
  },
  member(req, res) {
    res.json(members.getAdminMember(req.params.id));
  },
  updateMember(req, res) {
    res.json(members.updateMemberIdentity(req.params.id, v.memberAdminUpdate(req.body), req.user));
  },
  memberPayment(req, res) {
    res.status(201).json(roster.recordMemberPayment(req.params.id, v.memberPayment(req.body), req.user));
  },
  memberStatus(req, res) {
    if (req.params.id === req.user.id) throw errors.forbidden();
    res.json(members.setMemberStatus(req.params.id, v.memberStatus(req.body).status, req.user));
  },
  // ---- subscriptions (cotisations) and Excel imports
  async importSubscriptions(req, res) {
    if (!req.file) throw errors.validation({ file: 'Choisissez un fichier Excel (.xlsx) ou CSV.' });
    const season = v.seasonParam(req.body?.season) || v.currentSeason();
    const dryRun = String(req.body?.dryRun) !== 'false';
    res.status(dryRun ? 200 : 201).json(await roster.importFile({ buffer: req.file.buffer, filename: req.file.originalname, season, dryRun }, req.user));
  },
  addSubscription(req, res) {
    res.status(201).json(roster.addOne(v.subscriptionForm(req.body), req.user));
  },
  subscriptions(req, res) {
    const filters = {
      status: enumQuery(req.query.status, ['AVAILABLE', 'CLAIMED', 'REVOKED']),
      season: v.seasonParam(req.query.season),
      q: searchQuery(req.query.q),
    };
    res.json(roster.listSubscriptions(filters, pagination(req.query)));
  },
  revokeSubscription(req, res) {
    res.json(roster.revokeSubscription(req.params.id, req.user));
  },
  imports(req, res) {
    res.json(roster.listBatches(pagination(req.query, { defaultSize: 10 })));
  },
  revertImport(req, res) {
    res.json(roster.revertBatch(req.params.id, req.user));
  },
  async download(req, res) {
    const season = v.seasonParam(req.query.season) || v.currentSeason();
    const kind = req.params.kind;
    let file;
    if (kind === 'template') file = await roster.templateFile();
    else if (kind === 'members') file = await roster.membersFile({ status: enumQuery(req.query.status, ['ACTIVE', 'SUSPENDED', 'DEACTIVATED', 'ANY']) || 'ANY', season });
    else if (kind === 'subscriptions') file = await roster.subscriptionsFile({ status: enumQuery(req.query.status, ['AVAILABLE', 'CLAIMED', 'REVOKED']), season: req.query.season ? season : undefined });
    else throw errors.notFound();
    res.set({ 'Content-Type': file.type, 'Content-Disposition': `attachment; filename="${file.filename}"`, 'Content-Length': file.buffer.length });
    res.end(file.buffer);
  },
  events(req, res) {
    const filters = {
      q: searchQuery(req.query.q),
      type: enumQuery(req.query.type, v.EVENT_TYPES),
      status: enumQuery(req.query.status, [...v.EVENT_STATUSES, 'ALL']),
      when: whenQuery(req.query.when),
    };
    res.json(events.listForAdmin(filters, pagination(req.query, { defaultSize: 20 })));
  },
  event(req, res) {
    res.json(events.getForAdmin(req.params.id));
  },
  createEvent(req, res) {
    res.status(201).json(events.create(v.eventInput(req.body), req.user));
  },
  updateEvent(req, res) {
    res.json(events.update(req.params.id, v.eventInput(req.body, { forUpdate: true }), req.user));
  },
  archiveEvent(req, res) {
    res.json(events.archive(req.params.id, req.user));
  },
  setEventImage(req, res) {
    res.json(events.setImage(req.params.id, req.file, req.user));
  },
  removeEventImage(req, res) {
    res.json(events.removeImage(req.params.id, req.user));
  },
  addParticipation(req, res) {
    res.status(201).json(events.adminAdd(req.params.id, v.participationAdd(req.body).memberId, req.user));
  },
  validateParticipation(req, res) {
    res.json(events.adminValidate(req.params.pid, req.user));
  },
  removeParticipation(req, res) {
    res.json(events.adminRemove(req.params.pid, req.user));
  },
  sendMessage(req, res) {
    res.status(201).json(comm.sendMessage(v.message(req.body), req.user));
  },
  suggestions(req, res) {
    const status = enumQuery(req.query.status, v.SUGGESTION_STATUSES);
    res.json(comm.listSuggestions(status, pagination(req.query)));
  },
  suggestionStatus(req, res) {
    res.json(comm.setSuggestionStatus(req.params.id, v.suggestionStatus(req.body).status, req.user));
  },
};

module.exports = { auth, memberCtl, eventCtl, commCtl, admin };
