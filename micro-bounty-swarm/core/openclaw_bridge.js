/**
 * OpenClaw Bridge (openclaw_bridge.js)
 * 
 * Provides an integration layer for OpenClaw to interact with the Python-based
 * Micro-Bounty Swarm SQLite state, allowing OpenClaw to read bounties and potentially
 * orchestrate human-in-the-loop approvals via messaging channels (e.g. WhatsApp, Discord).
 */

const sqlite3 = require('sqlite3').verbose();
const path = require('path');

const dbPath = path.resolve(__dirname, '../db/swarm_state.db');

class OpenClawBridge {
  constructor() {
    this.db = new sqlite3.Database(dbPath, (err) => {
      if (err) {
        console.error('Failed to connect to Swarm State DB:', err.message);
      } else {
        console.log('Connected to Swarm State DB.');
      }
    });
  }

  /**
   * Fetch bounties by status for OpenClaw to process or notify about.
   */
  getBountiesByStatus(status) {
    return new Promise((resolve, reject) => {
      this.db.all('SELECT * FROM bounties WHERE status = ?', [status], (err, rows) => {
        if (err) {
          reject(err);
        } else {
          resolve(rows);
        }
      });
    });
  }

  /**
   * Close the database connection.
   */
  close() {
    this.db.close((err) => {
      if (err) {
        console.error('Error closing DB:', err.message);
      }
    });
  }
}

module.exports = OpenClawBridge;

// Example Usage for CLI testing
if (require.main === module) {
  const bridge = new OpenClawBridge();
  bridge.getBountiesByStatus('SUBMITTED').then(rows => {
    console.log('Submitted Bounties:', rows);
    bridge.close();
  });
}
