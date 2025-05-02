import socket
import sys


def start_client(host='::1', port=8888):
    client_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)

    try:
        client_socket.connect((host, port, 0, 0))
        print(f"Connecting to server [{host}]:{port}")

        while True:
            message = input("Enter message: ")

            if message:
                client_socket.sendall(message.encode('utf-8'))
                data = client_socket.recv(1024)
                response = data.decode('utf-8')

                print(f"Answer: {response}")

    except ConnectionRefusedError:
        print(f"Cannot connect to server [{host}]:{port}.")
    except KeyboardInterrupt:
        print("\nClient shutting down...")
    except Exception as e:
        print(f"Client error: {e}")
    finally:
        client_socket.close()


if __name__ == "__main__":
    host = '::1'
    port = 8888

    if len(sys.argv) > 1:
        host = sys.argv[1]

    if len(sys.argv) > 2:
        try:
            port = int(sys.argv[2])
        except ValueError:
            print(f"Invalid port: {sys.argv[2]}")
            sys.exit(1)

    start_client(host, port)
