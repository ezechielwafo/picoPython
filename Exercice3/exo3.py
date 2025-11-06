# ============================================================
# Thermostat multi-états MicroPython - Raspberry Pi Pico W
# LED, Buzzer, OLED Grove, Potentiomètre et DHT11
# ============================================================

from machine import Pin, ADC, PWM, I2C
import utime
import dht

# === CONFIGURATION DU MATÉRIEL ===
pot = ADC(2)                    # Potentiomètre sur GP26
led = PWM(Pin(16))              # LED PWM sur GP16 (pour dimming)
buzzer = PWM(Pin(20))           # Buzzer sur GP20
sensor = dht.DHT11(Pin(18))     # DHT11 sur GP18

# Initialisation PWM
led.freq(1000)
led.duty_u16(0)
buzzer.freq(2000)  # Fréquence audible pour le buzzer
buzzer.duty_u16(0)

# === I2C pour OLED Grove ===
i2c = I2C(1, scl=Pin(7), sda=Pin(6), freq=100000)
OLED_ADDR = 0x3E

# === CLASSE OLED Grove ===
class GroveOLED:
    def __init__(self, i2c, addr=OLED_ADDR):
        self.i2c = i2c
        self.addr = addr
        self.init_display()

    def init_display(self):
        cmds = [
            0x2A,0x71,0x5C,0x28,0x08,0x2A,0x79,0xD5,0x70,
            0x78,0x09,0x06,0x72,0x00,0x2A,0x79,0xDA,0x10,
            0xDC,0x00,0x81,0x7F,0xD9,0xF1,0xDB,0x40,0x78,
            0x28,0x01,0x80,0x0C
        ]
        for cmd in cmds:
            self.write_command(cmd)
            utime.sleep_ms(5)

    def write_command(self, cmd):
        try:
            self.i2c.writeto(self.addr, bytes([0x00, cmd]))
        except:
            pass

    def write_data(self, data):
        try:
            self.i2c.writeto(self.addr, bytes([0x40, data]))
        except:
            pass

    def clear(self):
        self.write_command(0x01)
        utime.sleep_ms(2)

    def set_cursor(self, row, col):
        addr = 0x80 if row == 0 else 0xC0
        self.write_command(addr + col)

    def print(self, text, row=0, col=0):
        self.set_cursor(row, col)
        # Complète avec des espaces pour effacer l'ancien texte
        padded = (text + " " * 16)[:16]
        for char in padded:
            self.write_data(ord(char))
            utime.sleep_ms(2)

# Initialisation OLED
oled = GroveOLED(i2c, OLED_ADDR)
oled.clear()
oled.print("Thermostat v2.0", 0, 0)
oled.print("Initialisation", 1, 0)
utime.sleep(2)

# === FONCTIONS UTILITAIRES ===
def read_set_temp():
    """Convertit la valeur du potentiomètre en température de consigne (15-35°C)."""
    raw = pot.read_u16()
    return 15 + (raw / 65535) * 20

def read_ambient_temp():
    """Lit la température du DHT11 avec gestion d'erreur."""
    try:
        sensor.measure()
        return sensor.temperature()
    except Exception as e:
        print("Erreur DHT11:", e)
        return None

