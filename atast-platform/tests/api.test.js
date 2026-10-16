'use strict';
/**
 * Integration + end-to-end API tests (chapter "Testing Strategy").
 * Runs the real Express app on an in-memory database.
 */
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const { startServer, Client, createAdmin, createMember, uploadDir } = require('./helpers');
const repo = require('../backend/repositories');

const day = (offset) => {
  const d = new Date();
  d.setUTCDate(d.getUTCDate() + offset);
  return d.toISOString().slice(0, 10);
};
const PNG_1PX = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg==', 'base64');

let srv;
let admin;
const eventBody = (o = {}) => ({ title: 'Atelier Arduino', type: 'SMALL', date: day(7), time: '14:00', location: 'Salle TP', isFree: true, status: 'PUBLISHED', ...o });

test.before(async () => {
  srv = await startServer();
  const creds = await createAdmin();
  admin = new Client(srv.base);
  const r = await admin.login(creds.email, creds.password);
  assert.equal(r.status, 200);
  assert.equal(r.data.user.role, 'ADMIN');
});
test.after(() => srv.close());

// ------------------------------------------------------------------ membership
test('registration creates a PENDING request, never a member', async () => {
  const anon = new Client(srv.base);
  const r = await anon.post('/api/auth/register', {
    name: 'Firas Belhadj', email: 'firas@test.tn', phone: '+21655123456', password: 'Secret123', passwordConfirm: 'Secret123', role: 'ADMIN',
  });
  assert.equal(r.status, 201);
  assert.equal(r.data.status, 'PENDING');

  const dup = await anon.post('/api/auth/register', { name: 'Firas B', email: 'FIRAS@test.tn', phone: '+21655123456', password: 'Secret123', passwordConfirm: 'Secret123' });
  assert.equal(dup.status, 409);
  assert.equal(dup.data.error.code, 'REQUEST_PENDING');

  const login = await anon.login('firas@test.tn', 'Secret123');
  assert.equal(login.status, 403);
  assert.equal(login.data.error.code, 'REQUEST_PENDING');

  const wrong = await anon.login('firas@test.tn', 'WrongPass1');
  assert.equal(wrong.status, 401, 'wrong password reveals nothing about the request');
  assert.equal(wrong.data.error.code, 'INVALID_CREDENTIALS');

  // Acceptance: MEMBER role even though "role: ADMIN" was sent at registration
  const list = await admin.get('/api/admin/membership-requests?status=PENDING');
  const req = list.data.items.find((x) => x.email === 'firas@test.tn');
  assert.ok(req);
  assert.equal(req.password_hash, undefined, 'hash never leaves the server');
  const acc = await admin.post(`/api/admin/membership-requests/${req.id}/accept`);
  assert.equal(acc.status, 200);
  const again = await admin.post(`/api/admin/membership-requests/${req.id}/accept`);
  assert.equal(again.status, 409);

  const ok = await anon.login('firas@test.tn', 'Secret123');
  assert.equal(ok.status, 200);
  assert.equal(ok.data.user.role, 'MEMBER');

  const dupActive = await new Client(srv.base).post('/api/auth/register', { name: 'Firas Clone', email: 'firas@test.tn', phone: '+21655123456', password: 'Secret123', passwordConfirm: 'Secret123' });
  assert.equal(dupActive.status, 409);
  assert.equal(dupActive.data.error.code, 'EMAIL_TAKEN');
});

test('rejection keeps the reason, never creates an active member', async () => {
  const anon = new Client(srv.base);
  const r = await anon.post('/api/auth/register', { name: 'Eya Romdhane', email: 'eya@test.tn', phone: '+21698765432', password: 'Secret123', passwordConfirm: 'Secret123' });
  const noReason = await admin.post(`/api/admin/membership-requests/${r.data.id}/reject`, {});
  assert.equal(noReason.status, 422);
  const rej = await admin.post(`/api/admin/membership-requests/${r.data.id}/reject`, { reason: 'Réservé aux étudiants ISIMM' });
  assert.equal(rej.status, 200);
  assert.equal(repo.users.findActiveByEmail('eya@test.tn'), undefined);
  const login = await anon.login('eya@test.tn', 'Secret123');
  assert.equal(login.status, 403);
  assert.equal(login.data.error.code, 'REQUEST_REJECTED');
  assert.match(login.data.error.message, /Réservé aux étudiants ISIMM/);
  // A new request is allowed after a rejection
  const retry = await anon.post('/api/auth/register', { name: 'Eya Romdhane', email: 'eya@test.tn', phone: '+21698765432', password: 'Secret123', passwordConfirm: 'Secret123' });
  assert.equal(retry.status, 201);
});

