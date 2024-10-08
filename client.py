import json
import os
import signal
import socket
import sys
import time
import colorama
import rich

colorama.init()

from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, TaskID, DownloadColumn, SpinnerColumn

# import hashlib

progress = Progress(
    TextColumn("[bold blue]{task.description}"),
	SpinnerColumn(),
    BarColumn(),
    "[progress.percentage] {task.percentage:>3.0f}%",
    "•",
    TimeElapsedColumn(),
	DownloadColumn(),
	# refresh_per_second=1
)

task_ids = {}

from msg import *
from utils import get_ip

server_files_data = []
request_files = []
downloaded_files = []
chunk_buffer = 4096
input_file = ""
output_folder = ""

input_file_hash = None

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
	if not os.path.exists(file_path):
		return -1
	return os.path.getsize(file_path)

def generate_request_file(input_file_path: str, silent: bool = False) -> bool:
	global request_files, input_file_hash
	try:
		with open(input_file_path, 'r') as f:
			file_data = f.read()
			# file_hash = hashlib.sha256(file_data.encode()).hexdigest()
			request_files_updates = file_data.splitlines()
	except Exception as e:
		if not silent:
			print(f"[!] File Error: {e}")

	# if input_file_hash is not None and input_file_hash == file_hash:
	# 	return False

	# input_file_hash = file_hash
	# print("Updated files", request_files_updates)

	for request_file in request_files_updates[:]:
		if request_file.strip() == "":
			if not silent:
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
					print(f"[!] The requested file \"{request_file}\" haven't done downloading yet. Re-queued to be downloaded!")
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
	global chunk_buffer, server_files_data, input_file, output_folder, task_ids
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

			print(f"[>] Requested File List: {request_files}")

			for request_file in request_files:
				file_id = get_file_enum_id(request_file)
				file_size = int(server_files_data[file_id]['size'])
				task_ids[request_file] = progress.add_task(f"[green]" + request_file, total=file_size, start=False)

			client_socket.send('\n'.join(request_files).encode('utf-8'))

			with progress:
				for request_file in request_files[:]:
					file_id = get_file_enum_id(request_file)
					file_size = int(server_files_data[file_id]['size'])
					output_file = output_folder + request_file
					print(f"[*] Downloading to : {output_file}")

					done: bool = False
					size: int = 0
					total_size: int = 0
					file_size = int(server_files_data[file_id]['size'])
					progress.start_task(task_ids[request_file])
					with open(output_file, 'wb') as f:
						while size < file_size:
							if done:
								break

							bytes_read = client_socket.recv(chunk_buffer)
							l = len(bytes_read)

							while l < chunk_buffer:
								bytes_read += client_socket.recv(chunk_buffer - l)
								l = len(bytes_read)

							if l > file_size:
								bytes_read = bytes_read[:l - file_size]

							total_size += len(bytes_read)
							if not bytes_read:
								break

							if total_size > file_size:
								print(f"[!] File size exceeds. {bytes_read}")

							if MSG_FILE_TRANSFER_END in bytes_read:
								# print("End a file")
								# print(bytes_read)
								bytes_read = bytes_read.split(MSG_FILE_TRANSFER_END)[0]
								# print(bytes_read)
								if len(bytes_read) == 0:
									# print(f"[*] File downloaded. Moving to next file...")
									continue
								else:
									done = True

							diff = f.write(bytes_read)
							size += diff
							progress.update(task_ids[request_file], advance=diff)
						# print("Closing file.")
						f.close()
					# progress.reset()
					progress.console.print(f"[*] Downloaded [yellow]{request_file}[default].")
					# print(f"[*] Downloaded {request_file}.")
					# progress.remove_task(task_ids[request_file])
					request_files.remove(request_file)
					# print(f"Downloaded {size}/{server_files_data[file_id]['size']} ({size / server_files_data[file_id]['size'] * 100:0.4f}%).")
					# print(total_size)
					# print("Still download?")
				print("End download. Wait until death...")
	else:
		print(f"[!] Client failed to connect to ({host_ip}:{host_port}) ({result})")
		client_socket.close()

if __name__ == "__main__":
	if len(sys.argv) < 2:
		start_client()
	else:
		start_client(sys.argv[1])
