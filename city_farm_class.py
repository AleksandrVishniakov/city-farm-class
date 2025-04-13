from json import load, dump
from datetime import datetime, time, timedelta
import RPi.GPIO as GPIO
import os

from devices import IDevice

# Переменная для общения с дисплеем
end_byte = b'\xff\xff\xff'

def setup_devices(devices: list[IDevice], debug: bool = True):
    if debug: print("[setup]")

    for device in devices:
        GPIO.setup(device.get_pin(), 0, initial=GPIO.HIGH)
        if debug: print(">>", device.get_name(), "connected;")

    if debug: print()


def convert_time(item, hour=0):
    h = int(item.split(':')[0])
    m = int(item.split(':')[1])
    return datetime.combine(datetime.today(), time(hour=h, minute=m)) + timedelta(hours=int(hour))

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
            "lamp_set": ["13:00", "21:04"],
            "water_day": 6,
            "water_night": 2,
            "time_water": 7
        })


def write_file(_list, path_to_file='settings.json'):
    if os.path.exists('settings.json'):
        with open(path_to_file, 'w') as f:
            dump(_list, f, indent=4)
    else:
        write_file({
            "lamp_set": ["13:00", "21:04"],
            "water_day": 6,
            "water_night": 2,
            "time_water": 7
        })


def watering(start, end, time_watering, watering_day, watering_night):
    day = timedelta(hours=23, minutes=59) - timedelta(hours=start.hour, minutes=start.minute)
    night = timedelta(hours=23, minutes=59) - day
    time_watering = time_watering
    interval_day = day / int(watering_day)
    interval_night = night / int(watering_night)
    watering_list = []
    for i in range(int(watering_day)):
        time_s = start + interval_day * i
        time_e = time_s + timedelta(minutes=int(time_watering))
        watering_list.append([time_s, time_e])
    for i in range(int(watering_night)):
        time_s = end + interval_night * i
        time_e = time_s + timedelta(minutes=int(time_watering))
        watering_list.append([time_s, time_e])
    for i in watering_list:
        if i[0] > datetime.now():
            return i


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
    print(">>", "lamp_set:", f"{settings['lamp_set'][0]} — {settings['lamp_set'][1]}")
    print(">>", "water_day", settings['water_day'])
    print(">>", "water_night", settings['water_night'])
    print(">>", "time_water", settings['time_water'])
    print()

