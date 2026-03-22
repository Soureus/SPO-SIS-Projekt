import decode_bin as decode
import matplotlib.pyplot as plt
import serial_communication as serial
import numpy as np


PORT = "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 1.0

if __name__ == "__main__":
    #serial.connect(PORT, BAUDRATE, TIMEOUT)
    
    with open("naloga_1_log.BIN", "rb") as f:
        raw = f.read()
        
    raw_packets, packets = decode.decode_recording(raw)
    
    gyro_packets = [p for p in packets if p.id == 0x01]
    acc_packets  = [p for p in packets if p.id == 0x02]
    mag_packets  = [p for p in packets if p.id == 0x03]
    
    fvz_gyro, y_gyro = decode.sestavi_podatke(gyro_packets)
    fvz_acc, y_acc   = decode.sestavi_podatke(acc_packets)
    fvz_mag, y_mag   = decode.sestavi_podatke(mag_packets)
    
    t_gyro = np.arange(len(y_gyro)) / fvz_gyro if fvz_gyro > 0 else np.array([], dtype=np.float32)
    t_acc = np.arange(len(y_acc)) / fvz_acc if fvz_acc > 0 else np.array([], dtype=np.float32)
    t_mag = np.arange(len(y_mag)) / fvz_mag if fvz_mag > 0 else np.array([], dtype=np.float32)
    

    fig, axs = plt.subplots(3, 1, figsize=(10, 8))

    # Gyro
    axs[0].plot(t_gyro, y_gyro[:, 0], label="x")
    axs[0].plot(t_gyro, y_gyro[:, 1], label="y")
    axs[0].plot(t_gyro, y_gyro[:, 2], label="z")
    axs[0].set_title("Gyroscope")
    axs[0].legend()
    axs[0].grid()
    
    #acc
    axs[1].plot(t_acc, y_acc[:, 0], label="x")
    axs[1].plot(t_acc, y_acc[:, 1], label="y")
    axs[1].plot(t_acc, y_acc[:, 2], label="z")
    axs[1].set_title("Accelerometer")
    axs[1].legend()
    axs[1].grid()
    
    # Magnetometer
    axs[2].plot(t_mag, y_mag[:, 0], label="x")
    axs[2].plot(t_mag, y_mag[:, 1], label="y")
    axs[2].plot(t_mag, y_mag[:, 2], label="z")
    axs[2].set_title("Magnetometer")
    axs[2].legend()
    axs[2].grid()
    
    plt.tight_layout()
    plt.show()
        
    