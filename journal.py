import sqlite3
from pathlib import Path
from datetime import datetime

DB_PATH = Path(__file__).with_name("trades.db")

def init_db():
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            direction TEXT NOT NULL,
            entry REAL NOT NULL,
            stop_loss REAL NOT NULL,
            take_profit REAL NOT NULL,
            rr REAL NOT NULL,
            score INTEGER NOT NULL,
            decision TEXT NOT NULL,
            outcome TEXT,
            pnl_r REAL,
            notes TEXT
        )
        """)
        conn.commit()

def save_setup(result, notes=""):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
        INSERT INTO trades (
            created_at, direction, entry, stop_loss, take_profit,
            rr, score, decision, outcome, pnl_r, notes
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().isoformat(timespec="seconds"),
            result.direction,
            result.entry,
            result.stop_loss,
            result.take_profit,
            result.rr,
            result.score,
            result.decision,
            None,
            None,
            notes,
        ))
        conn.commit()

def get_trades():
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
        SELECT id, created_at, direction, entry, stop_loss, take_profit,
               rr, score, decision, outcome, pnl_r, notes
        FROM trades
        ORDER BY id DESC
        """).fetchall()

    columns = [
        "id","created_at","direction","entry","stop_loss","take_profit",
        "rr","score","decision","outcome","pnl_r","notes"
    ]
    return columns, rows
