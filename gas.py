#!/usr/bin/env python3
import serial
import time
import requests
import threading
import logging
import hashlib
import uuid

SERIAL_PORT = '/dev/ttyAMA0'
BAUDRATE = 9600
TIMEOUT = 1
BACKEND_URL = 'https://api.xiwuzc.tech/iot/iot/sensing/sensor/data'
PACKET_HEADER = "3c02"
PACKET_SIZE = 32
TENANT_ID = 10002
COWSHED_NUMBER = 4
DEVICE_NUM = 2
SEND_INTERVAL = 10  # seconds

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s: %(message)s')

def get_mac_address():
    mac = uuid.getnode()
    mac_str = f"{mac:012x}"
    return ':'.join(mac_str[i:i + 2] for i in range(0, len(mac_str), 2))

def hash_mac_address(mac_address):
    hash_object = hashlib.sha1(mac_address.encode())
    return hash_object.hexdigest()

def send_data_to_backend(payload):
    try:
        headers = {'Content-Type': 'application/json'}
        response = requests.post(BACKEND_URL, json=payload, headers=headers)
        response.raise_for_status()
        logging.info(f'Success: {response.status_code}, Data sent: {payload}')
    except requests.exceptions.RequestException as e:
        logging.error(f'HTTP Request failed: {e}')

def process_data(line):
    hex_str = line.hex()
    logging.debug(f"Received hex string: {hex_str}, size: {len(hex_str)}")
    if len(hex_str) >= PACKET_SIZE and hex_str.startswith(PACKET_HEADER):
        pairs = [hex_str[i:i + 2] for i in range(0, PACKET_SIZE, 2)]
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
            payload = {
                'CO2': str(co2),
                'Ch2O': str(ch2o),
                'TVOC': str(tvoc),
                'PM25': str(pm25),
                'PM10': str(pm10),
                'Temperature': f'{temp_high}.{temp_low}',
                'Humidity': f'{humidity_high}.{humidity_low}',
                'tenantId': TENANT_ID,
                'cowshedNumber': COWSHED_NUMBER,
                'devCode': f'{hash_mac_address(get_mac_address())}_{DEVICE_NUM}',
            }
            logging.info(payload)
            return payload
        except ValueError as ve:
            logging.error(f'ValueError: {ve} while processing pairs: {pairs}')
    return None

def main():
    try:
        ser = serial.Serial(SERIAL_PORT, baudrate=BAUDRATE, timeout=TIMEOUT)
        last_send_time = time.time()
        while True:
            if ser.in_waiting > 0:
                line = ser.readline().strip()
                if line:
                    payload = process_data(line)
                    if payload and (time.time() - last_send_time >= SEND_INTERVAL):
                        logging.info('Sending gas data to server...')
                        thread = threading.Thread(target=send_data_to_backend, args=(payload,))
                        thread.start()
                        last_send_time = time.time()
            else:
                time.sleep(0.3)
    except serial.SerialException as e:
        logging.error(f"Serial error: {e}")
    except KeyboardInterrupt:
        logging.info("Exiting program")
    finally:
        try:
            ser.close()
        except Exception:
            pass

if __name__ == "__main__":
    main()
    # print(f"MAC Address: {hash_mac_address(get_mac_address())}")