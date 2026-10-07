'use strict';
/** Authentication: registration requests, login, sessions, password change. */
const crypto = require('node:crypto');
const bcrypt = require('bcryptjs');
const config = require('../config');
const repo = require('../repositories');
const { transaction } = require('../db/database');
const { AppError, errors, uuid, now } = require('../utils');
const dto = require('./dto');
const sync = require('./sync');
const roster = require('./roster');

const hashToken = (t) => crypto.createHash('sha256').update(t).digest('hex');
// Used to keep response time constant when the email is unknown.
let dummyHash = null;
const getDummy = async () => (dummyHash ??= await bcrypt.hash('atast-timing-guard', config.bcryptRounds));

const hashPassword = (pw) => bcrypt.hash(pw, config.bcryptRounds);

/**
 * FR-01: creates a membership request. It stays PENDING for an administrator to review, unless the
 * person is on the imported paid list (same email and phone): then it is accepted immediately.
 */
async function register(input) {
  const passwordHash = await hashPassword(input.password);
  return transaction(() => {
    if (repo.users.findActiveByEmail(input.email)) {
      throw errors.conflict('Un compte actif existe déjà avec cette adresse email. Connectez-vous.', 'EMAIL_TAKEN');
    }
    if (repo.requests.findPendingByEmail(input.email)) {
      throw errors.conflict("Une demande d'adhésion est déjà en attente pour cette adresse email.", 'REQUEST_PENDING');
    }
    const id = uuid();
    const request = {
      id, name: input.name, email: input.email, phone: input.phone, password_hash: passwordHash, created_at: now(),
    };
    repo.requests.insert(request);
    if (roster.tryAutoAccept(request)) return { id, status: 'ACCEPTED', autoAccepted: true };
    sync.publish('admins', ['requests', 'stats']);
    return { id, status: 'PENDING' };
  });
}

function createSession(userId) {
  const token = crypto.randomBytes(32).toString('base64url');
  const csrf = crypto.randomBytes(24).toString('base64url');
  const createdAt = now();
  const expiresAt = new Date(Date.now() + config.sessionTtlHours * 3600 * 1000).toISOString();
  repo.sessions.purgeExpired(createdAt);
  repo.sessions.insert({ idHash: hashToken(token), userId, csrf, createdAt, expiresAt });
  return { token, csrf, expiresAt };
}

async function login({ email, password }) {
  const user = repo.users.findActiveByEmail(email);
  if (user) {
    if (await bcrypt.compare(password, user.password_hash)) {
      const session = createSession(user.id);
      return { user: dto.sessionUser(user), session };
    }
    throw invalidCredentials();
  }
  // No active account: give a helpful status only to someone who knows the password.
  const pending = repo.requests.findPendingByEmail(email);
  if (pending?.password_hash && (await bcrypt.compare(password, pending.password_hash))) {
    throw new AppError(403, 'REQUEST_PENDING',
      "Votre demande d'adhésion est en cours d'examen. Vous pourrez vous connecter dès qu'elle sera acceptée.");
  }
  const inactive = repo.users.findAnyByEmail(email);
  if (inactive && inactive.status !== 'ACTIVE' && (await bcrypt.compare(password, inactive.password_hash))) {
    throw new AppError(403, 'ACCOUNT_INACTIVE',
      "Votre compte n'est plus actif. Contactez l'administration du club.");
  }
  const rejected = repo.requests.findLatestRejectedByEmail(email);
  if (rejected?.password_hash && (await bcrypt.compare(password, rejected.password_hash))) {
    const err = new AppError(403, 'REQUEST_REJECTED',
      `Votre demande d'adhésion a été refusée. Motif : ${rejected.rejection_reason}`);
    throw err;
  }
  await bcrypt.compare(password, await getDummy());
  throw invalidCredentials();
}

function invalidCredentials() {
  return new AppError(401, 'INVALID_CREDENTIALS', 'Email ou mot de passe incorrect.');
}

/** Resolves a cookie token into { user, session } or null. */
function resolveSession(token) {
  if (!token || typeof token !== 'string' || token.length > 100) return null;
  const idHash = hashToken(token);
  const s = repo.sessions.find(idHash);
  if (!s) return null;
  if (s.expires_at < now()) {
    repo.sessions.delete(idHash);
    return null;
  }
  const user = repo.users.findById(s.user_id);
  if (!user || user.status !== 'ACTIVE') {
    repo.sessions.delete(idHash);
    return null;
  }
  return { user, session: { idHash, csrf: s.csrf_token, expiresAt: s.expires_at } };
}

function logout(idHash) {
  if (!idHash) return;
  repo.sessions.delete(idHash);
  // Other tabs sharing this session are told to return to the sign-in page.
  sync.revoke({ sessionHash: idHash, reason: 'LOGOUT' });
}

/** FR-21: password change is a separate, secured procedure. */
async function changePassword(user, sessionHash, { currentPassword, newPassword }) {
  if (!(await bcrypt.compare(currentPassword, user.password_hash))) {
    throw errors.validation({ currentPassword: 'Le mot de passe actuel est incorrect.' });
  }
  const hash = await hashPassword(newPassword);
  transaction(() => {
    repo.users.setPassword(user.id, hash, now());
    // Sign out every other device.
    repo.sessions.deleteForUser(user.id, sessionHash);
    sync.revoke({ userId: user.id, exceptSession: sessionHash, reason: 'PASSWORD_CHANGED' });
  });
}

module.exports = { register, login, logout, resolveSession, changePassword, hashPassword, hashToken };
