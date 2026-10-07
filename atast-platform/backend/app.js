'use strict';
const path = require('node:path');
const fs = require('node:fs');
const express = require('express');
const helmet = require('helmet');
const cookieParser = require('cookie-parser');
const config = require('./config');
const routes = require('./routes');
const { authenticate, csrf } = require('./middleware/auth');
const { apiLimiter } = require('./middleware/security');
const { notFound, errorHandler } = require('./middleware/errors');
const { FILE_RE } = require('./services/files');

/** Client-side routes from the SRS ("Frontend Pages") served by the SPA shell. */
const SPA_ROUTES = [
  /^\/$/, /^\/login$/, /^\/register$/, /^\/home$/, /^\/events(\/[0-9a-f-]{36})?$/, /^\/scoreboard$/,
  /^\/members(\/[0-9a-f-]{36})?$/, /^\/suggestions$/, /^\/profile$/,
  /^\/admin$/, /^\/admin\/members(\/[0-9a-f-]{36})?$/, /^\/admin\/requests$/, /^\/admin\/subscriptions$/,
  /^\/admin\/events(\/new|\/[0-9a-f-]{36}(\/edit)?)?$/, /^\/admin\/messages$/, /^\/admin\/suggestions$/,
];

function createApp() {
  const app = express();
  app.disable('x-powered-by');
  if (config.isProduction) app.set('trust proxy', 1);

  app.use(helmet({
    contentSecurityPolicy: {
      useDefaults: false,
      directives: {
        'default-src': ["'self'"],
        'script-src': ["'self'"],
        'style-src': ["'self'"],
        'img-src': ["'self'", 'data:', 'blob:'],
        'font-src': ["'self'"],
        'connect-src': ["'self'"],
        'object-src': ["'none'"],
        'base-uri': ["'self'"],
        'form-action': ["'self'"],
        'frame-ancestors': ["'none'"],
        ...(config.isProduction ? { 'upgrade-insecure-requests': [] } : {}),
      },
    },
    hsts: config.isProduction,
    crossOriginEmbedderPolicy: false,
  }));

  app.use(cookieParser());
  app.use(express.json({ limit: '100kb' }));

  // ---------------- API
  app.use('/api', apiLimiter, (_req, res, next) => {
    res.set('Cache-Control', 'no-store');
    next();
  }, authenticate, csrf, routes);
  app.use('/api', notFound);

  // ---------------- Uploaded images: members only, strict file names, never executed
  app.get('/uploads/:file', authenticate, (req, res, next) => {
    if (!req.user) return res.status(401).end();
    if (!FILE_RE.test(req.params.file)) return res.status(404).end();
    const full = path.join(config.uploadDir, req.params.file);
    if (!fs.existsSync(full)) return res.status(404).end();
    res.set({ 'Cache-Control': 'private, max-age=86400', 'X-Content-Type-Options': 'nosniff', 'Content-Disposition': 'inline' });
    res.sendFile(full, (err) => err && next(err));
  });

  // ---------------- Frontend
  app.use(express.static(config.frontendDir, {
    index: false,
    setHeaders(res, file) {
      res.set('Cache-Control', file.includes(`${path.sep}assets${path.sep}fonts`) ? 'public, max-age=31536000, immutable' : 'no-cache');
    },
  }));
  const shell = path.join(config.frontendDir, 'index.html');
  app.get(SPA_ROUTES, (_req, res) => {
    res.set('Cache-Control', 'no-cache');
    res.sendFile(shell);
  });
  app.use((req, res) => {
    res.status(404);
    if (req.accepts('html')) return res.sendFile(shell);
    res.end();
  });

  app.use(errorHandler);
  return app;
}

module.exports = { createApp };
