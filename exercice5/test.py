"""
Objectif : Horloge pilotée par Servo Moteur, récupérant l'heure via Internet (NTP).
Étapes : 1. Connexion WiFi/NTP. 2. Calcul d'angle. 3. Contrôle Servo.
Bonus : Gestion du Fuseau Horaire (clic simple) et mode 24H (double clic).
"""
import network
import utime
from machine import Pin, PWM
import ntptime

# ==================== CONFIGURATION INTERNET ET MATÉRIEL ====================

# 1. Connexion à Internet (Étape 1, partie 1)
# REMPLACEZ VOTRE_SSID ET VOTRE_MOT_DE_PASSE
WIFI_SSID = "Pixel_4887"
WIFI_PASSWORD = "" # <--- REMPLACEZ PAR VOTRE MOT DE PASSE REEL

# Configuration du Servo (Étape 3)
SERVO_PIN = 16 # Utilisation de GPIO 16 (D16)
PWM_FREQ = 50
DUTY_MIN = 1500  # Correspond à 0°
DUTY_MAX = 7500  # Correspond à 180°

# Configuration du Bouton (Bonus 1 & 2)
BUTTON_PIN = 18 # Utilisation de GPIO 18 (D18)
# Configuration Pull-Up : la broche sera HIGH au repos, LOW quand pressée
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# ==================== VARIABLES DE SYNCHRONISATION ET ÉTAT ====================

# Décalages horaires en heures (exemple : UTC, UTC+1, UTC-5, etc.)
TIMEZONES = [0, 1, 2, -5, 5, 8]
current_tz_index = 1 # Démarre sur UTC+1 (Index 1)

is_24h_mode = False

# Temps de référence pour la détection de clic
last_button_press_time = 0
last_button_release_time = 0
double_click_timeout = 300 # ms pour la détection du double clic

# ==================== FONCTIONS DE GESTION DU RÉSEAU ====================

def connect_wifi(ssid, password):
    """Branche le Raspberry Pi Pico W au réseau Wi-Fi."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.connect(ssid, password)

    print(f"Tentative de connexion à {ssid}...")
    max_wait = 10
    while max_wait > 0:
        if wlan.status() < 0 or wlan.status() >= 3:
            break
        max_wait -= 1
        print('.', end='')
        utime.sleep(1)

    if wlan.status() != 3:
        raise RuntimeError("La connexion Wi-Fi a échoué.")
    else:
        status = wlan.ifconfig()
        print(f"\nConnecté. Adresse IP: {status[0]}")

def sync_ntp_time(tz_offset):
    """Récupère l'heure actuelle via NTP."""
    try:
        ntptime.settime()
        print(f"Heure synchronisée (UTC). Décalage TZ: {tz_offset}h")
    except Exception as e:
        print(f"Erreur de synchronisation NTP: {e}")

# ==================== FONCTIONS DE CONTRÔLE ET CALCUL D'ANGLE ====================

def map_angle_to_duty(angle):
    """Mappe un angle de 0-180 degrés au cycle PWM (DUTY_MIN à DUTY_MAX)."""
    return int((angle / 180) * (DUTY_MAX - DUTY_MIN) + DUTY_MIN)

def set_servo_angle(pwm, angle):
    """Règle l'angle du servo moteur."""
    duty = map_angle_to_duty(angle)
    pwm.duty_u16(duty)

def get_local_time(tz_offset):
    """Calcule l'heure locale en appliquant le décalage TZ."""
    current_utc_time_tuple = utime.localtime()
    current_utc_seconds = utime.mktime(current_utc_time_tuple)
    local_time_seconds = current_utc_seconds + (tz_offset * 3600)
    return utime.localtime(local_time_seconds)

def calculate_angle_12h(h_tz, m):
    """Calcul de l'angle pour un cadran de 12 heures (0° à 180°)."""
    h_display = h_tz % 12
    if h_display == 0:
        h_display = 12
    total_hours = h_display + (m / 60)
    angle = (total_hours % 12) * 15 # 15 degrés/heure
    return min(max(0, angle), 180) 

def calculate_angle_24h(h_tz, m):
    """Calcul de l'angle pour un cadran de 24 heures (0° à 180°)."""
    total_hours = h_tz + (m / 60)
    angle = total_hours * 7.5 # 7.5 degrés/heure
    return min(max(0, angle), 180) 

