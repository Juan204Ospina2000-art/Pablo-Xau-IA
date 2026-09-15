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
            result.direction, result.entry, result.stop_loss, result.take_profit,
            result.rr, result.score, result.decision, None, None, notes,
        ))
        conn.commit()

def get_trades():
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        rows=conn.execute("""
        SELECT id, created_at, direction, entry, stop_loss, take_profit,
               rr, score, decision, outcome, pnl_r, notes
        FROM trades ORDER BY id DESC
        """).fetchall()
    columns=["id","created_at","direction","entry","stop_loss","take_profit","rr","score","decision","outcome","pnl_r","notes"]
    return columns,rows

def update_outcome(trade_id, outcome, pnl_r):
    init_db()
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("UPDATE trades SET outcome=?, pnl_r=? WHERE id=?", (outcome,pnl_r,trade_id))
        conn.commit()

def journal_stats():
    columns, rows = get_trades()
    idx={name:i for i,name in enumerate(columns)}
    closed=[r for r in rows if r[idx["outcome"]] in ("WIN","LOSS","BE")]
    if not closed:
        return {"closed":0,"wins":0,"losses":0,"be":0,"win_rate":0.0,"net_r":0.0,"expectancy_r":0.0}
    wins=sum(1 for r in closed if r[idx["outcome"]]=="WIN")
    losses=sum(1 for r in closed if r[idx["outcome"]]=="LOSS")
    be=sum(1 for r in closed if r[idx["outcome"]]=="BE")
    pnl=[float(r[idx["pnl_r"]] or 0) for r in closed]
    decided=max(1,wins+losses)
    return {
        "closed":len(closed),"wins":wins,"losses":losses,"be":be,
        "win_rate":round(wins/decided*100,1),
        "net_r":round(sum(pnl),2),
        "expectancy_r":round(sum(pnl)/len(closed),2),
    }
