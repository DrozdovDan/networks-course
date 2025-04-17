import socket
import threading
import time
import sys
import json
import datetime
import tkinter as tk
from tkinter import ttk

PORT = 12345
BROADCAST_ADDR = '<broadcast>'
HEARTBEAT_INTERVAL = 5
TIMEOUT_FACTOR = 3


class AppCounterGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Analyser")
        self.root.geometry("400x500")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        self.setup_ui()

        self.host_ip, self.port = self._get_local_ip_port()
        self.running = True
        self.peers = {}
        self.lock = threading.Lock()

        self.send_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.send_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.send_socket.bind((self.host_ip, self.port))

        self.receive_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.receive_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.receive_socket.bind(('', PORT))

        self.start_network_threads()
        self.update_gui()

    def setup_ui(self):
        counter_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        counter_frame.pack(fill=tk.X, padx=20, pady=20)

        self.counter_label = tk.Label(counter_frame, text="Copies running: 1", font=("Arial", 18))
        self.counter_label.pack(pady=10, padx=10)

        wait_frame = tk.Frame(self.root)
        wait_frame.pack(fill=tk.X, padx=20, pady=10)

        wait_label = tk.Label(wait_frame, text="Timeout, ms", font=("Arial", 12))
        wait_label.pack(side=tk.LEFT, padx=10)

        self.wait_entry = tk.Entry(wait_frame, font=("Arial", 12), width=8, justify=tk.RIGHT)
        self.wait_entry.pack(side=tk.RIGHT, padx=10)
        self.wait_entry.insert(0, "2000")

        list_frame = tk.Frame(self.root, bd=1, relief=tk.SUNKEN)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

        self.ip_list = tk.Text(list_frame, font=("Courier New", 11), bg="#f0ffff")
        self.ip_list.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)

        close_button = tk.Button(self.root, text="Close", font=("Arial", 12), command=self.on_closing)
        close_button.pack(fill=tk.X, padx=20, pady=20)

    def _get_local_ip_port(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 1))
            ip, port = s.getsockname()
        except Exception:
            ip = '127.0.0.1'
            port = 12345
        finally:
            s.close()
        return ip, port

    def start_network_threads(self):
        receiver_thread = threading.Thread(target=self._receive_messages)
        receiver_thread.daemon = True
        receiver_thread.start()
        checker_thread = threading.Thread(target=self._check_peers)
        checker_thread.daemon = True
        checker_thread.start()
        heartbeat_thread = threading.Thread(target=self._send_heartbeat)
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        self._send_message('startup')

    def update_gui(self):
        if not self.running:
            return

        with self.lock:
            count = len(self.peers)
            self.counter_label.config(text=f"Copies running: {count}")
            self.ip_list.delete(1.0, tk.END)

            for (ip, port) in sorted(self.peers.keys()):
                self.ip_list.insert(tk.END, f"{ip}:{port}\n")

        self.root.after(500, self.update_gui)

    def _send_message(self, msg_type):
        message = {
            'type': msg_type,
            'source_ip': self.host_ip,
            'source_port': self.port,
            'timestamp': time.time()
        }
        try:
            data = json.dumps(message).encode('utf-8')
            self.send_socket.sendto(data, (BROADCAST_ADDR, PORT))
        except Exception as e:
            print(f"Error while sending message: {e}")

    def _send_direct_message(self, msg_type, target_ip):
        message = {
            'type': msg_type,
            'source_ip': self.host_ip,
            'source_port': self.port,
            'timestamp': time.time()
        }
        try:
            data = json.dumps(message).encode('utf-8')
            self.send_socket.sendto(data, (target_ip, PORT))
        except Exception as e:
            print(f"Error while sending message: {e}")

    def _receive_messages(self):
        self.receive_socket.settimeout(0.5)

        while self.running:
            try:
                data, addr = self.receive_socket.recvfrom(1024)
                message = json.loads(data.decode('utf-8'))
                source_ip = message['source_ip']
                source_port = message['source_port']
                msg_type = message['type']

                peer_key = (source_ip, source_port)

                print(f'{source_ip}: {msg_type}')

                if msg_type == 'startup':
                    self._send_direct_message('active', source_ip)

                    with self.lock:
                        self.peers[peer_key] = time.time()

                elif msg_type == 'active' or msg_type == 'heartbeat':
                    with self.lock:
                        self.peers[peer_key] = time.time()

                elif msg_type == 'shutdown':
                    with self.lock:
                        if peer_key in self.peers:
                            del self.peers[peer_key]

            except socket.timeout:

                continue
            except Exception as e:
                if self.running:
                    print(f"Error while receiving message: {e}")

    def _send_heartbeat(self):
        while self.running:
            self._send_message('heartbeat')
            time.sleep(HEARTBEAT_INTERVAL)

    def _check_peers(self):
        while self.running:
            current_time = time.time()
            timeout_threshold = current_time - (HEARTBEAT_INTERVAL * TIMEOUT_FACTOR)

            with self.lock:
                peers_copy = self.peers.copy()

                for peer, last_seen in peers_copy.items():
                    if last_seen < timeout_threshold:
                        del self.peers[peer]

            time.sleep(HEARTBEAT_INTERVAL)

    def on_closing(self):
        self.running = False
        self._send_message('shutdown')
        time.sleep(0.5)

        try:
            self.send_socket.close()
            self.receive_socket.close()
        except:
            pass

        self.root.destroy()
        sys.exit(0)


if __name__ == "__main__":
    root = tk.Tk()
    app = AppCounterGUI(root)
    root.mainloop()