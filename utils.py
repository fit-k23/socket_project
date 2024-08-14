import os
import socket

def get_priority(input: str) -> int:
	match input:
		case "NORMAL":
			return 1
		case "HIGH":
			return 4
		case "CRITICAL":
			return 10
		case _:
			return 0

def get_ip(ip: str = "@all") -> str:
	match ip:
		case '@all':
			return '0.0.0.0'
		case '@localhost' | 'localhost':
			return '127.0.0.1'
		case '@hostip':
			return socket.gethostbyname(socket.gethostname())
		case '@broadcast':
			return ''
		case _:
			try:
				socket.inet_aton(ip)
			except socket.error:
				raise Exception(f'Invalid ip: {ip}')
			return ip

def recv_all(sock: socket.socket, length: int) -> bytes:
	data = b''
	l = len(data)
	# time_out_check = 10
	while l < length:
		buffer = sock.recv(length - l)
		# if not buffer:
		# 	return
		data += buffer
		l = len(data)
		# if time_out_check < 0:
			# raise TimeoutError("Recv timeout due to unknown reason. The data received is empty.")
		# time_out_check -= 1
	return data


def parse_file_info(directory: str):
	files_info = {}
	for filename in os.listdir(directory):
		filepath = os.path.join(directory, filename)
		file_size = get_file_size(filepath)
		if file_size != -1:
			files_info[filename] = file_size
	return files_info

def filesize_format(num):
    for unit in (" bytes", "KB", "MB", "GB", "TB", "PB", "EB", "ZB"):
        if abs(num) < 1024.0:
            return f"{num:3.2f}{unit}"
        num /= 1024.0
    return f"{num:.2f}Y"

def get_file_size(file_path) -> int:
	"""Return the size of a file in bytes."""
	try:
		result = os.path.getsize(file_path)
	except FileNotFoundError:
		result = -1
	# Bad code but work with rare case with wsl2 files being desync when file is deleted, the desync can flag a file
	# exist, but it really doesn't in the window side.
	# The sync takes time to do resulted in file being mis-flag as sexist, but it really doesn't.
	return result

def join_path(path: str, file: str) -> str:
	return os.path.join(os.path.dirname(os.path.realpath(path)), file)