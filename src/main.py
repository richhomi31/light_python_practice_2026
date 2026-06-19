import os
import sys
from scanner_module import scan_directory

if __name__ == "__main__":
    # обработка аргументов с помощью sys через argv, 
    # где 0 - скрипт, 1 - путь к папке, 2 - фильтр (если переден)
    if len(sys.argv) < 2:
        print("Не указан путь к папке.")
        sys.exit(1)
    
    target_dir = sys.argv[1]

    extension = sys.argv[2] if len(sys.argv) > 2 else None

    if os.path.exists(target_dir):
        scan_directory(target_dir, ext_filter=extension)
    