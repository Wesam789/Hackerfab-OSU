from flask import Flask, jsonify, request, send_from_directory, Response
from flask_sock import Sock
import threading, json, time, os, atexit, csv
from keypad import KeypadReader
from motion import motion, motion_lock, motion_queue
from wave import audio_stream_start, audio_stream_stop
from camera import FLIRCamera
import RPi.GPIO as GPIO

app = Flask(__name__, static_folder="frontend", static_url_path="")
sock = Sock(app)

# websocket clients
clients = set()
clients_lock = threading.Lock()
audio_stream = None
camera_active = False

# FPS testing
fps_data = []
test_duration = 60.0
test_completed = False 

# open file and write CSV data
def save_fps_data():
    # saves FPS data to CSV file
    file_path = 'fps_data.csv'
    try:
        with open(file_path, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["Elapsed Time (s)", "FPS"])
            writer.writerows(fps_data)
        print(f"\nTEST COMPLETE: CSV file generated at: {os.path.abspath(file_path)} ***\n")
    except Exception as e:
        print(f"Failed to write CSV: {e}")

# GPIO pins
def init_gpio():
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BCM)

    # setup pins with confirmation message
    GPIO.setup(26, GPIO.OUT)
    GPIO.setup(16, GPIO.OUT)
    print("GPIO Pins 26 and 16 initialized")
    
    # Pin 26 set to high
    GPIO.output(26, GPIO.HIGH)
    
    # Pin 16 default to 0 (Y-axis is 1, X-axis is 0)
    GPIO.output(16, GPIO.LOW)

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

flir_cam = None

def stream_frames():
    # ADD "camera_active"
    global flir_cam, test_completed
    if flir_cam is None:
        try:
            flir_cam = FLIRCamera()
            flir_cam.start()
        except Exception as e:
            print(f"Camera Init Failed: {e}")
            return
    
    last_frame_time = time.time()
    test_start_time = time.time()

    while True:
        frame = flir_cam.get_frame()
        current_time = time.time()

        if frame:
            # calculate FPS
            time_diff = current_time - last_frame_time
            instant_fps = 1.0 / time_diff if time_diff > 0 else 0.0
            last_frame_time = current_time
            
            # print to terminal
            print(f"FPS: {instant_fps:.2f}")

            # collection Window
            total_elapsed = current_time - test_start_time
            if total_elapsed <= test_duration and not test_completed:
                # capture 1800-3600 points 
                fps_data.append([round(total_elapsed, 4), round(instant_fps, 2)])
            elif total_elapsed > test_duration and not test_completed:
                save_fps_data()
                test_completed = True

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
            time.sleep(0.03)
        else:
            time.sleep(0.01)
        

# serve html page
@app.get("/")
def index():
    return send_from_directory("frontend", "index.html")

# REST API endpoint
@app.post("/apply-step")
def apply_step():
    data = request.get_json() or {}
    dist = float(data.get("dist", 0))  # motion steps
    axis = data.get("axis", "x").lower()
    dirSign = data.get("dirSign", 1)

    print("Received command:", axis, dist)

    if axis not in ("x", "y"):
        return jsonify(ok=False, error="Invalid axis")
    
    if dist == 0:
        return jsonify(ok=False, error="Zero move, ignored")

    if not isinstance(dist, (int, float)):
        return jsonify(ok=False, error="Invalid distance")
    
    # output for MUX 
    if axis == 'x':
        GPIO.output(16, GPIO.LOW)   # 0 for X-axis
        print("MUX: Pin 16 LOW (x-axis)")
    elif axis == 'y':
        GPIO.output(16, GPIO.HIGH)  # 1 for Y-axis
        print("MUX: Pin 16 HIGH (y-axis)")
    
    with motion_lock:
        motion_queue.append({
            "steps": abs(dist) * 200,  # scaled up
            "direction": 1 if dirSign > 0 else -1,
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

@app.post("/stop-motion")
def stop_motion():
    print("Stopping motion")
    with motion_lock:
        motion_queue.clear()         # clear pending steps
        motion["active"] = False 
        motion["targetSteps"] = motion["currentSteps"] 
        
    return jsonify(ok=True)

@app.post("/auto-control")
def auto_control():
    data = request.get_json() or {}
    cmd = data.get("command")

    if cmd == "START":
        print("Auto START")
    elif cmd == "STOP":
        print("Auto STOP")

    return jsonify(ok=True)

@app.route('/video_feed')
def video_feed():
    return Response(stream_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')


# decides whether camera toggle is on or not
# @app.post("/toggle-cam")
# def toggle_cam():
#     global camera_active
#     data = request.get_json() or {}
#     camera_active = data.get("active", False)
#     print(f"Camera state: {camera_active}")
#     return jsonify(ok=True)

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
    last_payload = None

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
        if payload != last_payload:
            ws_broadcast(payload)
            last_payload = payload

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
        init_gpio()
        audio_stream = audio_stream_start()

        
    # start web server
    app.run(host="0.0.0.0", port=8080, debug=True)
