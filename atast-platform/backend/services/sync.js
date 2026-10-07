'use strict';
/**
 * Real-time synchronisation between devices (Server-Sent Events).
 *
 * Every open device keeps one /api/sync stream. When data changes, the server
 * sends a small "change" notice naming the topics that changed (never the data
 * itself); each device then re-reads what it displays through the normal,
 * permission-checked API. Private data therefore never travels on the stream.
 *
 * Audiences: a single user (all of their devices), admins only, or everyone.
 * Notices are only sent after the database transaction has committed.
 */
const crypto = require('node:crypto');
const { afterCommit } = require('../db/database');

const HEARTBEAT_MS = 25000;
const MAX_STREAMS_PER_USER = 12;

/** @type {Map<string, {res: import('express').Response, userId: string, role: string, sessionHash: string, heartbeat: NodeJS.Timeout}>} */
const clients = new Map();
let seq = 0;

function write(client, event, data) {
  try {
    client.res.write(`id: ${++seq}\nevent: ${event}\ndata: ${JSON.stringify(data)}\n\n`);
  } catch {
    drop(client.id);
  }
}

function drop(id) {
  const c = clients.get(id);
  if (!c) return;
  clearInterval(c.heartbeat);
  clients.delete(id);
  try {
    c.res.end();
  } catch {
    /* already closed */
  }
}

/** Opens a stream for an authenticated request. */
function connect(req, res) {
  const user = req.user;
  const mine = [...clients.values()].filter((c) => c.userId === user.id);
  if (mine.length >= MAX_STREAMS_PER_USER) drop(mine[0].id); // oldest device tab gives way

  res.status(200).set({
    'Content-Type': 'text/event-stream; charset=utf-8',
    'Cache-Control': 'no-store, no-transform',
    Connection: 'keep-alive',
    'X-Accel-Buffering': 'no', // let Nginx stream instead of buffering
  });
  res.flushHeaders?.();
  req.socket.setTimeout?.(0);
  req.socket.setNoDelay?.(true);

  const id = crypto.randomUUID();
  const client = {
    id, res, userId: user.id, role: user.role, sessionHash: req.authSession.idHash,
    heartbeat: setInterval(() => {
      try {
        res.write(': ping\n\n');
      } catch {
        drop(id);
      }
    }, HEARTBEAT_MS),
  };
  clients.set(id, client);
  res.write('retry: 3000\n\n');
  write(client, 'ready', { at: new Date().toISOString() });
  req.on('close', () => drop(id));
}

function audienceMatches(client, audience) {
  if (audience === 'all') return true;
  if (audience === 'admins') return client.role === 'ADMIN';
  if (audience === 'members') return client.role === 'MEMBER';
  if (audience && typeof audience === 'object' && audience.userId) return client.userId === audience.userId;
  return false;
}

/**
 * Announces a change. `topics` are UI areas to refresh, e.g. ['events', 'scoreboard'].
 * `notice` is an optional short sentence shown to the recipient (only use it for
 * single-user audiences or for information everyone may see).
 */
function publish(audience, topics, extra = {}) {
  const payload = { topics, ...extra };
  afterCommit(() => {
    for (const c of clients.values()) {
      if (!audienceMatches(c, audience)) continue;
      if (extra.exceptSession && c.sessionHash === extra.exceptSession) continue;
      const { exceptSession, ...body } = payload;
      write(c, 'change', body);
    }
  });
}

/**
 * Ends live streams of a user's sessions after a revocation (password change,
 * suspension). The devices are told why, then the stream is closed.
 */
function revoke({ userId, exceptSession = null, sessionHash = null, reason }) {
  afterCommit(() => {
    for (const c of [...clients.values()]) {
      const match = sessionHash ? c.sessionHash === sessionHash : c.userId === userId && c.sessionHash !== exceptSession;
      if (!match) continue;
      write(c, 'session', { revoked: true, reason });
      drop(c.id);
    }
  });
}

function stats() {
  return { streams: clients.size, users: new Set([...clients.values()].map((c) => c.userId)).size };
}

function closeAll() {
  for (const id of [...clients.keys()]) drop(id);
}

module.exports = { connect, publish, revoke, stats, closeAll };
