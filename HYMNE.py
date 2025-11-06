from machine import Pin, PWM
from utime import sleep_ms


# utilitaires musique (noms uniques pour éviter collisions)
def music_note_to_freq(note):
    """Convertit une note textuelle (ex: 'C#4') en fréquence (Hz). 'R' ou 'REST' = silence."""
    note = note.strip()
    if note == 'R' or note.upper() == 'REST':
        return 0
    if len(note) >= 2 and note[-1].isdigit():
        octave = int(note[-1])
        name = note[:-1]
    else:
        return 0

    semitone_map = {
        'C': -9, 'C#': -8, 'Db': -8,
        'D': -7, 'D#': -6, 'Eb': -6,
        'E': -5,
        'F': -4, 'F#': -3, 'Gb': -3,
        'G': -2, 'G#': -1, 'Ab': -1,
        'A': 0,  'A#': 1,  'Bb': 1,
        'B': 2
    }
    if name not in semitone_map:
        return 0
    n = semitone_map[name] + 12 * (octave - 3)
    freq = 440.0 * (2 ** (n / 12.0))
    return int(freq)


def music_play_melody(melodie, tempo=190, pwm_pin=18, duty_u16=32000):
    """Joue une mélodie listée sous forme [(note_str, beats), ...].
    beats : nombre de noires (1 = noire). tempo en BPM.
    """
    pwm = PWM(Pin(pwm_pin, Pin.OUT))
    quarter_ms = 60000 / tempo

    for note, beats in melodie:
        dur_ms = int(beats * quarter_ms)
        f = music_note_to_freq(note)
        if f == 0:
            pwm.duty_u16(0)
            sleep_ms(dur_ms)
        else:
            pwm.freq(f)
            pwm.duty_u16(duty_u16)
            play_ms = int(dur_ms * 0.92)
            sleep_ms(play_ms)
            pwm.duty_u16(0)
            sleep_ms(dur_ms - play_ms)
        sleep_ms(20)

    pwm.deinit()


# --- Mélodie de Noël (approx. "Jingle Bells") ---
# Format : (note, beats) where 1 = quarter note
jingle_bells = [
    ("E4", 1), ("E4", 1), ("E4", 2),
    ("E4", 1), ("E4", 1), ("E4", 2),
    ("E4", 1), ("G4", 1), ("C4", 1), ("D4", 1), ("E4", 4),
    ("F4", 1), ("F4", 1), ("F4", 1), ("F4", 1), ("F4", 1), ("E4", 1),
    ("E4", 1), ("E4", 1), ("E4", 1), ("D4", 1), ("D4", 1), ("E4", 1), ("D4", 2), ("G4", 4)
]


if __name__ == '__main__':
    print("Joue 'Jingle Bells' (approx.) — pin PWM:18, tempo:120 BPM")
    music_play_melody(jingle_bells, tempo=120, pwm_pin=18)