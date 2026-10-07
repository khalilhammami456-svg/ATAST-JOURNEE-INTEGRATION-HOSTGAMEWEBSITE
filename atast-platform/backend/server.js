'use strict';
const config = require('./config');
const db = require('./db/database');
const { createApp } = require('./app');
const sync = require('./services/sync');

db.open();
const app = createApp();
const server = app.listen(config.port, () => {
  console.log(`ATAST running on ${config.appUrl} (port ${config.port}, ${config.env})`);
});

function shutdown() {
  sync.closeAll(); // open streams would otherwise keep the server alive
  server.close(() => {
    db.close();
    process.exit(0);
  });
}
process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
