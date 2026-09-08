import os, sqlite3, json
from pathlib import Path

DB_URL=os.getenv('DATABASE_URL','sqlite:///./truthtrace.db')
DB_PATH=Path(DB_URL.replace('sqlite:///','')) if DB_URL.startswith('sqlite:///') else Path('./truthtrace.db')
if not DB_PATH.is_absolute(): DB_PATH=Path(__file__).resolve().parents[1]/DB_PATH
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def conn():
    c=sqlite3.connect(DB_PATH)
    c.row_factory=sqlite3.Row
    return c

def init_db():
    c=conn()
    c.executescript('''
    CREATE TABLE IF NOT EXISTS cases(id TEXT PRIMARY KEY, investigation_type TEXT, claim TEXT, platform TEXT, date TEXT, location TEXT, with_media INTEGER, notes TEXT, reference_url TEXT, priority TEXT, status TEXT, created_at TEXT, updated_at TEXT);
    CREATE TABLE IF NOT EXISTS evidence(id TEXT PRIMARY KEY, case_id TEXT, file_name TEXT, file_path TEXT, mime_type TEXT, file_type TEXT, file_size INTEGER, sha256 TEXT, phash TEXT, dna_id TEXT, embedding_json TEXT, width INTEGER, height INTEGER, duration REAL, metadata_json TEXT, analysis_status TEXT, created_at TEXT, FOREIGN KEY(case_id) REFERENCES cases(id));
    CREATE TABLE IF NOT EXISTS analysis(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, evidence_id TEXT, result_json TEXT, created_at TEXT, FOREIGN KEY(case_id) REFERENCES cases(id));
    CREATE TABLE IF NOT EXISTS propagation(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, evidence_id TEXT, platform TEXT, account TEXT, observed_at TEXT, similarity REAL, transformation TEXT, source_url TEXT, from_node TEXT, to_node TEXT, spread TEXT, tag TEXT);
    CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, timestamp TEXT, event TEXT, actor_user_id TEXT);
    CREATE TABLE IF NOT EXISTS reports(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT, path TEXT, created_at TEXT);
    CREATE TABLE IF NOT EXISTS users(id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL, name TEXT NOT NULL, role TEXT NOT NULL, password_hash TEXT NOT NULL, active INTEGER NOT NULL DEFAULT 1, created_at TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS sessions(id TEXT PRIMARY KEY, user_id TEXT NOT NULL, token_hash TEXT UNIQUE NOT NULL, expires_at TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS case_assignments(case_id TEXT NOT NULL, user_id TEXT NOT NULL, assigned_at TEXT NOT NULL, assigned_by TEXT, PRIMARY KEY(case_id,user_id), FOREIGN KEY(case_id) REFERENCES cases(id), FOREIGN KEY(user_id) REFERENCES users(id));
    CREATE TABLE IF NOT EXISTS chat_messages(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, user_id TEXT, role TEXT NOT NULL, message TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(id));
    CREATE TABLE IF NOT EXISTS osint_results(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, query TEXT NOT NULL, result_json TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(id));
    CREATE TABLE IF NOT EXISTS case_reviews(id INTEGER PRIMARY KEY AUTOINCREMENT, case_id TEXT NOT NULL, reviewer_user_id TEXT NOT NULL, disposition TEXT NOT NULL, rationale TEXT NOT NULL, evidence_sufficiency TEXT NOT NULL, investigator_finding TEXT NOT NULL, created_at TEXT NOT NULL, FOREIGN KEY(case_id) REFERENCES cases(id), FOREIGN KEY(reviewer_user_id) REFERENCES users(id));
    ''')
    try: c.execute('ALTER TABLE evidence ADD COLUMN embedding_json TEXT')
    except: pass
    try: c.execute('ALTER TABLE audit ADD COLUMN actor_user_id TEXT')
    except: pass
    c.commit(); c.close()

def q(sql,args=(),one=False):
    c=conn(); rows=c.execute(sql,args).fetchall(); c.close(); return (rows[0] if rows else None) if one else rows

def execute(sql,args=()):
    c=conn(); cur=c.execute(sql,args); c.commit(); last=cur.lastrowid; c.close(); return last

def jdump(x): return json.dumps(x, ensure_ascii=False)
def jload(x,default=None):
    try:return json.loads(x)
    except:return default
