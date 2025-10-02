from machine import Pin

pin_button = Pin(18, mode=Pin.IN, pull=Pin.PULL_UP)
pin_led    = Pin(20, mode=Pin.OUT)

while True:
    if not pin_button.value():
        pin_led.on()
    else:
        pin_led.off()