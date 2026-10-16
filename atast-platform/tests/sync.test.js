'use strict';
/** Synchronisation between devices: who is told what, and when. */
const test = require('node:test');
const assert = require('node:assert/strict');
const { startServer, Client, createAdmin, createMember } = require('./helpers');

/** Opens /api/sync like a browser tab and collects frames. */
async function openStream(client) {
  const ctrl = new AbortController();
  const res = await fetch(`${client.base}/api/sync`, { headers: { Cookie: client.cookie }, signal: ctrl.signal });
  const frames = [];
  let closed = false;
  const reader = res.body.getReader();
  const dec = new TextDecoder();
  let buf = '';
  (async () => {
    try {
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        let i;
        while ((i = buf.indexOf('\n\n')) !== -1) {
          const raw = buf.slice(0, i);
          buf = buf.slice(i + 2);
          const ev = /^event: (.*)$/m.exec(raw)?.[1];
          const data = /^data: (.*)$/m.exec(raw)?.[1];
          if (ev) frames.push({ event: ev, data: data ? JSON.parse(data) : null });
        }
      }
    } catch {
      /* aborted */
    }
    closed = true;
  })();
  const s = {
    status: res.status,
    frames,
    get closed() { return closed; },
    changes: () => frames.filter((f) => f.event === 'change').map((f) => f.data),
    close: () => ctrl.abort(),
    async waitFor(pred, ms = 2000) {
      const end = Date.now() + ms;
      while (Date.now() < end) {
        const hit = frames.find(pred);
        if (hit) return hit;
        await new Promise((r) => setTimeout(r, 20));
      }
      return null;
    },
  };
  await s.waitFor((f) => f.event === 'ready');
  return s;
}
const settle = () => new Promise((r) => setTimeout(r, 150));
const day = (o) => { const d = new Date(); d.setUTCDate(d.getUTCDate() + o); return d.toISOString().slice(0, 10); };

let srv;
let admin;
test.before(async () => {
  srv = await startServer();
  const c = await createAdmin();
  admin = new Client(srv.base);
  await admin.login(c.email, c.password);
});
test.after(() => srv.close());

test('stream requires a signed-in user', async () => {
  const res = await fetch(`${srv.base}/api/sync`);
  assert.equal(res.status, 401);
});

test('validating a participation reaches all of the member’s devices, with a personal notice only for them', async () => {
  const phone = await createMember(srv.base, admin, { name: 'Yasmine Trabelsi', email: 'y@test.tn' });
  const laptop = new Client(srv.base);
  await laptop.login('y@test.tn', 'Membre2026'); // second device, second session
  const other = await createMember(srv.base, admin, { name: 'Ahmed Hammami', email: 'a@test.tn' });

  const sPhone = await openStream(phone);
  const sLaptop = await openStream(laptop);
  const sOther = await openStream(other);
  const sAdmin = await openStream(admin);

  const ev = await admin.post('/api/admin/events', { title: 'Hackathon', type: 'BIG', date: day(-1), time: '09:00', location: 'Amphi A', isFree: true, status: 'COMPLETED' });
  await admin.post(`/api/admin/events/${ev.data.id}/participations`, { memberId: phone.user.id });

  for (const s of [sPhone, sLaptop]) {
    const hit = await s.waitFor((f) => f.event === 'change' && f.data.topics.includes('profile') && f.data.notice);
    assert.ok(hit, 'both devices of the member are told');
    assert.match(hit.data.notice, /Hackathon.*\+30 pts/);
  }
  assert.ok(await sOther.waitFor((f) => f.event === 'change' && f.data.topics.includes('scoreboard')), 'everyone refreshes the ranking');
  await settle();
  assert.ok(!sOther.changes().some((c) => c.notice && /Hackathon/.test(c.notice)), 'no one else gets the personal notice');
  assert.ok(sAdmin.changes().some((c) => c.topics.includes('stats')));

  // Frames carry topics/ids only — never personal data
  const all = JSON.stringify([...sPhone.frames, ...sOther.frames, ...sAdmin.frames]);
  assert.ok(!/@test\.tn|password|phone|birthday/.test(all));

  // The phone now reads the same score the laptop reads
  assert.equal((await phone.get('/api/members/me')).data.score, 30);
  assert.equal((await laptop.get('/api/members/me')).data.score, 30);
  [sPhone, sLaptop, sOther, sAdmin].forEach((s) => s.close());
});

