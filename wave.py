import numpy as np
from scipy import signal
import sounddevice as sd
import time
from motion import motion, motion_lock, motion_queue

sd.default.device = 0

sr = 48000        # sample rate 
freq = 200        # wave frequency 
amplitude = 0.9
phase = 0.0

steps_per_cycle = 1

#  calibration
steps_per_second = freq * steps_per_cycle

print("motion calibration")
print("Frequency:", freq)
print("Steps per cycle:", steps_per_cycle)
print("Steps per second:", steps_per_second)

def load_next_step():
    # load next step from queue into active motion state
    with motion_lock:
        if motion["active"] or not motion_queue:
            return

        step = motion_queue.popleft()
        motion["targetSteps"] = step["steps"]
        motion["currentSteps"] = 0.0
        motion["direction"] = step["direction"]
        motion["axis"] = step["axis"]
        motion["active"] = True

        print(f"Starting job: {step}")
        print(f"Loaded step: {motion['axis']} {motion['targetSteps']} dir={motion['direction']}")


def audio_callback(outdata, frames, time_info, status):
    global phase

    load_next_step()

    # copy motion state 
    with motion_lock:
        active = motion["active"]
        direction = motion["direction"]
        current_axis = motion["axis"]
        target = motion["targetSteps"]
        current = motion["currentSteps"]

    if not active:
        outdata[:] = 0
        phase = (phase + frames) % sr
        return

    # time vector   
    n = np.arange(frames) + phase
    t = n / sr

    # sawtooth wave
    wave = amplitude * signal.sawtooth(2 * np.pi * freq * t)
    # final wave
    wave *= direction
    
    steps_generated = steps_per_second * (frames / sr)
   
    # stop condition
    with motion_lock:
        remaining = max(0.0, motion["targetSteps"] - motion["currentSteps"])
        actual_steps = min(steps_generated, remaining)

        motion["currentSteps"] += actual_steps
        motion["position"] += actual_steps * direction

        if motion["currentSteps"] >= motion["targetSteps"]:
            motion["active"] = False
            motion["currentSteps"] = motion["targetSteps"]

    outdata[:] = 0.0
    if current_axis.lower() == "x":
        outdata[:, 0] = wave.astype(np.float32)   # left channel
    else:
        outdata[:, 1] = wave.astype(np.float32)   # right channel

    phase = (phase + frames) % sr

def audio_stream_start():
    print("Audio stream attempt")

    try:
        stream = sd.OutputStream(
            samplerate=sr,
            channels=2,
            dtype='float32',
            blocksize=256,
            callback=audio_callback
        )
        stream.start()
        print("Audio stream started")
        return stream
    
    except Exception as e:
        print(f"Error starting audio: {e}")
        return None

def audio_stream_stop(stream):
    print("Stopping audio")
    if stream:
        stream.stop()
        stream.close()

    # cleanup
    try:
        sd.play(np.zeros((1024, 2), dtype=np.float32), sr)
        sd.wait() 
    except Exception:
        pass
    
    sd.stop() 
    print("DAC output cleared")
