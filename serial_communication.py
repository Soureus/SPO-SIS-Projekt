import serial
import decode_bin as decode
import matplotlib.pyplot as plt

def connect(port: str, baudrate = 115200, timeout = 1.0):
    with serial.Serial(port, baudrate, timeout=timeout) as ser:
        print("Connected.")
        
        buffer = b""
        
        while True:
            data_chunk = ser.read(64)
            if data_chunk:
                buffer += data_chunk
            
    