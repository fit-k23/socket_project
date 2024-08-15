import json
import os
import socket

from msg import *
from utils import get_ip, parse_file_info, join_path


def start_server(ip: str, port: int, chunk_buffer: int, input_folder: str = "input/"):
	input_path = join_path(__file__, input_folder)
	os.makedirs(input_path, exist_ok=True)

	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((ip, port))
	server_socket.listen()

	print(f"[*] Hosting on {server_ip}:{server_port}")
	while True:
		try:
			client_socket, addr = server_socket.accept()
			print(f"[+] Accepted connection from client {addr}")
			client_host, client_port = client_socket.getpeername()

			file_info = json.dumps(parse_file_info(input_path), separators=(',', ':'))
			file_info_len = len(file_info)
			client_socket.sendall((MSG_NOTIFY_DATA_BUFFER + str(file_info_len) + ":" + str(chunk_buffer)).ljust(32).encode('utf-8'))
			client_socket.sendall(file_info.encode('utf-8'))

			while True:
				try:
					response = client_socket.recv(chunk_buffer)
					if not response:
						break
					if MSG_CLIENT_DISCONNECT in response:
						print(f"[-] Disconnected with client ({client_host}:{client_port}).")
						break
				except ConnectionResetError:
					print(f"[-] Connection with client ({client_host}:{client_port}) is broken.")
					break

				print(f"[*] Client ({client_host}:{client_port}) requested to download {response.decode().splitlines()}")

				for file in response.decode().splitlines():
					if not os.path.exists(input_path + file):
						print(f"[!] The requested file \"{file}\" does not exist.")
						continue
					try:
						with open(input_path + file, 'rb') as f:
							while True:
								bytes_read = f.read(chunk_buffer)
								if not bytes_read:
									break
								raw_buffer_len = len(bytes_read)
								if raw_buffer_len < chunk_buffer:
									client_socket.sendall(bytes_read + MSG_FILE_TRANSFER_END.ljust(chunk_buffer - raw_buffer_len))
									break
								else:
									client_socket.sendall(bytes_read)
					except Exception as e:
						print(f"Error: {e}")
					finally:
						# print("L2.5")
						if raw_buffer_len >= chunk_buffer:
							try:
								client_socket.sendall(MSG_FILE_TRANSFER_END.ljust(chunk_buffer))
							except ConnectionResetError:
								break
		except ConnectionResetError:
			print(f"[-] Connection with client is broken.")

if __name__ == '__main__':
	data = json.load(open('server.json'))
	server_ip = get_ip(data['ip'])
	server_port = data['port']
	# chunk_buffer = int(data['buffer'])

	start_server(server_ip, server_port, int(data['buffer']))
