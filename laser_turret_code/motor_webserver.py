import socket
import RPi.GPIO as GPIO
import threading
import multiprocessing

from time import sleep
from shifter import Shifter
from motorcontrol import Stepper

GPIO.setmode(GPIO.BCM)


# Generate HTML for the web page:
def web_page():
    # taken & modified from ChatGPT
    html = f""" 
        <html>
        <body>

        <h2>Two-Axis Control (Pitch + Yaw)</h2>

        <!-- Angle Readouts -->
        <h3>Pitch Angle: <span id="pitch-angle">?</span>°</h3>
        <h3>Yaw Angle: <span id="yaw-angle">?</span>°</span></h3>

        <!-- Step Inputs -->
        <div>
          Pitch Step: <input id="pitch-step" type="number" value="50"><br><br>
          Yaw Step: <input id="yaw-step" type="number" value="50"><br><br>
        </div>

        <!-- Zero Buttons -->
        <button onclick="zeroAxis('pitch')">Zero Pitch</button>
        <button onclick="zeroAxis('yaw')">Zero Yaw</button>

        <br><br>

        <!-- D-Pad -->
        <table border="0" cellpadding="10">
          <tr>
            <td></td>
            <td><button onclick="movePitch(1)">▲ Pitch +</button></td>
            <td></td>
          </tr>
          <tr>
            <td><button onclick="moveYaw(-1)">◀ Yaw -</button></td>
            <td></td>
            <td><button onclick="moveYaw(1)">▶ Yaw +</button></td>
          </tr>
          <tr>
            <td></td>
            <td><button onclick="movePitch(-1)">▼ Pitch -</button></td>
            <td></td>
          </tr>
        </table>

        <script>
        // === POLLING ===
        async function updatePositions() {{
          try {{
            let res = await fetch("/pos");
            let data = await res.json();

            document.getElementById("pitch-angle").textContent = data.pitch;
            document.getElementById("yaw-angle").textContent = data.yaw;

          }} catch (e) {{
            console.log("Couldn't read positions");
          }}
        }}
        setInterval(updatePositions, 500);
        updatePositions();

        // === MOVE FUNCTIONS ===
        async function movePitch(direction) {{
          let step = Number(document.getElementById("pitch-step").value);
          await sendMove("pitch", direction * step);
        }}

        async function moveYaw(direction) {{
          let step = Number(document.getElementById("yaw-step").value);
          await sendMove("yaw", direction * step);
        }}

        async function sendMove(axis, delta) {{
          await fetch("/move", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ axis: axis, delta: delta }})
          }});
          updatePositions();
        }}

        // === ZERO AXIS ===
        async function zeroAxis(axis) {{
          await fetch("/zero", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ axis: axis }})
          }});
          updatePositions();
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
        # print('Waiting for connection...')
        conn, (client_ip, client_port) = s.accept()     # blocking call

        # post request stuff
        # print(f'Connection from {client_ip}')
        client_message = conn.recv(2048).decode('utf-8')

        if client_message.startswith('POST'): # only post messages !!!
            print(f'Message from client:\n{client_message}')

            data_dict = parsePOSTdata(client_message)
            try:
                axis = int(data_dict["axis"])
                delta = int(data_dict["delta"])

                if axis == "yaw":
                    m1.rotate(delta / 4096.0 * 360.0)
                elif axis == "pitch":
                    m2.rotate(delta / 4096.0 * 360.0)
            except Exception as e:  
                print("Parsing error: ", e)

        conn.send(b'HTTP/1.1 200 OK\n')         # status line
        conn.send(b'Content-type: text/html\r\n') # header (content type)
        conn.send(b'Connection: close\r\n\r\n') # header (tell client to close at end)
        # send body in try block in case connection is interrupted:
        try:
            conn.sendall(web_page())                  # body
        finally:
            conn.close()




# webserver setup
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # address reuse
s.bind(('', 8080))
s.listen(3)

webpageThread = threading.Thread(target=serve_web_page)
webpageThread.daemon = True
webpageThread.start()




# Motor control/setup
if __name__ == '__main__':

    shift_reg = Shifter(data=16,latch=20,clock=21)   # set up Shifter

    # Use multiprocessing.Lock() to prevent motors from trying to 
    # execute multiple operations at the same time:
    lock1 = multiprocessing.Lock()
    lock2 = multiprocessing.Lock()
    # Instantiate 2 Steppers:
    m1 = Stepper(shift_reg, lock1)
    m2 = Stepper(shift_reg, lock2)

    m1.zero()
    m2.zero()

    m1.goAngle(30)
    m1.goAngle(-30)
    m2.goAngle(30)
    m2.goAngle(-30)

    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
    try:
        while True:
            pass
    except KeyboardInterrupt:
        GPIO.cleanup() 
        print('Closing socket')
        s.close()
        print('Joining webpageThread')
        webpageThread.join()

