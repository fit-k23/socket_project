import os
import socket

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