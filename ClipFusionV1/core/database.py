"""
ClipFusionV1.core.database (sqlite3)
===================================

Módulo de persistência usando a biblioteca padrão ``sqlite3``.  Este
arquivo substitui o uso do SQLAlchemy para evitar dependências
externas, permitindo execução em ambientes sem acesso à internet.  As
tabelas são criadas sob demanda e funções de conveniência são
fornecidas para inserir e consultar registros.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_DB_PATH = "clipfusion_v1.db"


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Cria as tabelas necessárias caso ainda não existam."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()
    # Tabela de projetos
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS projects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            name TEXT NOT NULL,
            video_path TEXT NOT NULL,
            niche TEXT,
            status TEXT DEFAULT 'pending'
        )
        """
    )
    # Tabela de clipes
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS video_clips (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            start_time REAL,
            end_time REAL,
            hook_text TEXT,
            viral_score REAL,
            archetype TEXT,
            protection_level TEXT,
            output_path TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
        """
    )
    # Tabela de jobs
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            project_id INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            state TEXT,
            error_message TEXT,
            FOREIGN KEY(project_id) REFERENCES projects(id)
        )
        """
    )
    # Tabela de agendamento de postagem
    cur.execute(
        """
        CREATE TABLE IF NOT EXISTS post_schedules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clip_id INTEGER,
            scheduled_time TIMESTAMP NOT NULL,
            platform TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(clip_id) REFERENCES video_clips(id)
        )
        """
    )
    conn.commit()
    conn.close()


def _get_conn(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    return sqlite3.connect(db_path)


def insert_project(name: str, video_path: str, status: str = "pending", niche: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO projects (name, video_path, niche, status) VALUES (?, ?, ?, ?)",
        (name, video_path, niche, status),
    )
    project_id = cur.lastrowid
    conn.commit()
    conn.close()
    return project_id


def get_project(project_id: int, db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, created_at, name, video_path, niche, status FROM projects WHERE id = ?", (project_id,))
    row = cur.fetchone()
    conn.close()
    if row:
        keys = ["id", "created_at", "name", "video_path", "niche", "status"]
        return dict(zip(keys, row))
    return None


def list_projects(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute("SELECT id, name, video_path, status FROM projects")
    rows = cur.fetchall()
    conn.close()
    return [dict(zip(["id", "name", "video_path", "status"], r)) for r in rows]


def insert_job(project_id: int, state: str = "queued", error_message: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO jobs (project_id, state, error_message) VALUES (?, ?, ?)",
        (project_id, state, error_message),
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()
    return job_id


def update_job(job_id: int, state: str, error_message: Optional[str] = None, db_path: str = DEFAULT_DB_PATH) -> None:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "UPDATE jobs SET state = ?, error_message = ? WHERE id = ?",
        (state, error_message, job_id),
    )
    conn.commit()
    conn.close()


def get_next_job(db_path: str = DEFAULT_DB_PATH) -> Optional[Dict[str, Any]]:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, project_id, state FROM jobs WHERE state = 'queued' ORDER BY created_at LIMIT 1"
    )
    row = cur.fetchone()
    conn.close()
    if row:
        keys = ["id", "project_id", "state"]
        return dict(zip(keys, row))
    return None


def insert_clip(project_id: int, start_time: float, end_time: float, hook_text: str, viral_score: float, archetype: str, protection_level: str, output_path: str, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO video_clips (project_id, start_time, end_time, hook_text, viral_score, archetype, protection_level, output_path)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (project_id, start_time, end_time, hook_text, viral_score, archetype, protection_level, output_path),
    )
    clip_id = cur.lastrowid
    conn.commit()
    conn.close()
    return clip_id


def list_clips(db_path: str = DEFAULT_DB_PATH) -> List[Dict[str, Any]]:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "SELECT id, project_id, start_time, end_time, hook_text, viral_score, archetype, protection_level, output_path FROM video_clips"
    )
    rows = cur.fetchall()
    conn.close()
    keys = ["id", "project_id", "start_time", "end_time", "hook_text", "viral_score", "archetype", "protection_level", "output_path"]
    return [dict(zip(keys, r)) for r in rows]


def insert_schedule(clip_id: int, scheduled_time: str, platform: str, db_path: str = DEFAULT_DB_PATH) -> int:
    conn = _get_conn(db_path)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO post_schedules (clip_id, scheduled_time, platform) VALUES (?, ?, ?)",
        (clip_id, scheduled_time, platform),
    )
    schedule_id = cur.lastrowid
    conn.commit()
    conn.close()
    return schedule_id
