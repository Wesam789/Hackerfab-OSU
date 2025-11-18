from flask import Flask, jsonify, request, send_from_directory
from flask_sock import Sock
import threading, json
from keypad import KeypadReader

app = Flask(__name__, static_folder="frontend", static_url_path="")
sock = Sock(app)

# websocket clients
clients = set()
clients_lock = threading.Lock()

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
        ws.send(json.dumps({"type": "hello", "msg": "connected"}))
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
    data = request.get_json(silent=True) or {}
    axis = data.get("axis")
    dist = data.get("dist")
    print(f"[APPLY] axis={axis} dist={dist}")
    return jsonify(ok=True, axis=axis, dist=dist)

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

if __name__ == "__main__":
    import os
    # keypad listener running in background
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true":
        threading.Thread(target=keypad_thread, daemon=True).start()
    # start web server
    app.run(host="0.0.0.0", port=8080, debug=True)
