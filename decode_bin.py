import numpy as np
import struct
from dataclasses import dataclass

@dataclass
class Packet:
    """Actuall packet object including everything we need for final data visuilization"""
    id: int
    ts: float
    data: np.ndarray
    
@dataclass
class raw_packet:
    """Fully decoded raw packet"""
    packet_counter: int
    timestamp: int
    packet_size: int
    chunk_bytes: bytes
    crc16: int

SYNC = b"\xFF\xFF"

SENSOR_FORMATS = {
    0x01: {"dtype": np.int16, "coords": 3, "bytes_per_value": 2, "scale": 0.00875, "unit": "deg/s"},
    0x02: {"dtype": np.int16, "coords": 3, "bytes_per_value": 2, "scale": 0.001,   "unit": "g"},
    0x03: {"dtype": np.int16, "coords": 3, "bytes_per_value": 2, "scale": 0.15,    "unit": "mGauss"},
}

def split_packets(raw: bytes) -> list[bytes]:
    """
    Takes recorded bytes as input parameter and returns seperated packets
    
    Return type: list[bytes]
    Each list entry is one seperated packet
    """
    starts = []
    for i in range(len(raw) - 1):
        if raw[i: i+2] == SYNC: #IE dva prebrana byta sta 0xFF in 0xFF
            starts.append(i)    #Shrani vse zacetne lokacije paketov, toraj raw[starts[0]] bo zacetek prvega paketa
            
    packets = []
    for i in range(len(starts) - 1): #loops through first all packets but the last one (we don't know where it ends yet, because we can't just read until the start of the next one)
        packets.append(raw[starts[i]:starts[i+1]]) #en entry v packets bodo vsi byty od konca prejsnjega do zacetka naslednjega paketa
        
    return packets

def unstuff_bytes(data: bytes) -> bytes:
    """
    Takes stuffed bytes as input and returns unstuffed bytes
    """
    out = bytearray()
    i = 0
    
    while i < len(data):
        if data[i] == 0xFE:
            if i+1 >= len(data):
                raise ValueError("Uncompleted stuffing sequence")
            out.append(0xFE ^ data[i+1])
            i += 2
        else:
            out.append(data[i])
            i += 1
            
    return bytes(out)

def parse_data(recorded_data: bytes) -> struct:
    """DEPRICATED - Does not work with current workflow, left here for easier understanding of protocol"""
    packets = split_packets(recorded_data)
    
    fvz_gyro, y_gyro = create_sensor_matrix(packets, 0x01, 0.00875)
    fvz_acc, y_acc = create_sensor_matrix(packets, 0x02, 0.001)
    fvz_mag, y_mag = create_sensor_matrix(packets, 0x03, 0.15)
    
    t_gyro = np.arange(len(y_gyro)) / fvz_gyro if fvz_gyro > 0 else np.array([], dtype=np.float32)
    t_acc = np.arange(len(y_acc)) / fvz_acc if fvz_acc > 0 else np.array([], dtype=np.float32)
    t_mag = np.arange(len(y_mag)) / fvz_mag if fvz_mag > 0 else np.array([], dtype=np.float32)
    
    return{
        "fvz_gyro": fvz_gyro,
        "y_gyro": y_gyro,
        "t_gyro": t_gyro,
        
        "fvz_acc": fvz_acc,
        "y_acc": y_acc,
        "t_acc": t_acc,
        
        "fvz_mag": fvz_mag,
        "y_mag": y_mag,
        "t_mag": t_mag
        }
    
    
def decode_recording(recorded_data: bytes) -> tuple[list[raw_packet], list[Packet]]:
    raw_packet_bytes = split_packets(recorded_data)
    
    decoded_raw_packets = []
    for packet_bytes in raw_packet_bytes:
        try:
            rp = separate_data(packet_bytes)
            decoded_raw_packets.append(rp)
        except ValueError as e:
            print(f"Skipping invalid packet: {e}")
            
    missing = check_missing_packets(decoded_raw_packets)
    if missing:
        print("Missing packet jumps detected: ")
        for expected, actuall in missing:
            print(f"Expected {expected}, got {actuall}")
            
    all_packets = []
    for rp in decoded_raw_packets:
        all_packets.extend(raw_packet_to_packet(rp))
        
    return decoded_raw_packets, all_packets
    
