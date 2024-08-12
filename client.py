import json
import os
import signal
import socket
import sys
# import hashlib
import colorama
colorama.init()

from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, DownloadColumn, SpinnerColumn

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
from utils import get_ip, get_file_size, join_path

server_files_data = []
request_files = []
downloaded_files = []

# input_file_hash = None

def get_file_enum_id(file_name: str) -> int:
	"""Get the index of a file in the server's file list by its name."""
	i = 0
	for item in server_files_data:  # enumerate?
		if file_name == item['name']:
			return i
		i += 1
	return -1

def generate_request_file(input_file_path: str, output_folder_path: str, silent: bool = False) -> bool:
	global request_files#, input_file_hash
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
		file_path = output_folder_path + request_file
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

def start_client(server_ip: str, server_port: int, input_file: str = "input.txt", output_folder: str = "output/") -> bool:
	global server_files_data, task_ids
	input_file_path = join_path(__file__, input_file)
	output_folder_path = join_path(__file__, output_folder)
	os.makedirs(output_folder, exist_ok=True)

	if os.path.isfile(input_file_path):
		print(f"[_] Configured input file: \"{input_file}\" was found.")
	else:
		print(f"[!] Configured input file \"{input_file}\" does not exist!")
		return False
	print(f"[_] Configured output path: \"{output_folder}\".")

	client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	result = client_socket.connect_ex((server_ip, server_port))

	if result == 0:
		def handle_exit(signum, frame):
			print("[*] Client was forced to shutting down.")
			client_socket.sendall(MSG_CLIENT_DISCONNECT)
			client_socket.close()
			sys.exit(0)

		signal.signal(signal.SIGINT, handle_exit)
		print(f"[*] Client connected to {server_ip}:{server_port}")
		temp_sbd = client_socket.recv(32).decode('utf-8').split(MSG_NOTIFY_DATA_BUFFER)[-1].split(":")
		temp_server_file_buffer_size = int(temp_sbd[0])  # TODO: Error checking: This might not get send correctly
		chunk_buffer = int(temp_sbd[1] if len(temp_sbd) else 4096)  # ugly a$$ null coalescing
		print(f"[*] Receiving Chunk Buffer's Size: {chunk_buffer}")

		server_files_data = json.loads(client_socket.recv(temp_server_file_buffer_size).decode('utf-8'))

		print(f"[>] Server File List: {[e['name'] for e in server_files_data]}")

		disconnected = False
		while not disconnected:
			request_files_changed = generate_request_file(input_file_path, output_folder_path, True)
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
		print(f"[!] Client failed to connect to ({server_ip}:{server_port}) ({result})")
		client_socket.close()

def handle_args(args) -> bool:
	l = len(args)
	if l > 3:
		if args[1] == "-m":
			server_ip = args[2]
			server_port = int(args[3])

			input_file: str = args[4] if l > 4 else "input.txt"
			output_folder: str = args[5] if l > 5 else "output/"

			start_client(server_ip, server_port, input_file, output_folder)
			return True

		if args[1] == "-h" or args[1] == "?":
			print(f"[*] Usage:")
			print(f"[*] 	   <config_file>	  						  Start client with config file.")
			print(f"[*] 	-h 											  Show helps for all available args.")
			print(f"[*] 	-m <in> <port> <input_file> <output_folder>	  Start client with manual inputs.")
			return True

	config_file = ""
	if l < 2:
		print(f"[!] Config file not set. Finding client.json in running folder...")
		config_file = "client.json"

	if l >= 2:
		config_file = args[1]

	if not config_file:
		print(f"[!] Config file was empty!")
		return False

	if not os.path.exists(config_file):
		print(f"[!] Config file '{config_file}' does not exist!")
		return False

	data = json.load(open(config_file))
	server_ip: str = get_ip(data['host_ip'] if 'host_ip' in data else '@hostip')
	server_port: int = data['host_port'] if 'host_port' in data else 15522

	input_file: str = data['input_file'] if 'input_file' in data else "input.txt"
	output_folder: str = data['output_folder'] if 'output_folder' in data else "output/"
	start_client(server_ip, server_port, input_file, output_folder)
	return True

if __name__ == "__main__":
	handle_args(sys.argv)
