import machine
import time
button = machine.Pin(18,machine.Pin.IN)
LED = machine.Pin(20,machine.Pin.OUT)
while True:
    val = button.value()
    if val == 0:
        LED.value(1)
        time.sleep(0.5)
        LED.value(0)
        time.sleep(0.5)
        LED.value(1)
        a = 1
        print("voici A:",a)
    elif val == 1 and a==1 :
          
            LED.value(0)
            time.sleep(0.1)
            LED.value(1)
            time.sleep(0.1)
            LED.value(0)
            b = 2
            print("voici B:",b)
    elif b == 2 and a== 1 and val ==1:
        print("Goodbye, World from Pico!")
        break
       