import socket
import random
import time
import threading
from datetime import datetime


class HeartbeatServer:
    def __init__(self, host='localhost', port=9999, timeout=5):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.server_address = (host, port)
        self.server_socket.bind(self.server_address)
        self.clients = {}
        self.client_timeout = timeout
        self.running = True
        self.monitor_thread = threading.Thread(target=self.monitor_clients)
        self.monitor_thread.daemon = True

    def start(self):
        print(f"Heartbeat server is running on {self.server_address[0]}:{self.server_address[1]}")
        print(f"Timeout for clients: {self.client_timeout} seconds")

        self.monitor_thread.start()

        try:
            while self.running:
                data, client_address = self.server_socket.recvfrom(1024)
                self.process_packet(data, client_address)

        except KeyboardInterrupt:
            print("Server shutting down...")
        finally:
            self.server_socket.close()

    def process_packet(self, data, client_address):
        message = data.decode('utf-8')
        parts = message.split()

        if len(parts) >= 3 and parts[0] == "Heartbeat":
            seq_num = int(parts[1])
            timestamp = float(parts[2])
            current_time = time.time()
            delay = current_time - timestamp

            if random.random() < 0.2:
                print(f"Package from {client_address} was dropped")
                return

            if client_address in self.clients:
                last_seq = self.clients[client_address]['last_seq']

                if seq_num > last_seq + 1:
                    missed = seq_num - last_seq - 1
                    print(f"Client {client_address} missed {missed} package(s) ({last_seq + 1}-{seq_num - 1})")

                # Обновляем информацию о клиенте
                self.clients[client_address]['last_seq'] = seq_num
                self.clients[client_address]['last_time'] = current_time
            else:
                # Новый клиент
                print(f"New client was connected: {client_address}")
                self.clients[client_address] = {
                    'last_seq': seq_num,
                    'last_time': current_time
                }

            print(
                f"[{datetime.now().strftime('%H:%M:%S')}] Received Heartbeat #{seq_num} from {client_address}, delay: {delay:.6f} sec")

            response = f"ACK {seq_num}"
            self.server_socket.sendto(response.encode('utf-8'), client_address)

    def monitor_clients(self):
        while self.running:
            current_time = time.time()
            disconnected_clients = []

            for client_address, info in self.clients.items():
                last_time = info['last_time']

                if current_time - last_time > self.client_timeout:
                    print(
                        f"[{datetime.now().strftime('%H:%M:%S')}] WARNING: Client {client_address} was disconnected (no activity for {self.client_timeout} seconds)")
                    disconnected_clients.append(client_address)

            for client in disconnected_clients:
                del self.clients[client]

            time.sleep(1)


if __name__ == "__main__":
    server = HeartbeatServer(timeout=5)
    server.start()