import PySpin
import numpy as np
import os
import io
from PIL import Image # This is much lighter than OpenCV

os.environ['OPENBLAS_CORETYPE'] = 'ARMV8'

class FLIRCamera:
    def __init__(self):
        self.system = PySpin.System.GetInstance()
        self.cam_list = self.system.GetCameras()
        self.processor = PySpin.ImageProcessor() # Create processor
        
        if self.cam_list.GetSize() == 0:
            self._cleanup()
            raise RuntimeError("No FLIR cameras detected.")
        
        self.cam = self.cam_list[0]
        self.cam.Init()
        self._setup_settings()

    def _setup_settings(self):
        s_nodemap = self.cam.GetTLStreamNodeMap()
        handling_mode = PySpin.CEnumerationPtr(s_nodemap.GetNode('StreamBufferHandlingMode'))
        if PySpin.IsWritable(handling_mode):
            handling_mode.SetIntValue(handling_mode.GetEntryByName('NewestOnly').GetValue())

    def start(self):
        if not self.cam.IsStreaming():
            self.cam.BeginAcquisition()

    def get_frame(self):
        """Captures frame and converts to JPEG using PIL instead of OpenCV."""
        try:
            image_result = self.cam.GetNextImage(1000)
            if image_result.IsIncomplete():
                image_result.Release()
                return None
            
            # Use Spinnaker to convert the raw image to a standard Mono8 format
            image_converted = self.processor.Convert(image_result, PySpin.PixelFormat_Mono8)
            
            # Get the data as a numpy array
            frame_nd = image_converted.GetNDArray()
            
            # Use PIL to save the array to a byte buffer as a JPEG
            img = Image.fromarray(frame_nd)
            buf = io.BytesIO()
            img.save(buf, format='JPEG')
            jpeg_bytes = buf.getvalue()

            image_result.Release()
            return jpeg_bytes
        except Exception as e:
            print(f"Frame Grab Error: {e}")
            return None

    def stop(self):
        if hasattr(self, 'cam') and self.cam.IsStreaming():
            self.cam.EndAcquisition()
        if hasattr(self, 'cam'):
            self.cam.DeInit()
            del self.cam
        self.cam_list.Clear()
        self.system.ReleaseInstance()