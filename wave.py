import numpy as np
import sounddevice as sd

# sampling rate, per second
fs = 48000
# time array from 0 to 1 second
t = np.linspace(0, 1, fs, endpoint=False)

# 200 Hz sawtooth wave, ramps back to 0 after reaching 1
saw = (t*200) % 1.0  
# scale waveform, give DAC full-scale amplitude  
# convert float to 16-bit signed integers for DAC    
saw = (saw * 32767).astype(np.int16)

# send signal to DAC 
sd.play(saw, fs)
sd.wait()
