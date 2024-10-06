import requests
import websocket
import json
import socket
import fcntl
import struct
import time
from PIL import Image, ImageDraw, ImageFont
import Adafruit_SSD1306

# Initialize the OLED display (128x32)
disp = Adafruit_SSD1306.SSD1306_128_32(rst=None)

# Initialize library and clear the display
disp.begin()
disp.clear()
disp.display()

# Create a blank image for drawing
width = disp.width
height = disp.height
image = Image.new('1', (width, height))

# Get drawing object to draw on the image
draw = ImageDraw.Draw(image)

# Load default font
font = ImageFont.load_default()

# Global variables for status and indicator
cncjs_status = "Connecting..."
cncjs_port = 8000  # Default CNCjs port
visual_indicator = False  # For blinking dot

# Function to get IP address for wlan0
def get_ip_address(ifname):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        return socket.inet_ntoa(fcntl.ioctl(
            s.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack('256s', bytes(ifname[:15], 'utf-8'))
        )[20:24])
    except:
        return "No IP"

# Authenticate and retrieve the token from CNCjs using /api/signin
def authenticate():
    url = "http://localhost:8000/api/signin"
    headers = {'Content-Type': 'application/json'}
    data = {
        "name": "rpi",
        "password": "display"
    }
    try:
        response = requests.post(url, headers=headers, data=json.dumps(data))
        response.raise_for_status()
        return response.json()['token']  # Extract token from the response
    except requests.exceptions.RequestException as e:
        print(f"Authentication failed: {e}")
        return None

# WebSocket connection to CNCjs
def on_message(ws, message):
    global cncjs_status
    if "error" in message.lower():
        cncjs_status = "Error"
    elif "running" in message.lower():
        cncjs_status = "Running"
    else:
        cncjs_status = "Idle"

def on_error(ws, error):
    global cncjs_status
    cncjs_status = "WS Error"

def on_close(ws, close_status_code, close_msg):
    global cncjs_status
    cncjs_status = "Reconnecting"

def on_open(ws):
    global cncjs_status
    cncjs_status = "Connected"

# Function to display CNCjs status and wlan0 IP
def display_status_and_ip():
    global visual_indicator

    # Clear the display
    draw.rectangle((0, 0, width, height), outline=0, fill=0)

    # Get wlan0 IP address
    ip = get_ip_address('wlan0')

    # Move text up by adjusting Y-coordinates
    draw.text((8, -2), f"IP: {ip}", font=font, fill=255)
    draw.text((8, 10), f"CNCjs: {cncjs_status}", font=font, fill=255)
    draw.text((8, 22), f"Port: {cncjs_port}", font=font, fill=255)

    # Visual indicator (blinking dot)
    if visual_indicator:
        draw.text((118, 22), ".", font=font, fill=255)
    visual_indicator = not visual_indicator

    # Rotate the image and display it
    rotated_image = image.rotate(180)
    disp.image(rotated_image)
    disp.display()

# Function to handle WebSocket reconnection
def connect_websocket():
    while True:
        token = authenticate()
        if token:
            ws = websocket.WebSocketApp(
                f"ws://localhost:{cncjs_port}/socket.io/?EIO=3&transport=websocket&token={token}",
                on_message=on_message,
                on_error=on_error,
                on_close=on_close
            )
            ws.on_open = on_open
            ws.run_forever()
        else:
            print("Failed to authenticate, retrying in 5 seconds...")
            time.sleep(5)

if __name__ == "__main__":
    # Start WebSocket connection in the background
    import threading
    websocket_thread = threading.Thread(target=connect_websocket)
    websocket_thread.daemon = True
    websocket_thread.start()

    # Main loop to update display
    while True:
        display_status_and_ip()
        time.sleep(1)
