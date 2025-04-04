import socket
import time
import sys
import random
import threading


class HeartbeatClient:
    def __init__(self, server_host='localhost', server_port=9999, interval=1.0, client_id=None):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.client_socket.settimeout(1.0)
        self.server_address = (server_host, server_port)
        self.interval = interval
        self.seq_num = 1
        self.sent_packets = 0
        self.received_packets = 0
        self.running = True
        self.client_id = client_id if client_id else f"Client-{random.randint(1000, 9999)}"

    def start(self):
        print(f"Running Heartbeat client {self.client_id}")
        print(f"Connecting to server {self.server_address[0]}:{self.server_address[1]}")
        print(f"Sending interval: {self.interval} seconds")

        stats_thread = threading.Thread(target=self.show_stats)
        stats_thread.daemon = True
        stats_thread.start()

        try:
            while self.running:
                self.send_heartbeat()
                time.sleep(self.interval)

        except KeyboardInterrupt:
            print(f"\nClient {self.client_id} shutting down...")
        finally:
            self.client_socket.close()

    def send_heartbeat(self):
        send_time = time.time()
        message = f"Heartbeat {self.seq_num} {send_time}"

        try:
            self.client_socket.sendto(message.encode('utf-8'), self.server_address)
            self.sent_packets += 1
            data, server = self.client_socket.recvfrom(1024)
            response = data.decode('utf-8')
            self.received_packets += 1
            recv_time = time.time()
            rtt = recv_time - send_time

            print(f"[{self.client_id}] Sent #{self.seq_num}, received answer: {response}, RTT: {rtt:.6f} sec")

        except socket.timeout:
            print(f"[{self.client_id}] Package #{self.seq_num} was missed or no answer")

        # Увеличиваем номер последовательности
        self.seq_num += 1

    def show_stats(self):
        while self.running:
            time.sleep(10)

            if self.sent_packets > 0:
                loss_rate = (self.sent_packets - self.received_packets) / self.sent_packets * 100
            else:
                loss_rate = 0

            print(f"\n--- {self.client_id} statistics ---")
            print(f"Sent packages: {self.sent_packets}")
            print(f"Received answers: {self.received_packets}")
            print(f"Missed packages: {loss_rate:.1f}%")
            print("-----------------------\n")


def main():
    server_host = 'localhost'
    server_port = 9999
    interval = 1.0
    client_id = None

    if len(sys.argv) > 1:
        client_id = sys.argv[1]

    client = HeartbeatClient(server_host, server_port, interval, client_id)
    client.start()


if __name__ == "__main__":
    main()