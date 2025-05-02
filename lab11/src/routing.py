import threading
import queue
import time
from copy import deepcopy


class AsyncNode:
    def __init__(self, node_id, neighbors_costs):
        self.node_id = node_id
        self.neighbors_costs = neighbors_costs.copy()
        self.routing_table = {}
        self.message_queue = queue.Queue()
        self.lock = threading.Lock()
        self.processing_thread = None
        self.running = False

        for neighbor_id, cost in neighbors_costs.items():
            self.routing_table[neighbor_id] = (neighbor_id, cost)

        self.routing_table[node_id] = (node_id, 0)
        self.neighbor_handlers = {}

    def start_processing(self):
        self.running = True
        self.processing_thread = threading.Thread(target=self._process_message_queue)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def stop_processing(self):
        self.running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=1.0)

    def _process_message_queue(self):
        while self.running:
            try:
                message = self.message_queue.get(timeout=0.1)
                sender_id, distance_vector = message
                self._process_update(sender_id, distance_vector)
                self.message_queue.task_done()
            except queue.Empty:
                continue

    def register_neighbor_handler(self, neighbor_id, handler):
        self.neighbor_handlers[neighbor_id] = handler

    def receive_message(self, sender_id, distance_vector):
        self.message_queue.put((sender_id, distance_vector))

    def get_distance_vector(self):
        with self.lock:
            distance_vector = {}

            for dest, (_, cost) in self.routing_table.items():
                distance_vector[dest] = cost

            return distance_vector

    def update_link_cost(self, neighbor_id, new_cost):
        if neighbor_id not in self.neighbors_costs:
            raise ValueError(f"Node {neighbor_id} is not a direct neighbor of node {self.node_id}")

        with self.lock:
            old_cost = self.neighbors_costs[neighbor_id]
            self.neighbors_costs[neighbor_id] = new_cost
            self.routing_table[neighbor_id] = (neighbor_id, new_cost)
            has_changes = old_cost != new_cost

        if has_changes:
            self._notify_neighbors()

    def _process_update(self, sender_id, distance_vector):
        if sender_id not in self.neighbors_costs:
            print(f"Warning: Node {self.node_id} received update from non-neighbor {sender_id}")
            return

        has_changes = False

        with self.lock:
            sender_cost = self.neighbors_costs[sender_id]

            for dest, cost_via_sender in distance_vector.items():
                if dest == self.node_id:
                    continue

                total_cost = sender_cost + cost_via_sender
                current_cost = float('inf')

                if dest in self.routing_table:
                    _, current_cost = self.routing_table[dest]

                if total_cost < current_cost:
                    self.routing_table[dest] = (sender_id, total_cost)
                    has_changes = True

        if has_changes:
            self._notify_neighbors()

    def _notify_neighbors(self):
        distance_vector = self.get_distance_vector()

        for neighbor_id, handler in self.neighbor_handlers.items():
            if not handler:
                continue

            handler(self.node_id, deepcopy(distance_vector))

    def __str__(self):
        with self.lock:
            result = f"Routing table for Node {self.node_id}:\n"
            result += f"{'Destination':<15} {'Next Hop':<15} {'Cost':<10}\n"
            result += "-" * 40 + "\n"

            for dest in sorted(self.routing_table.keys()):
                next_hop, cost = self.routing_table[dest]
                cost_str = str(cost) if cost != float('inf') else "∞"
                result += f"{dest:<15} {next_hop:<15} {cost_str:<10}\n"

            return result


class AsyncNetwork:
    def __init__(self):
        self.nodes = {}
        self.lock = threading.Lock()

    def add_node(self, node_id, neighbors_costs):
        with self.lock:
            self.nodes[node_id] = AsyncNode(node_id, neighbors_costs)

    def setup_network(self):
        with self.lock:
            for node_id, node in self.nodes.items():
                for neighbor_id in node.neighbors_costs:
                    if neighbor_id in self.nodes:
                        def create_handler(target_node):
                            return lambda sender_id, dv: target_node.receive_message(sender_id, dv)

                        neighbor_node = self.nodes[neighbor_id]
                        handler = create_handler(neighbor_node)
                        node.register_neighbor_handler(neighbor_id, handler)

            for node in self.nodes.values():
                node.start_processing()

            for node in self.nodes.values():
                node._notify_neighbors()

    def update_link_cost(self, node1_id, node2_id, new_cost):
        with self.lock:
            if node1_id in self.nodes:
                self.nodes[node1_id].update_link_cost(node2_id, new_cost)

            if node2_id in self.nodes:
                self.nodes[node2_id].update_link_cost(node1_id, new_cost)

    def stop_all_nodes(self):
        with self.lock:
            for node in self.nodes.values():
                node.stop_processing()

    def print_routing_tables(self):
        with self.lock:
            for node_id in sorted(self.nodes.keys()):
                print(self.nodes[node_id])
                print()


def create_async_test_network():
    network = AsyncNetwork()
    network.add_node(0, {1: 1, 3: 7})
    network.add_node(1, {0: 1, 2: 1})
    network.add_node(2, {1: 1, 3: 2})
    network.add_node(3, {0: 7, 2: 2})
    network.setup_network()
    print("Waiting for the network to stabilize...")
    time.sleep(2)
    print("\nInitial Routing Tables:")
    network.print_routing_tables()

    return network


def test_async_network():
    network = create_async_test_network()

    try:
        print("\n=== Testing async network ===\n")
        print("\nUpdated Routing Tables:")
        network.print_routing_tables()

    finally:
        network.stop_all_nodes()


def test_async_link_cost_change():
    network = create_async_test_network()

    try:
        print("\n=== Testing async link cost change ===\n")
        print("Changing link cost between Node 0 and Node 3 from 7 to 3...")
        network.update_link_cost(0, 3, 3)
        print("Waiting for updates to propagate...")
        time.sleep(2)
        print("\nUpdated Routing Tables:")
        network.print_routing_tables()
    finally:
        network.stop_all_nodes()


if __name__ == "__main__":
    test_async_network()
    test_async_link_cost_change()
