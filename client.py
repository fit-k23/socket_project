import json
import os
import signal
import socket
import sys
import threading
import time

# import colorama
# colorama.init()

from rich.progress import Progress, TextColumn, BarColumn, TimeElapsedColumn, DownloadColumn, SpinnerColumn

from msg import *
from utils import get_ip, get_file_size, join_path, get_priority, recv_all

request_files_update = False
request_live_update = False
server_files = {}
request_files = {}

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
				# print(file_name)
				if file_name == "" or file_name not in server_files:
					if file_name in request_files:
						print("Removed from L1")
						request_files.pop(file_name)

					continue
				file_path = output_folder_path + file_name
				downloaded_size = get_file_size(file_path)

				if downloaded_size != -1 and file_name in request_files:
					continue

				if downloaded_size == server_files[file_name]:
					if file_name in request_files:
						request_files.pop(file_name)
					continue
				else:
					print(f"Delete {file_path}")
					open(file_path, "w").close()
					if not silent:
						print(f"[!] The requested file \"{file_name}\" haven't done downloading yet. Re-queued to be downloaded!")

				file_priority = get_priority(file_priority_str)

				if file_priority == 0:
					if not silent:
						print(f"[!] File ({file_name})'s priority is corrupted. Downloading as normal priority!")
					file_priority = 1

				changed = True
				request_files[file_name] = file_priority
	except Exception as e:
		if not silent:
			print(f"[!] File Error: {e}")
	return changed

def handle_input_file(input_file_path: str = "input.txt", output_folder_path: str = "output/", sleep_time: int = 2):
	global request_files_update, request_live_update
	while True:
		request_files_update = generate_request_file(input_file_path, output_folder_path, silent=True)
		if request_files_update:
			request_live_update = True
		time.sleep(sleep_time)

