print("Hello, World from Pico!")
import machine
import time
LED = machine.Pin(20,machine.Pin.OUT)
LED.value(1)
time.sleep(1)
LED.value(0)
time.sleep(2)
LED.value(1)