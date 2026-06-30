import sqlite3

DB_NAME = "practice_index.db"

#создание конекта с базой и таблиц в ней если они не существуют
def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    #хранение индексов файлов

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS files (
            path TEXT,
            root_path TEXT,
            size INTEGER,
            mtime TEXT,
            hash TEXT,
            status TEXT DEFAULT 'active',
            PRIMARY KEY (root_path, path)
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

    #!!история сравнений с бэкапом

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS backup_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_time TEXT,
            work_dir TEXT,
            backup_dir TEXT,
            file_path TEXT,
            difference_type TEXT
        )
    ''')

    conn.commit()
    return conn