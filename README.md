**Project Summary**

This project automates the motion of a photolithography stage to achieve micron-scale precision using a piezoelectric slip-stick mechanism. A Raspberry Pi based control system generates differential sawtooth signals that drive a custom PCB and piezoelectric stack, enabling precise and repeatable stage movement. The system is operated through a real-time GUI which allows users to control motion, and was validated through testing with an average step size of 1.36 microns. Key project components are organized in this repository. The main control and backend logic can be found in the Python files , while the frontend interface is located in the frontend/ directory. Mechanical designs are in the solidworks/ folder, and all PCB designs and related files are packaged in capstone.zip.

**Running the Project**

1. Navigate to the project root directory.
2. Install required dependencies:
   
  pip install -r requirements.txt
  
3. Run the backend server:

  python app.py
  
4.Open a browser and go to:

  http://localhost:5000
  
5. Use the GUI to control and monitor the system.
