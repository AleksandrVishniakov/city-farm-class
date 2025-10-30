#!/usr/bin/env python3
"""
Запуск консольной версии для Raspberry Pi
"""
import sys
import os

sys.path.append(os.path.dirname(__file__))

try:
    from main import main
    print("🚀 Запуск консольной версии...")
    main()
except Exception as e:
    print(f"❌ Ошибка запуска: {e}")