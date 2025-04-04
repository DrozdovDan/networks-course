import socket
import random


def run_server():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_address = ('localhost', 9999)
    server_socket.bind(server_address)

    print(f"Server is running on {server_address[0]}:{server_address[1]}")

    while True:
        data, client_address = server_socket.recvfrom(1024)
        message = data.decode('utf-8')
        print(f"Received from {client_address}: {message}")

        if random.random() < 0.2:
            print(f"Package from {client_address} was dropped")
            continue

        response = message.upper()
        server_socket.sendto(response.encode('utf-8'), client_address)
        print(f"Sent to {client_address}: {response}")


if __name__ == "__main__":
    run_server()