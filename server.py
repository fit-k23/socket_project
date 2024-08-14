import json
import os
import signal
import socket
import sys
import threading
from typing import List

from msg import *
from utils import get_ip, parse_file_info, join_path

# clients = []

def handle_client(client_socket: socket, chunk_buffer: int, file_info: str, input_path: str):
	client_host, client_port = client_socket.getpeername()
	print(f"Client {client_host}:{client_port} is threaded.")

	client_socket.sendall((MSG_NOTIFY_DATA_BUFFER + str(len(file_info)) + ":" + str(chunk_buffer)).ljust(1024).encode('utf-8'))
	client_socket.sendall(file_info.encode('utf-8'))

	request_files: dict = {}
	file_objs = {}

	while True:
		try:
			response = client_socket.recv(chunk_buffer)
			if not response:
				break

			if MSG_NO_NEW_UPDATE not in response:
				if MSG_NOTIFY_DATA_BUFFER.encode('utf-8') in response:
					print("Recieved data msg notify")
					request_files_json_size = int(response.split(MSG_NOTIFY_DATA_BUFFER.encode())[-1])
					print(request_files_json_size)
					request_files_json_return = client_socket.recv(request_files_json_size).decode('utf-8')
					request_files = json.loads(request_files_json_return)
					print(f"Client {client_host}:{client_port} requested to download {request_files}")
				print(response)
				if MSG_CLIENT_DISCONNECT in response:
					print(f"[-] Disconnected with client ({client_host}:{client_port}).")
					# clients.pop(client_host + client_port)
					break
				print(f"[*] Client ({client_host}:{client_port}) requested to download {request_files}")

			for request_file in request_files.copy():
				file_priority = request_files[request_file]
				prioritied_chunk_buffer = chunk_buffer * file_priority
				if not os.path.exists(input_path + request_file):
					client_socket.sendall(MSG_FILE_NOT_EXIST.ljust(prioritied_chunk_buffer))
					print(f"[!] The requested file \"{request_file}\" does not exist.")
					request_files.pop(request_file)

					continue
				if request_file not in file_objs:
					file_objs[request_file] = open(input_path + request_file, 'rb')

				file_obj = file_objs[request_file]
				bytes_read = file_obj.read(prioritied_chunk_buffer)
				# print(bytes_read, "\n\n")
				raw_buffer_len = len(bytes_read)
				if raw_buffer_len < prioritied_chunk_buffer:
					client_socket.sendall(bytes_read.ljust(prioritied_chunk_buffer))
					request_files.pop(request_file)
					file_objs[request_file].close()
					file_objs.pop(request_file)
				else:
					client_socket.sendall(bytes_read)
		except ConnectionResetError:
			print(f"[-] Connection with client ({client_host}:{client_port}) is broken.")
			client_socket.close()
			break

def start_server(ip: str, port: int, chunk_buffer: int, input_folder: str = "input/", max_user: int = 2):
	input_path = join_path(__file__, input_folder)
	os.makedirs(input_path, exist_ok=True)

	server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	server_socket.bind((ip, port))
	server_socket.listen()

	print(f"[*] Hosting on {server_ip}:{server_port}")

	file_info = json.dumps(parse_file_info(input_path), separators=(',', ':'))

	print(f"[*] File info: {file_info}")

	threads: List[threading.Thread|None] = [None] * max_user

	def get_first_free_thread() -> int:
		for (thread_id, thread_ins) in enumerate(threads):
			if thread_ins is None or (type(thread_ins) is threading.Thread and not thread_ins.is_alive()):
				return thread_id
		return -1

	def handle_exit(signum, frame):
		print("[x] Server was forced to shutting down.")
		for t in threads:
			if t is not None:
				t.join(0.1)
		sys.exit(0)

	signal.signal(signal.SIGINT, handle_exit)

	try:
		while True:
			client_socket, addr = server_socket.accept()
			first_free_thread: int = get_first_free_thread()
			if first_free_thread == -1:
				print(f"[*] Denied connection from client {addr} due to server full.")
				client_socket.close()
				continue

			print(f"[+] Accepted connection from client {addr} [{first_free_thread + 1}/{max_user}]")
			threads[first_free_thread] = threading.Thread(target=handle_client, args=(client_socket,chunk_buffer, file_info, input_path), daemon=True)
			threads[first_free_thread].start()
	except KeyboardInterrupt as err:
		print(f"[x] Interrupted! Server is closing... {err}")
	finally:
		for thread in threads:
			if thread is not None and type(thread) is threading.Thread:
				thread.join()
		server_socket.close()
		print(f"[x] Server is closed.")

if __name__ == '__main__':
	data = json.load(open('server.json'))
	server_ip = get_ip(data['ip'])
	server_port = data['port']
	# chunk_buffer = int(data['buffer'])

	start_server(server_ip, server_port, int(data['buffer']))
