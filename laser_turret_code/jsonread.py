import requests

host = "http://192.168.1.254:8000/positions.json"

r = requests.get(host)
data = r.json()

print(data)
