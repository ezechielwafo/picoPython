
from machine import Pin, ADC
import utime
import urandom
import neopixel
import uos # Utilisé pour les opérations de fichiers (Bonus)

# ==================== CONFIGURATION DES PINS ET MATÉRIEL ====================

# 1. Initialisation du microphone (Consigne 1)
# Broche analogique ADC0 (GPIO 26) pour la lecture des données sonores.
MIC_PIN = ADC(0) 

# 1. Initialisation de la LED RGB (Consigne 1)
LED_PIN_NUM = 20
NUM_LEDS = 1
try:
    # Utilisation de la bibliothèque NeoPixel (WS2812)
    np = neopixel.NeoPixel(Pin(LED_PIN_NUM, Pin.OUT), NUM_LEDS)
except ValueError:
    print("Erreur: Le Pin de la LED est mal configuré.")

# ==================== PARAMÈTRES DE DÉTECTION ====================

# Seuil ajusté à 12900, basé sur la calibration de votre microphone.
# Si la LED ne réagit pas -> Diminuer ce nombre.
# Si la LED clignote tout le temps -> Augmenter ce nombre.
THRESHOLD = 12900           # Seuil de détection de crête sonore (ADC u16)
MIN_BEAT_INTERVAL = 200     # Intervalle minimum entre battements (ms) - Anti-rebond
SAMPLE_WINDOW = 50          # Fenêtre d'échantillonnage pour trouver le pic (ms)

# Paramètres pour le BONUS: Calcul du BPM et Sauvegarde
BPM_HISTORY_SIZE = 60       # Taille de l'historique des BPM pour la moyenne par minute

# ==================== VARIABLES GLOBALES ====================

last_beat_time = 0
beat_times = []             # Stocke les temps des 10 derniers battements pour le calcul BPM
bpm_history = []            # Stocke les BPM pour la moyenne de la minute (Bonus)
last_save_time = utime.ticks_ms()

# ==================== FONCTIONS LED RGB ====================

def set_led_color(r, g, b):
    """Définit la couleur de la LED RGB (valeurs 0-255) et l'affiche."""
    np[0] = (r, g, b)
    np.write()

def random_color():
    """Consigne 4: Change la couleur de la LED RGB de manière aléatoire."""
    # S'assure que la couleur est lumineuse (composantes > 100) pour être visible
    r = urandom.randint(100, 255)
    g = urandom.randint(100, 255)
    b = urandom.randint(100, 255)
    return r, g, b

def led_off():
    """Éteint la LED."""
    set_led_color(0, 0, 0)

# ==================== FONCTIONS DE DÉTECTION DE BATTEMENTS ====================

def detect_peak():
    """
    Consigne 2: Lit constamment les données sonores du microphone.
    Analyse les données pour trouver la crête maximale sur la fenêtre d'échantillonnage.
    """
    max_value = 0
    start_time = utime.ticks_ms()
    
    # Lecture rapide et répétée pour trouver le pic
    while utime.ticks_diff(utime.ticks_ms(), start_time) < SAMPLE_WINDOW:
        value = MIC_PIN.read_u16() # Lecture sur 16 bits (0-65535)
        if value > max_value:
            max_value = value
        utime.sleep_ms(2) # Petite pause pour l'échantillonnage
        
    return max_value

def is_beat(sound_level):
    """
    Consigne 3: Analyse les données sonores pour détecter les battements (méthode de pic).
    """
    global last_beat_time
    
    current_time = utime.ticks_ms()
    time_since_last = utime.ticks_diff(current_time, last_beat_time)
    
    # Le battement est détecté si :
    # 1. Le niveau dépasse le seuil (pic détecté)
    # 2. L'intervalle minimum (anti-rebond) est respecté.
    if sound_level > THRESHOLD and time_since_last > MIN_BEAT_INTERVAL:
        return True
    return False

# ==================== FONCTIONS BPM ET SAUVEGARDE (Bonus) ====================

def calculate_bpm():
    """Bonus 1: Calcule le rythme de la musique en BPM."""
    global beat_times
    
    if len(beat_times) < 2:
        return 0
    
    # Calcule le temps total écoulé entre le premier et le dernier battement enregistré
    time_elapsed_ms = utime.ticks_diff(beat_times[-1], beat_times[0])
    num_intervals = len(beat_times) - 1 

    if num_intervals > 0 and time_elapsed_ms > 0:
         # Conversion: (Intervalle * 60000ms/minute) / Temps écoulé en ms
        bpm = (num_intervals * 60000) / time_elapsed_ms
        return bpm
        
    return 0

