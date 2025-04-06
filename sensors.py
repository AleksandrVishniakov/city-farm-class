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
        self.__temperature = 0
        self.__humidity = 0
        self.__co2 = 0
        self.__ec = 0
        self.__ph = 0
        self.__water_value_dis = 0
        self.__block_water = True

    def set_temperature(self, temp):
        self.__temperature = temp

    def get_temperature(self):
        return self.__temperature

    def set_humidity(self, hum):
        self.__humidity = hum

    def get_humidity(self):
        return self.__humidity

    def set_co2(self, co2):
        self.__co2 = co2

    def get_co2(self):
        return self.__co2

    def set_ec(self, ec):
        self.__ec = ec

    def get_ec(self):
        return self.__ec

    def set_ph(self, ph):
        self.__ph = ph

    def get_ph(self):
        return self.__ph

    def set_water_value_dis(self, water_value_dis):
        self.__water_value_dis = water_value_dis

    def get_water_value_dis(self):
        return self.__water_value_dis

    def set_block_water(self, block_water):
        self.__block_water = block_water

    def get_block_water(self):
        return self.__block_water


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
            pump_off: callable,
    ):
        self.__state = SensorsState()
        self.__temp_sensor = temp
        self.__hum_sensor = hum
        self.__co2_sensor = co2
        self.__ec_sensor = ec
        self.__ph_sensor = ph
        self.__low_water_sensor = low_ws
        self.__high_water_sensor = high_ws
        self.__pump_off = pump_off

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

                handle_sensor(
                    self.__temp_sensor,
                    self.__state.set_temperature,
                    self.__state.get_temperature,
                )

                handle_sensor(
                    self.__hum_sensor,
                    self.__state.set_humidity,
                    self.__state.get_humidity,
                )

                handle_sensor(
                    self.__co2_sensor,
                    self.__state.set_co2,
                    self.__state.get_co2,
                )

                handle_sensor(
                    self.__ec_sensor,
                    self.__state.set_ec,
                    self.__state.get_ec,
                )

                handle_sensor(
                    self.__ph_sensor,
                    self.__state.set_ph,
                    self.__state.get_ph,
                )

                if not(self.__low_water_sensor is None or self.__high_water_sensor is None):
                    low_val = self.__low_water_sensor.read()
                    high_val = self.__high_water_sensor.read()

                    if high_val == 1 and low_val == 1:
                        self.__state.set_block_water(True)
                        self.__state.set_water_value_dis(0)
                    elif high_val == 0 and low_val == 0:
                        self.__state.set_block_water(True)
                        self.__state.set_water_value_dis(90)
                    elif high_val == 1 and low_val == 0:
                        self.__state.set_block_water(False)
                        self.__pump_off()
                        self.__state.set_water_value_dis(100)
                    elif high_val == 0 and low_val == 1:
                        self.__state.set_block_water(True)
                        self.__state.set_water_value_dis(50)

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


def handle_sensor(sens: ISensor | None, setter: callable, getter: callable):
    if not (sens is None):
        setter(read_sensor(sens, getter()))
