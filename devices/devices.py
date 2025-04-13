import string

import RPi.GPIO as GPIO

SIG_ON = 0
SIG_OFF = 1

class IDevice:
    def __init__(self, pin: int):
        self.__pin = pin
        self._name = f"device[{pin}]"

    def get_pin(self) -> int:
        return self.__pin

    def get_name(self) -> string:
        return self._name

    def on(self):
        GPIO.output(self.__pin, SIG_ON)

    def off(self):
        GPIO.output(self.__pin, SIG_OFF)

    def is_working(self) -> bool:
        return not GPIO.input(self.__pin)

class Lamp(IDevice):
    def __init__(self, pin: int):
        super().__init__(pin)
        self._name = f"lamp[{pin}]"

class Pump(IDevice):
    def __init__(self, pin: int):
        super().__init__(pin)
        self._name = f"pump[{pin}]"

class Doser(IDevice):
    def __init__(self, pin: int):
        super().__init__(pin)
        self._name = f"dozer[{pin}]"
