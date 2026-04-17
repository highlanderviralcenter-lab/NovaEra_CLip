import sqlite3, json, os
from pathlib import Path

DB_PATH = Path(os.path.expanduser("~")) / ".clipfusion" / "db.sqlite"

def _conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    c = sqlite3.connect(str(DB_PATH))
    c.row_factory = sqlite3.Row
    return c

def init():
    c = _conn()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT, video_path TEXT,
            status TEXT DEFAULT 'novo',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS transcriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, full_text TEXT, segments TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS cuts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER, cut_index INTEGER,
            start_time REAL, end_time REAL,
            title TEXT, archetype TEXT, hook TEXT, reason TEXT,
            platforms TEXT, status TEXT DEFAULT 'pendente',
            output_paths TEXT, metadata TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    c.commit()
    c.close()

def create_project(name, video_path):
    c = _conn()
    cur = c.execute("INSERT INTO projects (name,video_path,status) VALUES (?,?,'transcrevendo')", (name, video_path))
    pid = cur.lastrowid
    c.commit()
    c.close()
    return pid

def update_project_status(pid, status):
    c = _conn()
    c.execute("UPDATE projects SET status=? WHERE id=?", (status, pid))
    c.commit()
    c.close()

def get_project(pid):
    c = _conn()
    r = c.execute("SELECT * FROM projects WHERE id=?", (pid,)).fetchone()
    c.close()
    return dict(r) if r else None

def list_projects():
    c = _conn()
    rows = c.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    c.close()
    return [dict(r) for r in rows]

def save_transcription(pid, full_text, segments, confidence=None):
    c = _conn()
    c.execute("INSERT INTO transcriptions (project_id,full_text,segments) VALUES (?,?,?)", (pid, full_text, json.dumps(segments, ensure_ascii=False)))
    c.commit()
    c.close()

def get_transcription(pid):
    c = _conn()
    r = c.execute("SELECT * FROM transcriptions WHERE project_id=? ORDER BY id DESC LIMIT 1", (pid,)).fetchone()
    c.close()
    if not r:
        return None
    d = dict(r)
    d["segments"] = json.loads(d["segments"] or "[]")
    return d

def save_cuts(pid, cuts):
    c = _conn()
    c.execute("DELETE FROM cuts WHERE project_id=?", (pid,))
    for i, cut in enumerate(cuts):
        c.execute("""INSERT INTO cuts (project_id,cut_index,start_time,end_time,title,archetype,hook,reason,platforms,status,metadata) VALUES (?,?,?,?,?,?,?,?,?,?,?)""", (pid, i, cut["start"], cut["end"], cut.get("title",""), cut.get("archetype",""), cut.get("hook",""), cut.get("reason",""), json.dumps(cut.get("platforms",[])), "pendente", json.dumps(cut.get("metadata",{}), ensure_ascii=False)))
    c.commit()
    c.close()

def get_cuts(pid, status=None):
    c = _conn()
    if status:
        rows = c.execute("SELECT * FROM cuts WHERE project_id=? AND status=? ORDER BY cut_index", (pid, status)).fetchall()
    else:
        rows = c.execute("SELECT * FROM cuts WHERE project_id=? ORDER BY cut_index", (pid,)).fetchall()
    c.close()
    result = []
    for r in rows:
        d = dict(r)
        d["platforms"] = json.loads(d["platforms"] or "[]")
        d["output_paths"] = json.loads(d["output_paths"] or "{}")
        d["metadata"] = json.loads(d["metadata"] or "{}")
        result.append(d)
    return result

def update_cut_status(cut_id, status):
    c = _conn()
    c.execute("UPDATE cuts SET status=? WHERE id=?", (status, cut_id))
    c.commit()
    c.close()

def update_cut_output(cut_id, paths):
    c = _conn()
    c.execute("UPDATE cuts SET output_paths=?,status='renderizado' WHERE id=?", (json.dumps(paths), cut_id))
    c.commit()
    c.close()

init()
