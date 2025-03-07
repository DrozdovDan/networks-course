import argparse
import json
import socket
import threading
import time
from turtledemo.penrose import start

threads = {}
last_index = 0


def one_socket_worker(current_socket: socket, addr, sem: threading.Semaphore) -> None:
    sem.acquire()

    request = current_socket.recv(1024).decode()
    if not request:
        sem.release()
        return

    global threads
    global last_index

    if not addr[1] in threads:
        threads[addr[1]] = last_index
        last_index += 1

    file = request.split()[1][1:]

    try:
        with open(file, 'r') as f:
            response = 'HTTP/1.1 200 OK\n\n' + f.read()
    except FileNotFoundError:
        time.sleep(10)
        response = 'HTTP/1.1 404 Not Found\nFile not found error'

    current_socket.sendall(response.encode())
    current_socket.close()
    sem.release()


def main(port: int, concurrency_level: int) -> None:
    start_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    start_socket.bind(('', port))

    start_socket.listen(7)

    semaphore = threading.Semaphore(concurrency_level)

    max_requests = 10
    for i in range(max_requests):
        current_socket, addr = start_socket.accept()

        thread = threading.Thread(target=one_socket_worker, args=(current_socket, addr, semaphore))
        thread.start()

    start_socket.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('port', type=int, help='Port to listen on')
    parser.add_argument('concurrency_level', type=int, help='Maximum number of concurrent threads')

    args = parser.parse_args()

    main(args.port, args.concurrency_level)
