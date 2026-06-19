import sqlite3

DB_NAME = "practice_index.db"

#создание конекта с базой и таблиц в ней если они не существуют
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    #хранение индексов файлов

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            path TEXT PRIMARY KEY,
            root_path TEXT,
            size INTEGER,
            mtime TEXT,
            hash TEXT,
            status TEXT DEFAULT 'active'
        )
    ''')
    
    #история запусков и резервов

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT,
            root_path TEXT,
            scan_time TEXT,
            status TEXT DEFAULT 'created'
        )
    ''')
    conn.commit()
    return conn