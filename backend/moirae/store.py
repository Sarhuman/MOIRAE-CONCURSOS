"""Persistência SQLite para piloto de instância única; sem estado em memória."""
import sqlite3
from contextlib import contextmanager
from pathlib import Path

SCHEMA = '''
CREATE TABLE IF NOT EXISTS schema_version(version INTEGER PRIMARY KEY);
INSERT OR IGNORE INTO schema_version VALUES(1);
CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY,email TEXT UNIQUE NOT NULL,password_hash TEXT NOT NULL,created_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS auth_sessions(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),csrf TEXT NOT NULL,expires_at INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS rate_limits(bucket TEXT NOT NULL,window INTEGER NOT NULL,count INTEGER NOT NULL,PRIMARY KEY(bucket,window));
CREATE TABLE IF NOT EXISTS practice_sessions(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),status TEXT NOT NULL CHECK(status IN ('active','completed')),created_at INTEGER NOT NULL);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_session ON practice_sessions(user_id) WHERE status='active';
CREATE TABLE IF NOT EXISTS session_questions(session_id TEXT NOT NULL REFERENCES practice_sessions(id),position INTEGER NOT NULL,question_id TEXT NOT NULL,PRIMARY KEY(session_id,position),UNIQUE(session_id,question_id));
CREATE TABLE IF NOT EXISTS attempts(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),session_id TEXT NOT NULL REFERENCES practice_sessions(id),question_id TEXT NOT NULL,choice TEXT NOT NULL,correct INTEGER NOT NULL,day TEXT NOT NULL,created_at INTEGER NOT NULL,UNIQUE(session_id,question_id));
CREATE INDEX IF NOT EXISTS daily_attempts ON attempts(user_id,day);
CREATE TABLE IF NOT EXISTS mock_exams(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),day INTEGER NOT NULL CHECK(day IN (1,2)),
 started_at INTEGER NOT NULL,deadline INTEGER NOT NULL,status TEXT NOT NULL CHECK(status IN ('active','submitted','expired')),
 essay TEXT NOT NULL DEFAULT '',essay_revision INTEGER NOT NULL DEFAULT 0,charged_questions INTEGER NOT NULL,
 quota_period TEXT NOT NULL,start_key TEXT NOT NULL,UNIQUE(user_id,start_key));
CREATE INDEX IF NOT EXISTS monthly_mock_usage ON mock_exams(user_id,quota_period);
CREATE UNIQUE INDEX IF NOT EXISTS one_active_mock ON mock_exams(user_id) WHERE status='active';
CREATE TABLE IF NOT EXISTS mock_items(
 exam_id TEXT NOT NULL REFERENCES mock_exams(id),position INTEGER NOT NULL,question_id TEXT NOT NULL,
 choice TEXT,flagged INTEGER NOT NULL DEFAULT 0,revision INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(exam_id,question_id),UNIQUE(exam_id,position));
INSERT OR IGNORE INTO schema_version VALUES(2);
CREATE TABLE IF NOT EXISTS idempotency(user_id TEXT NOT NULL REFERENCES users(id),key TEXT NOT NULL,payload TEXT NOT NULL,response TEXT NOT NULL,PRIMARY KEY(user_id,key));
'''


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript(SCHEMA)

    @contextmanager
    def connect(self, write=False):
        db = sqlite3.connect(self.path, timeout=15, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute('PRAGMA foreign_keys=ON')
        db.execute('PRAGMA busy_timeout=15000')
        try:
            if write:
                db.execute('BEGIN IMMEDIATE')
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()
