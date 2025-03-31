import RPi.GPIO as GPIO

from time import sleep
GPIO.cleanup()

GPIO.setmode(GPIO.BCM)

relayL = 5
relayP = 6

GPIO.setup(relayL, GPIO.OUT)
GPIO.setup(relayP, GPIO.OUT)

GPIO.output(relayL, 1)
GPIO.output(relayP, 1)

print("1 - turn on lights\n2 - turn off lights\n3 - turn on pomp\n4 - turn off pomp\n0 - exit")
n = int(input())

while n!=0:
    if n == 1:
        GPIO.output(relayL, 0)
        print("Working...")
    if n==2:
        GPIO.output(relayL, 1)
        print("Silence... ");
    if n == 3:
        GPIO.output(relayP, 0)
        print("Working...")
    if n==4:
        GPIO.output(relayP, 1)
        print("Silence... ");
    n = int(input())



GPIO.cleanup()

