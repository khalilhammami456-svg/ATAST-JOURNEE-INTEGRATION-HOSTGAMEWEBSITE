'use strict';
/**
 * Data access bootstrap. Uses Node's built-in SQLite driver (no native build
 * step). All queries go through prepared statements => parameterised SQL,
 * no string concatenation of user input (protection against SQL injection).
 */
const fs = require('node:fs');
const path = require('node:path');

// node:sqlite prints an ExperimentalWarning on load; silence only that one.
const originalEmit = process.emitWarning;
process.emitWarning = function (warning, ...args) {
  const msg = typeof warning === 'string' ? warning : warning && warning.message;
  if (msg && msg.includes('SQLite')) return;
  return originalEmit.call(process, warning, ...args);
};
const { DatabaseSync } = require('node:sqlite');
process.emitWarning = originalEmit;

const config = require('../config');

let db = null;

function open(url = config.databaseUrl) {
  if (db) return db;
  if (url !== ':memory:') fs.mkdirSync(path.dirname(url), { recursive: true });
  db = new DatabaseSync(url);
  db.exec('PRAGMA foreign_keys = ON;');
  if (url !== ':memory:') db.exec('PRAGMA journal_mode = WAL;');
  db.exec('PRAGMA busy_timeout = 5000;');
  migrate(db);
  return db;
}

function migrate(conn) {
  conn.exec(`CREATE TABLE IF NOT EXISTS schema_migrations (
    name TEXT PRIMARY KEY, applied_at TEXT NOT NULL)`);
  const applied = new Set(conn.prepare('SELECT name FROM schema_migrations').all().map((r) => r.name));
  const files = fs.readdirSync(config.migrationsDir).filter((f) => f.endsWith('.sql')).sort();
  for (const file of files) {
    if (applied.has(file)) continue;
    const sql = fs.readFileSync(path.join(config.migrationsDir, file), 'utf8');
    transaction(() => {
      conn.exec(sql);
      conn.prepare('INSERT INTO schema_migrations (name, applied_at) VALUES (?, ?)')
        .run(file, new Date().toISOString());
    }, conn);
  }
}

function get() {
  if (!db) throw new Error('Database not opened');
  return db;
}

let depth = 0;
let pending = [];

/**
 * Runs fn after the outermost transaction commits (immediately when no
 * transaction is open). Callbacks are dropped if the transaction rolls back,
 * so nothing is announced for a change that did not happen.
 */
function afterCommit(fn) {
  if (depth === 0) fn();
  else pending.push(fn);
}

function flushPending() {
  const list = pending;
  pending = [];
  for (const fn of list) {
    try {
      fn();
    } catch (err) {
      console.error('afterCommit callback failed', err);
    }
  }
}

/** Runs fn inside a transaction (nested calls use savepoints). */
function transaction(fn, conn = get()) {
  const sp = `sp_${depth}`;
  conn.exec(depth === 0 ? 'BEGIN IMMEDIATE' : `SAVEPOINT ${sp}`);
  depth += 1;
  try {
    const result = fn();
    depth -= 1;
    conn.exec(depth === 0 ? 'COMMIT' : `RELEASE ${sp}`);
    if (depth === 0) flushPending();
    return result;
  } catch (err) {
    depth -= 1;
    conn.exec(depth === 0 ? 'ROLLBACK' : `ROLLBACK TO ${sp}`);
    if (depth === 0) pending = [];
    throw err;
  }
}

function close() {
  if (db) db.close();
  db = null;
}

module.exports = { open, get, transaction, afterCommit, close };
