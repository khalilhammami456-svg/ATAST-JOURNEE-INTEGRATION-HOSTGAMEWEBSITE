'use strict';
/** Paid-subscription roster: Excel/CSV import, automatic acceptance, exports and admin member management. */
const test = require('node:test');
const assert = require('node:assert/strict');
const { startServer, Client, createAdmin, createMember } = require('./helpers');
const { readSheet } = require('read-excel-file/node');
const writeXlsx = require('write-excel-file/node').default;
const { zipSync } = require('fflate');
const v = require('../backend/validators');

let srv;
let admin;
const SEASON = v.currentSeason();

test.before(async () => {
  srv = await startServer();
  const creds = await createAdmin();
  admin = new Client(srv.base);
  assert.equal((await admin.login(creds.email, creds.password)).status, 200);
});
test.after(() => srv.close());

const header = ['Nom complet', 'Email', 'Téléphone', 'Montant (DT)', 'Date de paiement', 'Référence'];
async function xlsx(rows) {
  const cells = rows.map((r) => r.map((c) => (c instanceof Date ? { value: c, format: 'yyyy-mm-dd' } : c)));
  return writeXlsx([header, ...cells]).toBuffer();
}
function upload(client, buffer, { filename = 'liste.xlsx', season = SEASON, dryRun = true, type } = {}) {
  const form = new FormData();
  form.append('season', season);
  form.append('dryRun', String(dryRun));
  form.append('file', new Blob([buffer], type ? { type } : {}), filename);
  return client.req('POST', '/api/admin/imports', { form });
}
const register = (email, phone, name = 'Personne Test') =>
  new Client(srv.base).post('/api/auth/register', { name, email, phone, password: 'Membre2026', passwordConfirm: 'Membre2026' });
const byEmail = (rows, email) => rows.find((r) => r.email === email);

test('import preview classifies every row and writes nothing', async () => {
  await createMember(srv.base, admin, { name: 'Déjà Membre', email: 'deja@test.tn' });
  const pending = await register('attente@test.tn', '+216 20 111 222', 'En Attente');
  assert.equal(pending.data.status, 'PENDING');
  await register('autretel@test.tn', '+216 20 999 999', 'Autre Tel');

  const buf = await xlsx([
    ['Nouvelle Personne', 'nouvelle@test.tn', '+216 21 000 001', '25,5 DT', '15/09/2026', 'R-001'],
    ['Déjà Membre', 'DEJA@test.tn', '20123456', 25, new Date('2026-09-20'), null],
    ['En Attente', 'attente@test.tn', '20111222', 25, null, null],
    ['Autre Tel', 'autretel@test.tn', '21555555', 25, null, null],
    ['Doublon', 'nouvelle@test.tn', '21000001', 25, null, null],
    ['Mauvais Email', 'pas-un-email', '21000002', 25, null, null],
    ['Mauvais Montant', 'montant@test.tn', '21000003', 'abc', null, null],
  ]);
  const r = await upload(admin, buf);
  assert.equal(r.status, 200);
  assert.equal(r.data.dryRun, true);
  const rows = r.data.rows;
  assert.equal(byEmail(rows, 'nouvelle@test.tn').status, 'NEW');
  assert.equal(byEmail(rows, 'nouvelle@test.tn').amount, '25.500');
  assert.equal(byEmail(rows, 'nouvelle@test.tn').paidAt, '2026-09-15');
  assert.equal(byEmail(rows, 'deja@test.tn').status, 'RENEWAL');
  assert.equal(byEmail(rows, 'attente@test.tn').status, 'AUTO_ACCEPT');
  const mismatch = byEmail(rows, 'autretel@test.tn');
  assert.equal(mismatch.status, 'NEW');
  assert.match(mismatch.note, /autre numéro/);
  assert.equal(rows.find((x) => x.status === 'DUPLICATE').line, 6);
  assert.equal(rows.find((x) => x.name === 'Mauvais Email').status, 'INVALID');
  assert.equal(rows.find((x) => x.name === 'Mauvais Montant').status, 'INVALID');
  assert.equal(r.data.summary.willImport, 4);

  const list = await admin.get('/api/admin/subscriptions');
  assert.equal(list.data.total, 0, 'a preview must not write anything');
  const reqs = await admin.get('/api/admin/membership-requests?status=PENDING');
  assert.ok(byEmail(reqs.data.items, 'attente@test.tn'), 'request still pending after preview');
});