def start_client(server_ip: str, server_port: int, input_file: str = "input.txt", output_folder: str = "output/") -> bool:
	global server_files
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

	handle_input_file_thread = None

	if result == 0:
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
		server_data = client_socket.recv(1024).decode('utf-8').split(MSG_NOTIFY_DATA_BUFFER)[-1].split(":")
		server_files_data_buffer_size = int(server_data[0])
		chunk_buffer = int(server_data[1] if len(server_data) > 1 else 4096)
		print(f"[*] Receiving Chunk Buffer's Size: {chunk_buffer}")
		server_files = json.loads(client_socket.recv(server_files_data_buffer_size).decode('utf-8'))
		print(f"[>] Server File List: {server_files}")

		handle_input_file_thread = threading.Thread(target=handle_input_file, args=(input_file_path, output_folder_path), daemon=True)
		handle_input_file_thread.start()

		disconnected = False

		progress = Progress(
			TextColumn("[bold blue]{task.description}"),
			SpinnerColumn(), BarColumn(),
			"[progress.percentage] {task.percentage:>3.0f}%", "•",
			TimeElapsedColumn(), DownloadColumn(),
			auto_refresh=True,
			# refresh_per_second=1,
		)

		file_objs = {}
		task_ids = {}
		with progress:
			while not disconnected:
				if request_files_update:
					progress.print(f"[>] Requested File List: {request_files}")
					request_files_json = json.dumps(request_files, separators=(',', ':'))
					client_socket.sendall((MSG_NOTIFY_DATA_BUFFER + str(len(request_files_json))).ljust(chunk_buffer).encode('utf-8'))
					client_socket.send(request_files_json.encode('utf-8'))
				else:
					client_socket.sendall(MSG_NO_NEW_UPDATE.ljust(chunk_buffer))

				for request_file in request_files.copy():
					file_size = int(server_files[request_file] if request_file in server_files else 0)
					file_priority = request_files[request_file]
					prioritied_chunk_buffer = chunk_buffer * file_priority
					output_file_path = output_folder + request_file

					if request_file not in file_objs:
						task_ids[request_file] = progress.add_task(f"[green]" + request_file, total=file_size, start=True)
						file_objs[request_file] = open(output_file_path, "ab")

					file_obj = file_objs[request_file]

					bytes_read = recv_all(client_socket, prioritied_chunk_buffer)
					if MSG_FILE_NOT_EXIST in bytes_read:
						file_objs[request_file].close()
						file_objs.pop(request_file)
						request_file.pop(request_file)
						progress.remove_task(task_ids[request_file])
						continue

					if MSG_FILE_TRANSFER_END in bytes_read:
						bytes_read = bytes_read.split(MSG_FILE_TRANSFER_END)[0]
					task = progress.tasks[task_ids[request_file]] if task_ids[request_file] in progress.tasks else None
					l = len(bytes_read)
					if task.completed + l >= task.total:
						bytes_read = bytes_read[:task.total - task.completed]

					progress.update(task_ids[request_file], advance=file_obj.write(bytes_read))
					if task is not None and task.completed == task.total:
						print(f"Download shit {request_file}")
						file_objs[request_file].close()
						file_objs.pop(request_file)
						request_file.pop(request_file)
						progress.remove_task(task_ids[request_file])






				for task_name in task_ids.keys():
					if task_name not in server_files:
						if task_name in file_objs:
							file_objs[task_name].close()
							print("File obj close")
							file_objs.pop(task_name)
						print(f"Progress task: {task_name} removed.")
						progress.remove_task(task_ids[task_name])

				for request_file in request_files.copy():
					output_file_path = output_folder + request_file
					if request_file not in task_ids:
						progress.print(f"Add new progress... {request_file}")
						task_ids[request_file] = progress.add_task(f"[green]" + request_file, total=file_size, start=True)
					if request_file not in file_objs:
						file_objs[request_file] = open(output_file_path, 'ab')

				request_files_json = json.dumps(request_files, separators=(',', ':'))
				client_socket.sendall((MSG_NOTIFY_DATA_BUFFER + str(len(request_files_json))).ljust(chunk_buffer).encode('utf-8'))
				client_socket.send(request_files_json.encode('utf-8'))

				for request_file in request_files.copy():
					time.sleep(0.5)

					if request_file not in file_objs:
						output_file_path = output_folder + request_file
						file_objs[request_file] = open(output_file_path, 'ab')

					file_obj = file_objs[request_file]
					if file_obj.closed:
						if request_file in request_files:
							print("Removed in L3")
							request_files.pop(request_file)
						continue

					file_priority = request_files[request_file]
					prioritied_chunk_buffer = chunk_buffer * file_priority
					bytes_read = recv_all(client_socket, prioritied_chunk_buffer)

					task = progress.tasks[task_ids[request_file]] if task_ids[request_file] in progress.tasks else None

					if MSG_FILE_NOT_EXIST in bytes_read:
						print(f"[!] File {request_file} does not exist in server side.")
						print("File removed in L2 and pop out, request lost")
						file_objs[request_file].close()
						file_objs.pop(request_file)
						progress.remove_task(task_ids[request_file])
						request_files.pop(request_file)
						continue

					if MSG_FILE_TRANSFER_END in bytes_read:
						print(f"[!] File {request_file} ended.")
						print(bytes_read)
						bytes_read = bytes_read.split(MSG_FILE_TRANSFER_END)[0]
						print(bytes_read)
						if len(bytes_read) == 0:
							file_objs[request_file].close()
							if task is not None:
								print(f"[>] Downloaded ", TextColumn("[bold blue]{task.description}").render(task).spans, " • ", TimeElapsedColumn().render(task).spans, DownloadColumn().render(task))
							print("File ded")
							progress.remove_task(task.id)
							request_files.pop(request_file)
							continue
					progress.update(task_ids[request_file], advance=file_obj.write(bytes_read))

					if task is not None and task.completed > task.total:
						print("Ded")
						file_objs[request_file].close()
						print(f"[>] Downloaded ", TextColumn("[bold blue]{task.description}").render(task).spans, " • ", TimeElapsedColumn().render(task).spans, DownloadColumn().render(task))
						print("File ded")
						progress.remove_task(task.id)
						request_files.pop(request_file)


		handle_input_file_thread.join()
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
