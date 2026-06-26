import os
import hashlib
import sqlite3
from datetime import datetime
from db_module import init_db, DB_NAME
from analyzer_module import find_duplicates, check_history_report

def custom_scan_recursive(current_dir, root_path, ext_filter=None):
    found_files = []
    
    try: 
        # список всех файлов и папок из current_dir
        items = os.listdir(current_dir)
    except Exception as e:
        # если папка заблокирована 
        print(f"Нет доступа к папке {current_dir}: {e}")
        return []

    for item in items:
        #инициализируем путь для файлов и папок
        full_path = os.path.join(current_dir, item)
        #если элемент это папка, то рекурсией проваливаемся в него
        if os.path.isdir(full_path):
            found_files.extend(custom_scan_recursive(full_path, root_path, ext_filter))
        #если это файл    
        else:
            #проверка фильтром по расширению файла
            if ext_filter and not item.endswith(ext_filter):
                continue
            #закладываем в переменную путь от выбранной папки до файла, то есть
            #того что между full_path и root_path
            rel_path = os.path.relpath(full_path, root_path)
            
            found_files.append((full_path, rel_path))
            
    return found_files

def calculate_hash(file_path):
    # вычисление md5 хэша
    hasher = hashlib.md5()
    try:
        # открываем файл в виде двоичного кода и чанками по 
        # 4 кб загружаем в калькулятор хэша
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return None

def scan_directory(root_path, ext_filter=None):
    conn = init_db()
    cursor = conn.cursor()
    # isoformat чтобы преобразовать из python формата в форму типа '2026-01-01T00:00:00...'
    current_time = datetime.now().isoformat()
    #учитываем что формат ввода папки может быть разным
    norm_root = os.path.normpath(root_path)

    cursor.execute("SELECT 1 FROM history WHERE root_path = ? LIMIT 1", [norm_root])
    is_already_indexed = cursor.fetchone() is not None

    #возвращаем нашим методом все файлы из выбранной пользователем директории
    all_files = custom_scan_recursive(root_path, root_path, ext_filter)

    print(f"\nСканировение директории: {root_path}")

    #если нет файлов с выбранным расширением, то делаем выход из метода
    if not all_files:
        print(f"\nНе найдено файлов с расширением '{ext_filter}'")
        conn.close()
        return

    #проставляем всем файлам в выбранной корневой папке статус пропажи, чтобы потом его исправить, а неисправленные удалить
    cursor.execute("UPDATE files SET status = 'missing' WHERE root_path = ?", ([norm_root]))

    for full_path, rel_path in all_files:
        try:
            #В цикле по каждому элементу указываем его метаданные и расчитываем хэш
            stat = os.stat(full_path)
            size = stat.st_size
            mtime = datetime.fromtimestamp(stat.st_mtime).isoformat()
            file_hash = calculate_hash(full_path)
            
            # отслеживание изменений (превращаем в modified)
            # Проверяем, существовал ли файл ранее и изменился ли его хэш
            cursor.execute("SELECT hash FROM files WHERE path = ? AND root_path = ?", ([rel_path, norm_root]))
            old_row = cursor.fetchone()
            
            if old_row:
                old_hash = old_row[0]
                # если старый хэш существует и он не совпадает с новым то файл изменен
                if old_hash and old_hash != file_hash:
                    cursor.execute(
                        "INSERT INTO history (path, root_path, scan_time, status) VALUES (?, ?, ?, 'modified')",
                        ([rel_path, norm_root, current_time])
                    )
                
            # установка статуса created если это первый запуск по директории и added если нет
            current_status = 'added' if is_already_indexed else 'created'

            # если не был создан раннее, 
            cursor.execute("SELECT 1 FROM history WHERE path = ? AND root_path = ?", [rel_path, norm_root])
            check_if_created = cursor.fetchone()

            # то добавляем запись о его создании или добавлении
            if not check_if_created:
                cursor.execute('''
                    INSERT INTO history (path, root_path, scan_time, status)
                    VALUES (?, ?, ?, ?)
                ''', [rel_path, norm_root, current_time, current_status])
                                   
            # запись в основную таблицу
            cursor.execute('''
                INSERT INTO files (path, root_path, size, mtime, hash, status)
                VALUES (?, ?, ?, ?, ?, 'active')
                ON CONFLICT(path) DO UPDATE SET
                    root_path=excluded.root_path,
                    size=excluded.size,
                    mtime=excluded.mtime,
                    hash=excluded.hash,
                    status='active'
            ''', [rel_path, norm_root, size, mtime, file_hash])

        except Exception as e:
            print(f"Ошибка обработки файла {full_path}: {e}")

    #выбор записей из директории, где у файлов все также остался статус пропавших
    #и удаление из базы файлов, а также добавление в историю записи об их удалении
    cursor.execute("SELECT path FROM files WHERE status = 'missing' AND root_path = ?", [norm_root])
    missing_files = cursor.fetchall()
    
    for (p,) in missing_files:
        cursor.execute("INSERT INTO history (path, root_path, scan_time, status) VALUES (?, ?, ?, 'deleted')", [p, norm_root, current_time])
    
    cursor.execute("DELETE FROM files WHERE status = 'missing' AND root_path = ?", [norm_root])
    
    conn.commit()
    conn.close()
    print("Сканирование и обновление индекса завершено.")

    find_duplicates(norm_root, ext_filter)
    check_history_report(norm_root, ext_filter)