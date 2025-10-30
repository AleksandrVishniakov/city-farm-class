import string
from time import sleep
from threading import Thread

import busio
from mh_z19 import read_from_pwm
from adafruit_dht import DHT22
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import RPi.GPIO as GPIO


class SensorsState:
    def __init__(self):
        self._temperature = 0
        self._humidity = 0
        self._co2 = 0
        self._ec = 0
        self._ph = 0
        self._water_value_dis = 0
        self._block_water = True
        self._subscribers = {}

    def subscribe(self, event):
        def decorator(callback):
            if event not in self._subscribers:
                self._subscribers[event] = []
            self._subscribers[event].append(callback)
            return callback

        return decorator

    def _notify(self, event, value):
        if event in self._subscribers:
            for callback in self._subscribers[event]:
                callback(value)

    @property
    def temperature(self):
        return self._temperature

    @temperature.setter
    def temperature(self, value):
        if self._temperature != value:
            self._temperature = value
            self._notify("on_change:temperature", value)

    @property
    def humidity(self):
        return self._humidity

    @humidity.setter
    def humidity(self, value):
        if self._humidity != value:
            self._humidity = value
            self._notify("on_change:humidity", value)

    @property
    def co2(self):
        return self._co2

    @co2.setter
    def co2(self, value):
        if self._co2 != value:
            self._co2 = value
            self._notify("on_change:co2", value)

    @property
    def ec(self):
        return self._ec

    @ec.setter
    def ec(self, value):
        if self._ec != value:
            self._ec = value
            self._notify("on_change:ec", value)

    @property
    def ph(self):
        return self._ph

    @ph.setter
    def ph(self, value):
        if self._ph != value:
            self._ph = value
            self._notify("on_change:ph", value)

    @property
    def water_value_dis(self):
        return self._water_value_dis

    @water_value_dis.setter
    def water_value_dis(self, value):
        if self._water_value_dis != value:
            self._water_value_dis = value
            self._notify("on_change:water_value_dis", value)

    @property
    def block_water(self):
        return self._block_water

    @block_water.setter
    def block_water(self, value):
        if self._block_water != value:
            self._block_water = value
            self._notify("on_change:block_water", value)


class ISensor:
    def __init__(self):
        self._name = "undefined sensor"

    def get_name(self) -> string:
        return self._name

    def read(self):
        pass


class DHTSensorWrapper:
    def __init__(self, pin: int = 4):
        self.__sensor = DHT22(pin)

    def read_temperature(self):
        return self.__sensor.temperature

    def read_humidity(self):
        return self.__sensor.humidity


class TemperatureSensor(ISensor):
    def __init__(self, dht_sensor: DHTSensorWrapper):
        super().__init__()
        self._name = "temperature sensor"
        self.__dht = dht_sensor

    def read(self):
        return self.__dht.read_temperature()


class HumiditySensor(ISensor):
    def __init__(self, dht_sensor: DHTSensorWrapper):
        super().__init__()
        self._name = "humidity sensor"
        self.__dht = dht_sensor

    def read(self):
        return self.__dht.read_humidity()


class CO2Sensor(ISensor):
    def __init__(self):
        super().__init__()
        self._name = "co2 sensor"

    def read(self):
        return read_from_pwm()['co2']


class PHSensor(ISensor):
    def __init__(self, ads: ADS.ADS1115):
        super().__init__()
        self._name = "ph sensor"
        self.__chan_ph = AnalogIn(ads, ADS.P1)

    def read(self):
        return round((self.__chan_ph.voltage * 5) * 14 / 20, 2)


class ECSensor(ISensor):
    def __init__(self, ads: ADS.ADS1115):
        super().__init__()
        self._name = "ec sensor"
        self.__chan_ec = AnalogIn(ads, ADS.P0)

    def read(self):
        return round(((self.__chan_ec.voltage * 5) * 4400) / 1000 * 500 / 20, 2)


class WaterSensor(ISensor):
    def __init__(self, pin: int):
        super().__init__()
        self._name = f"water sensor[{pin}]"
        self.__pin = pin

    def read(self):
        return GPIO.input(self.__pin)


class SensorsLifecycle:
    def __init__(
            self,
            temp: TemperatureSensor | None,
            hum: HumiditySensor | None,
            co2: CO2Sensor | None,
            ec: ECSensor | None,
            ph: PHSensor | None,
            low_ws: WaterSensor | None,
            high_ws: WaterSensor | None,
    ):
        self.__state = SensorsState()
        self.__temp_sensor = temp
        self.__hum_sensor = hum
        self.__co2_sensor = co2
        self.__ec_sensor = ec
        self.__ph_sensor = ph
        self.__low_water_sensor = low_ws
        self.__high_water_sensor = high_ws

    def get_state(self) -> SensorsState:
        return self.__state

    def start(self, interval: int = 2):
        print("Start listening sensors...\n")
        Thread(
            target=self.__get_listener(interval),
            daemon=True
        ).start()

    def __get_listener(self, interval: int) -> callable:
        def listen():
            while True:
                sleep(interval)

                self.__state.temperature = handle_sensor(self.__temp_sensor, self.__state.temperature)
                self.__state.humidity = handle_sensor(self.__hum_sensor, self.__state.humidity)
                self.__state.co2 = handle_sensor(self.__co2_sensor, self.__state.co2)
                self.__state.ec = handle_sensor(self.__ec_sensor, self.__state.ec)
                self.__state.ph = handle_sensor(self.__ph_sensor, self.__state.ph)

                if not (self.__low_water_sensor is None or self.__high_water_sensor is None):
                    low_val = self.__low_water_sensor.read()
                    high_val = self.__high_water_sensor.read()

                    if high_val == 1 and low_val == 1:
                        self.__state.block_water = True
                        self.__state.water_value_dis = 0
                    elif high_val == 0 and low_val == 0:
                        self.__state.block_water = True
                        self.__state.water_value_dis = 90
                    elif high_val == 1 and low_val == 0:
                        self.__state.block_water = False
                        self.__state.water_value_dis = 100
                    elif high_val == 0 and low_val == 1:
                        self.__state.block_water = True
                        self.__state.water_value_dis = 50

        return listen


def read_sensor(sens: ISensor, alt_value):
    try:
        return sens.read()
    except Exception as ex:
        print(
            f"Error occurred on {sens.get_name()}",
            ex, sep="\n"
        )
        return alt_value


def handle_sensor(sens: ISensor | None, alt):
    if not (sens is None):
        return read_sensor(sens, alt)
    return None