test('committing the import records subscriptions and accepts matching pending requests', async () => {
  const buf = await xlsx([
    ['Nouvelle Personne', 'nouvelle@test.tn', '+216 21 000 001', '25,5 DT', '15/09/2026', 'R-001'],
    ['Déjà Membre', 'deja@test.tn', '20123456', 25, null, null],
    ['En Attente', 'attente@test.tn', '20111222', 25, null, null],
    ['Autre Tel', 'autretel@test.tn', '21555555', 25, null, null],
    ['Mauvais Email', 'pas-un-email', '21000002', 25, null, null],
  ]);
  const r = await upload(admin, buf, { dryRun: false });
  assert.equal(r.status, 201);
  assert.equal(r.data.summary.counts.AUTO_ACCEPT, 1);
  assert.equal(r.data.summary.counts.RENEWAL, 1);
  assert.equal(r.data.summary.counts.INVALID, 1);
  assert.ok(r.data.batchId);

  // The pending request was accepted by the system, not left waiting.
  const reqs = await admin.get('/api/admin/membership-requests?status=ACCEPTED');
  const accepted = byEmail(reqs.data.items, 'attente@test.tn');
  assert.ok(accepted);
  assert.equal(accepted.autoAccepted, true);
  const login = await new Client(srv.base).login('attente@test.tn', 'Membre2026');
  assert.equal(login.status, 200, 'the person can sign in right away');
  assert.equal(login.data.user.role, 'MEMBER');

  // Mismatching phone number: stays pending for a human.
  const stillPending = await admin.get('/api/admin/membership-requests?status=PENDING');
  const mm = byEmail(stillPending.data.items, 'autretel@test.tn');
  assert.ok(mm);
  assert.equal(mm.onPaidList, true);

  const claimed = await admin.get('/api/admin/subscriptions?status=CLAIMED');
  assert.deepEqual(claimed.data.items.map((s) => s.email).sort(), ['attente@test.tn', 'deja@test.tn']);
  const awaiting = await admin.get('/api/admin/subscriptions?status=AVAILABLE');
  assert.deepEqual(awaiting.data.items.map((s) => s.email).sort(), ['autretel@test.tn', 'nouvelle@test.tn']);

  // Importing the same file again adds nothing.
  const again = await upload(admin, buf, { dryRun: false });
  assert.equal(again.data.summary.willImport, 0);
  assert.equal(again.data.summary.counts.ALREADY_LISTED, 4);
});

test('someone on the paid list is accepted at registration; a wrong phone number is not', async () => {
  const ok = await register('nouvelle@test.tn', '+216 21 000 001', 'Nouvelle Personne');
  assert.equal(ok.status, 201);
  assert.equal(ok.data.status, 'ACCEPTED');
  assert.equal(ok.data.autoAccepted, true);
  assert.match(ok.data.message, /confirmée/);
  const login = await new Client(srv.base).login('nouvelle@test.tn', 'Membre2026');
  assert.equal(login.status, 200);

  await admin.post('/api/admin/imports', undefined); // no file: handled below
  const listed = await upload(admin, await xlsx([['Intrus Visé', 'victime@test.tn', '22000111', 25, null, null]]), { dryRun: false });
  assert.equal(listed.status, 201);
  const intruder = await register('victime@test.tn', '+216 99 888 777', 'Intrus');
  assert.equal(intruder.data.status, 'PENDING', 'knowing the email is not enough');
  const blocked = await new Client(srv.base).login('victime@test.tn', 'Membre2026');
  assert.equal(blocked.status, 403);

  // The member list shows the subscription of the season.
  const members = await admin.get('/api/admin/members?subscription=paid');
  assert.ok(members.data.items.every((m) => m.subscription.paid));
  assert.ok(byEmail(members.data.items, 'nouvelle@test.tn'));
  assert.equal(members.data.season, SEASON);
  const unpaid = await admin.get('/api/admin/members?subscription=unpaid');
  assert.ok(unpaid.data.items.every((m) => !m.subscription.paid));
});

test('a suspended account is never re-activated by the paid list', async () => {
  const m = await createMember(srv.base, admin, { name: 'Sanctionné', email: 'sanction@test.tn' });
  await admin.patch(`/api/admin/members/${m.user.id}/status`, { status: 'SUSPENDED' });
  const r = await upload(admin, await xlsx([['Sanctionné', 'sanction@test.tn', '22333444', 25, null, null]]));
  assert.equal(r.data.rows[0].status, 'BLOCKED');
  assert.equal(r.data.summary.willImport, 0);
});

