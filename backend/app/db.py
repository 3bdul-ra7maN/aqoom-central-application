from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users(
 user_id TEXT PRIMARY KEY,
 name TEXT NOT NULL,
 role TEXT NOT NULL CHECK(role IN ('REQUESTER','EXECUTOR','TRAINER')),
 created_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'ACTIVE');

CREATE TABLE IF NOT EXISTS tasks(
 task_id TEXT PRIMARY KEY,
 requester_id TEXT NOT NULL REFERENCES users(user_id),
 description TEXT NOT NULL,
 created_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('CREATED','VALIDATED','ASSIGNED','IN_EXECUTION','COMPLETED','FAILED')));

CREATE TABLE IF NOT EXISTS assignments(
 assignment_id TEXT PRIMARY KEY,
 task_id TEXT NOT NULL UNIQUE REFERENCES tasks(task_id),
 executor_id TEXT NOT NULL REFERENCES users(user_id),
 assigned_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'ASSIGNED');

CREATE TABLE IF NOT EXISTS executions(
 execution_id TEXT PRIMARY KEY,
 task_id TEXT NOT NULL REFERENCES tasks(task_id),
 executor_id TEXT NOT NULL REFERENCES users(user_id),
 started_at TEXT,
 finished_at TEXT,
 status TEXT NOT NULL CHECK(status IN ('IN_EXECUTION','COMPLETED','FAILED')));

CREATE TABLE IF NOT EXISTS results(
 result_id TEXT PRIMARY KEY,
 execution_id TEXT NOT NULL UNIQUE REFERENCES executions(execution_id),
 result_status TEXT NOT NULL CHECK(result_status IN ('SUCCESS','FAILED','INCOMPLETE','REJECTED')),
 result_data TEXT NOT NULL,
 created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS evidence(
 evidence_id TEXT PRIMARY KEY,
 execution_id TEXT NOT NULL REFERENCES executions(execution_id),
 result_id TEXT NOT NULL REFERENCES results(result_id),
 evidence_type TEXT NOT NULL,
 evidence_reference TEXT NOT NULL,
 created_at TEXT NOT NULL,
 status TEXT NOT NULL CHECK(status IN ('SUBMITTED','VALIDATED')));

CREATE TABLE IF NOT EXISTS effort_records(
 effort_id TEXT PRIMARY KEY,
 execution_id TEXT NOT NULL UNIQUE REFERENCES executions(execution_id),
 t_accounted_ns INTEGER NOT NULL CHECK(t_accounted_ns > 0),
 calculation_rule TEXT NOT NULL,
 created_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'ACCOUNTED');

CREATE TABLE IF NOT EXISTS rt_records(
 rt_record_id TEXT PRIMARY KEY,
 execution_id TEXT NOT NULL UNIQUE REFERENCES executions(execution_id),
 effort_id TEXT NOT NULL UNIQUE REFERENCES effort_records(effort_id),
 t_accounted_ns INTEGER NOT NULL,
 rt_value REAL NOT NULL CHECK(rt_value > 0),
 calculation_rule TEXT NOT NULL,
 created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS settlement_records(
 settlement_id TEXT PRIMARY KEY,
 task_id TEXT NOT NULL REFERENCES tasks(task_id),
 execution_id TEXT NOT NULL UNIQUE REFERENCES executions(execution_id),
 rt_record_id TEXT NOT NULL REFERENCES rt_records(rt_record_id),
 rt_value REAL NOT NULL,
 settlement_status TEXT NOT NULL CHECK(settlement_status IN ('PENDING','READY','RECORDED')),
 created_at TEXT NOT NULL);

CREATE TABLE IF NOT EXISTS training_records(
 training_record_id TEXT PRIMARY KEY,
 execution_id TEXT NOT NULL UNIQUE REFERENCES executions(execution_id),
 result_reference TEXT NOT NULL,
 input_data_reference TEXT NOT NULL,
 created_at TEXT NOT NULL,
 status TEXT NOT NULL DEFAULT 'RECORDED');

CREATE TABLE IF NOT EXISTS trace_events(
 trace_event_id TEXT PRIMARY KEY,
 event_type TEXT NOT NULL,
 entity_type TEXT NOT NULL,
 entity_id TEXT NOT NULL,
 timestamp TEXT NOT NULL,
 actor_id TEXT,
 payload TEXT NOT NULL);
"""

class Database:
    def __init__(self, path: str | Path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def initialize(self) -> None:
        with self.connect() as conn:
            conn.executescript(SCHEMA)
