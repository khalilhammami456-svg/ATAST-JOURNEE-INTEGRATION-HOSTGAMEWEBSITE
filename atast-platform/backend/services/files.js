'use strict';
/** Image upload handling (chapter "File Upload Security"). */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const config = require('../config');
const { errors } = require('../utils');

/**
 * The real type is detected from the file's magic bytes — the browser-sent
 * MIME type and the original file name are never trusted.
 */
function detectImageType(buf) {
  if (!buf || buf.length < 12) return null;
  if (buf[0] === 0xff && buf[1] === 0xd8 && buf[2] === 0xff) return { ext: 'jpg', mime: 'image/jpeg' };
  if (buf.subarray(0, 8).equals(Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]))) {
    return { ext: 'png', mime: 'image/png' };
  }
  if (buf.subarray(0, 4).toString('ascii') === 'RIFF' && buf.subarray(8, 12).toString('ascii') === 'WEBP') {
    return { ext: 'webp', mime: 'image/webp' };
  }
  return null;
}

const ALLOWED_DECLARED = new Set(['image/jpeg', 'image/png', 'image/webp']);
const FILE_RE = /^[a-f0-9]{32}\.(jpg|png|webp)$/;

function saveImage(file) {
  if (!file) throw errors.validation({ file: 'Choisissez une image.' });
  if (!ALLOWED_DECLARED.has(file.mimetype)) {
    throw errors.validation({ file: 'Formats acceptés : JPEG, PNG ou WebP.' });
  }
  const type = detectImageType(file.buffer);
  if (!type) throw errors.validation({ file: "Ce fichier n'est pas une image JPEG, PNG ou WebP valide." });
  fs.mkdirSync(config.uploadDir, { recursive: true });
  // Server generated name; nothing from the original name is kept.
  const name = `${crypto.randomBytes(16).toString('hex')}.${type.ext}`;
  fs.writeFileSync(path.join(config.uploadDir, name), file.buffer, { flag: 'wx', mode: 0o640 });
  return name;
}

function removeImage(name) {
  if (!name || !FILE_RE.test(name)) return;
  fs.rm(path.join(config.uploadDir, name), { force: true }, () => {});
}

function publicUrl(name) {
  return name && FILE_RE.test(name) ? `/uploads/${name}` : null;
}

module.exports = { detectImageType, saveImage, removeImage, publicUrl, FILE_RE };
