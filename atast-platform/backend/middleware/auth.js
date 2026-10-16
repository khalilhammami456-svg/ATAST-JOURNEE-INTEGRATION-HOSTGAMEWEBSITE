'use strict';
/**
 * authenticate() -> identify user ; authorize(ADMIN) -> verify role ;
 * then the controller runs the business logic (chapter "Authorization").
 */
const crypto = require('node:crypto');
const config = require('../config');
const authService = require('../services/auth');
const { errors } = require('../utils');

/** Attaches req.user / req.session when a valid session cookie is present. */
function authenticate(req, _res, next) {
  const resolved = authService.resolveSession(req.cookies?.[config.sessionCookieName]);
  if (resolved) {
    req.user = resolved.user;
    req.authSession = resolved.session;
  }
  next();
}

function requireAuth(req, _res, next) {
  if (!req.user) return next(errors.unauthenticated());
  next();
}

/** RBAC guard. A MEMBER calling an ADMIN route receives HTTP 403. */
function authorize(...roles) {
  return (req, _res, next) => {
    if (!req.user) return next(errors.unauthenticated());
    if (!roles.includes(req.user.role)) return next(errors.forbidden());
    next();
  };
}

const SAFE = new Set(['GET', 'HEAD', 'OPTIONS']);

/**
 * CSRF protection for state-changing requests:
 *  1. a custom header is mandatory (cross-site forms cannot set it, and no CORS is enabled);
 *  2. if an Origin header is sent it must be our own origin;
 *  3. authenticated requests must echo the per-session CSRF token.
 */
function csrf(req, _res, next) {
  if (SAFE.has(req.method)) return next();
  if (req.get('X-Requested-With') !== 'fetch') return next(errors.forbidden());
  const origin = req.get('Origin');
  if (origin) {
    const host = req.get('Host');
    let ok = false;
    try {
      ok = new URL(origin).host === host;
    } catch {
      ok = false;
    }
    if (!ok) return next(errors.forbidden());
  }
  if (req.authSession) {
    const sent = Buffer.from(String(req.get('X-CSRF-Token') || ''));
    const expected = Buffer.from(req.authSession.csrf);
    if (sent.length !== expected.length || !crypto.timingSafeEqual(sent, expected)) {
      return next(errors.forbidden());
    }
  }
  next();
}

function setSessionCookie(res, session) {
  res.cookie(config.sessionCookieName, session.token, {
    httpOnly: true,
    secure: config.isProduction,
    sameSite: 'lax',
    path: '/',
    expires: new Date(session.expiresAt),
  });
}

function clearSessionCookie(res) {
  res.clearCookie(config.sessionCookieName, { httpOnly: true, secure: config.isProduction, sameSite: 'lax', path: '/' });
}

module.exports = { authenticate, requireAuth, authorize, csrf, setSessionCookie, clearSessionCookie };
