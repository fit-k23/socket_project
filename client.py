import json
import os
import signal
import socket
import sys
import threading
import time

from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, DownloadColumn, SpinnerColumn, Task

from msg import *
from utils import get_ip, get_file_size, join_path, get_priority, recv_all, get_task_from_id

request_files_update = False
server_files = {}
request_files = {}
updates_files = {}

def generate_request_file(input_file_path: str, output_folder_path: str, silent: bool = False) -> bool:
	global request_files
	changed: bool = False
	try:
		with open(input_file_path, 'r') as f:
			raw_file_data = f.read().splitlines()
			# print(raw_file_data)
			for line in raw_file_data:
				lr = line.split()
				file_name = lr[0]
				file_priority_str = lr[1] if len(lr) > 1 else ''
				if file_name.lstrip()[0] == '#' or file_name == "":
					if not silent:
						print(f"None valid case {file_name}")
					continue
				if file_name not in server_files:
					if not silent:
						print(f"Not in server {file_name}")
					continue

				file_path = output_folder_path + file_name
				downloaded_size = get_file_size(file_path)

				if downloaded_size == server_files[file_name]:
					if not silent:
						print(f"Downloaded alr {file_name}")
					continue

				file_priority = get_priority(file_priority_str)
				if file_priority == 0:
					continue
				if downloaded_size != -1 and file_name in request_files and file_priority == request_files[file_name]:
					if not silent:
						print(f"No update {file_name}")
					continue
				if downloaded_size > server_files[file_name]:
					open(file_path, 'w').close();
				changed = True
				updates_files[file_name] = file_priority
	except Exception as e:
		if not silent:
			print(f"[!] File Error: {e}")
	return changed

def handle_input_file(input_file_path: str = "input.txt", output_folder_path: str = "output/", sleep_time: int = 2):
	global request_files_update
	while True:
		request_files_update = generate_request_file(input_file_path, output_folder_path, silent=True)
		time.sleep(sleep_time)

def start_client(server_ip: str, server_port: int, input_file: str = "input.txt", output_folder: str = "output/") -> bool:
	global server_files, request_files, updates_files
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

	print(f"[>] Tried to connect to server...")
	progress = Progress(
		TextColumn("[bold blue]{task.description}"),
		SpinnerColumn(), BarColumn(),
		"[progress.percentage] {task.percentage:>3.0f}%", "•",
		TimeElapsedColumn(), DownloadColumn(),
		auto_refresh=True,
		# refresh_per_second=1,
	)

	handle_input_file_thread = None

	if result == 0:
		try:
			def handle_exit(signum, frame):
				print("[*] Client was forced to shutting down.")
				client_socket.sendall(MSG_CLIENT_DISCONNECT)
				client_socket.close()
				if type(handle_input_file) == threading.Thread:
					handle_input_file_thread.join(0.1)
				progress.stop()
				sys.exit(0)
			signal.signal(signal.SIGINT, handle_exit)

			print(f"[*] Client connected to {server_ip}:{server_port}")

			raw_data = client_socket.recv(1024)
			if not raw_data:
				print(f"[!] Client cannot connect to server. Maybe the server is full.")
				return False
			server_data = raw_data.decode('utf-8').split(MSG_NOTIFY_DATA_BUFFER)[-1].split(":")

			server_files_data_buffer_size = int(server_data[0])
			chunk_buffer = int(server_data[1] if len(server_data) > 1 else 4096)
			print(f"[*] Receiving Chunk Buffer's Size: {chunk_buffer}")
			server_files = json.loads(client_socket.recv(server_files_data_buffer_size).decode('utf-8'))
			print(f"[>] Server File List: {server_files}")

			handle_input_file_thread = threading.Thread(target=handle_input_file,
														args=(input_file_path, output_folder_path), daemon=True)
			handle_input_file_thread.start()

			disconnected = False

			global request_files_update

			file_objs = {}
			tasks = {}
			with progress:
				while not disconnected:
					if request_files_update:
						for update in updates_files:
							if update in request_files:
								print(f"[>] Updating {update} from {request_files[update]} to {updates_files[update]}")
							request_files[update] = updates_files[update]

						update_files_json = json.dumps(updates_files, separators=(',', ':'))
						client_socket.sendall((MSG_NOTIFY_DATA_BUFFER + str(len(update_files_json))).ljust(chunk_buffer).encode('utf-8'))
						client_socket.send(update_files_json.encode('utf-8'))
						progress.print(f"[>] Asked server to download more files: {updates_files}")
						# progress.print(f"[>] Update File List: {request_files}")
						updates_files = {}
						request_files_update = False
					else:
						client_socket.sendall(MSG_NO_NEW_UPDATE.ljust(chunk_buffer))

					for request_file in request_files.copy():
						# time.sleep(0.05)
						file_size = int(server_files[request_file] if request_file in server_files else 0)
						file_priority = request_files[request_file]
						prioritied_chunk_buffer = chunk_buffer * file_priority
						output_file_path = output_folder + request_file

						if request_file not in tasks:
							tasks[request_file]: Task = get_task_from_id(progress,
																		 progress.add_task(f"[green]" + request_file,
																						   total=file_size, start=True))

						task = tasks[request_file]
						if request_file not in file_objs:
							file_objs[request_file] = open(output_file_path, "ab")

						file_obj = file_objs[request_file]

						bytes_read = recv_all(client_socket, prioritied_chunk_buffer)
						if MSG_FILE_NOT_EXIST in bytes_read:
							print(f"[!] File {request_file} is not exist in server.")
							file_objs[request_file].close()
							file_objs.pop(request_file)
							request_files.pop(request_file)
							progress.remove_task(task.id)
							tasks.pop(request_file)
							continue

						l = len(bytes_read)
						if task.completed + l >= task.total:
							# print(f"Chooped :> from {l} to {l - task.total + task.completed} : {task.completed}/{task.total}")
							# print(bytes_read.rstrip(), " with len = ", len(bytes_read.rstrip()))
							# print(bytes_read)
							bytes_read = bytes_read[:task.total - task.completed]
						# print(bytes_read, " with len = ", len(bytes_read))

						file_obj.write(bytes_read)
						progress.update(task.id, advance=len(bytes_read))
						if task.completed == task.total:
							# print(f"Download shit {request_file}")
							print(f"[*] File {request_file} is downloaded.")
							file_objs[request_file].close()
							file_objs.pop(request_file)
							request_files.pop(request_file)
							progress.remove_task(task.id)
							tasks.pop(request_file)
		except ConnectionResetError:
			print(f"[!] Connection was closed.!")
		handle_input_file_thread.join(0.1)
		client_socket.close()
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

	if l > 1:
		if args[1] == "-h" or args[1] == "?":
			print(f"[*] Usage:")
			print(f"[*]     <config_file>                                Start client with config file.")
			print(f"[*]     -h                                           Show helps for all available args.")
			print(f"[*]     -m <ip> <port> <input_file> <output_folder>  Start client with manual inputs.")
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
