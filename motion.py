import threading
from collections import deque

motion_lock = threading.Lock()
motion_queue = deque()

motion = {
    "targetSteps": 0.0,
    "currentSteps": 0.0,
    "direction": 1,
    "axis": "x",
    "position": 0.0,
    "active": False,
    "absoluteTarget": 0.0
}
