import json
import os
import socket

data = json.load(open('client.json'))

from msg import *
from utils import get_ip

host_ip = get_ip(data['host_ip'])
host_port = data['host_port']
buffer = data['buffer']

# print(f"[*} Host IP: {host_ip}\nHost Port: {host_port}\nBuffer Len: {buffer}")

input_file = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), data['input_file']))
output_path = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), data['output_folder']))

print(output_path)

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
result = client_socket.connect_ex((host_ip, host_port))

server_files_list = []
downloaded_files_list = os.listdir(output_path)
print(downloaded_files_list)
require_files_list = []

output_path: str = ""

if result == 0:
    print(f"[*] Client connected to {host_ip}:{host_port}")
    # len("9223372036854775807\0") == 20 - 1
    tbuf1 = int(client_socket.recv(32).decode().split(MSG_NOTIFY_DATA_BUFFER)[-1])
    print(f"Receiving File Data Buffer: {tbuf1}")
    server_files_list = client_socket.recv(tbuf1).decode().splitlines()

    print(server_files_list)

    try:
        with open(input_file, 'r') as f:
            require_files_list = f.read().splitlines()
    except Exception as e:
        print(f"File Error: {e}")

    print(require_files_list)

    for i, require_file in enumerate(require_files_list):
        if require_file in downloaded_files_list:
            require_files_list.remove(require_file)
            continue
        output_file = output_path + require_file
        print(f"Requesting the server to download : {require_file}")

    client_socket.send('\n'.join(require_files_list).encode('utf-8'))

    c_result: str = ""

    while True:
        bytes_read = client_socket.recv(buffer)
        if not bytes_read:
            break
        c_result += bytes_read

    with open(output_file, 'wb') as f:
        f.write(c_result.encode('utf-8'))
        print(f"File Downloaded: {output_file}")
        require_files_list.remove(require_file)
else:
    print(f"Client failed to connect to ({host_ip}:{host_port}) ({result})")
    client_socket.close()
