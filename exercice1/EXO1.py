import machine
import time
button = machine.Pin(18,machine.Pin.IN)
LED = machine.Pin(20,machine.Pin.OUT)
def toggle_led(pin):
    LED.toggle()
while True:
    val = button.value()
    if val == 1:
        LED.value(1)
        time.sleep(0.5)
        LED.value(0)
        time.sleep(0.5)
        LED.value(1)
    elif val==0:
        print("Goodbye, World from Pico!")
   