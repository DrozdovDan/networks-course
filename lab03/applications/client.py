import socket
import argparse

def get_request_str(filename: str, host: str, port: int) -> str:
    return f'GET /{filename} HTTP/1.1 Host: {host}:{port}\r\n\n'


def main(host: str, port: int, filename: str) -> None:
    local_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    local_socket.connect((host, port))
    local_socket.send(get_request_str(filename, host, port).encode())

    data = local_socket.recv(1024).decode()

    print(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('server_host', type=str, help='The host address of the server')
    parser.add_argument('server_port', type=int, help='The port of the server')
    parser.add_argument('filename', type=str, help='The filename of the file')

    args = parser.parse_args()

    main(args.server_host, args.server_port, args.filename)