# === CONTRÔLE DES ACTIONNEURS ===
def control_system(diff, state):
    """
    Contrôle LED et buzzer selon l'écart de température.
    États:
    - OK: diff < 1°C → LED allumée fixe, pas de son
    - WARN: 1°C <= diff < 3°C → LED dimming progressif, pas de son
    - ALARM: diff >= 3°C → LED clignote rapide, buzzer continu
    """
    current_time = utime.ticks_ms()
    
    if diff >= 3:
        # ALARM: LED clignote rapide + buzzer
        state['mode'] = 'ALARM'
        blink = (current_time // 200) % 2  # Blink rapide (200ms)
        led.duty_u16(65535 if blink else 0)
        buzzer.duty_u16(32768)  # Buzzer à 50% duty cycle
        return True
    
    elif diff >= 1:
        # WARN: LED dimming progressif
        state['mode'] = 'WARN'
        # Intensité proportionnelle à l'écart (1°C = faible, 3°C = max)
        intensity = int(((diff - 1) / 2) * 65535)
        led.duty_u16(min(65535, max(0, intensity)))
        buzzer.duty_u16(0)  # Pas de son
        return False
    
    else:
        # OK: LED fixe allumée
        state['mode'] = 'OK'
        led.duty_u16(65535)
        buzzer.duty_u16(0)
        return False

def update_display(set_temp, ambient_temp, diff, alarm, state):
    """Met à jour l'affichage OLED."""
    # Ligne 1: Températures
    line1 = "S:{:.1f} A:{:.1f}".format(set_temp, ambient_temp)
    
    # Ligne 2: État et différence
    if alarm:
        blink = (utime.ticks_ms() // 300) % 2
        line2 = "!ALARM! +{:.1f}C".format(diff) if blink else " " * 16
    elif state['mode'] == 'WARN':
        line2 = "WARN   +{:.1f}C".format(diff)
    else:
        line2 = "OK     {:+.1f}C".format(diff)
    
    # Mise à jour uniquement si changement
    if line1 != state.get('line1', ''):
        oled.print(line1, 0, 0)
        state['line1'] = line1
    
    if line2 != state.get('line2', ''):
        oled.print(line2, 1, 0)
        state['line2'] = line2

# === ÉTAT DU SYSTÈME ===
state = {
    'mode': 'OK',
    'line1': '',
    'line2': '',
    'last_temp_read': 0,
    'temp_read_interval': 2000  # Lire DHT11 toutes les 2 secondes
}

# === BOUCLE PRINCIPALE ===
print("\n=== THERMOSTAT DÉMARRE ===\n")
oled.clear()

ambient_temp = None
last_print = 0

while True:
    try:
        current_time = utime.ticks_ms()
        
        # Lecture du setpoint (potentiomètre) - toujours
        set_temp = read_set_temp()
        
        # Lecture température ambiante (DHT11) - toutes les 2 secondes
        if utime.ticks_diff(current_time, state['last_temp_read']) >= state['temp_read_interval']:
            new_temp = read_ambient_temp()
            if new_temp is not None:
                ambient_temp = new_temp
            state['last_temp_read'] = current_time
        
        # Si on a une température valide
        if ambient_temp is not None:
            diff = ambient_temp - set_temp
            
            # Contrôle LED et buzzer
            alarm = control_system(diff, state)
            
            # Mise à jour affichage
            update_display(set_temp, ambient_temp, diff, alarm, state)
            
            # Affichage console toutes les 3 secondes
            if utime.ticks_diff(current_time, last_print) >= 3000:
                icon = "🔴" if alarm else ("🟡" if state['mode'] == 'WARN' else "🟢")
                sound = "🔊" if alarm else "  "
                print(f"{icon} {state['mode']:5s} {sound} | Set:{set_temp:5.1f}°C | Amb:{ambient_temp:5.1f}°C | Δ:{diff:+5.1f}°C")
                last_print = current_time
        
        else:
            # Pas de température disponible
            oled.print("Attente DHT11", 0, 0)
            oled.print("Set: {:.1f}C".format(set_temp), 1, 0)
        
        # Pause adaptative selon l'état
        if state['mode'] == 'ALARM':
            utime.sleep_ms(100)  # Mise à jour rapide pour le clignotement
        else:
            utime.sleep_ms(200)
    
    except KeyboardInterrupt:
        print("\n✓ Arrêt du thermostat")
        led.duty_u16(0)
        buzzer.duty_u16(0)
        oled.clear()
        oled.print("ARRETE", 0, 5)
        break
    
    except Exception as e:
        print("Erreur système:", e)
        utime.sleep(2)