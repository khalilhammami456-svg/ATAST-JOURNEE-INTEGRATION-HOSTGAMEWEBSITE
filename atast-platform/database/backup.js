'use strict';
/**
 * Consistent backup of the SQLite database (members, subscriptions, events, points…), safe to run while
 * the site is online. Writes database/backups/atast-<date>.sqlite and keeps the newest BACKUP_KEEP copies.
 *
 *   npm run backup
 *   BACKUP_DIR=/mnt/usb BACKUP_KEEP=30 npm run backup
 *
 * Restore: stop the server, copy a backup over database/atast.sqlite (and delete atast.sqlite-wal / -shm), start again.
 * Uploaded photos live in uploads/ and must be copied separately.
 */
const fs = require('node:fs');
const path = require('node:path');
const config = require('../backend/config');
const { DatabaseSync } = require('node:sqlite');

const dir = path.resolve(process.env.BACKUP_DIR || path.join(path.dirname(config.databaseUrl), 'backups'));
const keep = Number.parseInt(process.env.BACKUP_KEEP || '14', 10);

if (config.databaseUrl === ':memory:' || !fs.existsSync(config.databaseUrl)) {
  console.error(`No database file at ${config.databaseUrl}: nothing to back up.`);
  process.exit(1);
}
fs.mkdirSync(dir, { recursive: true });
const stamp = new Date().toISOString().replace(/[:T]/g, '-').slice(0, 19);
const target = path.join(dir, `atast-${stamp}.sqlite`);

const db = new DatabaseSync(config.databaseUrl);
try {
  db.exec('PRAGMA busy_timeout = 5000;');
  db.exec(`VACUUM INTO '${target.replace(/'/g, "''")}'`); // consistent snapshot, includes the WAL
} finally {
  db.close();
}
const check = new DatabaseSync(target, { readOnly: true });
const members = check.prepare(`SELECT COUNT(*) AS n FROM users WHERE role = 'MEMBER'`).get().n;
check.close();

const old = fs.readdirSync(dir).filter((f) => /^atast-.*\.sqlite$/.test(f)).sort().reverse().slice(keep);
for (const f of old) fs.rmSync(path.join(dir, f));
console.log(`Backup written: ${target} (${members} members, ${fs.statSync(target).size} bytes)${old.length ? `, ${old.length} old backup(s) removed` : ''}`);