def update_servo_angle(servo_pwm, tz_offset):
    """Calcule l'angle et met à jour le servo (Mise à jour immédiate)."""
    global is_24h_mode

    local_time = get_local_time(tz_offset)
    h_local = local_time[3]
    m_local = local_time[4]
    s_local = local_time[5]

    if is_24h_mode:
        angle = calculate_angle_24h(h_local, m_local)
        mode_str = "24H"
    else:
        angle = calculate_angle_12h(h_local, m_local)
        mode_str = "12H"
        
    set_servo_angle(servo_pwm, angle)
    
    print(f"Heure Locale: {h_local:02d}:{m_local:02d}:{s_local:02d} | TZ: {tz_offset:+}h | Mode: {mode_str} | Angle: {angle:.1f}°")


# ==================== FONCTIONS DE GESTION DU BOUTON ====================

def handle_button_press(servo_pwm):
    """Gère les clics simples (TZ) et doubles clics (24h) du bouton (GPIO 18)."""
    global current_tz_index, is_24h_mode, last_button_press_time, last_button_release_time
    
    current_time = utime.ticks_ms()
    
    # Détection de l'appui (bouton LOW - PULL_UP)
    if button.value() == 0:
        if utime.ticks_diff(current_time, last_button_press_time) > 50 and last_button_press_time == 0:
             last_button_press_time = current_time
        return

    # Détection du relâchement (bouton HIGH)
    if button.value() == 1 and last_button_press_time > 0:
        press_duration = utime.ticks_diff(current_time, last_button_press_time)
        time_since_last_release = utime.ticks_diff(current_time, last_button_release_time)
        
        # Réinitialiser la pression
        last_button_press_time = 0 
        
        # Détection du DOUBLE CLIC (Bonus 2)
        if time_since_last_release < double_click_timeout and press_duration < double_click_timeout:
            is_24h_mode = not is_24h_mode
            print(f"** DOUBLE CLIC DÉTECTÉ : Mode {'24 heures' if is_24h_mode else '12 heures'} activé **")
            update_servo_angle(servo_pwm, TIMEZONES[current_tz_index]) # MISE À JOUR IMMÉDIATE
            last_button_release_time = current_time 
            
        # Détection du CLIC SIMPLE (Bonus 1)
        elif press_duration < double_click_timeout and time_since_last_release > double_click_timeout:
            current_tz_index = (current_tz_index + 1) % len(TIMEZONES)
            print(f"* CLIC SIMPLE DÉTECTÉ : Nouveau fuseau horaire UTC{TIMEZONES[current_tz_index]:+d} *")
            update_servo_angle(servo_pwm, TIMEZONES[current_tz_index]) # MISE À JOUR IMMÉDIATE
            last_button_release_time = current_time


# ==================== BOUCLE PRINCIPALE ====================

def servo_clock_main():
    """Fonction principale pour l'horloge servo."""
    global current_tz_index
    
    # Initialisation du servo
    servo_pwm = PWM(Pin(SERVO_PIN))
    servo_pwm.freq(PWM_FREQ)

    # 1. Connexion au WiFi
    try:
        # L'appel à connect_wifi se trouve ici
        connect_wifi(WIFI_SSID, WIFI_PASSWORD)
    except Exception as e:
        print(e)
        return

    # 2. Synchronisation NTP initiale
    sync_ntp_time(TIMEZONES[current_tz_index])
    
    last_angle_update_time = utime.ticks_ms()
    
    print("\n--- Horloge Servo Démarrée ---")
    
    try:
        # Première mise à jour de l'angle
        update_servo_angle(servo_pwm, TIMEZONES[current_tz_index])
        
        while True:
            
            # Gestion du bouton (vérification très fréquente)
            handle_button_press(servo_pwm) 
            utime.sleep_ms(50) # TRES IMPORTANT : Délai court pour la réactivité du bouton

            # Vérification de l'heure toutes les 15 secondes
            if utime.ticks_diff(utime.ticks_ms(), last_angle_update_time) >= 15000:
                
                # Re-synchronisation NTP toutes les heures
                if utime.ticks_diff(utime.ticks_ms(), last_angle_update_time) >= 3600000:
                    sync_ntp_time(TIMEZONES[current_tz_index])
                    
                # Mise à jour périodique de l'angle
                update_servo_angle(servo_pwm, TIMEZONES[current_tz_index])
                
                last_angle_update_time = utime.ticks_ms()

    except KeyboardInterrupt:
        print("\nArrêt du programme.")
    finally:
        servo_pwm.deinit() # Désactiver le PWM
        print("PWM désactivé.")
        
if __name__ == "__main__":
    servo_clock_main()