import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BCM)

GPIO.setup(26, GPIO.OUT)
GPIO.setup(16, GPIO.OUT)

try:
    while True:
        GPIO.output(26, GPIO.HIGH)
        GPIO.output(16, GPIO.HIGH)
        time.sleep(1)

        GPIO.output(16, GPIO.LOW)
        time.sleep(1)
except:
    GPIO.cleanup()