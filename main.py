import decode_bin as decode
import matplotlib.pyplot as plt
import serial_communication as serial
import numpy as np
import string


PORT = "/dev/ttyACM0"
BAUDRATE = 115200
TIMEOUT = 1.0

def prikazi_signal(signal: np.ndarray, naslov: string, startInd: int = None, endInd: int = None, t: np.ndarray = None):
    if signal.size == 0:
        print("Empty Signal")
        return
    if len(t) != len(signal):
        print("Invalid data inputted")
        return
    
    if startInd is None:
        startInd = 0
    if endInd is None:
        endInd = len(signal)
        
    sig_show = signal[startInd:endInd]
    
    if t is not None:
        x = t[startInd:endInd]
        x_label = "Time [s]"
    else:
        x = np.arange(startInd, endInd)
        x_label = "sample index"
    
    plt.figure(figsize=(10,4))
    
    if sig_show.ndim == 1:
        plt.plot(x, sig_show, label = "signal")
    else:
        labels = ["x", "y", "z"]
        for i in range(sig_show.shape[1]):
            label = labels[i] if i < len(labels) else f"dim {i}"
            plt.plot(x, sig_show[:, i], label=label)
            
    if naslov is not None:
        plt.title(naslov)
        
    plt.xlabel(x_label)
    plt.ylabel("Value")
    plt.legend()
    plt.grid()
    
    plt.show()
    
def draw_from_file(filename: string):
    with open(filename, "rb") as f:
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
    
    prikazi_signal(y_gyro, f"Gyro (Calculated sampling rate {fvz_gyro:.3f} Hz)", t = t_gyro)
    prikazi_signal(y_acc, f"Gyro (Calculated sampling rate {fvz_acc:.3f} Hz)", t = t_acc)
    prikazi_signal(y_mag, f"Gyro (Calculated sampling rate {fvz_mag:.3f} Hz)", t = t_mag)
    

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

if __name__ == "__main__":
    serial.connect(PORT, BAUDRATE, TIMEOUT)
    
    #draw_from_file("naloga_1_log.BIN")
    
    
        
    