import socket
import threading
import time
import argparse
import tkinter as tk
from tkinter import ttk, scrolledtext
import json
from datetime import datetime
import struct


class ProtocolTestServer:
    def __init__(self, host='0.0.0.0', tcp_port=9000, udp_port=9001):
        self.host = host
        self.tcp_port = tcp_port
        self.udp_port = udp_port

        self.tcp_socket = None
        self.udp_socket = None

        self.tcp_running = False
        self.udp_running = False

        self.tcp_bytes_received = 0
        self.udp_bytes_received = 0
        self.udp_packets_received = 0
        self.udp_packets_expected = 0
        self.tcp_start_time = 0
        self.udp_start_time = 0
        self.tcp_last_time = 0
        self.udp_last_time = 0

        self.tcp_lock = threading.Lock()
        self.udp_lock = threading.Lock()

        self.tcp_log_callback = None
        self.udp_log_callback = None
        self.stats_callback = None

    def start_tcp_server(self):
        if self.tcp_running:
            return

        self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.tcp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.tcp_socket.bind((self.host, self.tcp_port))
            self.tcp_socket.listen(5)
            self.tcp_running = True

            with self.tcp_lock:
                self.tcp_bytes_received = 0
                self.tcp_start_time = 0
                self.tcp_last_time = 0

            if self.tcp_log_callback:
                self.tcp_log_callback(f"TCP server is running on {self.host}:{self.tcp_port}")

            tcp_thread = threading.Thread(target=self._handle_tcp_connections)
            tcp_thread.daemon = True
            tcp_thread.start()

            return True
        except Exception as e:
            if self.tcp_log_callback:
                self.tcp_log_callback(f"Error starting TCP server: {e}")
            return False

    def start_udp_server(self):
        if self.udp_running:
            return

        self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.udp_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        try:
            self.udp_socket.bind((self.host, self.udp_port))
            self.udp_running = True

            with self.udp_lock:
                self.udp_bytes_received = 0
                self.udp_packets_received = 0
                self.udp_packets_expected = 0
                self.udp_start_time = 0
                self.udp_last_time = 0

            if self.udp_log_callback:
                self.udp_log_callback(f"UDP server is running on {self.host}:{self.udp_port}")

            udp_thread = threading.Thread(target=self._handle_udp_packets)
            udp_thread.daemon = True
            udp_thread.start()

            return True
        except Exception as e:
            if self.udp_log_callback:
                self.udp_log_callback(f"Error starting UDP server: {e}")
            return False

    def stop_tcp_server(self):
        self.tcp_running = False
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass

        if self.tcp_log_callback:
            self.tcp_log_callback("TCP server shutting down...")

    def stop_udp_server(self):
        self.udp_running = False
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass

        if self.udp_log_callback:
            self.udp_log_callback("UDP server shutting down...")

    def stop_all(self):
        self.stop_tcp_server()
        self.stop_udp_server()

    def _handle_tcp_connections(self):
        while self.tcp_running:
            try:
                client_socket, address = self.tcp_socket.accept()
                client_thread = threading.Thread(
                    target=self._handle_tcp_client,
                    args=(client_socket, address)
                )
                client_thread.daemon = True
                client_thread.start()
            except Exception as e:
                if self.tcp_running and self.tcp_log_callback:
                    self.tcp_log_callback(f"Error accepting TCP-connection: {e}")
                break

    def _handle_tcp_client(self, client_socket, address):
        if self.tcp_log_callback:
            self.tcp_log_callback(f"Accepted TCP-connection from {address}")

        client_socket.settimeout(10)
        first_packet = True

        try:
            while self.tcp_running:
                try:
                    header = client_socket.recv(8)
                    if not header or len(header) < 8:
                        break

                    packet_size, packet_num = struct.unpack("!II", header)
                    data = b""
                    remaining = packet_size

                    while remaining > 0 and self.tcp_running:
                        chunk = client_socket.recv(min(4096, remaining))
                        if not chunk:
                            break
                        data += chunk
                        remaining -= len(chunk)

                    if len(data) < packet_size:
                        if self.tcp_log_callback:
                            self.tcp_log_callback(
                                f"Incomplete TCP-packet from {address}: received {len(data)} from {packet_size} byte")
                        break

                    with self.tcp_lock:
                        if first_packet:
                            self.tcp_start_time = time.time()
                            first_packet = False

                        self.tcp_bytes_received += len(header) + len(data)
                        self.tcp_last_time = time.time()

                    if self.stats_callback:
                        self._update_stats()

                except socket.timeout:
                    if self.tcp_log_callback:
                        self.tcp_log_callback(f"Timeout TCP-connection from {address}")
                    break
                except Exception as e:
                    if self.tcp_log_callback:
                        self.tcp_log_callback(f"Error handling TCP-data from {address}: {e}")
                    break
        finally:
            client_socket.close()
            if self.tcp_log_callback:
                self.tcp_log_callback(f"Closing TCP-connection from {address}")

    def _handle_udp_packets(self):
        if self.udp_log_callback:
            self.udp_log_callback(f"Waiting UDP-packets on {self.host}:{self.udp_port}")

        first_packet = True

        try:
            self.udp_socket.settimeout(0.5)

            while self.udp_running:
                try:
                    data, address = self.udp_socket.recvfrom(65535)

                    if len(data) < 8:
                        continue

                    total_packets, packet_num = struct.unpack("!II", data[:8])

                    with self.udp_lock:
                        if first_packet:
                            self.udp_start_time = time.time()
                            first_packet = False
                            self.udp_packets_expected = total_packets

                        self.udp_bytes_received += len(data)
                        self.udp_packets_received += 1
                        self.udp_last_time = time.time()

                    if self.stats_callback:
                        self._update_stats()

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.udp_running and self.udp_log_callback:
                        self.udp_log_callback(f"Error handling UDP-packet: {e}")
        except Exception as e:
            if self.udp_running and self.udp_log_callback:
                self.udp_log_callback(f"Error UDP-server: {e}")

    def _update_stats(self):
        tcp_stats = {}
        udp_stats = {}

        with self.tcp_lock:
            if self.tcp_start_time > 0 and self.tcp_last_time > 0:
                elapsed = self.tcp_last_time - self.tcp_start_time
                if elapsed > 0:
                    tcp_stats = {
                        "bytes_received": self.tcp_bytes_received,
                        "elapsed_time": elapsed,
                        "speed_mbps": (self.tcp_bytes_received * 8 / 1000000) / elapsed,
                        "packets_lost": "N/A"
                    }

        with self.udp_lock:
            if self.udp_start_time > 0 and self.udp_last_time > 0:
                elapsed = self.udp_last_time - self.udp_start_time
                if elapsed > 0:
                    packets_lost = max(0, self.udp_packets_expected - self.udp_packets_received)
                    loss_percent = 0
                    if self.udp_packets_expected > 0:
                        loss_percent = (packets_lost / self.udp_packets_expected) * 100

                    udp_stats = {
                        "bytes_received": self.udp_bytes_received,
                        "elapsed_time": elapsed,
                        "speed_mbps": (self.udp_bytes_received * 8 / 1000000) / elapsed,
                        "packets_received": self.udp_packets_received,
                        "packets_expected": self.udp_packets_expected,
                        "packets_lost": packets_lost,
                        "loss_percent": loss_percent
                    }

        if self.stats_callback:
            self.stats_callback(tcp_stats, udp_stats)


class ServerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Server")
        self.root.geometry("800x600")
        self.server = ProtocolTestServer()
        self.server.tcp_log_callback = self.log_tcp
        self.server.udp_log_callback = self.log_udp
        self.server.stats_callback = self.update_stats
        self._create_ui()

    def _create_ui(self):
        settings_frame = ttk.LabelFrame(self.root, text="Server settings")
        settings_frame.pack(padx=10, pady=10, fill=tk.X)

        ttk.Label(settings_frame, text="IP:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.ip_var = tk.StringVar(value="0.0.0.0")
        ttk.Entry(settings_frame, textvariable=self.ip_var, width=15).grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        ttk.Label(settings_frame, text="TCP port:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.tcp_port_var = tk.IntVar(value=9000)
        ttk.Entry(settings_frame, textvariable=self.tcp_port_var, width=6).grid(row=0, column=3, padx=5, pady=5,
                                                                                sticky=tk.W)
        ttk.Label(settings_frame, text="UDP port:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.udp_port_var = tk.IntVar(value=9001)
        ttk.Entry(settings_frame, textvariable=self.udp_port_var, width=6).grid(row=0, column=5, padx=5, pady=5,
                                                                                sticky=tk.W)
        buttons_frame = ttk.Frame(settings_frame)
        buttons_frame.grid(row=0, column=6, padx=10, pady=5, sticky=tk.E, columnspan=2)

        self.start_tcp_btn = ttk.Button(buttons_frame, text="Start TCP", command=self.start_tcp)
        self.start_tcp_btn.pack(side=tk.LEFT, padx=5)

        self.stop_tcp_btn = ttk.Button(buttons_frame, text="Stop TCP", command=self.stop_tcp, state=tk.DISABLED)
        self.stop_tcp_btn.pack(side=tk.LEFT, padx=5)

        self.start_udp_btn = ttk.Button(buttons_frame, text="Start UDP", command=self.start_udp)
        self.start_udp_btn.pack(side=tk.LEFT, padx=5)

        self.stop_udp_btn = ttk.Button(buttons_frame, text="Stop UDP", command=self.stop_udp, state=tk.DISABLED)
        self.stop_udp_btn.pack(side=tk.LEFT, padx=5)

        stats_frame = ttk.LabelFrame(self.root, text="Statistics")
        stats_frame.pack(padx=10, pady=10, fill=tk.X)

        tcp_stats_frame = ttk.LabelFrame(stats_frame, text="TCP")
        tcp_stats_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.BOTH, expand=True)

        ttk.Label(tcp_stats_frame, text="Bytes received:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.tcp_bytes_var = tk.StringVar(value="0")
        ttk.Label(tcp_stats_frame, textvariable=self.tcp_bytes_var).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(tcp_stats_frame, text="Time (s):").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.tcp_time_var = tk.StringVar(value="0")
        ttk.Label(tcp_stats_frame, textvariable=self.tcp_time_var).grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(tcp_stats_frame, text="Speed (Mb/s):").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        self.tcp_speed_var = tk.StringVar(value="0")
        ttk.Label(tcp_stats_frame, textvariable=self.tcp_speed_var).grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)

        udp_stats_frame = ttk.LabelFrame(stats_frame, text="UDP")
        udp_stats_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.BOTH, expand=True)

        ttk.Label(udp_stats_frame, text="Bytes received:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_bytes_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_bytes_var).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Time (s):").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_time_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_time_var).grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Speed (Mb/s):").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_speed_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_speed_var).grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Packets received:").grid(row=3, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_packets_received_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_packets_received_var).grid(row=3, column=1, padx=5, pady=2,
                                                                                    sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Packets lost:").grid(row=4, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_packets_lost_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_packets_lost_var).grid(row=4, column=1, padx=5, pady=2,
                                                                                sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Loss (%):").grid(row=5, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_loss_percent_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_loss_percent_var).grid(row=5, column=1, padx=5, pady=2,
                                                                                sticky=tk.W)

        log_frame = ttk.LabelFrame(self.root, text="Logs")
        log_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

        self.log_notebook = ttk.Notebook(log_frame)
        self.log_notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        tcp_log_frame = ttk.Frame(self.log_notebook)
        self.log_notebook.add(tcp_log_frame, text="TCP log")

        self.tcp_log = scrolledtext.ScrolledText(tcp_log_frame, wrap=tk.WORD)
        self.tcp_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        udp_log_frame = ttk.Frame(self.log_notebook)
        self.log_notebook.add(udp_log_frame, text="UDP log")

        self.udp_log = scrolledtext.ScrolledText(udp_log_frame, wrap=tk.WORD)
        self.udp_log.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.status_var = tk.StringVar(value="Ready to go")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def start_tcp(self):
        try:
            self.server.host = self.ip_var.get()
            self.server.tcp_port = self.tcp_port_var.get()

            if self.server.start_tcp_server():
                self.start_tcp_btn.config(state=tk.DISABLED)
                self.stop_tcp_btn.config(state=tk.NORMAL)
                self.status_var.set(f"TCP server is running on {self.server.host}:{self.server.tcp_port}")
        except Exception as e:
            self.log_tcp(f"Error starting TCP server: {e}")

    def stop_tcp(self):
        self.server.stop_tcp_server()
        self.start_tcp_btn.config(state=tk.NORMAL)
        self.stop_tcp_btn.config(state=tk.DISABLED)
        self.status_var.set("TCP server shutting down...")

    def start_udp(self):
        try:
            self.server.host = self.ip_var.get()
            self.server.udp_port = self.udp_port_var.get()

            if self.server.start_udp_server():
                self.start_udp_btn.config(state=tk.DISABLED)
                self.stop_udp_btn.config(state=tk.NORMAL)
                self.status_var.set(f"UDP server is running on {self.server.host}:{self.server.udp_port}")
        except Exception as e:
            self.log_udp(f"Error starting UDP server: {e}")

    def stop_udp(self):
        self.server.stop_udp_server()
        self.start_udp_btn.config(state=tk.NORMAL)
        self.stop_udp_btn.config(state=tk.DISABLED)
        self.status_var.set("UDP server shutting down...")

    def log_tcp(self, message):
        self._log(self.tcp_log, message)

    def log_udp(self, message):
        self._log(self.udp_log, message)

    def _log(self, log_widget, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_widget.insert(tk.END, f"[{timestamp}] {message}\n")
        log_widget.see(tk.END)

    def update_stats(self, tcp_stats, udp_stats):
        if tcp_stats:
            self.tcp_bytes_var.set(f"{tcp_stats['bytes_received']:,}")
            self.tcp_time_var.set(f"{tcp_stats['elapsed_time']:.2f}")
            self.tcp_speed_var.set(f"{tcp_stats['speed_mbps']:.2f}")

        if udp_stats:
            self.udp_bytes_var.set(f"{udp_stats['bytes_received']:,}")
            self.udp_time_var.set(f"{udp_stats['elapsed_time']:.2f}")
            self.udp_speed_var.set(f"{udp_stats['speed_mbps']:.2f}")
            self.udp_packets_received_var.set(f"{udp_stats['packets_received']:,}")
            self.udp_packets_lost_var.set(f"{udp_stats['packets_lost']:,}")
            self.udp_loss_percent_var.set(f"{udp_stats['loss_percent']:.2f}")

    def on_close(self):
        self.server.stop_all()
        self.root.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Protocol Speed Test Server')
    parser.add_argument('--nogui', action='store_true', help='Run in console mode (no GUI)')
    parser.add_argument('--host', default='0.0.0.0', help='Host to bind to')
    parser.add_argument('--tcp-port', type=int, default=9000, help='TCP port to listen on')
    parser.add_argument('--udp-port', type=int, default=9001, help='UDP port to listen on')
    args = parser.parse_args()

    if args.nogui:
        server = ProtocolTestServer(args.host, args.tcp_port, args.udp_port)
        server.tcp_log_callback = lambda msg: print(f"[TCP] {msg}")
        server.udp_log_callback = lambda msg: print(f"[UDP] {msg}")

        print(f"Starting server on {args.host} (TCP: {args.tcp_port}, UDP: {args.udp_port})")
        server.start_tcp_server()
        server.start_udp_server()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("Shutting down...")
        finally:
            server.stop_all()
    else:
        root = tk.Tk()
        app = ServerGUI(root)
        root.mainloop()
