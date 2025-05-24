import psutil
import time
import os
from collections import defaultdict, namedtuple
import socket

ConnectionInfo = namedtuple('ConnectionInfo', ['pid', 'name', 'local_port', 'remote_port', 'status'])


class PortTrafficMonitor:
    def __init__(self):
        self.port_stats = defaultdict(lambda: {'sent': 0, 'recv': 0, 'connections': 0, 'process_name': 'Unknown'})
        self.initial_stats = None
        self.start_time = time.time()

    def format_bytes(self, bytes_value):
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_value < 1024.0:
                return f"{bytes_value:.2f} {unit}"
            bytes_value /= 1024.0
        return f"{bytes_value:.2f} PB"

    def get_process_name(self, pid):
        try:
            process = psutil.Process(pid)
            return process.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "Unknown"

    def get_active_connections(self):
        connections = []
        try:
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == psutil.CONN_ESTABLISHED and conn.pid:
                    process_name = self.get_process_name(conn.pid)
                    local_port = conn.laddr.port if conn.laddr else 0
                    remote_port = conn.raddr.port if conn.raddr else 0

                    conn_info = ConnectionInfo(
                        pid=conn.pid,
                        name=process_name,
                        local_port=local_port,
                        remote_port=remote_port,
                        status=conn.status
                    )
                    connections.append(conn_info)
        except (psutil.AccessDenied, PermissionError):
            pass
        return connections

    def update_port_statistics(self):
        connections = self.get_active_connections()
        current_stats = psutil.net_io_counters()

        if self.initial_stats is None:
            self.initial_stats = current_stats
            return

        total_sent = current_stats.bytes_sent - self.initial_stats.bytes_sent
        total_recv = current_stats.bytes_recv - self.initial_stats.bytes_recv

        active_ports = set()
        port_processes = {}

        for conn in connections:
            if conn.local_port > 0:
                active_ports.add(conn.local_port)
                port_processes[conn.local_port] = conn.name
            if conn.remote_port > 0:
                active_ports.add(conn.remote_port)
                if conn.remote_port not in port_processes:
                    port_processes[conn.remote_port] = conn.name

        if active_ports:
            avg_sent_per_port = total_sent / len(active_ports)
            avg_recv_per_port = total_recv / len(active_ports)

            for port in active_ports:
                self.port_stats[port]['sent'] = avg_sent_per_port
                self.port_stats[port]['recv'] = avg_recv_per_port
                self.port_stats[port]['connections'] = sum(1 for conn in connections
                                                           if conn.local_port == port or conn.remote_port == port)
                if port in port_processes:
                    self.port_stats[port]['process_name'] = port_processes[port]

    def get_service_name(self, port):
        common_ports = {
            80: 'HTTP', 443: 'HTTPS', 21: 'FTP', 22: 'SSH', 23: 'Telnet',
            25: 'SMTP', 53: 'DNS', 110: 'POP3', 143: 'IMAP', 993: 'IMAPS',
            995: 'POP3S', 587: 'SMTP', 465: 'SMTPS', 3389: 'RDP', 5432: 'PostgreSQL',
            3306: 'MySQL', 1521: 'Oracle', 6379: 'Redis', 27017: 'MongoDB'
        }
        return common_ports.get(port, f'Port-{port}')

    def clear_screen(self):
        os.system('cls' if os.name == 'nt' else 'clear')

    def display_statistics(self):
        self.clear_screen()
        elapsed_time = time.time() - self.start_time

        print("=" * 80)
        print("PORT-BASED NETWORK TRAFFIC MONITOR")
        print("=" * 80)
        print(f"Session Duration: {int(elapsed_time)} seconds")
        print(f"Active Ports: {len(self.port_stats)}")
        print("Press Ctrl+C to generate final report")
        print("=" * 80)

        if self.port_stats:
            print(f"{'Port':<8} {'Service':<15} {'Process':<20} {'Sent':<12} {'Received':<12} {'Connections':<11}")
            print("-" * 80)

            sorted_ports = sorted(self.port_stats.items(), key=lambda x: x[1]['sent'] + x[1]['recv'], reverse=True)

            for port, stats in sorted_ports[:20]:
                service_name = self.get_service_name(port)
                process_name = stats['process_name'][:19] if len(stats['process_name']) > 19 else stats['process_name']

                print(f"{port:<8} {service_name:<15} {process_name:<20} "
                      f"{self.format_bytes(stats['sent']):<12} "
                      f"{self.format_bytes(stats['recv']):<12} "
                      f"{stats['connections']:<11}")
        else:
            print("No active connections detected...")

        print("=" * 80)

    def generate_report(self):
        elapsed_time = time.time() - self.start_time
        total_sent = sum(stats['sent'] for stats in self.port_stats.values())
        total_recv = sum(stats['recv'] for stats in self.port_stats.values())

        print("\n" + "=" * 80)
        print("FINAL TRAFFIC REPORT BY PORTS")
        print("=" * 80)
        print(f"Total Session Time: {int(elapsed_time)} seconds")
        print(f"Total Ports Monitored: {len(self.port_stats)}")
        print(f"Total Traffic Sent: {self.format_bytes(total_sent)}")
        print(f"Total Traffic Received: {self.format_bytes(total_recv)}")
        print(f"Combined Traffic: {self.format_bytes(total_sent + total_recv)}")
        print("=" * 80)

        if self.port_stats:
            print(
                f"{'Rank':<5} {'Port':<8} {'Service':<15} {'Process':<20} {'Sent':<12} {'Received':<12} {'Total':<12}")
            print("-" * 90)

            sorted_ports = sorted(self.port_stats.items(),
                                  key=lambda x: x[1]['sent'] + x[1]['recv'], reverse=True)

            for rank, (port, stats) in enumerate(sorted_ports, 1):
                service_name = self.get_service_name(port)
                process_name = stats['process_name'][:19] if len(stats['process_name']) > 19 else stats['process_name']
                total_traffic = stats['sent'] + stats['recv']

                print(f"{rank:<5} {port:<8} {service_name:<15} {process_name:<20} "
                      f"{self.format_bytes(stats['sent']):<12} "
                      f"{self.format_bytes(stats['recv']):<12} "
                      f"{self.format_bytes(total_traffic):<12}")

        print("=" * 80)

    def run(self):
        print("Starting Port Traffic Monitor...")
        print("Monitoring network connections and traffic by ports...")

        try:
            while True:
                self.update_port_statistics()
                self.display_statistics()
                time.sleep(2)

        except KeyboardInterrupt:
            self.generate_report()
            print("\nMonitoring stopped.")


def main():
    monitor = PortTrafficMonitor()
    monitor.run()


if __name__ == "__main__":
    main()