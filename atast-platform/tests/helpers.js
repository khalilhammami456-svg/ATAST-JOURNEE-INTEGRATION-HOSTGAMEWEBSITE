'use strict';
/** Shared test harness: in-memory database, real HTTP server, cookie-aware client. */
const os = require('node:os');
const fs = require('node:fs');
const path = require('node:path');

process.env.NODE_ENV = 'test';
process.env.DATABASE_URL = ':memory:';
process.env.BCRYPT_ROUNDS = '4';
process.env.UPLOAD_DIR = fs.mkdtempSync(path.join(os.tmpdir(), 'atast-uploads-'));

const db = require('../backend/db/database');
const { createApp } = require('../backend/app');
const repo = require('../backend/repositories');
const { hashPassword } = require('../backend/services/auth');
const { uuid, now } = require('../backend/utils');

async function startServer() {
  db.open();
  const app = createApp();
  const server = await new Promise((resolve) => {
    const s = app.listen(0, () => resolve(s));
  });
  const base = `http://127.0.0.1:${server.address().port}`;
  return { base, close: () => new Promise((r) => { require('../backend/services/sync').closeAll(); server.close(() => { db.close(); r(); }); }) };
}

/** Minimal browser-like client: keeps the session cookie and CSRF token. */
class Client {
  constructor(base) {
    this.base = base;
    this.cookie = '';
    this.csrf = '';
  }
  async req(method, url, { body, form, headers = {}, raw = false } = {}) {
    const h = { 'X-Requested-With': 'fetch', ...headers };
    if (this.cookie) h.Cookie = this.cookie;
    if (method !== 'GET' && this.csrf && !('X-CSRF-Token' in headers)) h['X-CSRF-Token'] = this.csrf;
    let payload;
    if (form) payload = form;
    else if (body !== undefined) {
      h['Content-Type'] = 'application/json';
      payload = JSON.stringify(body);
    }
    for (const k of Object.keys(h)) if (h[k] === null) delete h[k];
    const res = await fetch(this.base + url, { method, headers: h, body: payload, redirect: 'manual' });
    const set = res.headers.get('set-cookie');
    if (set) {
      const m = /atast_sid=([^;]*)/.exec(set);
      if (m) this.cookie = m[1] ? `atast_sid=${m[1]}` : '';
    }
    if (raw) return res;
    const text = await res.text();
    let data = null;
    try { data = text ? JSON.parse(text) : null; } catch { data = text; }
    if (data && data.csrfToken) this.csrf = data.csrfToken;
    return { status: res.status, data };
  }
  get(url, o) { return this.req('GET', url, o); }
  post(url, body, o = {}) { return this.req('POST', url, { ...o, body }); }
  put(url, body, o = {}) { return this.req('PUT', url, { ...o, body }); }
  patch(url, body, o = {}) { return this.req('PATCH', url, { ...o, body }); }
  del(url, o) { return this.req('DELETE', url, o); }
  async login(email, password) {
    const r = await this.post('/api/auth/login', { email, password });
    return r;
  }
}

async function createAdmin(email = 'admin@test.tn', password = 'AdminPass1') {
  const at = now();
  repo.users.insert({
    id: uuid(), name: 'Admin Test', email, password_hash: await hashPassword(password), phone: '+21620000000',
    role: 'ADMIN', status: 'ACTIVE', created_at: at, updated_at: at,
  });
  return { email, password };
}

/** Registers someone and has the admin accept them; returns a logged-in client. */
async function createMember(base, admin, { name, email, password = 'Membre2026' }) {
  const anon = new Client(base);
  const reg = await anon.post('/api/auth/register', { name, email, phone: '+216 22 333 444', password, passwordConfirm: password });
  if (reg.status !== 201) throw new Error(`register failed ${JSON.stringify(reg.data)}`);
  const acc = await admin.post(`/api/admin/membership-requests/${reg.data.id}/accept`);
  if (acc.status !== 200) throw new Error(`accept failed ${JSON.stringify(acc.data)}`);
  const c = new Client(base);
  const login = await c.login(email, password);
  if (login.status !== 200) throw new Error('login failed');
  c.user = login.data.user;
  return c;
}

module.exports = { startServer, Client, createAdmin, createMember, uploadDir: process.env.UPLOAD_DIR };
