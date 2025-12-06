import requests
import json

host = "http://192.168.1.254:8000/positions.json"
class PositionReceiver():

    host = "http://192.168.1.254:8000/positions.json"
    
    def get_json(host):
        r = requests.get(host)
        return r.json()



if __name__ == "__main__":
    host = "http://127.0.0.1:8000/positions.json"
    print(json.dumps(PositionReceiver.get_json(host),indent = 4))