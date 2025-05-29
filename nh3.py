import serial
import time
# Configuration
SERIAL_PORT = '/dev/ttyAMA0'  # This may vary based on your configuration
BAUD_RATE = 9600               # Change as per your device's settings
TIMEOUT = 1                    # Timeout in seconds
# Initialize serial connection
ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=TIMEOUT)
buffer = ''
try:
    # Give some time for the serial connection to initialize
    time.sleep(2)
    
    while True:
        if ser.in_waiting > 0:  # Check if there is data available to read
            rawdata = ser.readline().rstrip()
            hex_str = rawdata.hex()
            buffer += hex_str
            if len(buffer) >= 32 and buffer.startswith('3c02'):
                pairs = [hex_str[i:i + 4] for i in range(0, 32, 4)]
                print(f"Received: {hex_str}, size: {len(hex_str)}")
                high = int(pairs[2], 16)
                low = int(pairs[3], 16)
                print(f'pairs: {pairs}')
                print(f'NH3 : {high * 256 + low}')
                buffer = ''
except KeyboardInterrupt:
    print("Exiting...")
finally:
    ser.close()  # Ensure that the serial port is closed on exit