// ------------------------------------------------------------------ permissions
test('admin routes: 401 when signed out, 403 for members (server-side RBAC)', async () => {
  const member = await createMember(srv.base, admin, { name: 'Karim Jlassi', email: 'karim@test.tn' });
  const anon = new Client(srv.base);
  const routes = [
    ['get', '/api/admin/stats'], ['get', '/api/admin/members'], ['get', '/api/admin/membership-requests'],
    ['post', '/api/admin/events'], ['post', '/api/admin/messages'], ['get', '/api/admin/suggestions'],
  ];
  for (const [m, url] of routes) {
    assert.equal((await anon[m](url, {})).status, 401, `${url} anonymous`);
    assert.equal((await member[m](url, {})).status, 403, `${url} member`);
  }
  assert.equal((await member.post('/api/admin/events', eventBody())).status, 403);
});

test('CSRF: mutating requests need the custom header and the session token', async () => {
  const member = await createMember(srv.base, admin, { name: 'Ines Bouzid', email: 'ines@test.tn' });
  const noToken = await member.post('/api/suggestions', { content: 'Une idée intéressante' }, { headers: { 'X-CSRF-Token': 'forged' } });
  assert.equal(noToken.status, 403);
  const noHeader = await member.post('/api/suggestions', { content: 'Une idée intéressante' }, { headers: { 'X-Requested-With': null } });
  assert.equal(noHeader.status, 403);
  const foreign = await member.post('/api/suggestions', { content: 'Une idée intéressante' }, { headers: { Origin: 'https://evil.example' } });
  assert.equal(foreign.status, 403);
  const ok = await member.post('/api/suggestions', { content: 'Une idée intéressante' });
  assert.equal(ok.status, 201);
});

// ------------------------------------------------------------------ privacy
test('members never receive other members’ private data', async () => {
  const a = await createMember(srv.base, admin, { name: 'Nour Ayari', email: 'nour@test.tn' });
  await a.put('/api/members/me', { name: 'Nour Ayari', phone: '+21622111222', birthday: '2004-05-06', description: 'Maths', github: 'https://github.com/nour' });
  const b = await createMember(srv.base, admin, { name: 'Bilel Saidi', email: 'bilel@test.tn' });
  const list = await b.get('/api/members?q=Nour');
  const n = list.data.items[0];
  assert.equal(n.name, 'Nour Ayari');
  assert.equal(n.socials.github, 'https://github.com/nour');
  for (const key of ['email', 'phone', 'birthday', 'password_hash', 'passwordHash', 'status']) assert.equal(n[key], undefined, key);
  const one = await b.get(`/api/members/${n.id}`);
  assert.equal(one.data.email, undefined);
  assert.equal(one.data.phone, undefined);
  const board = await b.get('/api/scoreboard');
  assert.ok(board.data.items.every((r) => Object.keys(r).sort().join() === 'avatarUrl,memberId,name,rank,score'));
  const full = await admin.get(`/api/admin/members/${n.id}`);
  assert.equal(full.data.email, 'nour@test.tn');
  assert.equal(full.data.birthday, '2004-05-06');
  const forbidden = await b.get(`/api/admin/members/${n.id}`);
  assert.equal(forbidden.status, 403);
});

