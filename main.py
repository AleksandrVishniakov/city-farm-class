from typing import Any

import board

try:
    import busio
except:
    print('busio er')
import RPi.GPIO as GPIO
from mh_z19 import read_from_pwm
from adafruit_dht import DHT22

try:
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
except:
    print('err ADS')
from city_farm_class import *

from serial import Serial
from devices import Lamp, Pump, Dozer
from auto import AutoLifecycle
from sensors import *

# Devices setup
lamp = Lamp(5)
pump = Pump(6)
dozers = [
    None,
    Dozer(19),
    Dozer(20),
    Dozer(21),
    Dozer(26),
]
setup_devices([lamp, pump, dozers[1], dozers[2], dozers[3], dozers[4]])

# Sensors setup
dht_wrapper = DHTSensorWrapper(pin=4)
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

# Water sensors setup
GPIO.setup(23, 1, pull_up_down=GPIO.PUD_UP)
GPIO.setup(27, 1, pull_up_down=GPIO.PUD_UP)
low_water_sensor = WaterSensor(23)
high_water_sensor = WaterSensor(27)

temp_sensor = TemperatureSensor(dht_wrapper)
hum_sensor = HumiditySensor(dht_wrapper)
co2_sensor = CO2Sensor()
ph_sensor = PHSensor(ads)
ec_sensor = ECSensor(ads)
sensors = SensorsLifecycle(
    temp=temp_sensor,
    hum=hum_sensor,
    co2=co2_sensor,
    ph=ph_sensor,
    ec=ec_sensor,
    low_ws=low_water_sensor,
    high_ws=high_water_sensor,
    pump_off=pump.off,
)
sensors.start(interval=2)


def auto_handler(settings: Any, state: SensorsState):
    if convert_time(settings['lamp_set'][0]) <= datetime.now() < convert_time(settings['lamp_set'][1]):
        lamp.on()
    else:
        lamp.off()

    watering_list = watering(convert_time(settings['lamp_set'][0]), convert_time(settings['lamp_set'][1]),
                             settings['time_water'], settings['water_day'], settings['water_night'])
    if watering_list[0] <= datetime.now() < watering_list[1] and not state.get_block_water():
        pump.on()
    else:
        pump.off()


# Configure auto mode
auto_mode = AutoLifecycle(
    get_state=sensors.get_state,
    get_settings=read_file,
    handler=auto_handler
)
auto_mode.start(interval=1)

# Initialize display
device = Serial('/dev/ttyS0', timeout=1)


def txt(name, value):
    device.write(convert_txt(name, value))


def val(name, value):
    device.write(convert_val(name, value))


def main():
    print("Start main")
    page = 'page0'
    while True:
        sleep(0.1)
        info = device.read_all().decode('koi8-r')
        if len(info) > 0: print(info)
        if 'page' in info:
            page = info
            settings = read_file()
            if 'page2' in page:
                day = list(map(int, settings['lamp_set'][0].split(':')))
                night = list(map(int, settings['lamp_set'][1].split(':')))
                val('n1.val', day[0])
                val('n0.val', day[1])
                val('n2.val', night[0])
                val('n3.val', night[1])
            if 'page4' in page:
                val('n1.val', settings['water_day'])
                val('n0.val', settings['water_night'])
                val('n2.val', settings['time_water'])
            if 'page0' in page:
                val('bt2.val', int(auto_mode.active))
            if 'page3' in page:
                val("bt1.val", int(dozers[1].is_working()))
                val("bt0.val", int(dozers[2].is_working()))
                val("bt2.val", int(dozers[3].is_working()))
                val("bt3.val", int(dozers[4].is_working()))

        if not auto_mode.active:
            if 'lamp_on' in info:
                lamp.on()
            elif "lamp_off" in info:
                lamp.off()

            if "pump_on" in info:
                pump.on()
            elif "pump_off" in info:
                pump.off()

        if "doz_1_on" in info:
            dozers[1].on()
        elif "doz_1_off" in info:
            dozers[1].off()

        if "doz_2_on" in info:
            dozers[2].on()
        elif "doz_2_off" in info:
            dozers[2].off()

        if "doz_3_on" in info:
            dozers[3].on()
        elif "doz_3_off" in info:
            dozers[3].on()

        if "doz_4_on" in info:
            dozers[4].on()
        elif "doz_4_off" in info:
            dozers[4].off()

        if "auto_on" in info:
            auto_mode.set_active(True)
        elif "auto_off" in info:
            auto_mode.set_active(False)

        if "time" in info:
            h_list = info.split('/')
            time_list = [h_list[1], h_list[2]]
            settings = read_file()
            settings['lamp_set'] = time_list
            write_file(settings)

        if "water" in info:
            waterings = list(map(int, info.split('/')[1].split(',')))
            setting = read_file()
            setting["time_water"] = waterings[2]
            setting["water_day"] = waterings[0]
            setting["water_night"] = waterings[1]
            write_file(setting)

        if page == "page0":
            state = sensors.get_state()
            txt('t0.txt', datetime.now().time().strftime('%H:%M'))
            txt('t1.txt', state.get_temperature())
            txt('t2.txt', state.get_temperature())
            txt('t4.txt', state.get_co2())
            txt('t7.txt', state.get_ph())
            txt('t9.txt', state.get_ec())
            val('j0.val', state.get_water_value_dis())
            if auto_mode.active:
                val('bt0.val', int(lamp.is_working()))
                val('bt1.val', int(pump.is_working()))


Thread(
    target=main,
    daemon=True
).start()

while True: pass
