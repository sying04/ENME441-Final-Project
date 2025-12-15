import json
import socket
import RPi.GPIO as GPIO
import threading
import multiprocessing

from time import sleep
from shifter import Shifter
from motorcontrol import Stepper
from targeting import Targeter

GPIO.setmode(GPIO.BCM)

currentTarget = 0;

# Generate HTML for the web page:
def web_page():
    # webpage taken & modified from ChatGPT
    html = f""" 
        <html>
        <head>
        <meta charset="UTF-8">
        </head>
        <body>

        <h2>Motor Control</h2>

        <!-- Angle Readouts -->
        <h3>Pitch Angle: <span id="pitch-angle">?</span>°</h3>
        <h3>Yaw Angle: <span id="yaw-angle">?</span>°</h3>

        <!-- Targeting -->
        <h3>Current Target: <span id="target">?</span></h3>
        <h3>Current Target Theta: <span id="target-theta">?</span>°</h3>     
        <h3>Current Target Height: <span id="target-height">?</span>°</h3>

        <div>
        <button onclick="switchTarget(-1)">←</button>
        <button onclick="switchTarget(1)">→</button>           
        </div>

        <!-- Step Text Input -->
        <div>
          Pitch (steps, 512 = 45°): <input id="pitch-step" type="number" value="8"><br><br>
          Yaw (steps, 512 = 45°): <input id="yaw-step" type="number" value="8"><br><br>
        </div>

        <!-- Zero Buttons -->
        <button onclick="zeroAxis('pitch')">Zero Pitch</button>
        <button onclick="zeroAxis('yaw')">Zero Yaw</button>

        <br><br>

        <!-- Controls -->
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

        <button onclick="fireLaser()">Fire</button>

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

        // === manual move functions ===
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

        async function fireLaser() {{
          await fetch("/fire", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{}})
          }})
        }}

        // === targeting == 
        async function switchTarget(direction) {{
          await fetch("/switch", {{
            method: "POST",
            headers: {{ "Content-Type": "application/json" }},
            body: JSON.stringify({{ direction: direction}})
          }})
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
# some extra json functions and responses taken and modified from ChatGPT
def serve_web_page():
    while True:
        # print('Waiting for connection...')
        conn, (client_ip, client_port) = s.accept()     # blocking call

        # post request stuff
        # print(f'Connection from {client_ip}')
        client_message = conn.recv(2048).decode('utf-8')

        request_line = client_message.split("\r\n", 1)[0]
        parts = request_line.split()

        if len(parts) < 2:
            conn.close()
            continue

        method = parts[0]
        path = parts[1]

        if path == "/pos":
            response = json.dumps({
               "pitch": m2.getAngle(),
               "yaw": m1.getAngle(),
               #"target": turret_targeter.target,
               #"target-theta": turret_target.heading,
               "target-height": 10
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

            conn.send(b"HTTP/1.1 200 OK\r\n\r\n")
            conn.close()
            continue

        elif path == "/zero" and method == "POST":
            data = parseJSONbody(client_message)
            axis = data.get("axis")

            if axis == "yaw":
                m1.zero()
            elif axis == "pitch":
                m2.zero()

            conn.send(b"HTTP/1.1 200 OK\r\n\r\n")
            conn.close()
            continue
       # elif path == "/fire" and method == "POST":
            # set gpio on laser to high
            # set timer to zero
            # have other thread counting timer to turn laser off
        elif path == "/switch" and method == "POST":
            data = parseJSONbody(client_message)
            direction = data.get("direction")
            global currentTarget
            temp = currentTarget + int(direction)

            if temp > 0 and temp < 21:
                turret_targeter.pick_target(temp)
                print(f'going to target {temp} @ {turret_target.aim_heading}')
                currentTarget = temp
                m1.rotate(turret_targeter.aim_at_target())
            
            # print(f'Target {n} is being aimed at with this heading: {turret_targeter.aim_heading}')
            conn.send(b"HTTP/1.1 200 OK\r\n\r\n")
            conn.close()
            continue
        else:
            print("Unkown request")

        #  send webpage by default
        conn.send(b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\n\r\n")
        try:
            conn.sendall(web_page())
        finally:
            conn.close()



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
    m1 = Stepper(shift_reg, lock2)
    m2 = Stepper(shift_reg, lock1)

    m1.zero()
    m2.zero()

    # in class
    host = "http://192.168.1.254:8000/positions.json"
    team = 21
    number_of_teams = 22

    # values for local testing
    # host = "http://sying.local:8080/positions.json"
    # team = 2
    # number_of_teams = 20 
    laser_height = 0

    # turret targetting setup
    turret_targeter = Targeter(host, team, number_of_teams, laser_height)
    team_r, team_ang, team_z = turret_targeter.locate_self()
    
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

    # While the motors are running in their separate processes, the main
    # code can continue doing its thing: 
    try:
        while True:
            sleep(1)
    except KeyboardInterrupt:
        GPIO.cleanup() 
        print('Closing socket')
        s.close()
        print('Joining webpageThread')
        webpageThread.join()

