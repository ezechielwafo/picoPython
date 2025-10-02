import time
from machine import Pin

pin_button = Pin(18, mode=Pin.IN, pull=Pin.PULL_UP)
LED   = Pin(20, mode=Pin.OUT)


def button_isr(pin):
  LED.value(not LED.value())

pin_button.irq(trigger=Pin.IRQ_FALLING,handler=button_isr)

while True:
        val = pin_button.value()
        if val == 1:
            LED.value(1)
            time.sleep(0.5)
            LED.value(0)
            time.sleep(0.5)
            LED.value(1)
        elif val == 0 :
            LED.value(0)
            time.sleep(0.1)
            LED.value(1)
            time.sleep(0.1)
            LED.value(0)