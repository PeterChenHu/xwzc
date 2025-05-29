#!/usr/bin/env python3   
import serial
import time
import requests
import threading
ser = serial.Serial('/dev/ttyAMA0', baudrate=9600, timeout=1)
backend_url = 'https://api.xiwuzc.tech/iot/iot/sensing/sensor/data'
buffer = ''
payload = None
lock = threading.Lock()
last_send_time = time.time()
def send_data_to_backend(payload):
    try:
        headers = {
            'Content-Type': 'application/json',
        }
        response = requests.post(backend_url, json=payload, headers=headers)
        response.raise_for_status()
        print(f'Success: {response.status_code}, Data sent: {payload}')
    except requests.exceptions.RequestException as e:
        print(f'HTTP Request failed: {e}')
def process_data(line):
    global buffer
    hex_str = line.hex()
    print(f"Received hex string: {hex_str}, size: {len(hex_str)}")
    buffer += hex_str
    print(f'Current Buffer: {buffer}, buffer size {len(buffer)}')
    if len(buffer) >= 32 and buffer.startswith("3c02"):
        pairs = [buffer[i:i + 2] for i in range(0, 32, 2)]
        #print(f'Pairs: {pairs}')
        buffer = ''
        print(f'clean up buffer.... size: {len(buffer)}')
        try:
            co2 = int(pairs[2] + pairs[3], 16)
            ch2o = int(pairs[4] + pairs[5], 16)
            tvoc = int(pairs[6] + pairs[7], 16)
            pm25 = int(pairs[8] + pairs[9], 16)
            pm10 = int(pairs[10] + pairs[11], 16)
            temp_high = int(pairs[12], 16)
            temp_low = int(pairs[13], 16)
            humidity_high = int(pairs[14], 16)
            humidity_low = int(pairs[15], 16)
            double_humid = float(f'{humidity_high}.{humidity_low}')
            payload = {
                'CO2': f'{co2}',
                'Ch2O': f'{ch2o}',
                'TVOC': f'{tvoc}',
                'PM25': f'{pm25}',
                'PM10': f'{pm10}',
                'Temperature': f'{temp_high}.{temp_low}',
                'Humidity': f'{humidity_high}.{humidity_low}'
            }
            print(payload)
            
            return payload
        except ValueError as ve:
            print(f'ValueError: {ve} while processing pairs: {pairs}')
    return None
try:
    while True:
        if ser.in_waiting > 0:
            line = ser.readline().strip()
            if line:
                payload = process_data(line)
                if payload is not None:
                    if time.time() - last_send_time >= 300:
                        with lock:
                            print('sending gas data to server...')
                            thread = threading.Thread(target=send_data_to_backend, args=(payload,))
                            thread.start()
                        last_send_time = time.time()
                        
        else:
            time.sleep(0.2)
except KeyboardInterrupt:
    print("Exiting program")
finally:
    ser.close()
