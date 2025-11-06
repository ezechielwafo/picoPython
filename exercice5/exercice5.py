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
WIFI_PASSWORD = ""

# Configuration du Servo (Étape 3)
SERVO_PIN = 16 # CHANGEMENT: Utilisation de GPIO 16 comme demandé
# Plage de PWM typique pour un servo (50Hz)
PWM_FREQ = 50
# Les valeurs de duty cycle (0-65535) correspondent généralement à ~0.5ms (0°) à ~2.5ms (180°)
DUTY_MIN = 1500  # Correspond à 0°
DUTY_MAX = 7500  # Correspond à 180°

# Configuration du Bouton (Bonus 1 & 2)
BUTTON_PIN = 15
# Configuration Pull-Up : la broche sera HIGH au repos, LOW quand pressée
button = Pin(BUTTON_PIN, Pin.IN, Pin.PULL_UP)

# ==================== VARIABLES DE SYNCHRONISATION ET ÉTAT ====================

# Décalages horaires en heures (exemple : UTC, UTC+1, UTC-5, etc.)
TIMEZONES = [0, 1, 2, -5, 5, 8]
current_tz_index = 1

# État de l'horloge pour le Bonus 2
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
    """
    Étape 1, partie 2: Récupère l'heure actuelle via NTP et applique le fuseau horaire.
    """
    try:
        ntptime.settime()
        # Le Pico est synchronisé sur UTC (utime.time() est UTC)
        # On applique le décalage horaire pour l'affichage
        print(f"Heure synchronisée (UTC). Décalage TZ: {tz_offset}h")
    except Exception as e:
        print(f"Erreur de synchronisation NTP: {e}")

# ==================== FONCTIONS DE CONTRÔLE DU SERVO ====================

def map_angle_to_duty(angle):
    """Mappe un angle de 0-180 degrés au cycle PWM (DUTY_MIN à DUTY_MAX)."""
    # La fonction map équivalente: y = (x - x_min) * (y_max - y_min) / (x_max - x_min) + y_min
    return int((angle / 180) * (DUTY_MAX - DUTY_MIN) + DUTY_MIN)

def set_servo_angle(pwm, angle):
    """Règle l'angle du servo moteur."""
    duty = map_angle_to_duty(angle)
    pwm.duty_u16(duty)

# ==================== FONCTIONS DE CALCUL D'ANGLE ====================

def calculate_angle_12h(h_tz, m):
    """
    Étape 2: Calcul de l'angle pour un cadran de 12 heures (0° à 180°).
    L'angle est basé sur l'heure (H) et la minute (M).
    - 12h = 0°
    - 6h = 90°
    """
    # 1. Heure en format 12h (1 à 12)
    # 0h et 12h doivent être considérés comme 12h pour la rotation
    h_display = h_tz % 12
    if h_display == 0:
        h_display = 12

    # 2. Heures totales sur une base de 12 (avec décimales pour les minutes)
    total_hours = h_display + (m / 60)
    
    # 3. Angle par unité d'heure : 180 degrés / 12 heures = 15 degrés/heure
    # On soustrait 12 pour que 12h (le début du cycle) soit à 0 degré
    # On utilise modulo 12 pour que 12h (0.00) soit le point de départ
    
    # Ex: 12:00 -> 0.0 * 15 = 0°
    # Ex: 06:00 -> 6.0 * 15 = 90°
    # Ex: 01:00 -> 1.0 * 15 = 15°
    angle = (total_hours % 12) * 15
    
    return min(max(0, angle), 180) # S'assurer que l'angle est entre 0 et 180

def calculate_angle_24h(h_tz, m):
    """
    Bonus 2: Calcul de l'angle pour un cadran de 24 heures (0° à 180°).
    L'angle est basé sur l'heure (H) et la minute (M).
    - 00h = 0°
    - 12h = 90°
    - 24h (00h) = 180°
    """
    # 1. Heures totales sur une base de 24 (avec décimales pour les minutes)
    total_hours = h_tz + (m / 60)
    
    # 2. Angle par unité d'heure : 180 degrés / 24 heures = 7.5 degrés/heure
    angle = total_hours * 7.5
    
    return min(max(0, angle), 180) # S'assurer que l'angle est entre 0 et 180

# ==================== FONCTIONS DE GESTION DU BOUTON ====================

