"""
Controle LED RGB (NeoPixel) au rythme de la musique - Raspberry Pi Pico W
Detecte les battements et calcule les BPM.
LED RGB adressable (WS2812/NeoPixel) sur GPIO 20
Microphone (Analogique) sur GPIO 26 (ADC0)
"""

from machine import Pin, ADC
import utime
import urandom
import neopixel
import uos # Pour les operations de fichier

# ==================== CONFIGURATION DES PINS ====================
# Microphone (sortie analogique) : ADC0 (GPIO 26)
MIC_PIN = ADC(0) 

# LED RGB adressable (WS2812/NeoPixel) sur GPIO 20
LED_PIN_NUM = 20
NUM_LEDS = 1
try:
    np = neopixel.NeoPixel(Pin(LED_PIN_NUM, Pin.OUT), NUM_LEDS)
except ValueError:
    print("Erreur: Le Pin de la LED est mal configure.")

# ==================== PARAMÈTRES DE DÉTECTION ====================
# SEUIL CRITIQUE : AJUSTÉ À 12900 (très sensible, basé sur votre calibration)
THRESHOLD = 12900           # Beat detection threshold (ADC u16)
MIN_BEAT_INTERVAL = 200     # Minimum interval between beats (ms)
SAMPLE_WINDOW = 50          # Sampling window for peak detection (ms)
BPM_HISTORY_SIZE = 60       # BPM history size for average calculation

# ==================== VARIABLES GLOBALES ====================
last_beat_time = 0
beat_times = []
bpm_history = []
last_save_time = utime.ticks_ms()

# ==================== FONCTIONS LED RGB ====================

def set_led_color(r, g, b):
    """Sets the RGB LED color (0-255 values)"""
    np[0] = (r, g, b)
    np.write()

def random_color():
    """Generates a random, visible color"""
    r = urandom.randint(100, 255)
    g = urandom.randint(100, 255)
    b = urandom.randint(100, 255)
    return r, g, b

def led_off():
    """Turns the LED off"""
    set_led_color(0, 0, 0)

# ==================== FONCTIONS DE DÉTECTION AUDIO ====================

def detect_peak():
    """Reads the maximum sound level over a sampling window"""
    max_value = 0
    start_time = utime.ticks_ms()
    
    # Fast read loop to find the peak value
    while utime.ticks_diff(utime.ticks_ms(), start_time) < SAMPLE_WINDOW:
        value = MIC_PIN.read_u16() # 16-bit read (0-65535)
        if value > max_value:
            max_value = value
        utime.sleep_ms(2)
        
    return max_value

def is_beat(sound_level):
    """Determines if a beat is detected, respecting the minimum interval"""
    global last_beat_time
    
    current_time = utime.ticks_ms()
    time_since_last = utime.ticks_diff(current_time, last_beat_time)
    
    # Check if threshold is exceeded AND minimum beat interval is respected
    if sound_level > THRESHOLD and time_since_last > MIN_BEAT_INTERVAL:
        return True
    return False

# ==================== FONCTIONS BPM (Bonus) ====================

def calculate_bpm():
    """Calculates BPM based on the last detected beats (last 10)"""
    global beat_times
    
    if len(beat_times) < 2:
        return 0
    
    # Calculate total time elapsed between the first and last beat
    time_elapsed_ms = utime.ticks_diff(beat_times[-1], beat_times[0])
    num_intervals = len(beat_times) - 1 

    if num_intervals > 0 and time_elapsed_ms > 0:
         # BPM = (Number of intervals / elapsed time in minutes)
        bpm = (num_intervals * 60000) / time_elapsed_ms
        return bpm
        
    return 0

