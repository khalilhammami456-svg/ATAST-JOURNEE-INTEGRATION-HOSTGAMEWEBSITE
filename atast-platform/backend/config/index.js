'use strict';
/**
 * Central configuration. Every value can be overridden with an environment
 * variable (see .env.example). No secret is ever hard-coded for production.
 */
const path = require('node:path');

const ROOT = path.resolve(__dirname, '..', '..');

function int(name, fallback) {
  const raw = process.env[name];
  if (raw === undefined || raw === '') return fallback;
  const n = Number.parseInt(raw, 10);
  if (!Number.isFinite(n) || n <= 0) throw new Error(`Invalid numeric env var ${name}`);
  return n;
}

const env = process.env.NODE_ENV || 'development';

const config = {
  env,
  isProduction: env === 'production',
  isTest: env === 'test',
  port: int('PORT', 3000),
  appUrl: process.env.APP_URL || 'http://localhost:3000',

  // Database (DATABASE_URL accepts a file path, or ":memory:" for tests)
  databaseUrl: process.env.DATABASE_URL || path.join(ROOT, 'database', 'atast.sqlite'),
  migrationsDir: path.join(ROOT, 'database', 'migrations'),

  // Sessions
  sessionCookieName: 'atast_sid',
  sessionTtlHours: int('SESSION_TTL_HOURS', 24 * 7),

  // Password hashing (bcrypt cost factor)
  bcryptRounds: int('BCRYPT_ROUNDS', 12),

  // Uploads (FR-23 / File Upload Security): size limit is configurable
  uploadDir: process.env.UPLOAD_DIR || path.join(ROOT, 'uploads'),
  uploadMaxBytes: int('UPLOAD_MAX_BYTES', 2 * 1024 * 1024),

  // Excel / CSV imports of paid subscriptions
  importMaxBytes: int('IMPORT_MAX_BYTES', 2 * 1024 * 1024),
  importMaxRows: int('IMPORT_MAX_ROWS', 2000),
  // Automatic acceptance needs the phone number of the registration to match the paid list too,
  // so that knowing someone's email address is not enough to take their place.
  autoAcceptRequirePhone: process.env.AUTO_ACCEPT_REQUIRE_PHONE !== 'false',

  // Rate limiting for login / registration (brute force protection)
  loginWindowMinutes: int('LOGIN_WINDOW_MINUTES', 15),
  loginMaxAttempts: int('LOGIN_MAX_ATTEMPTS', 10),

  frontendDir: path.join(ROOT, 'frontend'),
  timezone: process.env.CLUB_TIMEZONE || 'Africa/Tunis',
  defaultCurrency: 'TND',
  supportedCurrencies: ['TND', 'EUR', 'USD'],
};

if (config.isProduction && !process.env.APP_URL) {
  // HTTPS is mandatory in production: fail loudly rather than run misconfigured.
  throw new Error('APP_URL must be set (https://...) in production');
}

module.exports = config;
