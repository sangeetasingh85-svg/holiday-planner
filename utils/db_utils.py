import sqlite3
import json
import os
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent.parent / "plans.db"


def get_connection():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS plans (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            holiday_name TEXT,
            num_days INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            plan_data TEXT NOT NULL
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS used_worksheets (
            worksheet_id TEXT NOT NULL,
            plan_id INTEGER NOT NULL,
            PRIMARY KEY (worksheet_id, plan_id),
            FOREIGN KEY (plan_id) REFERENCES plans(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    conn.close()


def save_plan(name, holiday_name, num_days, plan_data):
    conn = get_connection()
    cursor = conn.execute(
        "INSERT INTO plans (name, holiday_name, num_days, created_at, plan_data) VALUES (?, ?, ?, ?, ?)",
        (name, holiday_name, num_days, datetime.now().isoformat(), json.dumps(plan_data))
    )
    plan_id = cursor.lastrowid
    for day in plan_data["days"]:
        for ws in day["worksheets"]:
            if ws.get("id") and not ws.get("is_speed_math"):
                conn.execute(
                    "INSERT OR IGNORE INTO used_worksheets (worksheet_id, plan_id) VALUES (?, ?)",
                    (ws["id"], plan_id)
                )
    conn.commit()
    conn.close()
    return plan_id


def get_all_plans():
    conn = get_connection()
    plans = conn.execute(
        "SELECT id, name, holiday_name, num_days, created_at FROM plans ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return [dict(p) for p in plans]


def get_plan(plan_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)).fetchone()
    conn.close()
    if row:
        d = dict(row)
        d["plan_data"] = json.loads(d["plan_data"])
        return d
    return None


def delete_plan(plan_id):
    conn = get_connection()
    conn.execute("DELETE FROM used_worksheets WHERE plan_id = ?", (plan_id,))
    conn.execute("DELETE FROM plans WHERE id = ?", (plan_id,))
    conn.commit()
    conn.close()


def get_all_used_worksheet_ids():
    conn = get_connection()
    rows = conn.execute("SELECT DISTINCT worksheet_id FROM used_worksheets").fetchall()
    conn.close()
    return {r["worksheet_id"] for r in rows}


def update_plan_data(plan_id, plan_data):
    conn = get_connection()
    conn.execute("UPDATE plans SET plan_data = ? WHERE id = ?", (json.dumps(plan_data), plan_id))
    conn.execute("DELETE FROM used_worksheets WHERE plan_id = ?", (plan_id,))
    for day in plan_data["days"]:
        for ws in day["worksheets"]:
            if ws.get("id") and not ws.get("is_speed_math"):
                conn.execute(
                    "INSERT OR IGNORE INTO used_worksheets (worksheet_id, plan_id) VALUES (?, ?)",
                    (ws["id"], plan_id)
                )
    conn.commit()
    conn.close()
