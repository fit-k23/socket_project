import json
import os
import socket
import time

data = json.load(open('client.json'))

from msg import *
from utils import get_ip

host_ip = get_ip(data['host_ip'])
host_port = data['host_port']
buffer = data['buffer']

input_file = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), data['input_file']))
output_path = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), data['output_folder']))
os.makedirs(output_path, exist_ok=True)
print(output_path)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = client_socket.connect_ex((host_ip, host_port))

server_files_list = []
downloaded_files_list = os.listdir(output_path)
print(f"[>] Downloaded File: {downloaded_files_list}")
require_files_list = []

output_path += str(time.time())

if result == 0:
    print(f"[*] Client connected to {host_ip}:{host_port}")
    # len("9223372036854775807\0") == 20 - 1
    tbuf1 = int(client_socket.recv(32).decode().split(MSG_NOTIFY_DATA_BUFFER)[-1])
    print(f"[*] Receiving File Data Buffer: {tbuf1}")
    server_files_data = json.loads(client_socket.recv(tbuf1).decode('utf-8'))
    # [{'name': 'file1.txt', 'size': 27096510}, {'name': 'meow.txt', 'size': 51}]
    server_files_list = [e['name'] for e in server_files_data]
    # ['file1.txt', 'meow.txt']
    
    print(f"[>] Server File List: {server_files_list}")

    try:
        with open(input_file, 'r') as f:
            require_files_list = f.read().splitlines()
    except Exception as e:
        print(f"[!] File Error: {e}")



    print(f"[>] Require File List: {require_files_list}")

    for require_file in require_files_list:
        if require_file in downloaded_files_list or not require_file in server_files_list:
            require_files_list.remove(require_file)
            continue
        print(f"[*] Requesting the server to download : {require_file}")

    print(f"[>] Valid require file list: {require_files_list}")
    print(f"[>] Valid require file list: {server_files_data[:]}")

    client_socket.send('\n'.join(require_files_list).encode('utf-8'))

    for (_, file_name, _, size) in server_files_data:
        print(file_name, size)
        output_file = output_path + file_name
        print(f"[*] Downloading to : {output_file}")

        done: bool = False
        size: int = 0
        with open(output_file, 'wb') as f:
            while True:
                print(f"[*] Downloading : {size}")
                if done:
                    break
                bytes_read = client_socket.recv(buffer)
                # print(f"[>] Raw Data Received: {bytes_read}")
                if MSG_FILE_TRANSFER_END in bytes_read.decode('utf-8'):
                    bytes_read = bytes_read.decode('utf-8').split(MSG_FILE_TRANSFER_END)[0].encode('utf-8')
                    done = True
                if not bytes_read:
                    print("End Section.")
                    break
                # print(f"[>] Data Received: {bytes_read}")
                size += f.write(bytes_read)
            print("Removing file from list.")
            require_files_list.remove(file_name)
            print("Closing file.")
            f.close()
        print("Still download?")
    print("End Download!")
else:
    print(f"[!] Client failed to connect to ({host_ip}:{host_port}) ({result})")
    client_socket.close()

server_files_data = []

def is_file_exist(file_name: str):
    for item in server_files_data:
        if file_name == item['name']:
            return True
        return False

def start_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = client_socket.connect_ex((host_ip, host_port))

    # len("9223372036854775807\0") == 20 - 1
    tbuf1 = int(client_socket.recv(32).decode().split(MSG_NOTIFY_DATA_BUFFER)[-1])
    print(f"[*] Receiving File Data Buffer: {tbuf1}")

    global server_files_data
    server_files_data = json.loads(client_socket.recv(tbuf1).decode('utf-8'))

    if result == 0:
        print(f"[*] Client connected to {host_ip}:{host_port}")

    else:
        print(f"[!] Client failed to connect to ({host_ip}:{host_port}) ({result})")
        client_socket.close()