def get_sensor_samples(packet: bytes, sensor_id: int) -> tuple[int, list[list[int]]]:
    """
    Takes a packet and returns packet timestamp + all samples for one sensor
    i.e [timestamp, [[x,y,z], [x,y,z], ... ]]
    
    Return type: tuple[int, int[list[int]]]
    """
    
    packet_data = separate_data(packet);
    chunks = split_chunks(packet_data["chunk_bytes"])
    
    packet_samples = []
    
    for chunk in chunks:
        if chunk["chunk_id"] == sensor_id:
            samples = parse_chunk_data(chunk["chunk_data"])
            packet_samples.extend(samples)
            
    return packet_data["timestamp"], packet_samples

def create_sensor_matrix(packets: list[bytes], sensor_id: int, scale:float) -> tuple[float, np.ndarray]:
    """
    DEPRICATED - Do not use
    Takes in all recorded packets, creates a full data matrix for one sensor and calculates it's sampling frequency
    
    Returns: [Fvz: float, data_matrix: (N, 3)]
    """
    all_samples = []
    freqs = []
    
    prev_timestamp = None
    
    for packet in packets:
        try:
            timestamp, packet_samples = get_sensor_samples(packet, sensor_id)
        except ValueError:
            continue
        
        all_samples.extend(packet_samples)
        
        if prev_timestamp != None:
            delta_T = timestamp - prev_timestamp
            nvz = len(packet_samples)
            
            if nvz > 0 and delta_T > 0:
                fvz = nvz * 1000 / delta_T
                freqs.append(fvz)
        
        prev_timestamp = timestamp
        
    data = np.array(all_samples, dtype=np.float32)
    data *= scale
    
    avg_fvz = float(np.mean(freqs)) if freqs else 0.0
    
    return avg_fvz, data

def sestavi_podatke(packet_list: list[Packet]) -> tuple[float, np.ndarray]:
    """
    Takes in a list of already parsed packets and returns sampling frequency and a full signal matrix
    
    Return: [fvz, signal]
    """
    if not packet_list:
        return 0.0, np.empty((0, 3), dtype=np.float32)
    
    all_data = []
    tpacket_values = []
    nvz_values = []
    
    for i, packet in enumerate(packet_list):
        all_data.append(packet.data)
        
        if i > 0:
            dt = packet.ts - packet_list[i-1].ts
            if dt > 0:
                tpacket_values.append(dt)
                nvz_values.append(packet.data.shape[0])
                
    signal = np.vstack(all_data).astype(np.float32)
    
    if tpacket_values and nvz_values:
        avg_tpacket = float(np.mean(tpacket_values))
        avg_nvz = float(np.mean(nvz_values))
        fvz = avg_nvz / avg_tpacket
    else:
        fvz = 0.0
        
    return fvz,signal
        

def parse_chunk_data(chunk_data: bytes, sensor_id: int) -> np.ndarray:
    """
    
    Takes in chunk_data and sensor id, then parses it into a matrix of samples for that specific sensor
    
    Return type: np.ndarray(-1, coord_amt)
    """
    
    if sensor_id not in SENSOR_FORMATS:
        raise ValueError(f"Unsopported sensor id: {sensor_id}:#x")
    
    fmt = SENSOR_FORMATS[sensor_id]
    coords = fmt["coords"]
    bpv = fmt["bytes_per_value"]
    sample_size = coords * bpv
    scale = fmt["scale"]
    
    if len(chunk_data) % sample_size != 0:
        raise ValueError("Chunk data not aligned to sample size")
        
    if fmt["dtype"] == np.int16:
        data = np.frombuffer(chunk_data, dtype="<i2") #read two bytes from chunk_data
    else:
        raise ValueError("Usupported dtype")
        
    data = data.reshape(-1, coords).astype(np.float32)
    data *= scale
    
    return data

