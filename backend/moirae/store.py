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
CREATE TABLE IF NOT EXISTS user_profiles(user_id TEXT PRIMARY KEY REFERENCES users(id),email_verified INTEGER NOT NULL DEFAULT 0,policy_version TEXT,accepted_at INTEGER,adult_pilot INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS account_tokens(token_hash TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),purpose TEXT NOT NULL CHECK(purpose IN ('verify','reset')),expires_at INTEGER NOT NULL,created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS account_token_owner ON account_tokens(user_id,purpose);
INSERT OR IGNORE INTO schema_version VALUES(3);
CREATE TABLE IF NOT EXISTS billing_orders(id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),plan_id TEXT NOT NULL,amount_cents INTEGER NOT NULL,status TEXT NOT NULL,created_at INTEGER NOT NULL,request_key TEXT NOT NULL,preference_id TEXT,checkout_url TEXT,payment_id TEXT UNIQUE,provider_version REAL,refund_requested_at INTEGER,UNIQUE(user_id,request_key));
CREATE UNIQUE INDEX IF NOT EXISTS one_pending_order ON billing_orders(user_id) WHERE status IN ('preparing','pending','in_process','authorized');
CREATE TABLE IF NOT EXISTS access_grants(order_id TEXT PRIMARY KEY REFERENCES billing_orders(id),user_id TEXT NOT NULL REFERENCES users(id),plan_id TEXT NOT NULL,starts_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,status TEXT NOT NULL,essay_credits INTEGER NOT NULL);
CREATE TABLE IF NOT EXISTS essay_submissions(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id),grant_id TEXT NOT NULL REFERENCES access_grants(order_id),
 request_key TEXT NOT NULL,theme TEXT NOT NULL,text TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('received','processing','completed','failed')),
 created_at INTEGER NOT NULL,result TEXT,error TEXT,UNIQUE(user_id,request_key));
CREATE INDEX IF NOT EXISTS essay_owner ON essay_submissions(user_id,created_at);
CREATE TABLE IF NOT EXISTS essay_rewrites(
 id TEXT PRIMARY KEY,essay_id TEXT NOT NULL REFERENCES essay_submissions(id),annotation_id TEXT NOT NULL,
 request_key TEXT NOT NULL,text TEXT NOT NULL,created_at INTEGER NOT NULL,UNIQUE(essay_id,request_key));
