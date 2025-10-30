"""
Менеджер оборудования - автоматически определяет ОС и подключает соответствующие драйверы
"""
import sys
import platform


def setup_hardware():
    """Определяет ОС и возвращает соответствующие модули"""

    system = platform.system().lower()

    if system == 'windows' or system == 'darwin':  # Windows или Mac
        print("🔧 Режим эмуляции: запуск на ПК")

        # Импортируем моки
        from mock_hardware import (
            MockGPIO as GPIO,
            MockDHT22,
            MockSerial,
            MockI2C,
            MockADS1115,
            MockAnalogIn,
            mock_read_from_pwm
        )

        # Создаем мок-модули
        hardware_modules = {
            'GPIO': GPIO,
            'DHT22': MockDHT22,
            'Serial': MockSerial,
            'I2C': MockI2C,
            'ADS1115': MockADS1115,
            'AnalogIn': MockAnalogIn,
            'read_from_pwm': mock_read_from_pwm,
            'is_emulation': True
        }

    elif system == 'linux':
        # Проверяем, это Raspberry Pi или обычный Linux
        try:
            with open('/proc/device-tree/model', 'r') as f:
                if 'raspberry pi' in f.read().lower():
                    print(
                        "🍓 Режим Raspberry Pi: использование реального оборудования")

                    # Импортируем реальные библиотеки
                    import RPi.GPIO as GPIO
                    from adafruit_dht import DHT22
                    from serial import Serial
                    import busio
                    import adafruit_ads1x15.ads1115 as ADS1115
                    from adafruit_ads1x15.analog_in import AnalogIn
                    from mh_z19 import read_from_pwm

                    hardware_modules = {
                        'GPIO': GPIO,
                        'DHT22': DHT22,
                        'Serial': Serial,
                        'busio': busio,
                        'ADS1115': ADS1115,
                        'AnalogIn': AnalogIn,
                        'read_from_pwm': read_from_pwm,
                        'is_emulation': False
                    }
                else:
                    raise ImportError("Не Raspberry Pi")
        except:
            print("🐧 Обычный Linux: режим эмуляции")
            from mock_hardware import (
                MockGPIO as GPIO,
                MockDHT22,
                MockSerial,
                MockI2C,
                MockADS1115,
                MockAnalogIn,
                mock_read_from_pwm
            )

            hardware_modules = {
                'GPIO': GPIO,
                'DHT22': MockDHT22,
                'Serial': MockSerial,
                'I2C': MockI2C,
                'ADS1115': MockADS1115,
                'AnalogIn': MockAnalogIn,
                'read_from_pwm': mock_read_from_pwm,
                'is_emulation': True
            }
    else:
        print("❓ Неизвестная ОС: режим эмуляции")
        from mock_hardware import (
            MockGPIO as GPIO,
            MockDHT22,
            MockSerial,
            MockI2C,
            MockADS1115,
            MockAnalogIn,
            mock_read_from_pwm
        )

        hardware_modules = {
            'GPIO': GPIO,
            'DHT22': MockDHT22,
            'Serial': MockSerial,
            'I2C': MockI2C,
            'ADS1115': MockADS1115,
            'AnalogIn': MockAnalogIn,
            'read_from_pwm': mock_read_from_pwm,
            'is_emulation': True
        }

    return hardware_modules


# Глобальная переменная с модулями оборудования
hardware = setup_hardware()
