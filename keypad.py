import time
from evdev import InputDevice, categorize, ecodes, list_devices

KEYS = {
    ecodes.KEY_BACKSPACE:"BACKSPACE", ecodes.KEY_KPENTER:"ENTER", ecodes.KEY_ENTER:"ENTER",
    ecodes.KEY_KP0:"0", ecodes.KEY_KP1:"1", ecodes.KEY_KP2:"2", ecodes.KEY_KP3:"3",
    ecodes.KEY_KP4:"4", ecodes.KEY_KP5:"5", ecodes.KEY_KP6:"6", ecodes.KEY_KP7:"7",
    ecodes.KEY_KP8:"8", ecodes.KEY_KP9:"9",
    ecodes.KEY_UP:"UP", ecodes.KEY_DOWN:"DOWN", ecodes.KEY_LEFT:"LEFT", ecodes.KEY_RIGHT:"RIGHT", 
    ecodes.KEY_TAB:"TAB", ecodes.KEY_NUMLOCK:"NUM"}


class KeypadReader:
    def __init__(self, name="Homertech USB Keyboard"):
        self.dev = self._find(name)
        print(f"[Keypad] Using: {self.dev.name} ({self.dev.path})")

    def _find(self, exact_name):
        # finds correct keypad event
        for path in list_devices():
            d = InputDevice(path)
            name = d.name or ""

            # Must be exact name
            if name == exact_name:

                # Skip system/consumer controls
                lname = name.lower()
                if "system control" in lname or "consumer" in lname:
                    continue

                return d

        raise RuntimeError(f"Device '{exact_name}' not found")

    def events(self):
        print("[Keypad] Starting event loop…")
        last = 0.0

        for event in self.dev.read_loop():
            if event.type != ecodes.EV_KEY:
                continue

            ke = categorize(event)
            if ke.keystate not in (ke.key_down, ke.key_up):
                continue

            token = KEYS.get(ke.scancode)
            if not token:
                continue

            # debounce
            t = time.monotonic()
            if t - last < 0.02:
                continue
            last = t

            evt = {"token": token, "pressed": ke.keystate == ke.key_down}
            print("[Keypad] event:", evt)
            yield evt
