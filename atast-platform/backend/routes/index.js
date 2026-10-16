'use strict';
/** REST routes (chapter "API Design"). Every sensitive route is guarded server-side. */
const express = require('express');
const { auth, memberCtl, eventCtl, commCtl, admin } = require('../controllers');
const { requireAuth, authorize } = require('../middleware/auth');
const { upload, spreadsheetUpload, loginLimiter, registerLimiter } = require('../middleware/security');
const { errors } = require('../utils');
const sync = require('../services/sync');

const router = express.Router();

// Express 4 does not forward rejected promises: wrap every handler.
const h = (fn) => (req, res, next) => {
  try {
    const out = fn(req, res, next);
    if (out && typeof out.catch === 'function') out.catch(next);
  } catch (err) {
    next(err);
  }
};

// Reject malformed ids early (also avoids pointless queries).
const UUID_RE = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;
for (const p of ['id', 'pid']) {
  router.param(p, (_req, _res, next, value) => (UUID_RE.test(value) ? next() : next(errors.notFound())));
}

const ANY = authorize('MEMBER', 'ADMIN');
const MEMBER = authorize('MEMBER');
const ADMIN = authorize('ADMIN');

// ---------------- Authentication
router.post('/auth/register', registerLimiter, h(auth.register));
router.post('/auth/login', loginLimiter, h(auth.login));
router.post('/auth/logout', requireAuth, h(auth.logout));
router.get('/auth/me', requireAuth, h(auth.me));
router.put('/auth/password', requireAuth, h(auth.changePassword));

// ---------------- Real-time synchronisation between devices (Server-Sent Events)
router.get('/sync', ANY, (req, res) => sync.connect(req, res));

// ---------------- Members & profile
router.get('/members', ANY, h(memberCtl.list));
router.get('/members/me', ANY, h(memberCtl.me));
router.put('/members/me', ANY, h(memberCtl.updateMe));
router.post('/members/me/photo', ANY, upload, h(memberCtl.setPhoto));
router.delete('/members/me/photo', ANY, h(memberCtl.removePhoto));
router.get('/members/:id', ANY, h(memberCtl.get));
router.get('/scoreboard', ANY, h(memberCtl.scoreboard));

// ---------------- Events (member side)
router.get('/events', ANY, h(eventCtl.list));
router.get('/events/:id', ANY, h(eventCtl.get));
router.post('/events/:id/participation', MEMBER, h(eventCtl.register));
router.delete('/events/:id/participation', MEMBER, h(eventCtl.withdraw));

// ---------------- Messages & suggestions
router.get('/messages', ANY, h(commCtl.messages));
router.post('/suggestions', MEMBER, h(commCtl.sendSuggestion));
router.get('/suggestions/mine', MEMBER, h(commCtl.mySuggestions));

// ---------------- Admin (all require role ADMIN => HTTP 403 for members)
const a = express.Router();
a.use(ADMIN);
a.get('/stats', h(admin.stats));
a.get('/membership-requests', h(admin.requests));
a.post('/membership-requests/:id/accept', h(admin.accept));
a.post('/membership-requests/:id/reject', h(admin.reject));
a.get('/members', h(admin.members));
a.get('/members/:id', h(admin.member));
a.put('/members/:id', h(admin.updateMember));
a.post('/members/:id/subscriptions', h(admin.memberPayment));
a.patch('/members/:id/status', h(admin.memberStatus));
a.get('/subscriptions', h(admin.subscriptions));
a.post('/subscriptions', h(admin.addSubscription));
a.delete('/subscriptions/:id', h(admin.revokeSubscription));
a.get('/imports', h(admin.imports));
a.post('/imports', spreadsheetUpload, h(admin.importSubscriptions));
a.delete('/imports/:id', h(admin.revertImport));
a.get('/downloads/:kind', h(admin.download));
a.get('/events', h(admin.events));
a.post('/events', h(admin.createEvent));
a.get('/events/:id', h(admin.event));
a.put('/events/:id', h(admin.updateEvent));
a.delete('/events/:id', h(admin.archiveEvent));
a.post('/events/:id/image', upload, h(admin.setEventImage));
a.delete('/events/:id/image', h(admin.removeEventImage));
a.post('/events/:id/participations', h(admin.addParticipation));
a.post('/participations/:pid/validate', h(admin.validateParticipation));
a.delete('/participations/:pid', h(admin.removeParticipation));
a.post('/messages', h(admin.sendMessage));
a.get('/suggestions', h(admin.suggestions));
a.patch('/suggestions/:id', h(admin.suggestionStatus));
for (const p of ['id', 'pid']) {
  a.param(p, (_req, _res, next, value) => (UUID_RE.test(value) ? next() : next(errors.notFound())));
}
router.use('/admin', a);

module.exports = router;
