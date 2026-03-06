import numpy as np
from scipy import signal
import sounddevice as sd
import time

sd.default.device = 0

sr = 48000        # sample rate 
freq = 40         # wave frequency 
amplitude = 0.9
phase = 0.0

def send_wave(direction):
    if direction==1:
        print("Running test in positive direction")
    elif direction==-1:
        print("Running test in negative direction")

    duration = 5
    t = np.arange(0, duration, 1/sr)

    # sawtooth
    wave = amplitude * signal.sawtooth(2 * np.pi * freq * t)

    # apply direction
    wave *= direction

    # single wave on left channel
    out = np.zeros((len(wave), 2), dtype=np.float32)
    out[:, 0] = wave.astype(np.float32)

    sd.play(out, sr)
    sd.wait()

    # clear DAC
    sd.play(np.zeros((int(0.1 * sr), 2), dtype=np.float32), sr)
    sd.wait()

    print("Done")

# send positive wave, then negative after 2 seconds
send_wave(1)
time.sleep(2)
send_wave(-1)

# clear DAC output
sd.stop()
sd.reset()
print("DAC output cleared")

