#!/usr/bin/env python3
"""
Запуск графического интерфейса управления гидропонной системой
"""
import sys
import os

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(__file__))

try:
    from gui_main import main
    print("🚀 Запуск графического интерфейса...")
    main()
except Exception as e:
    print(f"❌ Ошибка запуска GUI: {e}")
    print("🔧 Попробуйте запустить консольную версию: python main.py")
    input("Нажмите Enter для выхода...")