def save_bpm_to_file():
    """Saves the average detected BPM from the last minute to a file"""
    global bpm_history, last_save_time
    
    if not bpm_history:
        print("[INFO] BPM history empty for saving.")
        return
    
    avg_bpm = sum(bpm_history) / len(bpm_history)
    
    try:
        # Create a timestamp for the log
        timestamp = utime.localtime()
        log_entry = "{:04d}-{:02d}-{:02d} {:02d}:{:02d}:{:02d},{:.2f}\n".format(
            timestamp[0], timestamp[1], timestamp[2],
            timestamp[3], timestamp[4], timestamp[5],
            avg_bpm
        )
        
        # Write to file (append mode 'a')
        with open('bpm_log.txt', 'a') as f:
            f.write(log_entry)
            
        print(f"[FICHIER] Average BPM ({len(bpm_history)} measurements) saved: {avg_bpm:.2f} BPM")
        
        # Reset history for the next minute
        bpm_history = []
        
    except Exception as e:
        print(f"[ERREUR FICHIER] Cannot save: {e}")

# ==================== FONCTION PRINCIPALE ====================

def main():
    global last_beat_time, beat_times, last_save_time, bpm_history
    
    # LED initialization (quick test for the user)
    try:
        set_led_color(10, 10, 10) 
        utime.sleep_ms(50)
        led_off()
        print("LED NeoPixel sur GPIO 20 | Micro sur ADC0 (GPIO 26)")
        print(f"Seuil actuel: {THRESHOLD} | Intervalle min: {MIN_BEAT_INTERVAL}ms")
    except NameError:
        print("[CRITICAL ERROR] NeoPixel could not be initialized. Check 'neopixel' and 'LED_PIN_NUM'.")
        return

    # No calibration test here, running directly to avoid unnecessary delays
    
    print("\n=== Demarrage de la detection de battements... ===")

    # Initialize BPM file (write header if file is empty)
    try:
        with open('bpm_log.txt', 'a') as f:
            if f.tell() == 0:
                f.write("YYYY-MM-DD HH:MM:SS,bpm\n")
    except:
        pass # Ignore if the file system is not ready

    beat_count = 0
    last_debug_time = utime.ticks_ms()
    
    try:
        while True:
            current_time = utime.ticks_ms()
            
            # 1. Read sound level (peak over SAMPLE_WINDOW)
            sound_level = detect_peak()
            
            # 2. Detect a beat
            if is_beat(sound_level):
                
                # Record beat time
                beat_times.append(current_time)
                if len(beat_times) > 10: # Keep only the last 10 times for instantaneous BPM
                    beat_times.pop(0)
                    
                last_beat_time = current_time
                beat_count += 1
                
                # 3. Change LED color and display
                r, g, b = random_color()
                set_led_color(r, g, b)
                
                # Calculate instantaneous BPM
                bpm = calculate_bpm()
                if bpm > 0:
                    bpm_history.append(bpm)
                    # Display beat
                    print(f"Beat #{beat_count} | Level: {sound_level} | BPM: {bpm:.1f} | RGB: ({r},{g},{b})")
                else:
                    print(f"Beat #{beat_count} | Level: {sound_level} | BPM: N/A (not enough data)")
            
            # 4. DEBUG display (Every 1000ms) - CRITICAL FOR CALIBRATION
            if utime.ticks_diff(current_time, last_debug_time) >= 1000:
                print(f"[DEBUG] Current Level: {sound_level} | Threshold: {THRESHOLD} (Diff: {sound_level - THRESHOLD})")
                last_debug_time = current_time
            
            # 5. Save BPM every 60 seconds (Bonus)
            if utime.ticks_diff(current_time, last_save_time) >= 60000:
                print("-" * 25)
                save_bpm_to_file()
                last_save_time = current_time
                print("-" * 25)
                
            utime.sleep_ms(10)
            
    except KeyboardInterrupt:
        print("\n\n=== Arret du programme ===")
        led_off()
        # Attempt final save
        if bpm_history:
            save_bpm_to_file() 
        else:
            print("[INFO] BPM history empty.")
            
        print("LED eteinte et donnees sauvegardees")

# ==================== DÉMARRAGE ====================
if __name__ == "__main__":
    main()