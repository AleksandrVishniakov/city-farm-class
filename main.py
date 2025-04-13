import board
from config.config import Pins
import busio
import RPi.GPIO as GPIO
from mh_z19 import read_from_pwm
from adafruit_dht import DHT22
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from city_farm_class import *
from serial import Serial
from devices.devices import Lamp, Pump, Doser
from devices.sensors import *

auto_mode = False

# Devices setup
GPIO.setmode(GPIO.BCM)
lamp = Lamp(Pins.LAMP)
pump = Pump(Pins.PUMP)
doz_1 = Doser(Pins.DOSER_1)
doz_2 = Doser(Pins.DOSER_2)
doz_3 = Doser(Pins.DOSER_3)
doz_4 = Doser(Pins.DOSER_4)
setup_devices([lamp, pump, doz_1, doz_2, doz_3, doz_4])

# Sensors setup
dht_wrapper = DHTSensorWrapper(pin=Pins.DHT)
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)

# Water sensors setup
GPIO.setup(Pins.WATER_LOW_SENSOR, 1, pull_up_down=GPIO.PUD_UP)
GPIO.setup(Pins.WATER_HIGH_SENSOR, 1, pull_up_down=GPIO.PUD_UP)
low_water_sensor = WaterSensor(Pins.WATER_LOW_SENSOR)
high_water_sensor = WaterSensor(Pins.WATER_HIGH_SENSOR)

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
)
sensors.start(interval=2)
sensors_state = sensors.get_state()

# Initialize display
device = Serial('/dev/ttyS0', timeout=1)


def txt(name, value):
    device.write(convert_txt(name, value))


def val(name, value):
    device.write(convert_val(name, value))


@sensors_state.subscribe("on_change:water_value_dis")
def handle_water_value_dis_change(value):
    if value == 100: pump.off()


def auto():
    while True:
        sleep(1)
        if not auto_mode: continue
        state = sensors_state
        settings = read_file()
        if convert_time(settings['lamp_set'][0]) <= datetime.now() < convert_time(settings['lamp_set'][1]):
            lamp.on()
        else:
            lamp.off()

        watering_list = watering(convert_time(settings['lamp_set'][0]), convert_time(settings['lamp_set'][1]),
                                 settings['time_water'], settings['water_day'], settings['water_night'])
        if watering_list[0] <= datetime.now() < watering_list[1] and not state.block_water:
            pump.on()
        else:
            pump.off()


def main():
    global auto_mode
    print("Start main")
    while True:
        sleep(0.01)
        info = device.read_all().decode('koi8-r')
        if len(info) > 0: print(info)
        if 'page' in info:
            handle_page(info)

        if not auto_mode:
            if 'lamp_on' in info:
                lamp.on()
            elif "lamp_off" in info:
                lamp.off()

            if "pump_on" in info:
                pump.on()
            elif "pump_off" in info:
                pump.off()

        if "doz_1_on" in info:
            doz_1.on()
        elif "doz_1_off" in info:
            doz_1.off()

        if "doz_2_on" in info:
            doz_2.on()
        elif "doz_2_off" in info:
            doz_2.off()

        if "doz_3_on" in info:
            doz_3.on()
        elif "doz_3_off" in info:
            doz_3.on()

        if "doz_4_on" in info:
            doz_4.on()
        elif "doz_4_off" in info:
            doz_4.off()

        if "auto_on" in info:
            auto_mode = True
        elif "auto_off" in info:
            auto_mode = False

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


def handle_page(page):
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
        txt('t0.txt', datetime.now().time().strftime('%H:%M'))
        txt('t1.txt', sensors_state.temperature)
        txt('t2.txt', sensors_state.temperature)
        txt('t4.txt', sensors_state.co2)
        txt('t7.txt', sensors_state.ph)
        txt('t9.txt', sensors_state.ec)
        val('j0.val', sensors_state.water_value_dis)
        val('bt2.val', int(auto_mode))
        if auto_mode:
            val('bt0.val', int(lamp.is_working()))
            val('bt1.val', int(pump.is_working()))
    if 'page3' in page:
        val("bt1.val", int(doz_1.is_working()))
        val("bt0.val", int(doz_2.is_working()))
        val("bt2.val", int(doz_3.is_working()))
        val("bt3.val", int(doz_4.is_working()))


Thread(
    target=main,
    daemon=True
).start()

Thread(
    target=auto,
    daemon=True
).start()

while True: pass
