# used webserver_threaded.py and web_gpio_POST.py as templates to start from
# website made with assistance from chatGPT

import socket
import RPi.GPIO as GPIO
import threading
from time import sleep
from motorcontrol import Stepper

GPIO.setmode(GPIO.BCM)

# Generate HTML for the web page:
def web_page():
    # taken & modified from ChatGPT
    html = f""" 
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Motor Control</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .led-control {{ margin-bottom: 20px; }}
                label {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <h1>Motor Control</h1>

            <div class="motor-control">
                <label for="m1">Motor 1 (Yaw):</label>
                <input type="range" id="m1" min="0" max="100" value="0">
                <span id="val0">0</span>%
            </div>

            <div class="motor-control">
                <label for="m2">Motor 2 (Pitch:</label>
                <input type="range" id="m2" min="0" max="100" value="0">
                <span id="val1">0</span>%
            </div>

            <script>
                function updateAngles(motor, angle) {{
                    fetch("/", {{
                        method: "POST",
                        headers: {{ "Content-Type": "application/x-www-form-urlencoded" }},
                        body: `selected_motor=${{motor}}&angle=${{angle}}`
                    }})
                    .then(response => response.text())
                    .then(data => {{
                        console.log(`Motor ${{motor}} pointed towards to ${{angle}}`);
                    }})
                    .catch(error => console.error("Error:", error));
                }}

                // Attach input event listeners to all sliders
                for (let i = 1; i < 3; i++) {{
                    const slider = document.getElementById(`motor${{i}}`);
                    const valueSpan = document.getElementById(`val${{i}}`);

                    slider.addEventListener("input", function() {{
                        const angle = slider.value;
                        valueSpan.textContent = angle; // Update displayed value
                        updateAngles(i, angle);           // Send POST request
                    }});
                }}
            </script>
        </body>
        </html>
        """

    return (bytes(html,'utf-8'))   # convert html string to UTF-8 bytes object

# Helper function to extract key,value pairs of POST data
def parsePOSTdata(data):
    data_dict = {}
    idx = data.find('\r\n\r\n')+4
    data = data[idx:]
    data_pairs = data.split('&')
    for pair in data_pairs:
        key_val = pair.split('=')
        if len(key_val) == 2:
            data_dict[key_val[0]] = key_val[1]
    return data_dict

# Serve the web page to a client on connection:
def serve_web_page():
    while True:
        print('Waiting for connection...')
        conn, (client_ip, client_port) = s.accept()     # blocking call

        # post request stuff
        print(f'Connection from {client_ip}')
        client_message = conn.recv(2048).decode('utf-8')
        print(f'Message from client:\n{client_message}')

        if client_message.startswith('POST'): # only post messages !!!
            data_dict = parsePOSTdata(client_message)
            try:
                motor = int(data_dict["motor"]) # which LED to change
                angle = int(data_dict["angle"]) # value from slider
            except Exception as e:  
                print("parsing error:", e)

        conn.send(b'HTTP/1.1 200 OK\n')         # status line
        conn.send(b'Content-type: text/html\r\n') # header (content type)
        conn.send(b'Connection: close\r\n\r\n') # header (tell client to close at end)
        # send body in try block in case connection is interrupted:
        try:
            conn.sendall(web_page())                  # body
        finally:
            conn.close()

# socket !!!
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # address reuse
s.bind(('', 8080))
s.listen(3)

webpageThread = threading.Thread(target=serve_web_page)
webpageThread.daemon = True
webpageThread.start()


if __name__ == '__main__':

    s = Shifter(data=16,latch=20,clock=21)   # set up Shifter

    # Use multiprocessing.Lock() to prevent motors from trying to 
    # execute multiple operations at the same time:
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()
    # Instantiate 2 Steppers:
    m1 = Stepper(s, lock1)
    m2 = Stepper(s, lock2)

    #lab 8 part 3
    m1.zero() 
    m2.zero() 
    m1.goAngle(45) 
    m1.goAngle(45)
    print("done")
    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
    try:
        while True:
            pass
    except:
        print('\nend')

try:
    while True:
        sleep(1)
        # print('.')

except KeyboardInterrupt:
    print('Closing socket')
    s.close()
    GPIO.cleanup() 
    print('Joining webpageThread')
    webpageThread.join()