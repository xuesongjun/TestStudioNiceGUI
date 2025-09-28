import sqlite3
from pathlib import Path

DB_FILE = Path("data/test_results.db")

def init_db(table_name="ble_test_results"):
    DB_FILE.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            chn INTEGER,
            rate TEXT,
            noise REAL,
            signal REAL,
            gain REAL,
            dc REAL,
            snr REAL,
            image REAL,
            imrr REAL,
            nf REAL,
            sensitive REAL,
            timestamp DATETIME DEFAULT (strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        )
        """)
    print(f"Database {table_name} initialized with local timestamp.")

def insert_test_data(table_name="ble_test_results", chn=None, rate=None, noise=None, signal=None, gain=None, dc=None,
                     snr=None, image=None, imrr=None, nf=None, sensitive=None):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(f"""
        INSERT INTO {table_name} 
        (chn, rate, noise, signal, gain, dc, snr, image, imrr, nf, sensitive, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """, (chn, rate, noise, signal, gain, dc, snr, image, imrr, nf, sensitive))
def query_results(table_name="ble_test_results", chn=None, rate=None):
    query = f"SELECT * FROM {table_name} WHERE 1=1"
    params = []
    if chn is not None:
        query += " AND chn=?"
        params.append(chn)
    if rate is not None:
        query += " AND rate=?"
        params.append(rate)
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall()
