import socket

host = "http://192.168.1.254/"
port = "8000"
def read(host,port):
    c = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    data = c.recv(1024)
    return data

print(read(host,port))
