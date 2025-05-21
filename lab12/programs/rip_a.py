import json
import random
import ipaddress
from typing import Dict, List, Tuple, Set
import time
import sys


class Router:
    def __init__(self, ip: str):
        self.ip = ip
        self.routing_table = {ip: (ip, 0)}
        self.neighbors = set()

    def add_neighbor(self, neighbor_ip: str):
        self.neighbors.add(neighbor_ip)
        self.routing_table[neighbor_ip] = (neighbor_ip, 1)

    def update_routing_table(self, sender_ip: str, received_table: Dict[str, Tuple[str, int]]) -> bool:
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

    def get_routing_table_for_neighbors(self) -> Dict[str, Tuple[str, int]]:
        table_for_neighbors = {}
        for dest_ip, (next_hop, metric) in self.routing_table.items():
            if metric < 16:
                table_for_neighbors[dest_ip] = (next_hop, metric)
        return table_for_neighbors

    def print_routing_table(self, is_final=True, step=None):
        if is_final:
            print(f"Final state of router {self.ip} table:")
        else:
            print(f"Simulation step {step} of router {self.ip}")

        print("[Source IP]      [Destination IP]    [Next Hop]       [Metric]  ")

        for dest_ip, (next_hop, metric) in sorted(self.routing_table.items()):
            if metric < 16:
                print(f"{self.ip:<16} {dest_ip:<18} {next_hop:<16} {metric:>10}  ")
        print()


class Network:
    def __init__(self):
        self.routers: Dict[str, Router] = {}
        self.connections: Set[Tuple[str, str]] = set()

    def add_router(self, ip: str) -> Router:
        if ip not in self.routers:
            self.routers[ip] = Router(ip)
        return self.routers[ip]

    def add_connection(self, ip1: str, ip2: str):
        router1 = self.add_router(ip1)
        router2 = self.add_router(ip2)

        router1.add_neighbor(ip2)
        router2.add_neighbor(ip1)

        self.connections.add((min(ip1, ip2), max(ip1, ip2)))

    def run_rip_simulation(self, max_iterations=100, show_intermediate=False):
        iteration = 0
        changes = True

        while changes and iteration < max_iterations:
            iteration += 1
            changes = False
            updates = []

            for router_ip, router in self.routers.items():
                table_to_send = router.get_routing_table_for_neighbors()

                for neighbor_ip in router.neighbors:
                    updates.append((neighbor_ip, router_ip, table_to_send))

            for (receiver_ip, sender_ip, table) in updates:
                if self.routers[receiver_ip].update_routing_table(sender_ip, table):
                    changes = True

            if show_intermediate:
                print(f"\n===== Simulation step {iteration} =====")
                for router_ip in sorted(self.routers.keys()):
                    self.routers[router_ip].print_routing_table(is_final=False, step=iteration)
                print("=" * 40)

        return iteration

    def print_all_routing_tables(self):
        for router_ip in sorted(self.routers.keys()):
            self.routers[router_ip].print_routing_table()


def generate_random_network(num_routers=5, connectivity=0.5):
    network = Network()
    ip_addresses = []

    for _ in range(num_routers):
        ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        while ip in ip_addresses:
            ip = f"{random.randint(1, 255)}.{random.randint(0, 255)}.{random.randint(0, 255)}.{random.randint(1, 254)}"
        ip_addresses.append(ip)

    for ip in ip_addresses:
        network.add_router(ip)

    for i in range(num_routers):
        for j in range(i + 1, num_routers):
            if random.random() < connectivity:
                network.add_connection(ip_addresses[i], ip_addresses[j])

    connected_components = find_connected_components(network)

    while len(connected_components) > 1:
        comp1 = random.choice(connected_components)
        comp2 = random.choice([c for c in connected_components if c != comp1])

        ip1 = random.choice(list(comp1))
        ip2 = random.choice(list(comp2))

        network.add_connection(ip1, ip2)

        connected_components = find_connected_components(network)

    return network


def find_connected_components(network):
    visited = set()
    components = []

    for router_ip in network.routers:
        if router_ip not in visited:
            component = set()
            dfs(network, router_ip, visited, component)
            components.append(component)

    return components


def dfs(network, router_ip, visited, component):
    visited.add(router_ip)
    component.add(router_ip)

    for neighbor_ip in network.routers[router_ip].neighbors:
        if neighbor_ip not in visited:
            dfs(network, neighbor_ip, visited, component)


def load_network_from_file(filename):
    with open(filename, 'r') as f:
        data = json.load(f)

    network = Network()

    for ip in data["routers"]:
        network.add_router(ip)

    for ip1, ip2 in data["connections"]:
        network.add_connection(ip1, ip2)

    return network


def main():
    print("RIP Protocol Emulator")
    print("-" * 30)
    print("1. Load network from file")
    print("2. Generate random network")
    choice = input("Enter your choice (1/2): ")

    network = None

    if choice == '1':
        filename = input("Enter filename (default: network.json): ") or "network.json"
        try:
            network = load_network_from_file(filename)
            print(f"Network loaded from {filename}")
        except Exception as e:
            print(f"Error loading file: {e}")
            print("Generating random network instead.")
            network = generate_random_network()
    else:
        try:
            num_routers = int(input("Enter number of routers (default 5): ") or 5)
            connectivity = float(input("Enter connectivity probability (0-1, default 0.5): ") or 0.5)
            network = generate_random_network(num_routers, connectivity)
            print(f"Random network with {num_routers} routers generated")
        except ValueError:
            print("Invalid input. Using default values.")
            network = generate_random_network()

    show_intermediate = input("Show intermediate routing tables? (y/n, default n): ").lower() == 'y'
    iterations = network.run_rip_simulation(show_intermediate=show_intermediate)
    print(f"\nRIP simulation converged after {iterations} iterations.")
    print("\n===== Final Routing Tables =====")
    network.print_all_routing_tables()


if __name__ == "__main__":
    main()
