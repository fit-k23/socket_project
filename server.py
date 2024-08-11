import os
import socket
import json
import sys

from msg import *
from utils import get_ip

print(sys.argv)

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

def startServer(ip: str, port: int, buffer: int, input_folder: str = "input/", max_users: int = 1, chunk_order: bool = False):
	input_path = str(os.path.join(os.path.dirname(os.path.realpath(__file__)), input_folder))
	os.makedirs(input_path, exist_ok=True)

	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((ip, port))
	server_socket.listen()

	print(f"[*] Hosting on {server_ip}:{server_port}")
	while True:
		client_socket, addr = server_socket.accept()
		print(f"[+] Accepted connection from client {addr}")
		client_host, client_port = client_socket.getpeername()

		t1 = json.dumps(parse_file_info(input_path), separators=(',', ':'))
		t1l = len(t1)
		client_socket.sendall((MSG_NOTIFY_DATA_BUFFER + str(len(t1)) + ":" + str(chunk_buffer)).ljust(32).encode('utf-8'))
		client_socket.sendall(t1.encode('utf-8'))

		while True:
			try:
				response = client_socket.recv(chunk_buffer)
				if not response:
					break
				if MSG_CLIENT_DISCONNECT in response:
					print(f"[-] Disconnected with client ({client_host}:{client_port}).")
					break
			except ConnectionResetError:
				break

			for file in response.decode().splitlines():
				if not os.path.exists(input_path + file):
					print(f"[!] File \"{file}\" does not exist.")
					continue
				print(f"[*] Client ({client_host}:{client_port}) requested to download {file}")
				try:
					with open(input_path + file, 'rb') as f:
						while True:
							# print("L0")
							bytes_read = f.read(chunk_buffer)
							# print("L0.5")
							if not bytes_read:
								break
							# print("L0.75")
							raw_buffer_len = len(bytes_read)
							if raw_buffer_len < chunk_buffer:
								client_socket.sendall(bytes_read + MSG_FILE_TRANSFER_END.ljust(chunk_buffer - raw_buffer_len))
								# print("L1")
								print(bytes_read + MSG_FILE_TRANSFER_END.ljust(chunk_buffer - raw_buffer_len))
								break
							else:
								client_socket.sendall(bytes_read)
								# print("L2")
								# print(bytes_read)
				except Exception as e:
					print(f"Error: {e}")
				finally:
					# if raw_buffer_len < chunk_buffer:
					# 	if raw_buffer_len + len(MSG_FILE_TRANSFER_END) > chunk_buffer:
					# 		client_socket.sendall(b'\0' * (chunk_buffer - raw_buffer_len))
					# 	else:
					# 		client_socket.sendall(MSG_FILE_TRANSFER_END.ljust(chunk_buffer - raw_buffer_len))
					# else:
					print("L2.5")
					if raw_buffer_len >= chunk_buffer:
						try:
							client_socket.sendall(MSG_FILE_TRANSFER_END.ljust(chunk_buffer))
						except ConnectionResetError:
							break
						print("L3")
						print(MSG_FILE_TRANSFER_END.ljust(chunk_buffer))
					print("L4")

if __name__ == '__main__':
	data = json.load(open('server.json'))
	server_ip = get_ip(data['ip'])
	server_port = data['port']
	chunk_buffer = int(data['buffer'])

	startServer(server_ip, server_port, chunk_buffer)
