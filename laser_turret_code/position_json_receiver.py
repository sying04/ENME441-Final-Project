import requests
import json


class PositionReceiver():

    host = "http://192.168.1.254:8000/positions.json"
    def __init__(self,json_host):
        self.host = json_host

    
    def get_json():
        r = requests.get(self.host)
        return r.json()



if __name__ == "__main__":
    host = "http://192.168.1.254:8000/positions.json"
    json_receiver = PositionReceiver(host)
    print(json.dumps(json_receiver.get_json(),indent = 4))