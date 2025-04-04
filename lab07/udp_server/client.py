import socket
import time


def run_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(1.0)
    server_address = ('localhost', 9999)

    for seq in range(1, 11):
        send_time = time.time()
        message = f"Ping {seq} {send_time}"

        try:
            print(f"Sent: {message}")
            client_socket.sendto(message.encode('utf-8'), server_address)
            data, server = client_socket.recvfrom(1024)
            recv_time = time.time()
            rtt = recv_time - send_time

            print(f"Received from {server}: {data.decode('utf-8')}")
            print(f"RTT: {rtt:.6f} seconds")

        except socket.timeout:
            print("Request timed out")

        time.sleep(0.5)

    client_socket.close()


if __name__ == "__main__":
    run_client()