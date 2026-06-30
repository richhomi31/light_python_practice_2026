import sqlite3
import os
from datetime import datetime
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

def compare_directories(work_dir, backup_dir, ext_filter, scan_func, hash_func):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    current_time = datetime.now().isoformat()
    sql_filter = f"%{ext_filter}" if ext_filter else "%"

    print(f"\nСравнение с бэкапом")
    print(f" Рабочая папка: {work_dir}")
    print(f" Папка бэкапа: {backup_dir}")

    # Считываем актуальные файлы рабочей папки из базы данных в словарь
    cursor.execute('''
        SELECT path, hash FROM files 
        WHERE root_path = ? AND path LIKE ?
    ''', [work_dir, sql_filter])
    
    work_files = {path: file_hash for path, file_hash in cursor.fetchall()}

    # делаем обход резервной папки
    backup_raw_files = scan_func(backup_dir, backup_dir, ext_filter)
    
    backup_files = {}
    for full_path, rel_path in backup_raw_files:
        file_hash = hash_func(full_path)
        if file_hash:
            backup_files[rel_path] = file_hash

    # массивы для отслеживания изменений и флаг о том, что папки различны
    is_different = False
    only_in_work = []
    only_in_backup = []
    modified_files = []

    # Сравниваем рабочую папку с бэкапом
    # Ищем то, что есть в рабочей, но нет в бэкапе, или то, что изменилось
    for rel_path, work_hash in work_files.items():
        # если нет в бекапе то это добавленный файл
        if rel_path not in backup_files:
            only_in_work.append(rel_path)
            # Добавление в историю проверок записи, что файл только в рабочей папке, а в бэкапе нет
            cursor.execute('''
                INSERT INTO backup_history (check_time, work_dir, backup_dir, file_path, difference_type)
                VALUES (?, ?, ?, ?, 'only_in_work')
            ''', [current_time, work_dir, backup_dir, rel_path])
        # если не совпадает хэш то это модифицированный файл
        elif work_hash != backup_files[rel_path]:
            modified_files.append(rel_path)
            # Добавление в историю проверок записи, что у файла различается содержимое
            cursor.execute('''
                INSERT INTO backup_history (check_time, work_dir, backup_dir, file_path, difference_type)
                VALUES (?, ?, ?, ?, 'modified')
            ''', [current_time, work_dir, backup_dir, rel_path])

    # есть в бэкапе, но пропало в рабочей папке
    for rel_path in backup_files:
        if rel_path not in work_files:
            only_in_backup.append(rel_path)
            # Добавление в историю проверок записи, что файл удален из рабочей
            cursor.execute('''
                INSERT INTO backup_history (check_time, work_dir, backup_dir, file_path, difference_type)
                VALUES (?, ?, ?, ?, 'only_in_backup')
            ''', [current_time, work_dir, backup_dir, rel_path])
            

    # Вывод результатов на экран
    if only_in_work:
        is_different = True
        print(f"\nОтсутствуют в бэкап папке, но есть в рабочей:")
        for p in only_in_work:
            print(f"  -> {p}")

    if only_in_backup:
        is_different = True
        print(f"Есть в бэкап папке, но нет в рабочей:")
        for p in only_in_backup:
            print(f"  -> {p}")

    if modified_files:
        is_different = True
        print(f"\nИзменено содержимое:")
        for p in modified_files:
            print(f"  -> {p}")
    #Если одинаковые
    if not is_different:
        print("\nРабочая папка идентична резервной копии.")
        # Добавление в историю проверок записи что папки идентичны
        cursor.execute('''
                INSERT INTO backup_history (check_time, work_dir, backup_dir, file_path, difference_type)
                VALUES (?, ?, ?, ?, 'equal')
            ''', [current_time, work_dir, backup_dir, None])
        
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