test('reverting an import removes people who have not registered yet, keeps members', async () => {
  const buf = await xlsx([
    ['Annulée Un', 'annule1@test.tn', '23000001', 20, null, null],
    ['Annulée Deux', 'annule2@test.tn', '23000002', 20, null, null],
  ]);
  const done = await upload(admin, buf, { dryRun: false, filename: 'erreur.xlsx' });
  await register('annule2@test.tn', '23000002', 'Annulée Deux');
  const rev = await admin.del(`/api/admin/imports/${done.data.batchId}`);
  assert.equal(rev.status, 200);
  assert.equal(rev.data.revoked, 1);
  assert.equal(rev.data.kept, 1);
  const again = await admin.del(`/api/admin/imports/${done.data.batchId}`);
  assert.equal(again.status, 409);
  const gone = await admin.get('/api/admin/subscriptions?status=REVOKED');
  assert.deepEqual(gone.data.items.map((s) => s.email), ['annule1@test.tn']);
  const batches = await admin.get('/api/admin/imports');
  const b = batches.data.items.find((x) => x.id === done.data.batchId);
  assert.ok(b.revertedAt);
  // A revoked entry can be listed again in a later import.
  const relist = await upload(admin, await xlsx([['Annulée Un', 'annule1@test.tn', '23000001', 20, null, null]]));
  assert.equal(relist.data.rows[0].status, 'NEW');
});

test('uploads are validated by content, not by name', async () => {
  const notExcel = await upload(admin, Buffer.from('MZ\x90\x00 pretending to be a spreadsheet'), { filename: 'virus.xlsx' });
  assert.equal(notExcel.status, 422);
  assert.ok(notExcel.data.error.fields.file);

  const oldXls = await upload(admin, Buffer.from([0xd0, 0xcf, 0x11, 0xe0, 0xa1, 0xb1, 0x1a, 0xe1, 0, 0, 0, 0]), { filename: 'vieux.xls' });
  assert.equal(oldXls.status, 422);
  assert.match(oldXls.data.error.fields.file, /\.xlsx/);

  // A small ZIP that expands to 60 MB must be refused before it is decompressed.
  const bomb = Buffer.from(zipSync({ 'xl/worksheets/sheet1.xml': new Uint8Array(60 * 1024 * 1024) }));
  assert.ok(bomb.length < 2 * 1024 * 1024);
  const b = await upload(admin, bomb, { filename: 'bombe.xlsx' });
  assert.equal(b.status, 422);
  assert.match(b.data.error.fields.file, /volumineux/);

  const noEmailColumn = await upload(admin, await writeXlsx([['Nom', 'Ville'], ['A B', 'Tunis']]).toBuffer());
  assert.equal(noEmailColumn.status, 422);
  assert.match(noEmailColumn.data.error.fields.file, /Email/);

  const noPhone = await upload(admin, await writeXlsx([['Nom', 'Email'], ['Ali Ben', 'ali@test.tn']]).toBuffer());
  assert.match(noPhone.data.error.fields.file, /Téléphone/);

  const missing = await admin.req('POST', '/api/admin/imports', { form: new FormData() });
  assert.equal(missing.status, 422);

  const badSeason = await upload(admin, await xlsx([]), { season: '2026-2030' });
  assert.equal(badSeason.status, 422);
});

test('CSV exports from French Excel (semicolons, Windows-1252) are understood', async () => {
  const csv = 'Prénom;Nom;E-mail;Tel;Montant\r\nÉlise;Hammami;elise@test.tn;"+216 24 000 111";25,000\r\nMohamed;"Ben Ali";mohamed@test.tn;24000222;25\r\n';
  const bytes = Buffer.from(csv, 'latin1');
  const r = await upload(admin, bytes, { filename: 'liste.csv' });
  assert.equal(r.status, 200);
  assert.equal(r.data.rows.length, 2);
  assert.equal(r.data.rows[0].name, 'Élise Hammami');
  assert.equal(r.data.rows[0].amount, '25.000');
  assert.equal(r.data.rows[1].name, 'Mohamed Ben Ali');
  const utf8 = await upload(admin, Buffer.from(`﻿${csv}`, 'utf8'), { filename: 'liste.csv' });
  assert.equal(utf8.data.rows[0].name, 'Élise Hammami');
});

test('members cannot reach any import, export or subscription route', async () => {
  const m = await createMember(srv.base, admin, { name: 'Simple Membre', email: 'simple@test.tn' });
  const form = new FormData();
  form.append('file', new Blob([await xlsx([])]), 'x.xlsx');
  for (const [method, url, o] of [
    ['POST', '/api/admin/imports', { form }],
    ['GET', '/api/admin/imports'],
    ['GET', '/api/admin/subscriptions'],
    ['GET', '/api/admin/downloads/members'],
    ['GET', '/api/admin/downloads/template'],
    ['PUT', `/api/admin/members/${m.user.id}`, { body: { name: 'X Y', email: 'x@y.tn', phone: '20123456' } }],
  ]) {
    const r = await m.req(method, url, o);
    assert.equal(r.status, 403, `${method} ${url}`);
  }
  assert.equal((await new Client(srv.base).get('/api/admin/downloads/members')).status, 401);
});