// ------------------------------------------------------------------ events, participations, points
test('E2E: event → registration → validation → score → type change → removal → archive', async () => {
  const yas = await createMember(srv.base, admin, { name: 'Yasmine Trabelsi', email: 'yasmine@test.tn' });

  // Invalid paid event is refused by the backend
  const bad = await admin.post('/api/admin/events', eventBody({ isFree: false }));
  assert.equal(bad.status, 422);
  assert.ok(bad.data.error.fields.price);

  // Draft is invisible to members
  const draft = await admin.post('/api/admin/events', eventBody({ status: 'DRAFT', title: 'Brouillon secret' }));
  assert.equal(draft.status, 201);
  assert.equal((await yas.get(`/api/events/${draft.data.id}`)).status, 404);

  const ev = await admin.post('/api/admin/events', eventBody({ isFree: false, price: '12,500' }));
  assert.equal(ev.status, 201);
  assert.equal(ev.data.price, '12.500');
  assert.equal(ev.data.currency, 'TND');
  assert.equal(ev.data.points, 10);
  const id = ev.data.id;

  const lib = await yas.get('/api/events?when=upcoming');
  assert.ok(lib.data.items.some((e) => e.id === id));
  assert.ok(!lib.data.items.some((e) => e.id === draft.data.id));

  // Member registers once; duplicate refused
  assert.equal((await yas.post(`/api/events/${id}/participation`)).status, 201);
  const dup = await yas.post(`/api/events/${id}/participation`);
  assert.equal(dup.status, 409);
  assert.equal(dup.data.error.code, 'DUPLICATE_PARTICIPATION');
  assert.equal((await yas.get('/api/members/me')).data.score, 0, 'registration alone gives no points');

  // A member can never award points to themself
  const parts = (await admin.get(`/api/admin/events/${id}`)).data.participants;
  assert.equal(parts.length, 1);
  assert.equal((await yas.post(`/api/admin/participations/${parts[0].id}/validate`)).status, 403);

  // Admin validates → +10, exactly once
  const val = await admin.post(`/api/admin/participations/${parts[0].id}/validate`);
  assert.equal(val.status, 200);
  assert.equal((await admin.post(`/api/admin/participations/${parts[0].id}/validate`)).status, 409);
  assert.equal((await admin.post(`/api/admin/events/${id}/participations`, { memberId: yas.user.id })).status, 409);
  assert.equal((await yas.get('/api/members/me')).data.score, 10);
  const withdraw = await yas.del(`/api/events/${id}/participation`);
  assert.equal(withdraw.status, 409, 'validated participation cannot be withdrawn by the member');

  // Editing the type recalculates points (SMALL → BIG)
  const upd = await admin.put(`/api/admin/events/${id}`, eventBody({ type: 'BIG', isFree: false, price: '12.5' }));
  assert.equal(upd.status, 200);
  assert.equal(upd.data.recalculatedParticipations, 1);
  assert.equal((await yas.get('/api/members/me')).data.score, 30);
  const stored = repo.participations.findById(parts[0].id);
  assert.equal(stored.points_awarded, 30, 'points_awarded stays consistent with the source of truth');

  // Meeting gives 0
  const meet = await admin.post('/api/admin/events', eventBody({ type: 'MEETING', title: 'Réunion du bureau' }));
  await admin.post(`/api/admin/events/${meet.data.id}/participations`, { memberId: yas.user.id });
  assert.equal((await yas.get('/api/members/me')).data.score, 30);

  // Archive keeps history and points
  const arch = await admin.del(`/api/admin/events/${id}`);
  assert.equal(arch.data.status, 'ARCHIVED');
  assert.equal((await yas.get(`/api/events/${id}`)).status, 404);
  assert.equal((await yas.get('/api/members/me')).data.score, 30);
  const hist = await admin.get(`/api/admin/members/${yas.user.id}`);
  assert.ok(hist.data.participations.some((p) => p.event.id === id && p.status === 'VALIDATED'));
  assert.equal((await admin.post(`/api/admin/events/${id}/participations`, { memberId: yas.user.id })).status, 409);

  // Removing a validated participation removes its points
  const rm = await admin.del(`/api/admin/participations/${parts[0].id}`);
  assert.equal(rm.status, 200);
  assert.equal((await yas.get('/api/members/me')).data.score, 0);
});

test('scoreboard: highest score first, ties broken by name', async () => {
  const zed = await createMember(srv.base, admin, { name: 'Zied Haddad', email: 'zied@test.tn' });
  const amel = await createMember(srv.base, admin, { name: 'Amel Haddad', email: 'amel@test.tn' });
  const big = await admin.post('/api/admin/events', eventBody({ type: 'BIG', title: 'Hackathon', date: day(-3), status: 'COMPLETED' }));
  const med = await admin.post('/api/admin/events', eventBody({ type: 'MEDIUM', title: 'Conférence', date: day(-2), status: 'COMPLETED' }));
  for (const m of [zed, amel]) await admin.post(`/api/admin/events/${big.data.id}/participations`, { memberId: m.user.id });
  await admin.post(`/api/admin/events/${med.data.id}/participations`, { memberId: zed.user.id });

  const board = (await zed.get('/api/scoreboard')).data.items;
  const scores = board.map((r) => r.score);
  assert.deepEqual(scores, [...scores].sort((x, y) => y - x), 'descending');
  assert.equal(board[0].name, 'Zied Haddad');
  assert.equal(board[0].score, 50);
  const z = board.findIndex((r) => r.name === 'Amel Haddad');
  assert.equal(board[z].score, 30);
  const tied = board.filter((r) => r.score === board[z].score).map((r) => r.name);
  assert.deepEqual(tied, [...tied].sort((x, y) => x.localeCompare(y)), 'stable alphabetical tie-break');
  assert.deepEqual(board.map((r) => r.rank), board.map((_, i) => i + 1));
  assert.ok(!board.some((r) => r.name === 'Admin Test'), 'admins are not ranked');
});

