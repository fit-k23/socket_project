import json
import os
import signal
import socket
import sys

from msg import *
from utils import get_ip

server_files_data = []
request_files = []
downloaded_files = []
chunk_buffer = 4096
input_file = ""
output_folder = ""


def get_file_enum_id(file_name: str) -> int:
	"""Get the index of a file in the server's file list by its name."""
	i = 0
	for item in server_files_data:  # enumerate?
		if file_name == item['name']:
			return i
		i += 1
	return -1


def get_file_size(file_path) -> int:
	"""Return the size of a file in bytes."""
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
		if request_file.strip() == "":
			print(f"[!] Empty Request File: {request_file}")
			request_files_updates.remove(request_file)
			continue
		file_id = get_file_enum_id(request_file)
		file_path = output_folder + request_file
		if file_id == -1:
			if not silent:
				print(f"[!] The requested file \"{request_file}\" doesn't exist in server side.")
			request_files_updates.remove(request_file)
			continue
		if os.path.isfile(file_path):
			if get_file_size(file_path) < server_files_data[file_id]['size']: # TODO: This is wrong
				if not silent:
					print(
						f"[!] The requested file \"{request_file}\" haven't done downloading yet. Re-queued to be downloaded!")
			else:
				request_files_updates.remove(request_file)
				continue
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
		def handle_exit(signum, frame):
			print("[*] Client is shutting down.")
			client_socket.sendall(MSG_CLIENT_DISCONNECT)
			client_socket.close()
			sys.exit(0)

		signal.signal(signal.SIGINT, handle_exit)
		print(f"[*] Client connected to {host_ip}:{host_port}")
		# len("9223372036854775807\0") == 20 - 1
		temp_sbd = client_socket.recv(32).decode('utf-8').split(MSG_NOTIFY_DATA_BUFFER)[-1].split(":")
		temp_server_file_buffer_size = int(temp_sbd[0])  # TODO: Error checking: This might not get send correctly
		chunk_buffer = int(temp_sbd[1] if len(temp_sbd) else 4096)  # ugly a$$ null coalescing
		print(f"[*] Receiving Chunk Buffer's Size: {chunk_buffer}")

		server_files_data = json.loads(client_socket.recv(temp_server_file_buffer_size).decode('utf-8'))

		print(f"[>] Server File List: {[e['name'] for e in server_files_data]}")

		disconnected = False
		while not disconnected:
			request_files_changed = generate_request_file(input_file, True)
			if not request_files_changed:
				continue

			print(request_files)
			print(f"[>] Requested File List: {request_files}")
			client_socket.send('\n'.join(request_files).encode('utf-8'))
			# time.sleep(2)
			flag_cached_trash = False
			for request_file in request_files[:]:
				file_id = get_file_enum_id(request_file)
				output_file = output_folder + request_file
				print(f"[*] Downloading to : {output_file}")

				done: bool = False
				size: int = 0
				total_size: int = 0
				file_size = int(server_files_data[file_id]['size'])
				with open(output_file, 'wb') as f:
					while size < file_size:
						# print(f"\r[*] Downloading : {size}")
						if done:
							break
						bytes_read = client_socket.recv(chunk_buffer)
						total_size += len(bytes_read)
						# print(f"[>] Raw Data Received: {bytes_read}")
						if not bytes_read:
							print("End Section.")
							break

						# if b'[' in bytes_read and MSG_FILE_TRANSFER_END not in bytes_read:
						# 	print(bytes_read, '\n')

						if MSG_FILE_TRANSFER_END in bytes_read:
							print("End a file")
							print(bytes_read)
							bytes_read = bytes_read.split(MSG_FILE_TRANSFER_END)[0]
							print(bytes_read)
							if len(bytes_read) == 0:
								print(f"[*] File downloaded. Moving to next file...")
								continue
							else:
								done = True

						# print(f"[>] Data Received: {bytes_read}")
						size += f.write(bytes_read)
					# print(f"Removing file \"{request_file}\" from list.")
					request_files.remove(request_file)
					print("Closing file.")
					f.close()
				print(
					f"Downloaded {size}/{server_files_data[file_id]['size']} ({size / server_files_data[file_id]['size'] * 100:0.4f}).")
				print(total_size)
				print("Still download?")
			print("End download. Wait until death...")
			# break
	else:
		print(f"[!] Client failed to connect to ({host_ip}:{host_port}) ({result})")
		client_socket.close()


if __name__ == "__main__":
	if len(sys.argv) < 2:
		start_client()
	else:
		start_client(sys.argv[1])
