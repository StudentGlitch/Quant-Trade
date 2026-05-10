-- SQLite Schema (schema.sql)
CREATE TABLE IF NOT EXISTS bounties (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL, -- 'github' | 'upwork'
    url TEXT NOT NULL,
    description TEXT,
    reward_estimate REAL DEFAULT 0.0,
    status TEXT DEFAULT 'DISCOVERED', -- 'DISCOVERED', 'SOLVING', 'READY_FOR_VERIFICATION', 'VERIFYING', 'READY_FOR_SUBMISSION', 'SUBMITTED_UNVERIFIED', 'SUBMITTED', 'FAILED', 'BLOCKED'
    verification_score REAL DEFAULT 0.0, -- 0.0 to 1.0 based on rubric
    verification_notes TEXT,
    verification_hard_fail INTEGER DEFAULT 0,
    verification_reason TEXT,
    discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    submitted_at TIMESTAMP,
    confidence_level TEXT DEFAULT 'LOW', -- 'LOW', 'MEDIUM', 'HIGH'
    proof_link TEXT,
    proof_verified_at TIMESTAMP,
    resolution_level TEXT DEFAULT 'L1' -- L1 artifact, L2 quality-passed, L3 proof-linked
);

CREATE TABLE IF NOT EXISTS verification_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    bounty_id TEXT NOT NULL,
    score REAL DEFAULT 0.0,
    confidence_level TEXT DEFAULT 'LOW',
    hard_fail INTEGER DEFAULT 0,
    passed INTEGER DEFAULT 0,
    reasons TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(bounty_id) REFERENCES bounties(id)
);

CREATE TABLE IF NOT EXISTS agent_learning (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    iteration INTEGER NOT NULL,
    agent_name TEXT NOT NULL,
    lessons_learned TEXT,
    success_count INTEGER DEFAULT 0,
    failure_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS verifier_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    queue_size INTEGER DEFAULT 0,
    processed_count INTEGER DEFAULT 0,
    failed_count INTEGER DEFAULT 0,
    empty_run INTEGER DEFAULT 0,
    elapsed_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
