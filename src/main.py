import os
import sys
from scanner_module import scan_directory, custom_scan_recursive, calculate_hash
from analyzer_module import compare_directories, find_duplicates, check_history_report

if __name__ == "__main__":
    # обработка аргументов с помощью sys через argv
    # обрезал первый аргумент, то есть название скрипта,
    # теперь по индексам 0 - рабочая папка, 1 - папка бэкапа, 2 - расширение  
    args = sys.argv[1:]

    if len(args) < 1:
        print("Ошибка: не указаны параметры запуска.")
        print("Проверка без бэкапа: python main.py <рабочая папка> [расширение]")
        print("Проверка со сравнением с бэкапом: python main.py <рабочая папка> <папка_бэкапа> [расширение]")
        sys.exit(1)

    target_dir1 = args[0]
    target_dir2 = None
    extension = None

    if len(args) == 2:
        if os.path.exists(args[1]):
            target_dir2 = args[1]
        else:
            extension = args[1]
    elif len(args) == 3:
        target_dir2 = args[1]
        extension = args[2]
    elif len(args) > 3:
        print(f"Ошибка: слишком много аргументов - {len(args)} (max 3)")
        print("Проверка без бэкапа: python main.py <рабочая папка> [расширение]")
        print("Проверка со сравнением с бэкапом: python main.py <рабочая папка> <папка_бэкапа> [расширение]")
        sys.exit(1)

    #Проверка основной папки
    if not os.path.exists(target_dir1):
        print(f"Ошибка: Рабочая папка '{target_dir1}' не найдена.")
        sys.exit(1)

    scan_directory(target_dir1, ext_filter=extension)
    norm_dir1 = os.path.normpath(target_dir1)

    if target_dir2:
        if not os.path.exists(target_dir2):
            print(f"Ошибка: Папка бэкапа '{target_dir2}' не найдена.")
            sys.exit(1)

        norm_dir2 = os.path.normpath(target_dir2)
        compare_directories(
            norm_dir1,
            norm_dir2,
            extension,
            custom_scan_recursive,
            calculate_hash
        ) 
    
    find_duplicates(norm_dir1, extension)
    check_history_report(norm_dir1, extension)