test('registration is closed for past events', async () => {
  const m = await createMember(srv.base, admin, { name: 'Hamza Dridi', email: 'hamza@test.tn' });
  const past = await admin.post('/api/admin/events', eventBody({ date: day(-1), title: 'Hier' }));
  const r = await m.post(`/api/events/${past.data.id}/participation`);
  assert.equal(r.status, 409);
  assert.equal(r.data.error.code, 'REGISTRATION_CLOSED');
});

// ------------------------------------------------------------------ messages & suggestions
test('global message reaches every member; suggestions flow to the admin', async () => {
  const m = await createMember(srv.base, admin, { name: 'Rania Khelifi', email: 'rania@test.tn' });
  assert.equal((await admin.post('/api/admin/messages', { title: 'Hi', content: 'x' })).status, 422);
  const sent = await admin.post('/api/admin/messages', { title: 'Assemblée générale', content: 'Rendez-vous jeudi en amphi B.' });
  assert.equal(sent.status, 201);
  const inbox = await m.get('/api/messages');
  assert.equal(inbox.data.items[0].title, 'Assemblée générale');
  assert.equal(inbox.data.items[0].author, 'Admin Test');

  const s = await m.post('/api/suggestions', { title: 'Atelier soudure', content: 'Organiser une initiation à la soudure.' });
  assert.equal(s.status, 201);
  const list = await admin.get('/api/admin/suggestions?status=NEW');
  const mine = list.data.items.find((x) => x.id === s.data.id);
  assert.equal(mine.author.name, 'Rania Khelifi');
  assert.equal((await admin.patch(`/api/admin/suggestions/${s.data.id}`, { status: 'BOGUS' })).status, 422);
  assert.equal((await admin.patch(`/api/admin/suggestions/${s.data.id}`, { status: 'IN_REVIEW' })).status, 200);
  const own = await m.get('/api/suggestions/mine');
  assert.equal(own.data.items[0].status, 'IN_REVIEW');
});

// ------------------------------------------------------------------ profile & uploads
test('profile: editing, photo upload validation, default avatar, password change', async () => {
  const m = await createMember(srv.base, admin, { name: 'Sarra Mejri', email: 'sarra@test.tn', password: 'FirstPass1' });
  let me = (await m.get('/api/members/me')).data;
  assert.equal(me.avatarUrl, null, 'no photo => frontend shows the default avatar');

  const bad = await m.put('/api/members/me', { name: 'Sarra Mejri', phone: '+21622000000', instagram: 'https://evil.com/x' });
  assert.equal(bad.status, 422);
  const ok = await m.put('/api/members/me', { name: 'Sarra M.', phone: '+21622000000', instagram: 'instagram.com/sarra', score: 9999, role: 'ADMIN', email: 'hack@x.tn' });
  assert.equal(ok.status, 200);
  assert.equal(ok.data.socials.instagram, 'https://instagram.com/sarra');
  assert.equal(ok.data.score, 0);
  assert.equal(ok.data.role, 'MEMBER');
  assert.equal(ok.data.email, 'sarra@test.tn');

  const fake = new FormData();
  fake.append('file', new Blob(['<?php system($_GET[0]); ?>'], { type: 'image/png' }), 'shell.php.png');
  const rejected = await m.req('POST', '/api/members/me/photo', { form: fake });
  assert.equal(rejected.status, 422);

  const real = new FormData();
  real.append('file', new Blob([PNG_1PX], { type: 'image/png' }), '../../etc/passwd.png');
  const up = await m.req('POST', '/api/members/me/photo', { form: real });
  assert.equal(up.status, 200);
  assert.match(up.data.avatarUrl, /^\/uploads\/[a-f0-9]{32}\.png$/);
  const file = up.data.avatarUrl.split('/').pop();
  assert.ok(fs.existsSync(`${uploadDir}/${file}`));
  const anonImg = await new Client(srv.base).req('GET', up.data.avatarUrl, { raw: true });
  assert.equal(anonImg.status, 401, 'photos are only served to signed-in users');
  const img = await m.req('GET', up.data.avatarUrl, { raw: true });
  assert.equal(img.status, 200);
  assert.equal(img.headers.get('x-content-type-options'), 'nosniff');

  const big = new FormData();
  big.append('file', new Blob([PNG_1PX, Buffer.alloc(3 * 1024 * 1024)], { type: 'image/png' }), 'big.png');
  assert.equal((await m.req('POST', '/api/members/me/photo', { form: big })).status, 422);

  const rm = await m.del('/api/members/me/photo');
  assert.equal(rm.data.avatarUrl, null);

  const wrong = await m.put('/api/auth/password', { currentPassword: 'nope', newPassword: 'NewPass22', newPasswordConfirm: 'NewPass22' });
  assert.equal(wrong.status, 422);
  const changed = await m.put('/api/auth/password', { currentPassword: 'FirstPass1', newPassword: 'NewPass22', newPasswordConfirm: 'NewPass22' });
  assert.equal(changed.status, 200);
  assert.equal((await new Client(srv.base).login('sarra@test.tn', 'FirstPass1')).status, 401);
  assert.equal((await new Client(srv.base).login('sarra@test.tn', 'NewPass22')).status, 200);
  me = (await m.get('/api/members/me')).data;
  assert.equal(me.name, 'Sarra M.');
});

