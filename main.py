
import board
try:
    import busio
except:
    print('busio er')
import RPi.GPIO as GPIO
from time import sleep
from threading import Thread
from mh_z19 import read_from_pwm
from adafruit_dht import DHT22
try:
    import adafruit_ads1x15.ads1115 as ADS
    from adafruit_ads1x15.analog_in import AnalogIn
except:
    print('err ADS')
from city_farm_class import *
from serial import Serial




def txt(name, value):
    device.write(convert_txt(name, value))


def val(name, value):
    device.write(convert_val(name, value))


def check_pin(pin):
    return int(not GPIO.input(pin)) 


def main_logic():
    while True:
        sleep(1)
        settings = read_file()
        if auto == 'on':
            if convert_time(settings['lamp_set'][0]) <= datetime.now() < convert_time(settings['lamp_set'][1]):
                GPIO.output(5, 0)
            else:
                GPIO.output(5, 1)
            watering_list = watering(convert_time(settings['lamp_set'][0]), convert_time(settings['lamp_set'][1]), settings['time_water'], settings['water_day'], settings['water_night'])
            if watering_list[0] <= datetime.now() < watering_list[1] and not block_water:
                GPIO.output(6, 0)
            else:
                GPIO.output(6, 1)

                    
def sens():
    global temp, hum, co2,block_water, ec, ph,water_value_dis
    last_temp = 0
    last_hum = 0
    last_co2 = 0
    while True:
        sleep(2)
        try:
            temp = pin.temperature
            last_temp = temp
            hum = pin.humidity
            last_hum = hum
        except:
            temp = last_temp
            hum = last_hum
        try:
            co2 = read_from_pwm()['co2']
            last_co2 = last_co2
        except:
            co2 = last_co2
        if GPIO.input(27) == 1 and GPIO.input(23) == 1:
            block_water = True
            water_value_dis = 0
        elif GPIO.input(27) == 0 and GPIO.input(23) == 0:
            block_water = True
            water_value_dis = '90'
        elif GPIO.input(27) == 1 and GPIO.input(23) == 0:
            block_water = False
            GPIO.output(6, 1)
            water_value_dis = 100
        elif GPIO.input(27) == 0 and GPIO.input(23) == 1:
            block_water = True
            water_value_dis = '50'
        try:
            ec = round(((chan_ec.voltage * 5) * 4400) / 1000 * 500 / 20,2)
        except:
            ec = "Err"
        try:
            ph = round((chan_ph.voltage * 5) * 14 / 20, 2)
        except:
            ph = "Err"
        

auto = 'off'
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    chan_ec = AnalogIn(ads, ADS.P0)
    chan_ph = AnalogIn(ads, ADS.P1)
except Exception as ex:
    print(ex)
    

try:
    ph = round((chan_ph.voltage * 5) * 14, 2)
except:
    ph = "Err"

try:
    ec = round(((chan_ec.voltage * 5) * 4400) / 1000 * 500,2)
except:
    ec = "Err"
        

lamp_state = 0
pump_state = 0

#sens
temp = 0
hum = 0
co2 = 0
ec = 0
ph = 0
water_value_dis = '0'

page='page0'

pin = DHT22(4)

#display
device = Serial('/dev/ttyS0', timeout=1)
#block
block_water = True
#settings
sets_list = []
emerg_sets_list = {
    "lamp_set": ["13:00","21:04"],
    "water_day": 6,
    "water_night": 2,
    "time_water": 7
}


Thread(target=main_logic, daemon=1).start()
Thread(target=sens, daemon=1).start()
while True:
        sleep(0.5)
        info = device.read_all().decode('koi8-r')
        print(info)
        if 'page' in info:
            page = info
            settings = read_file()
            if 'page2' in page:
                day = list(map(int,settings['lamp_set'][0].split(':')))
                night = list(map(int,settings['lamp_set'][1].split(':')))
                val('n1.val', day[0])
                val('n0.val', day[1])
                val('n2.val', night[0])
                val('n3.val', night[1])
            if 'page4' in page:
                val('n1.val', settings['water_day'])
                val('n0.val', settings['water_night'])
                val('n2.val', settings['time_water'])
            if 'page0' in page:
                val('bt2.val', 1 if auto == 'on' else 0)
            if 'page3' in page:
                val("bt1.val", check_pin(19))
                val("bt0.val", check_pin(20))
                val("bt2.val", check_pin(21))
                val("bt3.val", check_pin(26))
                

        if 'lamp_on' in info and auto == 'off':
            GPIO.output(5, 0)
        elif "lamp_off" in info and auto == 'off':
            GPIO.output(5, 1)

        if "pump_on" in info and auto == 'off':
            GPIO.output(6, 0)
        elif "pump_off" in info and auto == 'off':
            GPIO.output(6, 1)

        if "doz_1_on" in info:
            GPIO.output(19, 0)
        elif "doz_1_off" in info:
            GPIO.output(19, 1)

        if "doz_2_on" in info:
            GPIO.output(20, 0)
        elif "doz_2_off" in info:
            GPIO.output(20, 1)
        
        if "doz_3_on" in info:
            GPIO.output(21, 0)
        elif "doz_3_off" in info:
            GPIO.output(21, 1)

        if "doz_4_on" in info:
            GPIO.output(26, 0)
        elif "doz_4_off" in info:
            GPIO.output(26, 1)

        if "auto_on" in info:
            auto = 'on'
        elif "auto_off" in info:
            auto = 'off'

        if "time" in info:
            h_list = info.split('/')
            time_list = [h_list[1], h_list[2]]
            all_settings = read_file()
            all_settings['lamp_set'] = time_list
            write_file(all_settings)

        if "water" in info:
            waterings = list(map(int, info.split('/')[1].split(',')))
            setting = read_file()
            setting["time_water"] = waterings[2]
            setting["water_day"] = waterings[0]
            setting["water_night"] = waterings[1]
            write_file(setting)

        if page == "page0":
            txt('t0.txt',  datetime.now().time().strftime('%H:%M'))
            txt('t1.txt', temp)
            txt('t2.txt', hum)
            txt('t4.txt', co2)
            txt('t7.txt', ph)
            txt('t9.txt', ec)
            val('j0.val', water_value_dis)
            if auto == 'on':
                val('bt0.val', check_pin(5))
                val('bt1.val', check_pin(6))
            
