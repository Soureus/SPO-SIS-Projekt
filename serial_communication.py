import matplotlib
matplotlib.use("TkAgg")

import serial
import decode_bin as decode
import matplotlib.pyplot as plt
import numpy as np

def connect(port: str, baudrate = 115200, timeout = 1.0):
    with serial.Serial(port, baudrate, timeout=timeout) as ser:
        print("Connected.")
        
        buffer = b""
        gyro_packets = []
        acc_packets = []
        mag_packets = []

        plt.ion()
        fig, axs = plt.subplots(3, 1, figsize=(10, 8))
        
        try:
            packet_counter = 0
            last_plot_packet_counter = 0
            while True:
                data_chunk = ser.read(64)
                if not data_chunk:
                    continue
                
                buffer += data_chunk
                raw_packets_bytes, buffer = decode.extract_packets_from_buffer(buffer)
                
                for raw_packet_bytes in raw_packets_bytes:
                    try:
                        rp = decode.separate_data(raw_packet_bytes)
                        packets = decode.raw_packet_to_packet(rp)
                        
                        for p in packets:
                            if p.id == 0x01:
                                gyro_packets.append(p)
                            elif p.id == 0x02:
                                acc_packets.append(p)
                            elif p.id == 0x03:
                                mag_packets.append(p)
                        
                        packet_counter += 1
                            
                    except ValueError as e:
                        print(f"Skipping invalid packet: {e}")
                if packet_counter - last_plot_packet_counter >= 10:
                    last_plot_packet_counter = packet_counter
                    axs[0].cla()
                    axs[1].cla()
                    axs[2].cla()
    
                    if gyro_packets:
                        fvz_gyro, y_gyro = decode.sestavi_podatke(gyro_packets, 0.1)
                        t_gyro = np.arange(len(y_gyro)) / fvz_gyro if fvz_gyro > 0 else np.arange(len(y_gyro))
                        axs[0].plot(t_gyro, y_gyro[:, 0], label="x")
                        axs[0].plot(t_gyro, y_gyro[:, 1], label="y")
                        axs[0].plot(t_gyro, y_gyro[:, 2], label="z")
                        axs[0].set_title(f"Gyroscope (fs={fvz_gyro:.2f} Hz)")
                        axs[0].legend()
                        axs[0].grid()
    
                    if acc_packets:
                        fvz_acc, y_acc = decode.sestavi_podatke(acc_packets)
                        t_acc = np.arange(len(y_acc)) / fvz_acc if fvz_acc > 0 else np.arange(len(y_acc))
                        axs[1].plot(t_acc, y_acc[:, 0], label="x")
                        axs[1].plot(t_acc, y_acc[:, 1], label="y")
                        axs[1].plot(t_acc, y_acc[:, 2], label="z")
                        axs[1].set_title(f"Accelerometer (fs={fvz_acc:.2f} Hz)")
                        axs[1].legend()
                        axs[1].grid()
    
                    if mag_packets:
                        fvz_mag, y_mag = decode.sestavi_podatke(mag_packets)
                        t_mag = np.arange(len(y_mag)) / fvz_mag if fvz_mag > 0 else np.arange(len(y_mag))
                        axs[2].plot(t_mag, y_mag[:, 0], label="x")
                        axs[2].plot(t_mag, y_mag[:, 1], label="y")
                        axs[2].plot(t_mag, y_mag[:, 2], label="z")
                        axs[2].set_title(f"Magnetometer (fs={fvz_mag:.2f} Hz)")
                        axs[2].legend()
                        axs[2].grid()
    
                    plt.tight_layout()
                    fig.canvas.draw()
                    fig.canvas.flush_events()
                    plt.pause(0.01)

        except KeyboardInterrupt:
           print("Stopped by user.")

        finally:
            plt.ioff()
            plt.close('all')
            print("Disconnected.")

                        
            
            
    