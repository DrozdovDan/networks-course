import socket
import sys


def start_server(host='::1', port=8888):
    server_socket = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    try:
        server_socket.bind((host, port, 0, 0))
        server_socket.listen(5)
        print(f"Server is running on [{host}]:{port}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Connecting to [{client_address[0]}]:{client_address[1]}")

            try:
                while True:
                    data = client_socket.recv(1024)
                    if not data:
                        break

                    received_message = data.decode('utf-8')
                    print(f"Received: {received_message}")
                    response = received_message.upper()
                    client_socket.sendall(response.encode('utf-8'))
                    print(f"Sent: {response}")

            except Exception as e:
                print(f"Error while processing client data: {e}")
            finally:
                client_socket.close()
                print(f"Connection to [{client_address[0]}]:{client_address[1]} closed")

    except KeyboardInterrupt:
        print("\nServer shutting down...")
    except Exception as e:
        print(f"Server error: {e}")
    finally:
        server_socket.close()


if __name__ == "__main__":
    port = 8888
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port: {sys.argv[1]}")
            sys.exit(1)

    start_server(port=port)
