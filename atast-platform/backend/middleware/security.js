'use strict';
const multer = require('multer');
const rateLimit = require('express-rate-limit');
const config = require('../config');
const { AppError, errors } = require('../utils');

/** Uploads are kept in memory, validated (magic bytes) then written by the service. */
const imageUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: config.uploadMaxBytes, files: 1, fields: 5 },
}).single('file');

function upload(req, res, next) {
  imageUpload(req, res, (err) => {
    if (!err) return next();
    if (err.code === 'LIMIT_FILE_SIZE') {
      const mb = (config.uploadMaxBytes / (1024 * 1024)).toFixed(1).replace(/\.0$/, '');
      return next(errors.validation({ file: `L'image ne doit pas dépasser ${mb} Mo.` }));
    }
    return next(errors.validation({ file: "Le fichier n'a pas pu être lu. Choisissez une image JPEG, PNG ou WebP." }));
  });
}

/** Excel / CSV imports: in memory, one file, size and field count limited; parsed by the service. */
const sheetUpload = multer({
  storage: multer.memoryStorage(),
  limits: { fileSize: config.importMaxBytes, files: 1, fields: 6, fieldSize: 200 },
}).single('file');

function spreadsheetUpload(req, res, next) {
  sheetUpload(req, res, (err) => {
    if (!err) return next();
    if (err.code === 'LIMIT_FILE_SIZE') {
      const mb = (config.importMaxBytes / (1024 * 1024)).toFixed(1).replace(/\.0$/, '');
      return next(errors.validation({ file: `Le fichier ne doit pas dépasser ${mb} Mo.` }));
    }
    return next(errors.validation({ file: "Le fichier n'a pas pu être lu. Choisissez un fichier Excel (.xlsx) ou CSV." }));
  });
}

const tooMany = (message) => (_req, _res, next) => next(new AppError(429, 'RATE_LIMITED', message));

/** Brute-force protection on login (per IP + email). */
const loginLimiter = rateLimit({
  windowMs: config.loginWindowMinutes * 60 * 1000,
  limit: config.isTest ? 1000 : config.loginMaxAttempts,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  keyGenerator: (req) => `${req.ip}|${String(req.body?.email || '').toLowerCase().slice(0, 254)}`,
  handler: tooMany(`Trop de tentatives de connexion. Réessayez dans ${config.loginWindowMinutes} minutes.`),
  validate: { keyGeneratorIpFallback: false },
});

const registerLimiter = rateLimit({
  windowMs: 60 * 60 * 1000,
  limit: config.isTest ? 1000 : 5,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  handler: tooMany("Trop de demandes d'adhésion depuis cet appareil. Réessayez plus tard."),
});

/** Global safety net for the API. */
const apiLimiter = rateLimit({
  windowMs: 60 * 1000,
  limit: config.isTest ? 100000 : 300,
  standardHeaders: 'draft-7',
  legacyHeaders: false,
  handler: tooMany('Trop de requêtes. Patientez quelques instants.'),
});

module.exports = { upload, spreadsheetUpload, loginLimiter, registerLimiter, apiLimiter };
