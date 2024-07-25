import signal
import socket
import json
import sys
import threading

# Server configuration
from cfg import SERVER_HOST, SERVER_PORT, BUFFER_SIZE

class PRIORITY:
    NORMAL = 0
    HIGH = 1
    CRITICAL = 2

FILENAME = 'input.7z'  # Path to the file to send

def handle_client(client_socket):
    try:
        with open(FILENAME, 'rb') as file:
            while True:
                bytes_read = file.read(BUFFER_SIZE)
                if not bytes_read:
                    break
                client_socket.sendall(bytes_read)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()

def start_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind(('', SERVER_PORT))
    server_socket.listen()
    print(f"[*] Listening on {SERVER_HOST}:{SERVER_PORT}")

    def signal_handler(sig, frame):
        print("\n[!] Shutting down the server...")
        server_socket.close()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    while True:
        try:
            client_socket, addr = server_socket.accept()
            print(f"[+] Accepted connection from {addr}")
            client_handler = threading.Thread(target=handle_client, args=(client_socket,))
            client_handler.start()
        except KeyboardInterrupt:
            signal_handler(None, None)
            break


if __name__ == "__main__":
    try:
        start_server()
    except KeyboardInterrupt:
        print("\n[!] Client interrupted.")