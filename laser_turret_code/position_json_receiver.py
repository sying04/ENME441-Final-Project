import requests
import json


class PositionReceiver():

    host = ""

    def __init__(self,json_host):
        self.host = json_host

    
    def get_json_data(self):
        try:
            r = requests.get(self.host)
            return r.json()
        except:
            print("connection failed")
            return 0
        



if __name__ == "__main__":
    host = "http://192.168.1.254:8000/positions.json"
    #host = "http://127.0.0.254:8000/positions.json"
    json_receiver = PositionReceiver(host)
    data = json_receiver.get_json_data()
    print(json.dumps(data,indent = 4))