test('deactivation: sessions revoked, hidden from lists, history preserved', async () => {
  const m = await createMember(srv.base, admin, { name: 'Oussama Gharbi', email: 'oussama@test.tn' });
  const ev = await admin.post('/api/admin/events', eventBody({ type: 'MEDIUM', title: 'Visite', date: day(-5), status: 'COMPLETED' }));
  await admin.post(`/api/admin/events/${ev.data.id}/participations`, { memberId: m.user.id });
  const res = await admin.patch(`/api/admin/members/${m.user.id}/status`, { status: 'DEACTIVATED' });
  assert.equal(res.status, 200);
  assert.equal((await m.get('/api/members/me')).status, 401, 'existing session revoked');
  assert.equal((await m.login('oussama@test.tn', 'Membre2026')).data.error.code, 'ACCOUNT_INACTIVE');
  const board = (await admin.get('/api/scoreboard')).data.items;
  assert.ok(!board.some((r) => r.memberId === m.user.id));
  const detail = await admin.get(`/api/admin/members/${m.user.id}`);
  assert.equal(detail.data.score, 20);
  assert.equal(detail.data.participations.length, 1);
  assert.equal((await admin.patch(`/api/admin/members/${m.user.id}/status`, { status: 'ACTIVE' })).status, 200);
  assert.equal((await m.login('oussama@test.tn', 'Membre2026')).status, 200);
});

test('logout ends the session; audit log records sensitive admin actions without secrets', async () => {
  const m = await createMember(srv.base, admin, { name: 'Meriem Ferchichi', email: 'meriem@test.tn' });
  assert.equal((await m.post('/api/auth/logout')).status, 204);
  assert.equal((await m.get('/api/auth/me')).status, 401);
  const stats = await admin.get('/api/admin/stats');
  const actions = new Set(stats.data.recentActivity.map((a) => a.action));
  assert.ok(actions.size > 0);
  const all = require('../backend/db/database').get().prepare('SELECT action, metadata FROM audit_logs').all();
  for (const a of ['MEMBERSHIP_ACCEPTED', 'MEMBERSHIP_REJECTED', 'EVENT_CREATED', 'EVENT_UPDATED', 'EVENT_ARCHIVED', 'PARTICIPATION_VALIDATED', 'PARTICIPATION_REMOVED', 'MESSAGE_SENT']) {
    assert.ok(all.some((r) => r.action === a), a);
  }
  assert.ok(all.every((r) => !/password|hash|\$2[aby]\$/i.test(r.metadata || '')));
});

test('SPA routes serve the app shell; unknown API routes return JSON 404', async () => {
  const c = new Client(srv.base);
  for (const p of ['/login', '/admin/events/new', '/scoreboard']) {
    const r = await c.req('GET', p, { raw: true });
    assert.equal(r.status, 200);
    assert.match(r.headers.get('content-security-policy'), /script-src 'self'/);
  }
  const api = await c.get('/api/nope');
  assert.equal(api.status, 404);
  assert.equal(api.data.error.code, 'NOT_FOUND');
});