def split_chunks(chunk_bytes: bytes) -> list[dict]:
    """
    Takes all chunk bytes from packet as parameter, returns a list of all of the different chunks in the packet
    
    Return type: list[dict]
    dict{
        "chunk_id"
        "reserved"
        "chunk_data"
        }
    """
    i = 0
    chunks = []
    while i < len(chunk_bytes):
        chunk_id = chunk_bytes[i]
        chunk_size = int.from_bytes(chunk_bytes[i+1: i+3], "little") + 1
        reserved = chunk_bytes[i+3]
        
        start = i+4
        end = start + chunk_size
        
        if end > len(chunk_bytes):
            raise ValueError("Chunk Out Of Bounds")
            
        chunk_data = chunk_bytes[start:end]
        
        chunks.append({
                "chunk_id": chunk_id,
                "reserved": reserved,
                "chunk_data": chunk_data
            })
        i = end
    return chunks
        

def separate_data(data: bytes) -> raw_packet:
    """
    Takes packet Bytes as input paramater and returns a dictionary of seperated stored information
    
    Return type: raw_packet
    """
    sync_marker = data[0: 2]    #FFFF
    if sync_marker != SYNC:
        raise ValueError("Invalid sync marker!")
    packet_counter = data[2]    #uint8_t 0-253
    
    payload = unstuff_bytes(data[3:])   #the whole payload is stuffed so we unstuff first
    if len(payload) < 8:
        raise ValueError("Payload too short")
    
    timestamp_bytes = payload[0:4]
    packet_size_bytes = payload[4:6]
    chunk_bytes = payload[6:-2]
    CRC16_bytes = payload[-2:]
    
    timestamp = int.from_bytes(timestamp_bytes, "little")
    packet_size = int.from_bytes(packet_size_bytes, "little") + 1
    expected_size = 4 + 2 + packet_size + 2 #timestamp + len(packet_size) + size of chunks (packet_size) + CRC16
    
    if len(payload) != expected_size:
        raise ValueError("Payload length missmatch")
    
    received_crc16 = int.from_bytes(CRC16_bytes, "little")
    computed_crc16 = crc16_compute(payload[:-2])
    
    if received_crc16 != computed_crc16:
        raise ValueError(f"CRC missmatch: received=0x{received_crc16:04X}, computed=0x{computed_crc16:04X}")
    
    return raw_packet(
        packet_counter = packet_counter,
        timestamp = timestamp,
        packet_size = packet_size,
        chunk_bytes = chunk_bytes,
        crc16 = received_crc16
        )

def raw_packet_to_packet(i_raw_packet: raw_packet) -> list[Packet]:
    packets = []
    chunks = split_chunks(i_raw_packet.chunk_bytes)
    
    for chunk in chunks:
        chunk_id = chunk["chunk_id"]
        samples = parse_chunk_data(chunk["chunk_data"], chunk_id)
        
        if samples.size == 0:
            continue
        
        packets.append(Packet(
            id = chunk_id,
            ts = float(i_raw_packet.timestamp) / 1000.0, #convert to seconds
            data = samples
            ))
    return packets

def check_missing_packets(raw_packets: list[raw_packet]) -> list[tuple[int, int]]:
    """
    Takes in raw packets and returns a list of jumps.
    Return: list[[missing_packet_num, actuall packet_num]]
    actuall - missing = jump size
    """
    missing = []
    if not raw_packets:
        return missing
    
    prev = raw_packets[0].packet_counter
    for packet in raw_packets[1:]:
        expected = next_counter(prev)
        if packet.packet_counter != expected:
            missing.append((expected, packet.packet_counter))
        prev = packet.packet_counter
    return missing

def crc16_compute(data: bytes) -> int:
    crc = 0xFFFF
    
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc = crc >> 1
                
    return crc & 0xFFFF

def next_counter(counter: int) -> int:
    return 0 if counter == 253 else counter + 1





    
    