'use strict';
/** Shared helpers: typed HTTP errors, ids, time, pagination. */
const crypto = require('node:crypto');

class AppError extends Error {
  /**
   * @param {number} status HTTP status
   * @param {string} code machine readable code used by the frontend
   * @param {string} message human readable (French) message, never sensitive
   * @param {object} [fields] per-field validation messages
   */
  constructor(status, code, message, fields) {
    super(message);
    this.status = status;
    this.code = code;
    if (fields) this.fields = fields;
  }
}

const errors = {
  validation: (fields, message = 'Certains champs sont invalides.') =>
    new AppError(422, 'VALIDATION_ERROR', message, fields),
  unauthenticated: () => new AppError(401, 'UNAUTHENTICATED', 'Votre session a expiré. Reconnectez-vous.'),
  forbidden: () => new AppError(403, 'FORBIDDEN', "Vous n'avez pas l'autorisation d'effectuer cette action."),
  notFound: (what = 'Ressource') => new AppError(404, 'NOT_FOUND', `${what} introuvable.`),
  conflict: (message, code = 'CONFLICT') => new AppError(409, code, message),
  badRequest: (message, code = 'BAD_REQUEST') => new AppError(400, code, message),
};

const uuid = () => crypto.randomUUID();
const now = () => new Date().toISOString();

/** Parses ?page & ?pageSize safely (server-side pagination, NFR-02). */
function pagination(query, { defaultSize = 20, maxSize = 100 } = {}) {
  let page = Number.parseInt(query.page, 10);
  let pageSize = Number.parseInt(query.pageSize, 10);
  if (!Number.isFinite(page) || page < 1) page = 1;
  if (!Number.isFinite(pageSize) || pageSize < 1) pageSize = defaultSize;
  pageSize = Math.min(pageSize, maxSize);
  return { page, pageSize, offset: (page - 1) * pageSize };
}

function paged(items, total, { page, pageSize }) {
  return { items, total, page, pageSize, totalPages: Math.max(1, Math.ceil(total / pageSize)) };
}

/** Escapes LIKE wildcards in a user search term. */
function likeTerm(q) {
  return `%${String(q).replace(/[\\%_]/g, (m) => `\\${m}`)}%`;
}

module.exports = { AppError, errors, uuid, now, pagination, paged, likeTerm };
