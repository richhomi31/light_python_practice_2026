import sqlite3
from db_module import DB_NAME

def find_duplicates(target_directory, ext_filter):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    #фильтр для проверки дубликатов с возможностью не использовать его
    sql_filter = f"%{ext_filter}" if ext_filter else "%"
    
    #поиск осуществляется группировкой по хэшу
    #и установлением условия > 1
    cursor.execute('''
        SELECT hash, COUNT(*) 
        FROM files 
        WHERE hash IS NOT NULL AND root_path = ? AND path LIKE ?
        GROUP BY hash 
        HAVING COUNT(*) > 1
    ''', [target_directory, sql_filter])
    dup_hashes = cursor.fetchall()
    
    if not dup_hashes:
        print("Дубликаты файлов не найдены.")
        conn.close()
        return

    print("\nНайденные дубликаты файлов")
    #если дубликаты найдены, то выбираем записи из файлов 
    #с повторяющимися хэшами и выводим
    for file_hash, count in dup_hashes:
        cursor.execute("SELECT path FROM files WHERE hash = ? AND root_path = ? AND path LIKE ?", 
                       [file_hash, target_directory, sql_filter])
        paths = cursor.fetchall()
        print(f"Хэш: {file_hash} (Количество копий: {count})")
        for (p,) in paths:
            print(f"  -> {p}")
    conn.close()

def check_history_report(target_directory, ext_filter):
    #Отчет об изменениях
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    sql_filter = f"%{ext_filter}" if ext_filter else "%"

    # Достаем всю историю, сортируя от самых свежих к старым
    cursor.execute("SELECT status, path, scan_time FROM history WHERE root_path = ? AND path LIKE ? ORDER BY id DESC", 
                   [target_directory, sql_filter])
    logs = cursor.fetchall()
    
    if not logs:
        print("\nИстория изменений пуста.")
        conn.close()
        return

    # Словари для группировки данных в памяти Python
    groups = {
        'created': [],
        'added': [],
        'modified': [],
        'deleted': []
    }
    
    # Распределяем записи по соответствующим группам
    for status, path, scan_time in logs:
        if status in groups:
            groups[status].append((path, scan_time))

    print("\nОтчет об изменениях")
    
    for status, items in groups.items():
        # Если в группе нет файлов то пропускаем и не выводим на экран
        if not items:
            continue
            
        total_count = len(items)
        
        print(f"\n{status} (Всего: {total_count})")
        print("-" * 50)
        
        # оставляем максимум первые 5 последних записей
        for path, scan_time in items[:5]:
            # Обрезаем миллисекунды 
            print(f"  -> [{scan_time[:19]}] {path}")
            
        # если скрытых элементов оказалось больше 5 то указываем сколько было скрыто
        if total_count > 5:
            print(f"{total_count - 5} файлов скрыто лимитом.")
            
    conn.close()