def save_bpm_to_file():
    """Bonus 2: Calcule la moyenne des BPM détectés sur la dernière minute et écrit dans un fichier."""
    global bpm_history
    
    if not bpm_history:
        print("[INFO] Historique BPM vide. Pas de sauvegarde effectuée.")
        return
    
    # Calcul de la moyenne des BPM enregistrés
    avg_bpm = sum(bpm_history) / len(bpm_history)
    
    try:
        # Créer un timestamp local pour le log
        timestamp = utime.localtime()
        log_entry = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d},{:.2f}\n".format(
            timestamp[0], timestamp[1], timestamp[2],
            timestamp[3], timestamp[4], timestamp[5],
            avg_bpm
        )
        
        # Ouvre le fichier en mode 'a' (append) pour ajouter la ligne, puis le ferme (with)
        with open('bpm_log.txt', 'a') as f:
            f.write(log_entry)
            
        print(f"[FICHIER] BPM moyen ({len(bpm_history)} mesures) sauvegardé: {avg_bpm:.2f} BPM")
        
        # Réinitialiser l'historique pour la prochaine minute
        bpm_history = []
        
    except Exception as e:
        print(f"[ERREUR FICHIER] Impossible de sauvegarder: {e}")

# ==================== FONCTION PRINCIPALE (Consigne 2) ====================

def main():
    global last_beat_time, beat_times, last_save_time, bpm_history
    
    # Test LED rapide
    try:
        set_led_color(10, 10, 10) 
        utime.sleep_ms(50)
        led_off()
        print("LED NeoPixel sur GPIO 20 | Micro sur ADC0 (GPIO 26)")
        print(f"Seuil de détection: {THRESHOLD} | Intervalle min: {MIN_BEAT_INTERVAL}ms")
    except NameError:
        print("[ERREUR CRITIQUE] LED non initialisée.")
        return

    print("\n=== Démarrage de la détection de battements... ===")

    # Initialiser le fichier BPM avec l'en-tête (Bonus)
    try:
        with open('bpm_log.txt', 'a') as f:
            if f.tell() == 0:
                f.write("YYYY-MM-DD HH:MM:SS,bpm\n")
    except:
        pass 

    beat_count = 0
    last_debug_time = utime.ticks_ms()
    
    try:
        while True:
            current_time = utime.ticks_ms()
            
            # 1. Lire le niveau sonore (pic sur SAMPLE_WINDOW)
            sound_level = detect_peak()
            
            # 2. Détecter un battement (Consigne 3)
            if is_beat(sound_level):
                
                # Enregistrement du temps du battement
                beat_times.append(current_time)
                if len(beat_times) > 10: 
                    beat_times.pop(0)
                    
                last_beat_time = current_time
                beat_count += 1
                
                # 3. Changer la couleur de la LED (Consigne 4)
                r, g, b = random_color()
                set_led_color(r, g, b)
                
                # 4. Calculer le BPM (Bonus 1)
                bpm = calculate_bpm()
                if bpm > 0:
                    bpm_history.append(bpm)
                    # Affichage synchronisé avec le battement
                    print(f"Beat #{beat_count} | Niveau: {sound_level} | BPM: {bpm:.1f} | RGB: ({r},{g},{b})")
                else:
                    print(f"Beat #{beat_count} | Niveau: {sound_level} | BPM: N/A")
            
            # 5. Affichage de DEBUG toutes les secondes
            if utime.ticks_diff(current_time, last_debug_time) >= 1000:
                print(f"[DEBUG] Niveau actuel: {sound_level} | Seuil: {THRESHOLD} (Diff: {sound_level - THRESHOLD})")
                last_debug_time = current_time
            
            # 6. Sauvegarder les BPM toutes les 60 secondes (Bonus 2)
            if utime.ticks_diff(current_time, last_save_time) >= 60000:
                print("-" * 25)
                save_bpm_to_file()
                last_save_time = current_time
                print("-" * 25)
                
            utime.sleep_ms(10) # Petite pause pour ne pas surcharger le CPU
            
    except KeyboardInterrupt:
        print("\n\n=== Arrêt du programme ===")
        led_off()
        # Sauvegarde finale
        if bpm_history:
            save_bpm_to_file() 
        print("LED éteinte et données sauvegardées")

# ==================== DÉMARRAGE ====================
if __name__ == "__main__":
    main()