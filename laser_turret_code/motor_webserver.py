import json
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

        <h2>Motor Control</h2>

        <!-- Angle Readouts -->
        <h3>Pitch Angle: <span id="pitch-angle">?</span>°</h3>
        <h3>Yaw Angle: <span id="yaw-angle">?</span>°</h3>

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
        <table border="1" cellpadding="5">
          <tr>
            <td></td>
            <td><button onclick="movePitch(1)">↑</button></td>
            <td></td>
          </tr>
          <tr>
            <td><button onclick="moveYaw(-1)">←</button></td>
            <td></td>
            <td><button onclick="moveYaw(1)">→</button></td>
          </tr>
          <tr>
            <td></td>
            <td><button onclick="movePitch(-1)">↓</button></td>
            <td></td>
          </tr>
        </table>

        <script>
        // === polling ===
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

        // === move functions ===
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

        // === zero axes ===
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

# ==========================
# New parser w/ JSON
# ==========================
def parseJSONbody(data):
    # Find body start
    idx = data.find('\r\n\r\n') + 4
    body = data[idx:]
    try:
        return json.loads(body)
    except Exception:
        return {}

# ==========================
# Serve the web page to a client on connection:
# ==========================
def serve_web_page():
    while True:
        # print('Waiting for connection...')
        conn, (client_ip, client_port) = s.accept()     # blocking call

        # post request stuff
        # print(f'Connection from {client_ip}')
        client_message = conn.recv(2048).decode('utf-8')

        request_line = client_message.split('\n')[0]
        method, path, _ = request_line.split()

        if path == "/pos":
            response = json.dumps({
               "pitch": m2.getAngle(),
               "yaw": m1.getAngle()
            })
            conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\n\r\n")
            conn.send(response.encode())
            conn.close()
            continue

        elif path == "/move" and method == "POST":
            data = parseJSONbody(client_message)
            axis = data.get("axis")
            delta = data.get("delta")

            if axis == "yaw":
                m1.rotate(delta / 4096.0 * 360.0)
            elif axis == "pitch":
                m2.rotate(delta / 4096.0 * 360.0)

            conn.send(b"HTTP/1.1 200 OK\r\n\r\nOK")
            conn.close()
            continue

        elif path == "/zero" and method == "POST":
            data = parseJSONbody(client_message)
            axis = data.get("axis")

            if axis == "yaw":
                m1.zero()
            elif axis == "pitch":
                m2.zero()

            conn.send(b"HTTP/1.1 200 OK\r\n\r\nOK")
            conn.close()
            continue

        #  send webpage by default
        send_html(conn, web_page())


# moved webpage to separate function
def send_html(conn, html_string):
    body = html_string.encode("utf-8")

    header = (
        "HTTP/1.1 200 OK\r\n"
        "Content-Type: text/html; charset=utf-8\r\n"
        f"Content-Length: {len(body)}\r\n"
        "Connection: close\r\n"
        "\r\n"
    ).encode("utf-8")

    conn.sendall(header + body)

# ==========================
# webserver setup
# ==========================
s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # address reuse
s.bind(('', 8080))
s.listen(3)

webpageThread = threading.Thread(target=serve_web_page)
webpageThread.daemon = True
webpageThread.start()

# ==========================
# Motor control/setup
# ==========================
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

