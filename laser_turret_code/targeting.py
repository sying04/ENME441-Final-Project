import position_json_receiver
    

class Targeter():
    position_receiver = 0
    target_data_json = 0
    target data = 0
    def __init__(self, host)
	    self.position_receiver = position_json_receiver.PositionReceiver()
        self.target_data_json = position_receiver.get_json()
        datas = target_data_json.dumps()
        self.target_data = json.load(datas)



host = "http://192.168.1.254:8000/positions.json"

enme441_targeter = Targeter(host)
