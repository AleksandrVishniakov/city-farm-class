from dataclasses import dataclass

@dataclass
class Pins:
    LAMP: int = 5
    PUMP: int = 6
    DOSER_1: int = 19
    DOSER_2: int = 20
    DOSER_3: int = 21
    DOSER_4: int = 26
    DHT: int = 4
    WATER_LOW_SENSOR: int = 23
    WATER_HIGH_SENSOR: int = 27