import numpy as np
from scipy import signal
import sounddevice as sd
import math
import time

sd.default.device = 0

sr = 48000        # sample rate 
freq = 350        # wave frequency 
amplitude = 0.9
phase = 0.0

def audio_callback(outdata, frames, time_info, status):
    global phase
    cycles = (freq * frames) / sr

    # time vector   
    n = np.arange(frames) + phase
    t = n / sr

    # sawtooth wave
    x = amplitude * signal.sawtooth(2 * np.pi * freq * t)

    # output left and right channels
    outdata[:] = np.column_stack((x, -x)).astype(np.float32)
    phase = (phase + frames) % sr

print("Streaming wave on LOUT")
print("Streaming wave on ROUT")


try:
    with sd.OutputStream(
        samplerate=sr,
        channels=2,
        dtype='float32',
        callback=audio_callback
    ):
        while True:
            time.sleep(0.1)
except KeyboardInterrupt:
    print("\nStopping...")

# clear DAC output
sd.play(np.zeros((1024, 2), dtype=np.float32), sr)
sd.stop()
sd.reset()
print("DAC output cleared")