def handle_button_press():
    """Gère les clics simples (TZ) et doubles clics (24h) du bouton."""
    global current_tz_index, is_24h_mode, last_button_press_time, last_button_release_time
    
    current_time = utime.ticks_ms()
    
    # Détection de l'appui (bouton LOW)
    if button.value() == 0:
        # Si c'est un nouvel appui (pas un maintien)
        if utime.ticks_diff(current_time, last_button_press_time) > 100: # Anti-rebond
            last_button_press_time = current_time
        return # Attendre le relâchement

    # Détection du relâchement (bouton HIGH)
    if button.value() == 1 and utime.ticks_diff(current_time, last_button_press_time) > 100:
        press_duration = utime.ticks_diff(current_time, last_button_press_time)
        time_since_last_release = utime.ticks_diff(current_time, last_button_release_time)
        
        last_button_release_time = current_time

        # Détection du DOUBLE CLIC (Bonus 2)
        if time_since_last_release < double_click_timeout and press_duration < double_click_timeout:
            # Réinitialiser les temps pour éviter un triple clic non désiré
            last_button_press_time = 0
            last_button_release_time = 0 
            
            is_24h_mode = not is_24h_mode
            mode_str = "24 heures" if is_24h_mode else "12 heures"
            print(f"** DOUBLE CLIC DÉTECTÉ : Mode {mode_str} activé **")
            
        # Détection du CLIC SIMPLE (Bonus 1)
        elif press_duration < double_click_timeout:
            current_tz_index = (current_tz_index + 1) % len(TIMEZONES)
            print(f"* CLIC SIMPLE DÉTECTÉ : Nouveau fuseau horaire UTC{TIMEZONES[current_tz_index]:+d} *")


# ==================== BOUCLE PRINCIPALE ====================

def servo_clock_main():
    """Fonction principale pour l'horloge servo."""
    global current_tz_index, is_24h_mode
    
    # Initialisation du servo
    servo_pwm = PWM(Pin(SERVO_PIN))
    servo_pwm.freq(PWM_FREQ)

    # 1. Connexion au WiFi
    try:
        connect_wifi(WIFI_SSID, WIFI_PASSWORD)
    except Exception as e:
        print(e)
        return

    # 2. Synchronisation NTP initiale
    sync_ntp_time(TIMEZONES[current_tz_index])
    
    last_sync_time = utime.ticks_ms()
    
    print("\n--- Horloge Servo Démarrée ---")
    
    try:
        while True:
            # Gestion du bouton pour les bonus
            handle_button_press() 
            
            # Re-synchronisation toutes les heures (3 600 000 ms)
            if utime.ticks_diff(utime.ticks_ms(), last_sync_time) >= 3600000:
                sync_ntp_time(TIMEZONES[current_tz_index])
                last_sync_time = utime.ticks_ms()

            # Récupération de l'heure UTC actuelle
            current_utc_time_tuple = utime.localtime()
            
            # Application du décalage de fuseau horaire
            tz_offset = TIMEZONES[current_tz_index]
            
            # Conversion du temps UTC en secondes, application du décalage, et reconversion en tuple
            current_utc_seconds = utime.mktime(current_utc_time_tuple)
            local_time_seconds = current_utc_seconds + (tz_offset * 3600)
            local_time = utime.localtime(local_time_seconds)
            
            # Extraction de l'heure et des minutes locales (Index 3: Heure, Index 4: Minute)
            h_local = local_time[3]
            m_local = local_time[4]
            s_local = local_time[5]
            
            # 3. Calcul et Contrôle du Servo (Étape 3)
            if is_24h_mode:
                angle = calculate_angle_24h(h_local, m_local)
                mode_str = "24H"
            else:
                angle = calculate_angle_12h(h_local, m_local)
                mode_str = "12H"
                
            set_servo_angle(servo_pwm, angle)
            
            print(f"Heure Locale: {h_local:02d}:{m_local:02d}:{s_local:02d} | TZ: {tz_offset:+}h | Mode: {mode_str} | Angle: {angle:.1f}°")

            # Délai: Mise à jour toutes les 15 secondes pour économiser la batterie et le servo
            utime.sleep(15) 

    except KeyboardInterrupt:
        print("\nArrêt du programme.")
    finally:
        servo_pwm.deinit() # Désactiver le PWM
        print("PWM désactivé.")
        
if __name__ == "__main__":
    servo_clock_main()