test('downloads: template, members and subscriptions open as real Excel files', async () => {
  const tpl = await admin.get('/api/admin/downloads/template', { raw: true });
  assert.equal(tpl.status, 200);
  assert.match(tpl.headers.get('content-disposition'), /attachment/);
  const tplRows = await readSheet(Buffer.from(await tpl.arrayBuffer()));
  assert.deepEqual(tplRows[0].slice(0, 3), ['Nom complet', 'Email', 'Téléphone']);

  const res = await admin.get(`/api/admin/downloads/members?season=${SEASON}`, { raw: true });
  assert.equal(res.status, 200);
  const rows = await readSheet(Buffer.from(await res.arrayBuffer()));
  assert.equal(rows[0][7], `Cotisation ${SEASON}`);
  const row = rows.find((r) => r[1] === 'nouvelle@test.tn');
  assert.equal(row[7], 'Payée');
  const none = rows.find((r) => r[1] === 'simple@test.tn');
  assert.equal(none[7], 'Non payée');

  const subs = await admin.get(`/api/admin/downloads/subscriptions?season=${SEASON}`, { raw: true });
  const subRows = await readSheet(Buffer.from(await subs.arrayBuffer()));
  assert.ok(subRows.length > 3);
  assert.equal((await admin.get('/api/admin/downloads/passwords', { raw: true })).status, 404);
});

test('manual entry, member payment and dashboard figures', async () => {
  const m = await createMember(srv.base, admin, { name: 'Payeur Manuel', email: 'manuel@test.tn' });
  const detailBefore = await admin.get(`/api/admin/members/${m.user.id}`);
  assert.equal(detailBefore.data.subscription.paid, false);

  const pay = await admin.post(`/api/admin/members/${m.user.id}/subscriptions`, { season: SEASON, amount: '30', paidAt: '2026-10-01', reference: 'R-77' });
  assert.equal(pay.status, 201);
  assert.equal(pay.data.status, 'CLAIMED');
  assert.equal(pay.data.amount, '30.000');
  assert.equal((await admin.post(`/api/admin/members/${m.user.id}/subscriptions`, { season: SEASON })).status, 409);
  const detail = await admin.get(`/api/admin/members/${m.user.id}`);
  assert.equal(detail.data.subscription.paid, true);
  assert.equal(detail.data.subscriptions.length, 1);

  const add = await admin.post('/api/admin/subscriptions', { name: 'Ajout Manuel', email: 'ajout@test.tn', phone: '+216 25 111 000', season: SEASON, amount: '25' });
  assert.equal(add.status, 201);
  assert.equal(add.data.status, 'AVAILABLE');
  assert.equal((await admin.post('/api/admin/subscriptions', { name: 'Ajout Manuel', email: 'ajout@test.tn', phone: '25111000', season: SEASON })).status, 409);
  assert.equal((await admin.post('/api/admin/subscriptions', { name: 'X', email: 'bad', phone: '1', season: SEASON })).status, 422);
  assert.equal((await admin.del(`/api/admin/subscriptions/${add.data.id}`)).status, 200);
  assert.equal((await admin.del(`/api/admin/subscriptions/${add.data.id}`)).status, 409);
  const paidOne = await admin.del(`/api/admin/subscriptions/${pay.data.id}`);
  assert.equal(paidOne.status, 409, 'a claimed subscription cannot be removed from the list');

  const stats = await admin.get('/api/admin/stats');
  assert.equal(stats.data.subscriptions.season, SEASON);
  assert.ok(stats.data.subscriptions.paidMembers >= 2);
  assert.ok(stats.data.subscriptions.unpaidMembers >= 1);
});

test('administrators can correct a member’s details; the email stays unique', async () => {
  const a = await createMember(srv.base, admin, { name: 'Membre Alpha', email: 'alpha@test.tn' });
  await createMember(srv.base, admin, { name: 'Membre Beta', email: 'beta@test.tn' });
  const ok = await admin.put(`/api/admin/members/${a.user.id}`, { name: 'Membre Alpha Corrigé', email: 'Alpha.Nouveau@test.tn', phone: '+216 20 555 666', birthday: '2003-04-12', role: 'ADMIN', score: 999 });
  assert.equal(ok.status, 200);
  assert.equal(ok.data.email, 'alpha.nouveau@test.tn');
  assert.equal(ok.data.birthday, '2003-04-12');
  assert.equal(ok.data.score, 0, 'score cannot be edited');
  const login = await new Client(srv.base).login('alpha.nouveau@test.tn', 'Membre2026');
  assert.equal(login.data.user.role, 'MEMBER', 'role cannot be edited');
  const clash = await admin.put(`/api/admin/members/${a.user.id}`, { name: 'Membre Alpha', email: 'beta@test.tn', phone: '20555666' });
  assert.equal(clash.status, 422);
  assert.ok(clash.data.error.fields.email);
  assert.equal((await admin.put(`/api/admin/members/${a.user.id}`, { name: '', email: 'x', phone: '' })).status, 422);
});
