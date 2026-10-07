'use strict';
/**
 * Creates (or re-activates) an administrator account.
 * Admins can only be created from the server's command line — never from the
 * public website (business rule: no visitor can grant themselves ADMIN).
 *
 *   ADMIN_NAME="Nom" ADMIN_EMAIL=admin@exemple.tn ADMIN_PHONE=+21620000000 \
 *   ADMIN_PASSWORD='un-mot-de-passe-solide1' npm run create-admin
 */
const db = require('../../backend/db/database');
const v = require('../../backend/validators');
const repo = require('../../backend/repositories');
const { hashPassword } = require('../../backend/services/auth');
const { uuid, now } = require('../../backend/utils');

async function main() {
  const input = {
    name: process.env.ADMIN_NAME,
    email: process.env.ADMIN_EMAIL,
    phone: process.env.ADMIN_PHONE,
    password: process.env.ADMIN_PASSWORD,
    passwordConfirm: process.env.ADMIN_PASSWORD,
  };
  let clean;
  try {
    clean = v.register(input);
  } catch (err) {
    console.error('Invalid admin data:', err.fields || err.message);
    console.error('Set ADMIN_NAME, ADMIN_EMAIL, ADMIN_PHONE and ADMIN_PASSWORD (8+ chars, letters and digits).');
    process.exit(1);
  }
  db.open();
  if (repo.users.findActiveByEmail(clean.email)) {
    console.error(`An active account already uses ${clean.email}.`);
    process.exit(1);
  }
  const at = now();
  repo.users.insert({
    id: uuid(), name: clean.name, email: clean.email, password_hash: await hashPassword(clean.password),
    phone: clean.phone, role: 'ADMIN', status: 'ACTIVE', created_at: at, updated_at: at,
  });
  console.log(`Administrator ${clean.email} created.`);
  db.close();
}

main();
