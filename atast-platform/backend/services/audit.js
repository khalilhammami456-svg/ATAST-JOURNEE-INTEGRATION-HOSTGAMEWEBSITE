'use strict';
/** Audit log writer (chapter "Logging and Audit"). Never logs secrets. */
const repo = require('../repositories');
const { uuid, now } = require('../utils');

const FORBIDDEN_KEYS = /pass|hash|token|secret|csrf/i;

function clean(meta) {
  if (!meta) return null;
  const out = {};
  for (const [k, v] of Object.entries(meta)) if (!FORBIDDEN_KEYS.test(k)) out[k] = v;
  return JSON.stringify(out);
}

function log(actorId, action, entityType, entityId, metadata) {
  repo.audit.insert({
    id: uuid(), actorId, action, entityType, entityId: entityId ?? null, metadata: clean(metadata), createdAt: now(),
  });
}

module.exports = { log };
