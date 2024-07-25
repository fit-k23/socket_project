import socket
import time

# Client configuration
# from cfg import SERVER_PORT, BUFFER_SIZE

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 12211
BUFFER_SIZE = 4096

FILENAME = 'out' + str(time.time()) + '.7z' # Name of the file to save the downloaded content

def download_file():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = client_socket.connect_ex((SERVER_HOST, SERVER_PORT))

    if result != 0:
        print(f"Client failed to connect to ({SERVER_HOST}:{SERVER_PORT}) ({result})")
        client_socket.close()
        return

    with open(FILENAME, 'wb') as file:
        while True:
            bytes_read = client_socket.recv(BUFFER_SIZE)
            if not bytes_read:
                break
            file.write(bytes_read)

    client_socket.close()

if __name__ == "__main__":
    try:
        download_file()
    except KeyboardInterrupt:
        print("\n[!] Client interrupted.")