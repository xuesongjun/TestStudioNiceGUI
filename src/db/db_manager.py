import sqlite3
from pathlib import Path
from datetime import datetime

DB_FILE = Path("data/test_results.db")

def init_db(table_name="ble_test_results"):
    DB_FILE.parent.mkdir(exist_ok=True)
    with sqlite3.connect(DB_FILE) as conn:
        # 创建主表
        conn.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dut_id TEXT,
            batch_id TEXT,
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

        # 检查表是否存在dut_id和batch_id列,如果不存在则添加(用于兼容旧数据库)
        cursor = conn.execute(f"PRAGMA table_info({table_name})")
        columns = [row[1] for row in cursor.fetchall()]

        if 'dut_id' not in columns:
            print(f"添加 dut_id 列到 {table_name} 表...")
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN dut_id TEXT")

        if 'batch_id' not in columns:
            print(f"添加 batch_id 列到 {table_name} 表...")
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN batch_id TEXT")

        # 创建索引以提高查询性能
        conn.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_dut_batch
        ON {table_name} (dut_id, batch_id, chn)
        """)

    print(f"Database {table_name} initialized with DUT and batch support.")

def insert_test_data(table_name="ble_test_results", dut_id=None, batch_id=None, chn=None, rate=None,
                     noise=None, signal=None, gain=None, dc=None, snr=None, image=None, imrr=None,
                     nf=None, sensitive=None):
    with sqlite3.connect(DB_FILE) as conn:
        conn.execute(f"""
        INSERT INTO {table_name}
        (dut_id, batch_id, chn, rate, noise, signal, gain, dc, snr, image, imrr, nf, sensitive, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, strftime('%Y-%m-%d %H:%M:%S', 'now', 'localtime'))
        """, (dut_id, batch_id, chn, rate, noise, signal, gain, dc, snr, image, imrr, nf, sensitive))

def query_results(table_name="ble_test_results", dut_id=None, batch_id=None, chn=None, rate=None):
    query = f"SELECT * FROM {table_name} WHERE 1=1"
    params = []
    if dut_id is not None:
        query += " AND dut_id=?"
        params.append(dut_id)
    if batch_id is not None:
        query += " AND batch_id=?"
        params.append(batch_id)
    if chn is not None:
        query += " AND chn=?"
        params.append(chn)
    if rate is not None:
        query += " AND rate=?"
        params.append(rate)
    query += " ORDER BY dut_id, batch_id, chn, rate"
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(query, params)
        return cursor.fetchall()

def get_all_dut_ids(table_name="ble_test_results"):
    """获取所有DUT编号列表"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(f"SELECT DISTINCT dut_id FROM {table_name} WHERE dut_id IS NOT NULL ORDER BY dut_id")
        return [row[0] for row in cursor.fetchall()]

def get_all_batch_ids(table_name="ble_test_results"):
    """获取所有批次编号列表"""
    with sqlite3.connect(DB_FILE) as conn:
        cursor = conn.execute(f"SELECT DISTINCT batch_id FROM {table_name} WHERE batch_id IS NOT NULL ORDER BY batch_id DESC")
        return [row[0] for row in cursor.fetchall()]
