import cv2
import numpy as np
from math import hypot
import threading

prev_info = [
    "Frame center: -",
    "Rect center: -",
    "delta_x= -, delta_y= -, dist= -, - of diag",
    "Centered: -"
]

info_lock = threading.Lock()

# update prev info lines
def set_last_info(lines):
    global prev_info
    with info_lock:
        prev_info = list(lines)

# return prev info lines
def get_last_info():
    with info_lock:
        return list(prev_info)
    
def gen_frames():
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        print("Could not open camera")
        return
    
    while True:
        ret, frame = cap.read()    # read() grabs, decodes, and stores the next frame
                                # Returns false if no frames are grabbed
        if not ret:
            print("Failed to grab frame")
            break
    
        # img stores an output array from cap.read() because the frame is
        # simply an array and we want to extract the first two properties,
        # height and width, which is exactly what img.shape[:2] is doing.
        h, w = frame.shape[:2]   
        fx, fy = w // 2, h // 2 # Calculate the center by doing integer division
    
        # cvtColor() converts the frame from BGR (3 channels for Blue, Green, Red)
        # to grayscale (1 channel for gray). Edge detection algorithms depend on
        # changes in intensity and color adds more noise.
        # Grayscale makes the edge detection cleaner and more efficient.
        gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    
        # GaussianBlur() applies a filter to the grayscale frame. In this case the
        # Filter size is 5x5 pixels and it will reduce noise before edge detection.
        # The 0 means that OpenCV will automatically calculate the kernel standard
        # deviation in the x and y direction. In other words, makes this easy to use.
        blur  = cv2.GaussianBlur(gray, (5, 5), 0)
    
        # Canny() takes the input array, in this case the blurred grayscale.
        # It outputs the edges based on the input threshold 1 and threshold 2.
        # These thresholds can be tuned to exclude weaker edges
        edges = cv2.Canny(blur, 10, 70)
    
        # getStructuringElement() Returns a structuring element of the specified
        # size and shape for morphological operations. Element shape that could be
        # one of MorphShapes in this case MORPH_RECT.
        # Size of the structuring element is 5x5.
        k = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    
        # dilate() Dilates an image by using a specific structuring element. Here
        # we are using the edges images as input, the MORPH_RECT as the structuring
        # element, and we apply the dilation 2 times.
        mask = cv2.dilate(edges, k, iterations=2)
    
        # morphologyEx() Performs advanced morphological transformations using
        # dilation as a basic operation. Here, the input is the dilated image based
        # on the rectangular structing element and it's going to try and find a
        # closed morphology related to that mask. It will apply this one time.
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)
    
        # The function retrieves contours from the binary image using the algorithm
        # The contours are a useful tool for shape analysis and object detection
        # and recognition. If successful, it returns an array describing the
        # detected contours.
        cnts, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
        out = frame.copy() # copy the rectangle to a new array
    
        # draw frame center crosshair in the center of the camera frame (fx, fy)
        cv2.drawMarker(out, (fx, fy), (255, 0, 0), markerType=cv2.MARKER_CROSS,
                    markerSize=20, thickness=2)
    
        info1 = f"Frame center: ({fx}, {fy})"
        info2 = "Rect center:  (-, -)"
        info3 = "No rectangle detected"
        info4 = "Centered: -"

        if cnts:
            # Select the contour with the largest area
            c = max(cnts, key=cv2.contourArea)
    
            # Compute the closed contour perimeter
            peri = cv2.arcLength(c, True)
    
            # Approximate the contour with a polygon whose points can deviate
            # from the contour by up to 2% of its perimeter
            approx = cv2.approxPolyDP(c, 0.02 * peri, True)
            
            # Compute the minimum-area bounding rotated rectangle.
            # If the approximation yields 4 vertices, use it
            rect = cv2.minAreaRect(approx if len(approx) == 4 else c)
    
            # Finds the four vertices of a rotated rect.
            # Useful to draw the rotated rectangle.
            box = cv2.boxPoints(rect).astype(int)
    
            # Draws several polygonal curves.
            cv2.polylines(out, [box], True, (0, 255, 0), 3)
    
            # Gets the center of the rectanlge
            (cx, cy), (w, h), angle = rect
            cx, cy = int(cx), int(cy) # Rounds the center to integer pixels
    
            # draw center and connector
            cv2.circle(out, (cx, cy), 6, (0, 0, 255), -1)
            cv2.line(out, (fx, fy), (cx, cy), (0, 255, 255), 2)
    
            # deltas and similarity
            dx, dy = cx - fx, cy - fy
            dist = hypot(dx, dy)
            diag = hypot(w, h)
            pct = 100.0 * dist / diag
    
            # simple centered flag
            tol_px = max(20, 0.02 * diag)             # 20 px or 2 percent of diagonal
            centered = dist < tol_px

            info2 = f"Rect center:  ({cx}, {cy})"
            info3 = (
                f"delta_x={dx:+d}, delta_y={dy:+d}, "
                f"dist={dist:.1f}px, {pct:.2f}% of diag"
            )
            info4 = f"Centered: {centered}"
    
            y0 = 30

        set_last_info([info1, info2, info3, info4])

        ok, buffer = cv2.imencode('.jpg', out)
        if not ok:
            continue

        jpg_bytes = buffer.tobytes()
        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + jpg_bytes + b'\r\n'
        )
    
    cap.release()