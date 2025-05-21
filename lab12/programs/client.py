import socket
import threading
import time
import random
import argparse
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import json
from datetime import datetime
import struct


class ProtocolTestClient:
    def __init__(self):
        self.server_host = '127.0.0.1'
        self.tcp_port = 9000
        self.udp_port = 9001

        self.tcp_socket = None
        self.udp_socket = None

        self.tcp_running = False
        self.udp_running = False

        self.tcp_packet_size = 1024
        self.udp_packet_size = 1024
        self.tcp_total_size = 10 * 1024 * 1024
        self.udp_total_packets = 1000

        self.tcp_bytes_sent = 0
        self.udp_bytes_sent = 0
        self.udp_packets_sent = 0
        self.tcp_start_time = 0
        self.udp_start_time = 0

        self.tcp_lock = threading.Lock()
        self.udp_lock = threading.Lock()

        self.tcp_log_callback = None
        self.udp_log_callback = None
        self.stats_callback = None

    def start_tcp_test(self):
        if self.tcp_running:
            return False

        self.tcp_running = True

        with self.tcp_lock:
            self.tcp_bytes_sent = 0
            self.tcp_start_time = 0

        tcp_thread = threading.Thread(target=self._run_tcp_test)
        tcp_thread.daemon = True
        tcp_thread.start()

        return True

    def start_udp_test(self):
        if self.udp_running:
            return False

        self.udp_running = True

        with self.udp_lock:
            self.udp_bytes_sent = 0
            self.udp_packets_sent = 0
            self.udp_start_time = 0

        udp_thread = threading.Thread(target=self._run_udp_test)
        udp_thread.daemon = True
        udp_thread.start()

        return True

    def stop_tcp_test(self):
        self.tcp_running = False
        if self.tcp_socket:
            try:
                self.tcp_socket.close()
            except:
                pass

        if self.tcp_log_callback:
            self.tcp_log_callback("TCP test shutting down...")

    def stop_udp_test(self):
        self.udp_running = False
        if self.udp_socket:
            try:
                self.udp_socket.close()
            except:
                pass

        if self.udp_log_callback:
            self.udp_log_callback("UDP test shutting down...")

    def stop_all(self):
        self.stop_tcp_test()
        self.stop_udp_test()

    def _run_tcp_test(self):
        try:
            self.tcp_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.tcp_socket.settimeout(5)

            if self.tcp_log_callback:
                self.tcp_log_callback(f"Connecting to {self.server_host}:{self.tcp_port}...")

            self.tcp_socket.connect((self.server_host, self.tcp_port))

            if self.tcp_log_callback:
                self.tcp_log_callback(f"Connecting to {self.server_host}:{self.tcp_port}")

            with self.tcp_lock:
                self.tcp_start_time = time.time()

            packet_num = 0
            total_sent = 0

            while self.tcp_running and total_sent < self.tcp_total_size:
                remaining = self.tcp_total_size - total_sent
                packet_size = min(self.tcp_packet_size, remaining)

                data = random.randbytes(packet_size)

                header = struct.pack("!II", packet_size, packet_num)

                self.tcp_socket.sendall(header + data)

                with self.tcp_lock:
                    self.tcp_bytes_sent += len(header) + len(data)

                packet_num += 1
                total_sent += packet_size

                if self.stats_callback:
                    elapsed = time.time() - self.tcp_start_time
                    speed_mbps = (self.tcp_bytes_sent * 8 / 1000000) / max(0.001, elapsed)
                    self.stats_callback({
                        "protocol": "tcp",
                        "bytes_sent": self.tcp_bytes_sent,
                        "elapsed_time": elapsed,
                        "speed_mbps": speed_mbps,
                        "percent_complete": (total_sent / self.tcp_total_size) * 100
                    })

            self.tcp_socket.shutdown(socket.SHUT_RDWR)
            self.tcp_socket.close()

            if self.tcp_log_callback:
                elapsed = time.time() - self.tcp_start_time
                speed_mbps = (self.tcp_bytes_sent * 8 / 1000000) / max(0.001, elapsed)
                self.tcp_log_callback(f"TCP test completed. Sent: {self.tcp_bytes_sent:,} byte, "
                                      f"Speed: {speed_mbps:.2f} Mb/s")

            self.tcp_running = False

        except Exception as e:
            if self.tcp_log_callback:
                self.tcp_log_callback(f"Error TCP testing: {e}")
            self.tcp_running = False

    def _run_udp_test(self):
        try:
            self.udp_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

            if self.udp_log_callback:
                self.udp_log_callback(f"Sending UDP packets to {self.server_host}:{self.udp_port}...")

            with self.udp_lock:
                self.udp_start_time = time.time()

            packet_num = 0

            while self.udp_running and packet_num < self.udp_total_packets:
                payload_size = self.udp_packet_size - 8
                data = random.randbytes(payload_size)

                header = struct.pack("!II", self.udp_total_packets, packet_num)

                self.udp_socket.sendto(header + data, (self.server_host, self.udp_port))

                with self.udp_lock:
                    self.udp_bytes_sent += len(header) + len(data)
                    self.udp_packets_sent += 1

                packet_num += 1

                if self.stats_callback:
                    elapsed = time.time() - self.udp_start_time
                    speed_mbps = (self.udp_bytes_sent * 8 / 1000000) / max(0.001, elapsed)
                    self.stats_callback({
                        "protocol": "udp",
                        "bytes_sent": self.udp_bytes_sent,
                        "elapsed_time": elapsed,
                        "speed_mbps": speed_mbps,
                        "packets_sent": self.udp_packets_sent,
                        "total_packets": self.udp_total_packets,
                        "percent_complete": (packet_num / self.udp_total_packets) * 100
                    })

                time.sleep(0.001)

            self.udp_socket.close()

            if self.udp_log_callback:
                elapsed = time.time() - self.udp_start_time
                speed_mbps = (self.udp_bytes_sent * 8 / 1000000) / max(0.001, elapsed)
                self.udp_log_callback(f"UDP test completed. Sent: {self.udp_bytes_sent:,} bytes, "
                                      f"Packets: {self.udp_packets_sent:,}, "
                                      f"Speed: {speed_mbps:.2f} Mb/s")

            self.udp_running = False

        except Exception as e:
            if self.udp_log_callback:
                self.udp_log_callback(f"Error UDP testing: {e}")
            self.udp_running = False


class ClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Client")
        self.root.geometry("800x600")
        self.client = ProtocolTestClient()
        self.client.tcp_log_callback = self.log_tcp
        self.client.udp_log_callback = self.log_udp
        self.client.stats_callback = self.update_stats
        self._create_ui()

    def _create_ui(self):
        settings_frame = ttk.LabelFrame(self.root, text="Client settings")
        settings_frame.pack(padx=10, pady=10, fill=tk.X)

        server_frame = ttk.Frame(settings_frame)
        server_frame.pack(padx=5, pady=5, fill=tk.X)

        ttk.Label(server_frame, text="IP server:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.server_ip_var = tk.StringVar(value="127.0.0.1")
        ttk.Entry(server_frame, textvariable=self.server_ip_var, width=15).grid(row=0, column=1, padx=5, pady=5,
                                                                                sticky=tk.W)
        ttk.Label(server_frame, text="TCP port:").grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)
        self.tcp_port_var = tk.IntVar(value=9000)
        ttk.Entry(server_frame, textvariable=self.tcp_port_var, width=6).grid(row=0, column=3, padx=5, pady=5,
                                                                              sticky=tk.W)

        ttk.Label(server_frame, text="UDP port:").grid(row=0, column=4, padx=5, pady=5, sticky=tk.W)
        self.udp_port_var = tk.IntVar(value=9001)
        ttk.Entry(server_frame, textvariable=self.udp_port_var, width=6).grid(row=0, column=5, padx=5, pady=5,
                                                                              sticky=tk.W)

        test_params_frame = ttk.Frame(settings_frame)
        test_params_frame.pack(padx=5, pady=5, fill=tk.X)

        tcp_params_frame = ttk.LabelFrame(test_params_frame, text="TCP parameters")
        tcp_params_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        ttk.Label(tcp_params_frame, text="Packet size (bytes):").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.tcp_packet_size_var = tk.IntVar(value=8192)
        ttk.Entry(tcp_params_frame, textvariable=self.tcp_packet_size_var, width=8).grid(row=0, column=1, padx=5,
                                                                                         pady=2, sticky=tk.W)

        ttk.Label(tcp_params_frame, text="Total size (MB):").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.tcp_total_size_var = tk.DoubleVar(value=10)
        ttk.Entry(tcp_params_frame, textvariable=self.tcp_total_size_var, width=8).grid(row=1, column=1, padx=5, pady=2,
                                                                                        sticky=tk.W)

        udp_params_frame = ttk.LabelFrame(test_params_frame, text="UDP parameters")
        udp_params_frame.pack(side=tk.RIGHT, padx=5, pady=5, fill=tk.X, expand=True)

        ttk.Label(udp_params_frame, text="Packet size (bytes):").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_packet_size_var = tk.IntVar(value=1024)
        ttk.Entry(udp_params_frame, textvariable=self.udp_packet_size_var, width=8).grid(row=0, column=1, padx=5,
                                                                                         pady=2, sticky=tk.W)

        ttk.Label(udp_params_frame, text="Number of packets:").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_total_packets_var = tk.IntVar(value=1000)
        ttk.Entry(udp_params_frame, textvariable=self.udp_total_packets_var, width=8).grid(row=1, column=1, padx=5,
                                                                                           pady=2, sticky=tk.W)

        buttons_frame = ttk.Frame(settings_frame)
        buttons_frame.pack(padx=10, pady=10, fill=tk.X)

        self.start_tcp_btn = ttk.Button(buttons_frame, text="Start TCP test", command=self.start_tcp)
        self.start_tcp_btn.pack(side=tk.LEFT, padx=5)

        self.stop_tcp_btn = ttk.Button(buttons_frame, text="Stop TCP", command=self.stop_tcp, state=tk.DISABLED)
        self.stop_tcp_btn.pack(side=tk.LEFT, padx=5)

        self.start_udp_btn = ttk.Button(buttons_frame, text="Start UDP test", command=self.start_udp)
        self.start_udp_btn.pack(side=tk.LEFT, padx=5)

        self.stop_udp_btn = ttk.Button(buttons_frame, text="Stop UDP", command=self.stop_udp, state=tk.DISABLED)
        self.stop_udp_btn.pack(side=tk.LEFT, padx=5)

        progress_frame = ttk.LabelFrame(self.root, text="Progress")
        progress_frame.pack(padx=10, pady=5, fill=tk.X)

        ttk.Label(progress_frame, text="TCP:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.tcp_progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.tcp_progress.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        self.tcp_progress_var = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.tcp_progress_var).grid(row=0, column=2, padx=5, pady=5, sticky=tk.W)

        ttk.Label(progress_frame, text="UDP:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.udp_progress = ttk.Progressbar(progress_frame, orient=tk.HORIZONTAL, length=300, mode='determinate')
        self.udp_progress.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        self.udp_progress_var = tk.StringVar(value="0%")
        ttk.Label(progress_frame, textvariable=self.udp_progress_var).grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)

        stats_frame = ttk.LabelFrame(self.root, text="Statistics")
        stats_frame.pack(padx=10, pady=5, fill=tk.X)

        tcp_stats_frame = ttk.LabelFrame(stats_frame, text="TCP")
        tcp_stats_frame.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.BOTH, expand=True)

        ttk.Label(tcp_stats_frame, text="Bytes sent:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
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

        ttk.Label(udp_stats_frame, text="Bytes sent:").grid(row=0, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_bytes_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_bytes_var).grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Time (s):").grid(row=1, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_time_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_time_var).grid(row=1, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Speed (Mb/s):").grid(row=2, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_speed_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_speed_var).grid(row=2, column=1, padx=5, pady=2, sticky=tk.W)

        ttk.Label(udp_stats_frame, text="Packets sent:").grid(row=3, column=0, padx=5, pady=2, sticky=tk.W)
        self.udp_packets_sent_var = tk.StringVar(value="0")
        ttk.Label(udp_stats_frame, textvariable=self.udp_packets_sent_var).grid(row=3, column=1, padx=5, pady=2,
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

    def validate_settings(self):
        try:
            socket.inet_aton(self.server_ip_var.get())

            tcp_port = self.tcp_port_var.get()
            udp_port = self.udp_port_var.get()

            if not (1 <= tcp_port <= 65535) or not (1 <= udp_port <= 65535):
                messagebox.showerror("Error", "Ports must be in range 1-65535")
                return False

            tcp_packet_size = self.tcp_packet_size_var.get()
            tcp_total_size = int(self.tcp_total_size_var.get() * 1024 * 1024)

            if tcp_packet_size <= 0 or tcp_total_size <= 0:
                messagebox.showerror("Error", "Packet size and total size must be greater than zero")
                return False

            udp_packet_size = self.udp_packet_size_var.get()
            udp_total_packets = self.udp_total_packets_var.get()

            if udp_packet_size <= 0 or udp_total_packets <= 0:
                messagebox.showerror("Error", "Packet size and number of packets must be greater than zero")
                return False

            if udp_packet_size > 65507:
                messagebox.showerror("Error", "UDP packet size must be lesser than 65508 bytes")
                return False

            return True

        except Exception as e:
            messagebox.showerror("Error", f"Wrong settings: {e}")
            return False

    def apply_settings(self):
        self.client.server_host = self.server_ip_var.get()
        self.client.tcp_port = self.tcp_port_var.get()
        self.client.udp_port = self.udp_port_var.get()

        self.client.tcp_packet_size = self.tcp_packet_size_var.get()
        self.client.tcp_total_size = int(self.tcp_total_size_var.get() * 1024 * 1024)

        self.client.udp_packet_size = self.udp_packet_size_var.get()
        self.client.udp_total_packets = self.udp_total_packets_var.get()

    def start_tcp(self):
        if not self.validate_settings():
            return

        self.apply_settings()

        if self.client.start_tcp_test():
            self.start_tcp_btn.config(state=tk.DISABLED)
            self.stop_tcp_btn.config(state=tk.NORMAL)
            self.status_var.set("Starting TCP test...")

            self.tcp_progress['value'] = 0
            self.tcp_progress_var.set("0%")

    def stop_tcp(self):
        self.client.stop_tcp_test()
        self.start_tcp_btn.config(state=tk.NORMAL)
        self.stop_tcp_btn.config(state=tk.DISABLED)
        self.status_var.set("TCP test was stopped")

    def start_udp(self):
        if not self.validate_settings():
            return

        self.apply_settings()

        if self.client.start_udp_test():
            self.start_udp_btn.config(state=tk.DISABLED)
            self.stop_udp_btn.config(state=tk.NORMAL)
            self.status_var.set("Starting UDP test...")

            self.udp_progress['value'] = 0
            self.udp_progress_var.set("0%")

    def stop_udp(self):
        self.client.stop_udp_test()
        self.start_udp_btn.config(state=tk.NORMAL)
        self.stop_udp_btn.config(state=tk.DISABLED)
        self.status_var.set("UDP test was stopped")

    def log_tcp(self, message):
        self._log(self.tcp_log, message)

    def log_udp(self, message):
        self._log(self.udp_log, message)

    def _log(self, log_widget, message):
        timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        log_widget.insert(tk.END, f"[{timestamp}] {message}\n")
        log_widget.see(tk.END)

    def update_stats(self, stats):
        if stats["protocol"] == "tcp":
            self.tcp_bytes_var.set(f"{stats['bytes_sent']:,}")
            self.tcp_time_var.set(f"{stats['elapsed_time']:.2f}")
            self.tcp_speed_var.set(f"{stats['speed_mbps']:.2f}")

            self.tcp_progress['value'] = stats["percent_complete"]
            self.tcp_progress_var.set(f"{stats['percent_complete']:.1f}%")

            if stats["percent_complete"] >= 100:
                self.start_tcp_btn.config(state=tk.NORMAL)
                self.stop_tcp_btn.config(state=tk.DISABLED)
                self.status_var.set("TCP test completed")

        elif stats["protocol"] == "udp":
            self.udp_bytes_var.set(f"{stats['bytes_sent']:,}")
            self.udp_time_var.set(f"{stats['elapsed_time']:.2f}")
            self.udp_speed_var.set(f"{stats['speed_mbps']:.2f}")
            self.udp_packets_sent_var.set(f"{stats['packets_sent']:,}")

            self.udp_progress['value'] = stats["percent_complete"]
            self.udp_progress_var.set(f"{stats['percent_complete']:.1f}%")

            if stats["percent_complete"] >= 100:
                self.start_udp_btn.config(state=tk.NORMAL)
                self.stop_udp_btn.config(state=tk.DISABLED)
                self.status_var.set("UDP test completed")

    def on_close(self):
        self.client.stop_all()
        self.root.destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Protocol Speed Test Client')
    parser.add_argument('--nogui', action='store_true', help='Run in console mode (no GUI)')
    parser.add_argument('--host', default='127.0.0.1', help='Server host')
    parser.add_argument('--tcp-port', type=int, default=9000, help='TCP port')
    parser.add_argument('--udp-port', type=int, default=9001, help='UDP port')
    parser.add_argument('--tcp', action='store_true', help='Run TCP test')
    parser.add_argument('--udp', action='store_true', help='Run UDP test')
    parser.add_argument('--tcp-size', type=float, default=10, help='TCP test size in MB')
    parser.add_argument('--udp-packets', type=int, default=1000, help='UDP test packets count')
    args = parser.parse_args()

    if args.nogui:
        client = ProtocolTestClient()
        client.server_host = args.host
        client.tcp_port = args.tcp_port
        client.udp_port = args.udp_port
        client.tcp_total_size = int(args.tcp_size * 1024 * 1024)
        client.udp_total_packets = args.udp_packets

        client.tcp_log_callback = lambda msg: print(f"[TCP] {msg}")
        client.udp_log_callback = lambda msg: print(f"[UDP] {msg}")

        try:
            if args.tcp:
                print(f"Starting TCP test ({args.tcp_size} MB) to {args.host}:{args.tcp_port}")
                client.start_tcp_test()

                while client.tcp_running:
                    time.sleep(0.1)

            if args.udp:
                print(f"Starting UDP test ({args.udp_packets} packets) to {args.host}:{args.udp_port}")
                client.start_udp_test()

                while client.udp_running:
                    time.sleep(0.1)

            if not args.tcp and not args.udp:
                print("No tests specified to run. Use --tcp and/or --udp")

        except KeyboardInterrupt:
            print("Interrupted by user...")
        finally:
            client.stop_all()
    else:
        root = tk.Tk()
        app = ClientGUI(root)
        root.mainloop()