INSERT OR IGNORE INTO schema_version VALUES(5);
CREATE INDEX IF NOT EXISTS review_attempt_history ON attempts(user_id,question_id,created_at DESC);
CREATE TABLE IF NOT EXISTS review_favorites(user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,question_id TEXT NOT NULL,PRIMARY KEY(user_id,question_id));
INSERT OR IGNORE INTO schema_version VALUES(7);
CREATE TABLE IF NOT EXISTS review_schedule(user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,question_id TEXT NOT NULL,stage INTEGER NOT NULL CHECK(stage BETWEEN 0 AND 4),due_at INTEGER NOT NULL,last_answered_at INTEGER NOT NULL,PRIMARY KEY(user_id,question_id));
CREATE INDEX IF NOT EXISTS review_due ON review_schedule(user_id,due_at);
CREATE TABLE IF NOT EXISTS practice_plans(session_id TEXT PRIMARY KEY REFERENCES practice_sessions(id) ON DELETE CASCADE,minutes INTEGER NOT NULL,description TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS real_essay_jobs(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,grant_id TEXT NOT NULL REFERENCES access_grants(order_id),request_key TEXT NOT NULL,
 theme TEXT NOT NULL,text TEXT NOT NULL,external_notice_version TEXT NOT NULL DEFAULT 'openai-processing-v1',status TEXT NOT NULL CHECK(status IN ('pending','processing','completed','failed')),
 created_at INTEGER NOT NULL,available_at INTEGER NOT NULL,attempts INTEGER NOT NULL DEFAULT 0,
 lease_token TEXT,lease_until INTEGER,model TEXT NOT NULL,rubric_version TEXT NOT NULL,prompt_version TEXT NOT NULL,result TEXT,error TEXT,UNIQUE(user_id,request_key));
CREATE INDEX IF NOT EXISTS real_essay_queue ON real_essay_jobs(status,available_at,lease_until);
CREATE UNIQUE INDEX IF NOT EXISTS one_real_essay_pending ON real_essay_jobs(user_id) WHERE status IN ('pending','processing');
CREATE INDEX IF NOT EXISTS real_essay_owner ON real_essay_jobs(user_id,created_at);
CREATE TABLE IF NOT EXISTS essay_credit_events(job_id TEXT NOT NULL REFERENCES real_essay_jobs(id) ON DELETE CASCADE,grant_id TEXT NOT NULL REFERENCES access_grants(order_id),event TEXT NOT NULL CHECK(event IN ('reserve','consume','release')),delta INTEGER NOT NULL CHECK((event='reserve' AND delta=1) OR (event='release' AND delta=-1) OR (event='consume' AND delta=0)),created_at INTEGER NOT NULL,PRIMARY KEY(job_id,event));
CREATE INDEX IF NOT EXISTS real_essay_credit_grant ON essay_credit_events(grant_id);
CREATE TABLE IF NOT EXISTS essay_provider_calls(id INTEGER PRIMARY KEY AUTOINCREMENT,job_id TEXT NOT NULL REFERENCES real_essay_jobs(id) ON DELETE CASCADE,created_at INTEGER NOT NULL);
CREATE INDEX IF NOT EXISTS essay_daily_calls ON essay_provider_calls(created_at);
INSERT OR IGNORE INTO schema_version VALUES(9);
CREATE TABLE IF NOT EXISTS diagnostic_sessions(session_id TEXT PRIMARY KEY REFERENCES practice_sessions(id));
INSERT OR IGNORE INTO schema_version VALUES(10);
CREATE TABLE IF NOT EXISTS sandbox_credit_lots(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,source TEXT NOT NULL UNIQUE,
 units INTEGER NOT NULL CHECK(units>0),available INTEGER NOT NULL CHECK(available>=0),expires_at INTEGER NOT NULL,
 reserved INTEGER NOT NULL CHECK(reserved>=0),consumed INTEGER NOT NULL CHECK(consumed>=0),created_at INTEGER NOT NULL,revoked_at INTEGER,
 CHECK(available+reserved+consumed=units));
CREATE INDEX IF NOT EXISTS sandbox_wallet_owner ON sandbox_credit_lots(user_id,expires_at);
CREATE TABLE IF NOT EXISTS sandbox_credit_reservations(
 id TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,lot_id TEXT NOT NULL REFERENCES sandbox_credit_lots(id) ON DELETE CASCADE,
 request_key TEXT NOT NULL,status TEXT NOT NULL CHECK(status IN ('reserved','consumed','released','refunded')),created_at INTEGER NOT NULL,UNIQUE(user_id,request_key));
CREATE TABLE IF NOT EXISTS sandbox_wallet_events(
 id INTEGER PRIMARY KEY AUTOINCREMENT,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,lot_id TEXT NOT NULL REFERENCES sandbox_credit_lots(id) ON DELETE CASCADE,
 kind TEXT NOT NULL CHECK(kind IN ('grant','reserve','consume','release','refund','revoke')),reference TEXT NOT NULL,units INTEGER NOT NULL CHECK(units>0),created_at INTEGER NOT NULL,UNIQUE(kind,reference));
CREATE TABLE IF NOT EXISTS sandbox_coupon_campaigns(
 id TEXT PRIMARY KEY,starts_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,valid_seconds INTEGER NOT NULL CHECK(valid_seconds>0),products TEXT NOT NULL,outcomes TEXT NOT NULL,max_uses INTEGER NOT NULL CHECK(max_uses>0),enabled INTEGER NOT NULL CHECK(enabled IN (0,1)),CHECK(ends_at>starts_at));
CREATE TABLE IF NOT EXISTS sandbox_coupons(
 code TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,campaign_id TEXT NOT NULL REFERENCES sandbox_coupon_campaigns(id),
 discount_bps INTEGER NOT NULL CHECK(discount_bps BETWEEN 0 AND 10000),expires_at INTEGER NOT NULL,created_at INTEGER NOT NULL,UNIQUE(user_id,campaign_id));
CREATE TABLE IF NOT EXISTS sandbox_coupon_redemptions(
 order_reference TEXT PRIMARY KEY,user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,code TEXT NOT NULL UNIQUE REFERENCES sandbox_coupons(code) ON DELETE CASCADE,
 campaign_id TEXT NOT NULL REFERENCES sandbox_coupon_campaigns(id),product TEXT NOT NULL,snapshot TEXT NOT NULL,created_at INTEGER NOT NULL,mode TEXT NOT NULL CHECK(mode='sandbox'));
CREATE INDEX IF NOT EXISTS sandbox_event_owner ON sandbox_wallet_events(user_id,id);
CREATE INDEX IF NOT EXISTS sandbox_reservation_lot ON sandbox_credit_reservations(lot_id,status);
CREATE INDEX IF NOT EXISTS sandbox_coupon_usage ON sandbox_coupon_redemptions(campaign_id);
INSERT OR IGNORE INTO schema_version VALUES(11);
CREATE TABLE IF NOT EXISTS idempotency(user_id TEXT NOT NULL REFERENCES users(id),key TEXT NOT NULL,payload TEXT NOT NULL,response TEXT NOT NULL,PRIMARY KEY(user_id,key));
'''


class Store:
    def __init__(self, path: str):
        self.path = path
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as db:
            db.execute('PRAGMA journal_mode=WAL')
            db.executescript(SCHEMA)
            if 'free_charge' not in {r[1] for r in db.execute('PRAGMA table_info(attempts)')}:
                db.execute('ALTER TABLE attempts ADD COLUMN free_charge INTEGER NOT NULL DEFAULT 1')
            db.execute('INSERT OR IGNORE INTO schema_version VALUES(4)')
            columns={r[1] for r in db.execute('PRAGMA table_info(billing_orders)')}
            for column in ('essay_credits', 'access_days', 'catalog_version'):
                if column not in columns:
                    db.execute(f'ALTER TABLE billing_orders ADD COLUMN {column} INTEGER')
            # Only the two known legacy contracts can be backfilled safely.
            with self.connect(write=True) as migration:
                migration.execute("UPDATE billing_orders SET essay_credits=CASE plan_id WHEN 'essencial' THEN 3 ELSE 8 END, access_days=30, catalog_version=1 WHERE catalog_version IS NULL AND ((plan_id='essencial' AND amount_cents=3500) OR (plan_id='avancado' AND amount_cents=5500))")
                migration.execute('INSERT OR IGNORE INTO schema_version VALUES(6)')
                if not migration.execute('SELECT 1 FROM schema_version WHERE version=8').fetchone():
                    migration.execute("""WITH ranked AS (
                        SELECT user_id,question_id,correct,created_at,
                        row_number() OVER(PARTITION BY user_id,question_id ORDER BY created_at DESC,rowid DESC) AS position,
                        min(correct) OVER(PARTITION BY user_id,question_id) AS no_error
                        FROM attempts)
                        INSERT OR IGNORE INTO review_schedule(user_id,question_id,stage,due_at,last_answered_at)
                        SELECT user_id,question_id,CASE WHEN correct=1 THEN 1 ELSE 0 END,
                        created_at+CASE WHEN correct=1 THEN 259200 ELSE 86400 END,created_at
                        FROM ranked WHERE position=1 AND no_error=0""")
                    migration.execute('INSERT INTO schema_version VALUES(8)')

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

