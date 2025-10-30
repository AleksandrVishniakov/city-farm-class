import os
from datetime import datetime, time, timedelta
from json import load, dump

import RPi.GPIO as GPIO

from devices.devices import IDevice

# Глобальная переменная для переопределения датчиков
sensor_overrides = {
    'water_sensor': False
}


def set_sensor_override(sensor_type, enabled):
    """Установка переопределения датчика"""
    global sensor_overrides
    sensor_overrides[sensor_type] = enabled


def get_sensor_override(sensor_type):
    """Получение состояния переопределения датчика"""
    return sensor_overrides.get(sensor_type, False)


# Переменная для общения с дисплеем
end_byte = b'\xff\xff\xff'


def setup_devices(devices: list[IDevice], debug: bool = True):
    if debug: print("[setup]")

    for device in devices:
        GPIO.setup(device.get_pin(), 0, initial=GPIO.HIGH)
        if debug: print("  ", device.get_name(), "connected;")

    if debug: print()


def convert_time(item, hour=0):
    h = int(item.split(':')[0])
    m = int(item.split(':')[1])
    return datetime.combine(datetime.today(),
                            time(hour=h, minute=m)) + timedelta(
        hours=int(hour))


last_settings = None


def read_file(path_to_file='settings.json'):
    global last_settings
    if os.path.exists('settings.json'):
        with open(path_to_file, 'r') as f:
            data = load(f)
        if data != last_settings:
            print_settings(data)
            last_settings = data
        return data
    else:
        write_file({
            "lamp_set": [
                "07:00",
                "21:00"
            ],
            "water_day": 1,
            "water_night": 0,
            "time_water": 2
        })


def write_file(_list, path_to_file='settings.json'):
    with open(path_to_file, 'w') as f:
        dump(_list, f, indent=4)


def watering(start: datetime, end: datetime, time_watering: int,
             watering_day: int, watering_night: int):
    now = datetime.now()
    daytime = end - start
    night = timedelta(hours=24) - daytime
    interval_day = daytime / watering_day if watering_day > 0 else timedelta()
    interval_night = night / watering_night if watering_night > 0 else timedelta()
    all_events = []
    for days in [0, 1]:
        for i in range(watering_day):
            event_start = (start + timedelta(days=days)) + interval_day * (
                        i + 0.5)
            event_end = event_start + timedelta(minutes=time_watering)
            all_events.append((event_start, event_end))
    for days in [0, 1]:
        for i in range(watering_night):
            event_start = (end + timedelta(days=days)) + interval_night * (
                        i + 0.5)
            event_end = event_start + timedelta(minutes=time_watering)
            all_events.append((event_start, event_end))
    all_events.sort(key=lambda x: x[0])
    for event in all_events:
        if event[1] < now: continue
        return event

    return None


def convert_val(name, value):
    name = str(name).encode()
    value = str(value).encode()
    return name + b'=' + value + end_byte


def convert_txt(name, value):
    name = str(name).encode()
    value = str(value).encode()
    return name + b'=' + b'"' + value + b'"' + end_byte


def print_settings(settings):
    print("Settings:")
    print("  ", "lamp_set:",
          f"{settings['lamp_set'][0]} — {settings['lamp_set'][1]}")
    print("  ", "water_day", settings['water_day'])
    print("  ", "water_night", settings['water_night'])
    print("  ", "time_water", settings['time_water'])
    print()
