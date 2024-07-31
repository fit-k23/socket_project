import socket


def get_ip(ip: str = "@all") -> str:
	match ip:
		case '@all':
			return '0.0.0.0'
		case '@localhost' | 'localhost':
			return '127.0.0.1'
		case '@hostip':
			return socket.gethostbyname(socket.gethostname())
		case _:
			try:
				socket.inet_aton(ip)
			except socket.error:
				raise Exception(f'Invalid ip: {ip}')
			return ip