test('admin-only topics are never sent to members', async () => {
  const m = await createMember(srv.base, admin, { name: 'Nour Ayari', email: 'n@test.tn' });
  const sMember = await openStream(m);
  const sAdmin = await openStream(admin);
  await new Client(srv.base).post('/api/auth/register', { name: 'Firas Belhadj', email: 'f@test.tn', phone: '+21655123456', password: 'Secret123', passwordConfirm: 'Secret123' });
  assert.ok(await sAdmin.waitFor((f) => f.event === 'change' && f.data.topics.includes('requests')));
  await settle();
  assert.ok(!sMember.changes().some((c) => c.topics.includes('requests') || c.topics.includes('stats')));
  sMember.close();
  sAdmin.close();
});

test('profile edited on one device refreshes the others; announcements reach members', async () => {
  const a = await createMember(srv.base, admin, { name: 'Sarra Mejri', email: 's@test.tn' });
  const b = new Client(srv.base);
  await b.login('s@test.tn', 'Membre2026');
  const viewer = await createMember(srv.base, admin, { name: 'Bilel Saidi', email: 'b@test.tn' });
  const sB = await openStream(b);
  const sViewer = await openStream(viewer);

  await a.put('/api/members/me', { name: 'Sarra M.', phone: '+21622000000' });
  assert.ok(await sB.waitFor((f) => f.event === 'change' && f.data.topics.includes('profile')));
  assert.ok(await sViewer.waitFor((f) => f.event === 'change' && f.data.topics.includes('members')), 'member lists show the new name');

  await admin.post('/api/admin/messages', { title: 'Assemblée générale', content: 'Jeudi, amphi B.' });
  const msg = await sViewer.waitFor((f) => f.event === 'change' && f.data.topics.includes('messages'));
  assert.match(msg.data.notice, /Assemblée générale/);
  sB.close();
  sViewer.close();
});

test('nothing is announced for a change that fails', async () => {
  const m = await createMember(srv.base, admin, { name: 'Hamza Dridi', email: 'h@test.tn' });
  const s = await openStream(m);
  const bad = await admin.post('/api/admin/events', { title: 'Payant sans prix', type: 'SMALL', date: day(3), time: '10:00', location: 'ISIMM', isFree: false, status: 'PUBLISHED' });
  assert.equal(bad.status, 422);
  await settle();
  assert.equal(s.changes().length, 0);
  s.close();
});

test('password change signs out the other devices immediately', async () => {
  const phone = await createMember(srv.base, admin, { name: 'Karim Jlassi', email: 'k@test.tn', password: 'FirstPass1' });
  const laptop = new Client(srv.base);
  await laptop.login('k@test.tn', 'FirstPass1');
  const sPhone = await openStream(phone);
  const sLaptop = await openStream(laptop);
  await phone.put('/api/auth/password', { currentPassword: 'FirstPass1', newPassword: 'NewPass22', newPasswordConfirm: 'NewPass22' });
  const ended = await sLaptop.waitFor((f) => f.event === 'session');
  assert.equal(ended.data.reason, 'PASSWORD_CHANGED');
  await settle();
  assert.ok(sLaptop.closed, 'stream of the other device is closed');
  assert.ok(!sPhone.frames.some((f) => f.event === 'session'), 'the device that changed it stays signed in');
  assert.equal((await laptop.get('/api/members/me')).status, 401);
  sPhone.close();
});

test('suspending a member ends their live sessions', async () => {
  const m = await createMember(srv.base, admin, { name: 'Ines Bouzid', email: 'i@test.tn' });
  const s = await openStream(m);
  await admin.patch(`/api/admin/members/${m.user.id}/status`, { status: 'SUSPENDED' });
  const ended = await s.waitFor((f) => f.event === 'session');
  assert.equal(ended.data.reason, 'ACCOUNT_INACTIVE');
});

test('logout ends the stream of every tab sharing that session only', async () => {
  const tab1 = await createMember(srv.base, admin, { name: 'Rania Khelifi', email: 'r@test.tn' });
  const tab2 = new Client(srv.base);
  tab2.cookie = tab1.cookie; // same browser, same cookie
  const phone = new Client(srv.base);
  await phone.login('r@test.tn', 'Membre2026');
  const s2 = await openStream(tab2);
  const sPhone = await openStream(phone);
  await tab1.post('/api/auth/logout');
  const ended = await s2.waitFor((f) => f.event === 'session');
  assert.equal(ended.data.reason, 'LOGOUT');
  await settle();
  assert.ok(!sPhone.frames.some((f) => f.event === 'session'), 'other devices stay signed in');
  sPhone.close();
});
