#!/usr/bin/env python3
import sys
import os
import subprocess


def check_dependencies():
    """Проверка и установка зависимостей"""
    try:
        from PyQt6 import QtWidgets
    except ImportError:
        print("Установка PyQt6...")
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "PyQt6"])

    # Проверка других зависимостей
    dependencies = [
        'RPi.GPIO',
        'adafruit-circuitpython-dht',
        'adafruit-circuitpython-ads1x15'
    ]

    for dep in dependencies:
        try:
            __import__(dep.replace('-', '_'))
        except ImportError:
            print(f"Установка {dep}...")
            subprocess.check_call(
                [sys.executable, "-m", "pip", "install", dep])


def main():
    # Проверка зависимостей
    check_dependencies()

    # Запуск GUI
    from gui_main import main as gui_main
    gui_main()


if __name__ == '__main__':
    main()
