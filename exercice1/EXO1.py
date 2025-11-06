import machine
import time
from machine import Pin

# Configuration des broches
button = Pin(18, Pin.IN, Pin.PULL_UP)
led = Pin(20, Pin.OUT)

# Variables globales
state = 0   # 0 = éteinte, 1 = clignote lentement, 2 = clignote vite
last_press = 0

def button_isr(pin):
    global state, last_press
    current_time = time.ticks_ms()
    # Anti-rebond : ignorer si appui trop rapproché (<300 ms)
    if time.ticks_diff(current_time, last_press) > 300:
        state = (state + 1) % 3  # Alterne entre 0, 1 et 2
        print("État :", state)
        last_press = current_time

# Attacher l’interruption sur front descendant (bouton pressé)
button.irq(trigger=Pin.IRQ_FALLING, handler=button_isr)

while True:
    if state == 0:
        led.value(0)  # LED éteinte
    elif state == 1:
        led.value(1)
        time.sleep(0.5)
        led.value(0)
        time.sleep(0.5)
    elif state == 2:
        led.value(1)
        time.sleep(0.1)
        led.value(0)
        time.sleep(0.1)

       