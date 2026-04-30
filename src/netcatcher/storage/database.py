"""SQLite database for persistent capture storage."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class CaptureDatabase:
    """SQLite-backed storage for capture sessions."""

    def __init__(self, db_path: str | Path = "captures.db"):
        self._db_path = str(db_path)
        self._conn: sqlite3.Connection | None = None

    def open(self):
        self._conn = sqlite3.connect(self._db_path, check_same_thread=False)
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.execute("PRAGMA cache_size=-64000")
        self._create_tables()

    def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None

    def _create_tables(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS capture_sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                started_at TEXT NOT NULL,
                stopped_at TEXT,
                interface TEXT,
                bpf_filter TEXT
            );

            CREATE TABLE IF NOT EXISTS packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES capture_sessions(id),
                timestamp REAL NOT NULL,
                src_ip TEXT, dst_ip TEXT,
                src_port INTEGER, dst_port INTEGER,
                protocol TEXT,
                length INTEGER,
                info TEXT,
                raw_blob BLOB,
                layer_json TEXT,
                source TEXT DEFAULT 'scapy'
            );

            CREATE INDEX IF NOT EXISTS idx_packets_protocol ON packets(protocol);
            CREATE INDEX IF NOT EXISTS idx_packets_timestamp ON packets(timestamp);

            CREATE TABLE IF NOT EXISTS http_flows (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER REFERENCES capture_sessions(id),
                method TEXT,
                url TEXT,
                host TEXT,
                path TEXT,
                status_code INTEGER,
                request_headers TEXT,
                request_body BLOB,
                response_headers TEXT,
                response_body BLOB,
                content_type TEXT,
                duration_ms REAL,
                is_https INTEGER DEFAULT 0
            );

            CREATE INDEX IF NOT EXISTS idx_http_flows_host ON http_flows(host);
        """)

    def start_session(self, interface: str = "", bpf_filter: str = "") -> int:
        cur = self._conn.execute(
            "INSERT INTO capture_sessions (started_at, interface, bpf_filter) VALUES (datetime('now'), ?, ?)",
            (interface, bpf_filter),
        )
        self._conn.commit()
        return cur.lastrowid

    def save_packet(self, session_id: int, record) -> int:
        self._conn.execute(
            """INSERT INTO packets (session_id, timestamp, src_ip, dst_ip, src_port, dst_port,
               protocol, length, info, raw_blob, layer_json, source)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, record.timestamp, record.src_ip, record.dst_ip,
             record.src_port, record.dst_port, record.protocol, record.length,
             record.info, record.raw_bytes, json.dumps(record.layer_details), record.capture_source),
        )
        return self._conn.total_changes

    def save_flow(self, session_id: int, flow) -> int:
        self._conn.execute(
            """INSERT INTO http_flows (session_id, method, url, host, path, status_code,
               request_headers, request_body, response_headers, response_body,
               content_type, duration_ms, is_https)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (session_id, flow.method, flow.url, flow.host, flow.path, flow.status_code,
             json.dumps(flow.request_headers), flow.request_body,
             json.dumps(flow.response_headers), flow.response_body,
             flow.content_type, flow.duration_ms, int(flow.is_https)),
        )
        return self._conn.total_changes

    def commit(self):
        if self._conn:
            self._conn.commit()
