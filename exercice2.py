from machine import Pin,PWM,ADC
pot = ADC(1)

from utime import sleep_ms

# fréquence en Hz des notes utiles
NOTE_G4 = 392
NOTE_A4 = 440
NOTE_B4 = 494
NOTE_C5 = 523
NOTE_D5 = 587
NOTE_E5 = 659
NOTE_F5 = 698
NOTE_G5 = 784

# les notes (hauteur et durée) de la mélodie à jouer
melodie = [ [NOTE_G4,1], [NOTE_G4,2], [NOTE_G4,1], [NOTE_C5,3],
    [NOTE_C5,3], [NOTE_D5,3], [NOTE_D5,3], [NOTE_G5,5], 
    [NOTE_E5,1], [NOTE_C5,2], [NOTE_C5,1], [NOTE_E5,2],
    [NOTE_C5,1], [NOTE_A4,3], [NOTE_F5,6], [NOTE_D5,2],
    [NOTE_B4,1], [NOTE_C5,4] ]    

pwm = PWM(Pin(18,Pin.OUT))

while True:
    print(pot.read_u16() )  
    for i in melodie:
        if pot.read_u16() ==944:
            duree = (i[1] * 200) - 50;  # durée de la note, en milliseconde
            pwm.freq(i[0])  # réglage de la fréquence (hauteur de la note)
            pwm.duty_u16(32512) # rapport cyclique 50% (production d'un son)
            sleep_ms(int(duree))  # on attend la durée requise
            pwm.duty_u16(0) # rapport cyclique nul (silence)
            sleep_ms(50) # silence pendant 50 ms (pour bien séparer les notes)
        elif pot.read_u16() >944 and pot.read_u16()<960:
            duree = (i[1] * 200) - 50;  # durée de la note, en milliseconde
            pwm.freq(i[0])  # réglage de la fréquence (hauteur de la note)
            pwm.duty_u16(32512) # rapport cyclique 50% (production d'un son)
            sleep_ms(int(duree))  # on attend la durée requise
            pwm.duty_u16(0) # rapport cyclique nul (silence)
            sleep_ms(50) # silence pendant 50 ms (pour bien séparer les notes)