import os
import socket
import json

from msg import *
from utils import get_ip

data = json.load(open('server.json'))

server_ip = get_ip(data['ip'])
server_port = data['port']
buffer = data['buffer']

input_path = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), data['input_folder']))
os.makedirs(input_path, exist_ok=True)

def parse_file_info(directory: str):
    files_info = []
    for filename in os.listdir(directory):
        filepath = os.path.join(directory, filename)
        if os.path.isfile(filepath):
            files_info.append({
                "name": filename,
                "size": os.path.getsize(filepath)
            })
    return files_info

print(parse_file_info(input_path))

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((server_ip, server_port))
server_socket.listen()

print(f"[*] Hosting on {server_ip}:{server_port}")

while True:
    client_socket, addr = server_socket.accept()
    print(f"[+] Accepted connection from {addr}")

    t1 = json.dumps(parse_file_info(input_path), separators=(',', ':'))
    t1l = len(t1)
    client_socket.sendall((MSG_NOTIFY_DATA_BUFFER + str(len(t1))).ljust(32).encode('utf-8'))
    client_socket.sendall(t1.encode('utf-8'))
    data = client_socket.recv(buffer).decode('utf-8')

    client_host, client_port = client_socket.getpeername()

    if not data:
        continue

    for file in data.splitlines():
        if not os.path.exists(input_path + file):
            print(f"[!] File \"{file}\" does not exist.")
            continue
        print(f"[*] Client ({client_host}:{client_port}) requested to download {file}")
        try:
            with open(input_path + file, 'rb') as f:
                while True:
                    bytes_read = f.read(buffer)
                    if not bytes_read:
                        break
                    client_socket.sendall(bytes_read)
        except Exception as e:
            print(f"Error: {e}")
        finally:
            client_socket.sendall(MSG_FILE_TRANSFER_END.ljust(buffer).encode('utf-8'))
            # print(f"[-] Client ({client_host}:{client_port}) disconnected.")
server_socket.close()