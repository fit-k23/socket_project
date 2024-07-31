import json
import os
import socket
import threading
import time
import sys

from msg import *
from utils import get_ip

# server_files_list = []
# downloaded_files_list = os.listdir(output_path)
#
# output_path += str(time.time())
#
# if result == 0:
#     print(f"[*] Client connected to {host_ip}:{host_port}")
#     # len("9223372036854775807\0") == 20 - 1
#     tbuf1 = int(client_socket.recv(32).decode().split(MSG_NOTIFY_DATA_BUFFER)[-1])
#     print(f"[*] Receiving File Data Buffer: {tbuf1}")
#     server_files_data = json.loads(client_socket.recv(tbuf1).decode('utf-8'))
#     # [{'name': 'file1.txt', 'size': 27096510}, {'name': 'meow.txt', 'size': 51}]
#     server_files_list = [e['name'] for e in server_files_data]
#     # ['file1.txt', 'meow.txt']
#
#
#
#     try:
#         with open(input_file, 'r') as f:
#             require_files_list = f.read().splitlines()
#     except Exception as e:
#         print(f"[!] File Error: {e}")
#
#
#
#     print(f"[>] Require File List: {require_files_list}")
#
#     for require_file in require_files_list:
#         if require_file in downloaded_files_list or not require_file in server_files_list:
#             require_files_list.remove(require_file)
#             continue
#         print(f"[*] Requesting the server to download : {require_file}")
#
#     print(f"[>] Valid require file list: {require_files_list}")
#     print(f"[>] Valid require file list: {server_files_data[:]}")
#
#     client_socket.send('\n'.join(require_files_list).encode('utf-8'))
#
#     for (_, file_name, _, size) in server_files_data:
#         print(file_name, size)
#         output_file = output_path + file_name
#         print(f"[*] Downloading to : {output_file}")
#
#         done: bool = False
#         size: int = 0
#         with open(output_file, 'wb') as f:
#             while True:
#                 print(f"[*] Downloading : {size}")
#                 if done:
#                     break
#                 bytes_read = client_socket.recv(buffer)
#                 # print(f"[>] Raw Data Received: {bytes_read}")
#                 if MSG_FILE_TRANSFER_END in bytes_read.decode('utf-8'):
#                     bytes_read = bytes_read.decode('utf-8').split(MSG_FILE_TRANSFER_END)[0].encode('utf-8')
#                     done = True
#                 if not bytes_read:
#                     print("End Section.")
#                     break
#                 # print(f"[>] Data Received: {bytes_read}")
#                 size += f.write(bytes_read)
#             print("Removing file from list.")
#             require_files_list.remove(file_name)
#             print("Closing file.")
#             f.close()
#         print("Still download?")
#     print("End Download!")
# else:
#     print(f"[!] Client failed to connect to ({host_ip}:{host_port}) ({result})")
#     client_socket.close()

server_files_data = []
request_files = []
downloaded_files = []
chunk_buffer = 4096
input_file = ""
output_folder = ""

def get_file_enum_id(file_name: str) -> int:
    i = 0
    for item in server_files_data:
        if file_name == item['name']:
            return i
        i += 1
    return -1

def get_file_size(file_path) -> int:
    return os.path.getsize(file_path)

def generate_request_file(input_file_path: str, silent: bool = False) -> bool:
    global request_files
    try:
        with open(input_file_path, 'r') as f:
            request_files_updates = f.read().splitlines()
    except Exception as e:
        if not silent:
            print(f"[!] File Error: {e}")

    for request_file in request_files_updates[:]:
        file_id = get_file_enum_id(request_file)
        file_path = output_folder + request_file
        if file_id == -1:
            if not silent:
                print(f"[!] The requested file \"{request_file}\" doesn't exist in server side.")
            request_files_updates.remove(request_file)
            continue
        if os.path.isfile(request_file) and get_file_size(file_path) < server_files_data[file_id]['size']:
            if not silent:
                print(f"[!] The requested file \"{request_file}\" haven't done downloading yet. Re-queued to be downloaded!")

    for request_file in request_files_updates:
        if not request_file in request_files:
            request_files = request_files_updates
            return True
    return False

def start_client(config_file: str = 'client.json') -> bool:
    if not os.path.exists(config_file):
        print(f"[!] Config file '{config_file}' does not exist!")
        return False

    data = json.load(open(config_file))
    host_ip = get_ip(data['host_ip'] or '@hostip')
    host_port: int = data['host_port'] or 15522
    global chunk_buffer, server_files_data, input_file, output_folder
    input_sleep: int = data['input_sleep'] or 0
    input_file = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), data['input_file']))
    output_folder = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), data['output_folder']))
    os.makedirs(output_folder, exist_ok=True)
    if os.path.isfile(input_file):
        print(f"[_] Configured input file: \"{data['input_file']}\" with sleep time {input_sleep}.")
    else:
        print(f"[!] Configured input file \"{input_file}\" does not exist!")
        return False
    print(f"[_] Configured output path: \"{data['output_folder']}\".")

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = client_socket.connect_ex((host_ip, host_port))

    if result == 0:
        print(f"[*] Client connected to {host_ip}:{host_port}")
        # len("9223372036854775807\0") == 20 - 1
        temp_sbd = client_socket.recv(32).decode('utf-8').split(MSG_NOTIFY_DATA_BUFFER)[-1].split(":")
        temp_server_file_buffer_size = int(temp_sbd[0]) # TODO: Error checking: This might not get send correctly
        chunk_buffer = int(temp_sbd[1] if len(temp_sbd) else 4096) # ugly a$$ null coalescing
        print(f"[*] Receiving Chunk Buffer's Size: {chunk_buffer}")

        server_files_data = json.loads(client_socket.recv(temp_server_file_buffer_size).decode('utf-8'))

        print(f"[>] Server File List: {[e['name'] for e in server_files_data]}")

        disconnected = False
        while not disconnected:
            request_files_changed = generate_request_file(input_file, True)
            if not request_files_changed:
                continue

            print(f"[>] Requested File List: {request_files}")
            client_socket.send('\n'.join(request_files).encode('utf-8'))
            # time.sleep(2)
            for request_file in request_files[:]:
                output_file = output_folder + request_file
                print(f"[*] Downloading to : {output_file}")

                done: bool = False
                size: int = 0
                with open(output_file, 'wb') as f:
                    while True:
                        # print(f"\r[*] Downloading : {size}")
                        if done:
                            break
                        bytes_read = client_socket.recv(chunk_buffer)
                        # print(f"[>] Raw Data Received: {bytes_read}")
                        if MSG_FILE_TRANSFER_END in bytes_read.decode('utf-8'):
                            bytes_read = bytes_read.decode('utf-8').split(MSG_FILE_TRANSFER_END)[0].encode('utf-8')
                            done = True
                        if not bytes_read:
                            print("End Section.")
                            break
                        # print(f"[>] Data Received: {bytes_read}")
                        size += f.write(bytes_read)
                    # print(f"Removing file \"{request_file}\" from list.")
                    # request_files.remove(request_file)
                    print("Closing file.")
                    f.close()
                print("Still download?")
            print("End download. Wait or die...")
    else:
        print(f"[!] Client failed to connect to ({host_ip}:{host_port}) ({result})")
        client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        start_client()
    else:
        start_client(sys.argv[1])