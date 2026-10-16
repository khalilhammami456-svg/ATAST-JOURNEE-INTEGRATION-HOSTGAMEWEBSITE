'use strict';
const config = require('../config');
const { AppError } = require('../utils');

function notFound(_req, _res, next) {
  next(new AppError(404, 'NOT_FOUND', 'Cette adresse ne correspond à aucune ressource.'));
}

/** Uniform JSON errors; internal details are never sent to the client. */
// eslint-disable-next-line no-unused-vars
function errorHandler(err, req, res, _next) {
  if (err instanceof AppError) {
    return res.status(err.status).json({ error: { code: err.code, message: err.message, fields: err.fields } });
  }
  if (err.type === 'entity.parse.failed') {
    return res.status(400).json({ error: { code: 'BAD_JSON', message: 'Requête mal formée.' } });
  }
  if (err.type === 'entity.too.large') {
    return res.status(413).json({ error: { code: 'TOO_LARGE', message: 'Requête trop volumineuse.' } });
  }
  if (err.code === 'ERR_SQLITE_ERROR' && /UNIQUE/.test(err.message)) {
    return res.status(409).json({ error: { code: 'CONFLICT', message: 'Cette opération crée un doublon.' } });
  }
  if (!config.isTest) console.error(`[${new Date().toISOString()}] ${req.method} ${req.originalUrl}`, err);
  return res.status(500).json({ error: { code: 'SERVER_ERROR', message: 'Le serveur a rencontré un problème. Réessayez plus tard.' } });
}

module.exports = { notFound, errorHandler };
