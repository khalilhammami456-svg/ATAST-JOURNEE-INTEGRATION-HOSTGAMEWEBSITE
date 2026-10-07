'use strict';
/**
 * Spreadsheet I/O for the admin imports/exports: reads .xlsx and .csv uploads into a plain
 * array of rows, writes .xlsx downloads.
 *
 * Uploads are untrusted: the real type comes from the file's bytes (not its name), an .xlsx
 * is a ZIP so its central directory is inspected before anything is decompressed (zip bombs),
 * and nothing in a cell is ever interpreted as a formula.
 */
const config = require('../config');
const { errors } = require('../utils');

const MAX_ZIP_ENTRIES = 200;
const MAX_UNCOMPRESSED_BYTES = 40 * 1024 * 1024;

const bad = (message) => errors.validation({ file: message });

/** Reads the ZIP central directory and refuses archives that would expand too much. */
function inspectZip(buf) {
  const minEocd = 22;
  let eocd = -1;
  for (let i = buf.length - minEocd; i >= Math.max(0, buf.length - minEocd - 0xffff); i -= 1) {
    if (buf.readUInt32LE(i) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd === -1) throw bad("Ce fichier n'est pas un classeur Excel (.xlsx) valide.");
  const entries = buf.readUInt16LE(eocd + 10);
  let offset = buf.readUInt32LE(eocd + 16);
  if (entries > MAX_ZIP_ENTRIES || entries === 0xffff) throw bad('Ce classeur Excel contient trop de fichiers internes.');
  let total = 0;
  for (let n = 0; n < entries; n += 1) {
    if (offset + 46 > buf.length || buf.readUInt32LE(offset) !== 0x02014b50) throw bad("Ce fichier n'est pas un classeur Excel (.xlsx) valide.");
    const compressed = buf.readUInt32LE(offset + 20);
    const size = buf.readUInt32LE(offset + 24);
    if (size === 0xffffffff || compressed === 0xffffffff) throw bad('Ce classeur Excel est trop volumineux.');
    total += size;
    if (total > MAX_UNCOMPRESSED_BYTES) throw bad('Ce classeur Excel est trop volumineux une fois décompressé.');
    offset += 46 + buf.readUInt16LE(offset + 28) + buf.readUInt16LE(offset + 30) + buf.readUInt16LE(offset + 32);
  }
}

function sniff(buf, filename) {
  if (buf.length >= 4 && buf.readUInt32BE(0) === 0x504b0304) return 'xlsx';
  if (buf.length >= 4 && buf.readUInt32BE(0) === 0xd0cf11e0) {
    throw bad("Ancien format Excel (.xls) non pris en charge. Ouvrez le fichier dans Excel puis enregistrez-le au format .xlsx.");
  }
  if (/\.(csv|txt)$/i.test(filename || '') && !buf.includes(0)) return 'csv';
  throw bad('Format non reconnu. Importez un fichier Excel (.xlsx) ou CSV (.csv).');
}

// ---------------------------------------------------------------- CSV
function decodeCsv(buf) {
  try {
    return new TextDecoder('utf-8', { fatal: true }).decode(buf).replace(/^﻿/, '');
  } catch {
    // Excel (French locale) saves CSV as Windows-1252 unless asked for UTF-8.
    return new TextDecoder('windows-1252').decode(buf);
  }
}

function parseCsv(text) {
  const firstLine = text.split(/\r?\n/, 1)[0] || '';
  const count = (c) => firstLine.split(c).length - 1;
  const delimiter = [';', '\t', ','].sort((a, b) => count(b) - count(a))[0];
  const rows = [];
  let row = [];
  let cell = '';
  let quoted = false;
  for (let i = 0; i < text.length; i += 1) {
    const ch = text[i];
    if (quoted) {
      if (ch === '"') {
        if (text[i + 1] === '"') { cell += '"'; i += 1; } else quoted = false;
      } else cell += ch;
    } else if (ch === '"' && cell === '') quoted = true;
    else if (ch === delimiter) { row.push(cell); cell = ''; }
    else if (ch === '\n' || ch === '\r') {
      if (ch === '\r' && text[i + 1] === '\n') i += 1;
      row.push(cell);
      rows.push(row);
      row = [];
      cell = '';
      if (rows.length > config.importMaxRows + 20) throw bad(`Le fichier dépasse ${config.importMaxRows} lignes.`);
    } else cell += ch;
  }
  if (cell !== '' || row.length) { row.push(cell); rows.push(row); }
  return rows.map((r) => r.map((c) => (c === '' ? null : c)));
}

// ---------------------------------------------------------------- Reading
/** Returns the first sheet (or the CSV) as an array of rows of string/number/Date/boolean/null cells. */
async function readRows(buffer, filename) {
  if (!Buffer.isBuffer(buffer) || buffer.length === 0) throw bad('Le fichier est vide.');
  const kind = sniff(buffer, filename);
  let rows;
  if (kind === 'csv') {
    rows = parseCsv(decodeCsv(buffer));
  } else {
    inspectZip(buffer);
    const { readSheet, InvalidInputError, InvalidSpreadsheetError } = require('read-excel-file/node');
    try {
      rows = await readSheet(buffer);
    } catch (err) {
      if (err instanceof InvalidInputError || err instanceof InvalidSpreadsheetError) {
        throw bad("Ce fichier n'est pas un classeur Excel (.xlsx) lisible. Vérifiez qu'il n'est pas protégé par mot de passe ni corrompu.");
      }
      throw err;
    }
  }
  if (rows.length > config.importMaxRows + 20) throw bad(`Le fichier dépasse ${config.importMaxRows} lignes.`);
  return rows;
}

// ---------------------------------------------------------------- Writing
const HEADER = { fontWeight: 'bold', backgroundColor: '#E8F0FB', textColor: '#0B1F4B' };

/**
 * Builds an .xlsx file. `columns` = [{ title, width, format? }], `rows` = arrays of
 * string | number | Date | null values. Text stays text: Excel never evaluates it as a formula.
 */
async function writeWorkbook(sheetName, columns, rows) {
  const writeXlsxFile = require('write-excel-file/node').default;
  const data = [
    columns.map((c) => ({ value: c.title, ...HEADER })),
    ...rows.map((r) => r.map((v, i) => {
      if (v === null || v === undefined || v === '') return null;
      if (v instanceof Date) return { value: v, format: columns[i].format || 'yyyy-mm-dd' };
      if (typeof v === 'number' && columns[i].format) return { value: v, format: columns[i].format };
      return v;
    })),
  ];
  return writeXlsxFile(data, { sheet: sheetName, columns: columns.map((c) => ({ width: c.width || 18 })), stickyRowsCount: 1 }).toBuffer();
}

module.exports = { readRows, writeWorkbook, inspectZip };
