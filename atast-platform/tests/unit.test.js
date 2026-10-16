'use strict';
/** Unit tests: points engine, validators, upload detection. */
const test = require('node:test');
const assert = require('node:assert/strict');

process.env.NODE_ENV = 'test';
const { pointsFor, computeScore, POINTS_BY_TYPE, pointsSql } = require('../backend/services/points');
const v = require('../backend/validators');
const { detectImageType } = require('../backend/services/files');

test('points: each event type awards exactly 10/20/30/0', () => {
  assert.deepEqual({ ...POINTS_BY_TYPE }, { SMALL: 10, MEDIUM: 20, BIG: 30, MEETING: 0 });
  assert.equal(pointsFor('SMALL'), 10);
  assert.equal(pointsFor('MEDIUM'), 20);
  assert.equal(pointsFor('BIG'), 30);
  assert.equal(pointsFor('MEETING'), 0);
  assert.throws(() => pointsFor('HUGE'));
});

test('points: SRS example 2x10 + 1x20 + 1x30 + 2x0 = 70', () => {
  assert.equal(computeScore(['SMALL', 'SMALL', 'MEDIUM', 'BIG', 'MEETING', 'MEETING']), 70);
  assert.equal(computeScore([]), 0);
});

test('points: SQL expression is generated from the same constants', () => {
  const sql = pointsSql('e.type');
  for (const [t, p] of Object.entries(POINTS_BY_TYPE)) assert.match(sql, new RegExp(`WHEN '${t}' THEN ${p}`));
});

const baseEvent = { title: 'Atelier', type: 'SMALL', date: '2026-11-02', time: '14:00', location: 'ISIMM', isFree: true };

test('event validation: free event price is normalised to 0', () => {
  const out = v.eventInput({ ...baseEvent, price: '25' });
  assert.equal(out.isFree, true);
  assert.equal(out.price, 0);
  assert.equal(out.status, 'DRAFT');
});

test('event validation: paid event requires a positive price, stored in minor units', () => {
  assert.throws(() => v.eventInput({ ...baseEvent, isFree: false }), (e) => !!e.fields.price);
  assert.throws(() => v.eventInput({ ...baseEvent, isFree: false, price: '0' }), (e) => !!e.fields.price);
  assert.throws(() => v.eventInput({ ...baseEvent, isFree: false, price: '-5' }), (e) => !!e.fields.price);
  assert.throws(() => v.eventInput({ ...baseEvent, isFree: false, price: 'abc' }), (e) => !!e.fields.price);
  assert.equal(v.eventInput({ ...baseEvent, isFree: false, price: '12,5' }).price, 12500);
  assert.equal(v.eventInput({ ...baseEvent, isFree: false, price: '15', currency: 'EUR' }).price, 1500);
});

test('event validation: type must belong to the enum; dates and times are real', () => {
  assert.throws(() => v.eventInput({ ...baseEvent, type: 'HUGE' }), (e) => !!e.fields.type);
  assert.throws(() => v.eventInput({ ...baseEvent, date: '2026-02-30' }), (e) => !!e.fields.date);
  assert.throws(() => v.eventInput({ ...baseEvent, time: '25:00' }), (e) => !!e.fields.time);
  assert.throws(() => v.eventInput({ ...baseEvent, isFree: undefined }), (e) => !!e.fields.isFree);
  // ARCHIVED is only reachable through edit/archive, not creation
  assert.throws(() => v.eventInput({ ...baseEvent, status: 'ARCHIVED' }), (e) => !!e.fields.status);
  assert.equal(v.eventInput({ ...baseEvent, status: 'ARCHIVED' }, { forUpdate: true }).status, 'ARCHIVED');
});

test('registration validation: confirmation, password policy, email, phone', () => {
  const ok = { name: 'Sarra Mejri', email: 'SARRA@Mail.tn ', phone: '+216 20 123 456', password: 'abcdef12', passwordConfirm: 'abcdef12' };
  const out = v.register(ok);
  assert.equal(out.email, 'sarra@mail.tn');
  assert.equal(out.phone, '+21620123456');
  assert.equal(out.role, undefined, 'unknown fields are dropped');
  assert.throws(() => v.register({ ...ok, passwordConfirm: 'other123' }), (e) => !!e.fields.passwordConfirm);
  assert.throws(() => v.register({ ...ok, password: 'short1', passwordConfirm: 'short1' }), (e) => !!e.fields.password);
  assert.throws(() => v.register({ ...ok, password: 'onlyletters', passwordConfirm: 'onlyletters' }), (e) => !!e.fields.password);
  assert.throws(() => v.register({ ...ok, email: 'not-an-email' }), (e) => !!e.fields.email);
  assert.throws(() => v.register({ ...ok, phone: '12' }), (e) => !!e.fields.phone);
  assert.throws(() => v.register({ ...ok, name: '<script>' }), (e) => !!e.fields.name);
});

test('profile validation: social links must point to the right network', () => {
  const base = { name: 'Ahmed', phone: '+21622000000' };
  assert.equal(v.profileUpdate({ ...base, github: 'github.com/ahmed' }).github, 'https://github.com/ahmed');
  assert.throws(() => v.profileUpdate({ ...base, github: 'https://evil.com/ahmed' }), (e) => !!e.fields.github);
  assert.throws(() => v.profileUpdate({ ...base, linkedin: 'javascript:alert(1)' }), (e) => !!e.fields.linkedin);
  assert.throws(() => v.profileUpdate({ ...base, instagram: 'https://instagram.com/' }), (e) => !!e.fields.instagram);
  assert.throws(() => v.profileUpdate({ ...base, birthday: '2999-01-01' }), (e) => !!e.fields.birthday);
  const out = v.profileUpdate({ ...base, score: 999, role: 'ADMIN' });
  assert.equal(out.score, undefined);
  assert.equal(out.role, undefined);
});

test('uploads: real type comes from magic bytes, not from the name', () => {
  const png = Buffer.from('89504e470d0a1a0a0000000d49484452', 'hex');
  const jpg = Buffer.from([0xff, 0xd8, 0xff, 0xe0, 0, 0, 0, 0, 0, 0, 0, 0]);
  const webp = Buffer.concat([Buffer.from('RIFF'), Buffer.alloc(4), Buffer.from('WEBP')]);
  assert.equal(detectImageType(png).ext, 'png');
  assert.equal(detectImageType(jpg).ext, 'jpg');
  assert.equal(detectImageType(webp).ext, 'webp');
  assert.equal(detectImageType(Buffer.from('<?php echo 1; ?>....')), null);
  assert.equal(detectImageType(Buffer.from('<svg onload=alert(1)>')), null);
});
