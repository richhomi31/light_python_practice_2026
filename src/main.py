import os
import sys
from scanner_module import scan_directory, custom_scan_recursive, calculate_hash
from analyzer_module import compare_directories

if __name__ == "__main__":
    # обработка аргументов с помощью sys через argv, 
    # где 0 - скрипт, 1 - путь к папке, 2 - бэкап, 3 - фильтр (если переден)
    if len(sys.argv) < 3:
        if len(sys.argv) < 2:
            print("Не указан путь к основной папке.\n")
        print("Не указан путь к папке бэкапа.")
        sys.exit(1)

    target_dir1 = sys.argv[1]
    target_dir2 = sys.argv[2]
    extension = sys.argv[3] if len(sys.argv) == 4 else None

    if os.path.exists(target_dir1):
        if os.path.exists(target_dir2):
            scan_directory(target_dir1, ext_filter=extension)

            norm_dir1 = os.path.normpath(target_dir1)
            norm_dir2 = os.path.normpath(target_dir2)

            compare_directories(
                norm_dir1,
                norm_dir2,
                extension,
                custom_scan_recursive,
                calculate_hash
            )
        else:
            print("\nНе найдена папка бэкапа.")
    else:
        print("\nНе найдена основная папка.")

    