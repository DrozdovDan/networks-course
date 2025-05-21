import json
import random
import socket
import threading
import time
import pickle
import sys
from typing import Dict, Set, Tuple


class RouterSocket(threading.Thread):
    def __init__(self, router_id, ip, port, stop_event, neighbor_info=None):
        super().__init__()
        self.router_id = router_id
        self.ip = ip
        self.port = port
        self.routing_table = {ip: (ip, 0)}
        self.neighbors = {}
        self.stop_event = stop_event
        self.iteration = 0
        self.lock = threading.Lock()
        self.print_lock = threading.Lock()

        if neighbor_info:
            self.neighbors = neighbor_info

        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            self.socket.bind(('localhost', self.port))
            self.socket.settimeout(0.5)
        except socket.error as e:
            print(f"Socket binding error for router {self.ip}: {e}")
            sys.exit(1)

    def add_neighbor(self, neighbor_ip, neighbor_real_ip, neighbor_port):
        with self.lock:
            self.neighbors[neighbor_ip] = (neighbor_real_ip, neighbor_port)
            self.routing_table[neighbor_ip] = (neighbor_ip, 1)

    def update_routing_table(self, sender_ip, received_table):
        with self.lock:
            updated = False
            for dest_ip, (next_hop, metric) in received_table.items():
                if dest_ip == self.ip:
                    continue

                new_metric = metric + 1

                if new_metric > 15:
                    new_metric = 16

                if (dest_ip not in self.routing_table or
                        new_metric < self.routing_table[dest_ip][1] or
                        (sender_ip == self.routing_table[dest_ip][0] and new_metric != self.routing_table[dest_ip][1])):

                    if new_metric == 16:
                        if dest_ip in self.routing_table:
                            if self.routing_table[dest_ip][0] == sender_ip:
                                self.routing_table[dest_ip] = (sender_ip, 16)
                                updated = True
                    else:
                        self.routing_table[dest_ip] = (sender_ip, new_metric)
                        updated = True

            return updated

    def get_routing_table_for_neighbors(self):
        with self.lock:
            table_for_neighbors = {}
            for dest_ip, (next_hop, metric) in self.routing_table.items():
                if metric < 16:
                    table_for_neighbors[dest_ip] = (next_hop, metric)
            return table_for_neighbors


    def print_routing_table(self, is_final=False):
        with self.lock:
            lines = []
            if is_final:
                lines.append(f"Final state of router {self.ip} table:")
            else:
                lines.append(f"Simulation step {self.iteration} of router {self.ip}")

            lines.append("[Source IP]      [Destination IP]    [Next Hop]       [Metric]  ")

            for dest_ip, (next_hop, metric) in sorted(self.routing_table.items()):
                if metric < 16:
                    lines.append(f"{self.ip:<16} {dest_ip:<18} {next_hop:<16} {metric:>10}  ")
            text = "\n".join(lines) + "\n\n"
            with self.print_lock:
                print(text, end="")

    def run(self):
        last_update_time = time.time()

        while not self.stop_event.is_set():
            current_time = time.time()
            if current_time - last_update_time >= 1:
                self.send_updates()
                last_update_time = current_time
            try:
                updated = self.receive_updates()
                if updated:
                    self.iteration += 1
                    self.print_routing_table()
                    last_update_time = time.time()
            except socket.timeout:
                pass

            time.sleep(0.1)

        self.print_routing_table(is_final=True)
        self.socket.close()

    def send_updates(self):
        table_to_send = self.get_routing_table_for_neighbors()
        message = pickle.dumps((self.ip, table_to_send))

        for neighbor_ip, (neighbor_real_ip, neighbor_port) in self.neighbors.items():
            try:
                self.socket.sendto(message, (neighbor_real_ip, neighbor_port))
            except socket.error as e:
                print(f"Error sending to neighbor {neighbor_ip}: {e}")

    def receive_updates(self):
        updated = False

        try:
            data, _ = self.socket.recvfrom(4096)
            sender_ip, received_table = pickle.loads(data)

            if self.update_routing_table(sender_ip, received_table):
                updated = True

        except socket.timeout:
            pass
        except Exception as e:
            print(f"Error receiving updates: {e}")

        return updated


class SocketNetwork:
    def __init__(self):
        self.routers = {}
        self.connections = set()
        self.router_threads = {}
        self.stop_event = threading.Event()
        self.base_port = 10000

    def add_router(self, router_id, ip):
        if ip not in self.routers:
            port = self.base_port + router_id
            self.routers[ip] = (router_id, port)
            self.router_threads[router_id] = RouterSocket(
                router_id, ip, port, self.stop_event
            )
        return self.router_threads[router_id]

    def add_connection(self, ip1, ip2):
        if ip1 not in self.routers or ip2 not in self.routers:
            raise ValueError("Router does not exist")

        router_id1, port1 = self.routers[ip1]
        router_id2, port2 = self.routers[ip2]
        self.router_threads[router_id1].add_neighbor(ip2, 'localhost', port2)
        self.router_threads[router_id2].add_neighbor(ip1, 'localhost', port1)
        self.connections.add((min(ip1, ip2), max(ip1, ip2)))

    def start_simulation(self):
        for router_thread in self.router_threads.values():
            router_thread.start()

    def stop_simulation(self):
        self.stop_event.set()
        for router_thread in self.router_threads.values():
            router_thread.join()


def generate_random_socket_network(num_routers=5, connectivity=0.5):
    network = SocketNetwork()
    ip_addresses = []

    for _ in range(num_routers):
        ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        while ip in ip_addresses:
            ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        ip_addresses.append(ip)

    for i, ip in enumerate(ip_addresses):
        network.add_router(i, ip)

    for i in range(num_routers):
        for j in range(i + 1, num_routers):
            if random.random() < connectivity:
                network.add_connection(ip_addresses[i], ip_addresses[j])

    for i in range(num_routers - 1):
        network.add_connection(ip_addresses[i], ip_addresses[i + 1])
    network.add_connection(ip_addresses[num_routers - 1], ip_addresses[0])

    return network


def load_socket_network_from_file(filename):
    with open(filename, 'r') as f:
        data = json.load(f)

    network = SocketNetwork()

    for i, ip in enumerate(data["routers"]):
        network.add_router(i, ip)

    for ip1, ip2 in data["connections"]:
        network.add_connection(ip1, ip2)

    return network


def main_socket():
    print("RIP Protocol Emulator (Socket Version)")
    print("-" * 40)

    print("1. Load network from file")
    print("2. Generate random network")
    choice = input("Enter your choice (1/2): ")

    network = None

    if choice == '1':
        filename = input("Enter filename (default: network.json): ") or "network.json"
        try:
            network = load_socket_network_from_file(filename)
            print(f"Network loaded from {filename}")
        except Exception as e:
            print(f"Error loading file: {e}")
            print("Generating random network instead.")
            network = generate_random_socket_network()
    else:
        try:
            num_routers = int(input("Enter number of routers (default 5): ") or 5)
            connectivity = float(input("Enter connectivity probability (0-1, default 0.5): ") or 0.5)
            network = generate_random_socket_network(num_routers, connectivity)
            print(f"Random network with {num_routers} routers generated")
        except ValueError:
            print("Invalid input. Using default values.")
            network = generate_random_socket_network()

    try:
        duration = int(input("Enter simulation duration in seconds (default 10): ") or 10)
        print(f"Running simulation for {duration} seconds...")
        network.start_simulation()
        time.sleep(duration)
    except (ValueError, KeyboardInterrupt):
        print("Stopping simulation...")
    finally:
        network.stop_simulation()


if __name__ == "__main__":
    main_socket()
