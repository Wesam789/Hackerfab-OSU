from flask import Flask, jsonify, request, send_from_directory
from flask_sock import Sock
import threading, json, time, os, atexit
from keypad import KeypadReader
from motion import motion, motion_lock, motion_queue
from wave import audio_stream_start, audio_stream_stop

app = Flask(__name__, static_folder="frontend", static_url_path="")
sock = Sock(app)

# websocket clients
clients = set()
clients_lock = threading.Lock()
audio_stream = None

# broadcasts data to clients
def ws_broadcast(obj):
    payload = json.dumps(obj)
    with clients_lock:
        targets = list(clients)
    done = []   # clients that disconnected 
    
    for c in targets:
        try:
            c.send(payload)
        except Exception:
            done.append(c)
    # remove disconnected clients
    if done:
        with clients_lock:
            for d in done:
                clients.discard(d)

# websocket endpoint    
@sock.route("/ws")
def ws(ws):
    # add new client to set
    with clients_lock:
        clients.add(ws)
    try:
        # ws.send(json.dumps({"type": "hello", "msg": "connected"}))
        # listen for messages
        while True:
            msg = ws.receive()
            if not msg:
                break  # client disconnected
    finally:
        # remove client
        with clients_lock:
            clients.discard(ws)

# serve html page
@app.get("/")
def index():
    return send_from_directory("frontend", "index.html")

# REST API endpoint
@app.post("/apply-step")
def apply_step():
    data = request.get_json() or {}
    dist = float(data.get("dist", 0))  # steps
    axis = data.get("axis", "x").lower()

    print("Received command:", axis, dist)

    if axis not in ("x", "y"):
        return jsonify(ok=False, error="Invalid axis")
    
    if dist == 0:
        return jsonify(ok=False, error="Zero move, ignored")

    if not isinstance(dist, (int, float)):
        return jsonify(ok=False, error="Invalid distance")
    
    with motion_lock:
        motion_queue.append({
            "steps": abs(dist),
            "direction": 1 if dist > 0 else -1,
            "axis": axis
        })
        
    return jsonify(ok=True)

@app.get("/status")
def status():
    with motion_lock:
        return jsonify({
            "position": motion["position"],
            "moving": motion["active"]
        })

@app.post("/auto-control")
def auto_control():
    data = request.get_json() or {}
    cmd = data.get("command")

    if cmd == "START":
        print("Auto START")
    elif cmd == "STOP":
        print("Auto STOP")

    return jsonify(ok=True)


# read keypad inputs and send to browsers
def keypad_thread():
    print("[Keypad] thread started")
    try:
        kp = KeypadReader()
        print("[Keypad] device opened:", kp.dev)
    except Exception as e:
        print(f"[Keypad] {e}")
        return

    # incoming events from keypad
    for evt in kp.events():
        print("[Keypad] event:", evt) 
        ws_broadcast({"type": "key", **evt})

def status_thread():
    print("Thread started")
    while True:
        time.sleep(0.1)
        
        # read motion state
        with motion_lock:
            payload = {
                "type": "status",
                "pos": round(motion["position"], 3),
                "active": motion["active"],
                "queue": len(motion_queue)
            }
        
        # Send to frontend
        ws_broadcast(payload)

# cleanup after server dies
def cleanup():
    global audio_stream
    if audio_stream:
        audio_stream_stop(audio_stream)

# run on exit
atexit.register(cleanup) 

if __name__ == "__main__":
    import os
    # keypad listener running in background
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=keypad_thread, daemon=True).start()
        threading.Thread(target=status_thread, daemon=True).start()
        audio_stream = audio_stream_start()
    # start web server
    app.run(host="0.0.0.0", port=8080, debug=True)
