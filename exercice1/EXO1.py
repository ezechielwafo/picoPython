import machine
import time
button = machine.Pin(18,machine.Pin.IN)
LED = machine.Pin(20,machine.Pin.OUT)
while True:
    val = button.value()
    a = 1
    if val == 0:
        LED.value(1)
        time.sleep(0.5)
        LED.value(0)
        time.sleep(0.5)
        LED.value(1)
    elif val == 1:
            LED.value(0)
            time.sleep(0.1)
            LED.value(1)
            time.sleep(0.1)
            LED.value(0)
    else:
        print("Goodbye, World from Pico!")
        break
       