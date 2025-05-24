import socket
import subprocess
import threading
import time
import tkinter as tk
from tkinter import ttk
import ipaddress
import platform
import re


class NetworkScanner:
    def __init__(self):
        self.computers = []
        self.current_pc = None
        self.network_range = None
        self.total_ips = 0
        self.scanned_ips = 0

    def get_current_pc_info(self):
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)

            if local_ip.startswith('127.'):
                s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                s.close()

            mac_address = self.get_mac_address(local_ip)
            self.current_pc = {
                'ip': local_ip,
                'mac': mac_address,
                'hostname': hostname
            }
            return self.current_pc
        except:
            return None

    def get_mac_address(self, ip):
        try:
            if platform.system().lower() == 'windows':
                result = subprocess.run(['arp', '-a', ip], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if ip in line:
                            match = re.search(r'([a-fA-F0-9]{2}[:-]){5}[a-fA-F0-9]{2}', line)
                            if match:
                                return match.group()
            else:
                result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    lines = result.stdout.strip().split('\n')
                    for line in lines:
                        if ip in line:
                            parts = line.split()
                            if len(parts) >= 3:
                                return parts[2]
        except:
            pass
        return '-'

    def get_hostname(self, ip):
        try:
            hostname = socket.gethostbyaddr(ip)[0]
            return hostname
        except:
            return '-'

    def ping_host(self, ip):
        try:
            if platform.system().lower() == 'windows':
                result = subprocess.run(['ping', '-n', '1', '-w', '1000', ip],
                                        capture_output=True, timeout=3)
            else:
                result = subprocess.run(['ping', '-c', '1', '-W', '1', ip],
                                        capture_output=True, timeout=3)
            return result.returncode == 0
        except:
            return False

    def scan_ip(self, ip, callback=None):
        ip_str = str(ip)
        if self.ping_host(ip_str):
            mac_address = self.get_mac_address(ip_str)
            hostname = self.get_hostname(ip_str)

            computer_info = {
                'ip': ip_str,
                'mac': mac_address,
                'hostname': hostname
            }

            if ip_str != self.current_pc['ip']:
                self.computers.append(computer_info)

        self.scanned_ips += 1
        if callback:
            callback()

    def scan_network(self, network_mask='255.255.255.0', callback=None):
        if not self.current_pc:
            self.get_current_pc_info()

        if not self.current_pc:
            return

        current_ip = ipaddress.IPv4Address(self.current_pc['ip'])

        if network_mask == '255.255.255.0':
            network = ipaddress.IPv4Network(f"{current_ip}/24", strict=False)
        else:
            network = ipaddress.IPv4Network(f"{current_ip}/{network_mask}", strict=False)

        self.network_range = network
        self.total_ips = len(list(network.hosts()))
        self.scanned_ips = 0
        self.computers = []

        threads = []
        for ip in network.hosts():
            if str(ip) != self.current_pc['ip']:
                thread = threading.Thread(target=self.scan_ip, args=(ip, callback))
                threads.append(thread)
                thread.start()

        for thread in threads:
            thread.join()

    def get_results(self):
        results = []
        if self.current_pc:
            results.append(self.current_pc)
        results.extend(sorted(self.computers, key=lambda x: ipaddress.IPv4Address(x['ip'])))
        return results


class NetworkScannerGUI:
    def __init__(self):
        self.scanner = NetworkScanner()
        self.root = tk.Tk()
        self.setup_gui()

    def setup_gui(self):
        self.root.title("Find all computers in network")
        self.root.geometry("800x500")
        self.root.resizable(True, True)

        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))

        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(2, weight=1)

        ttk.Label(main_frame, text="Network Mask:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.mask_var = tk.StringVar(value="255.255.255.0")
        mask_entry = ttk.Entry(main_frame, textvariable=self.mask_var, width=20)
        mask_entry.grid(row=0, column=1, sticky=tk.W, padx=(10, 0), pady=5)

        self.scan_button = ttk.Button(main_frame, text="Start Search", command=self.start_scan)
        self.scan_button.grid(row=0, column=2, padx=(10, 0), pady=5)

        self.progress = ttk.Progressbar(main_frame, mode='determinate')
        self.progress.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)

        columns = ('IP Address', 'MAC Address', 'Host name')
        self.tree = ttk.Treeview(main_frame, columns=columns, show='headings', height=15)

        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=200, anchor=tk.W)

        self.tree.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)

        scrollbar = ttk.Scrollbar(main_frame, orient=tk.VERTICAL, command=self.tree.yview)
        scrollbar.grid(row=2, column=3, sticky=(tk.N, tk.S), pady=5)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.status_label = ttk.Label(main_frame, text="Ready")
        self.status_label.grid(row=3, column=0, columnspan=3, sticky=tk.W, pady=5)

    def update_progress(self):
        if self.scanner.total_ips > 0:
            progress_value = (self.scanner.scanned_ips / self.scanner.total_ips) * 100
            self.progress['value'] = progress_value
            self.status_label.config(text=f"Scanned {self.scanner.scanned_ips}/{self.scanner.total_ips} addresses")
        self.root.update_idletasks()

    def start_scan(self):
        self.scan_button.config(state='disabled')
        self.tree.delete(*self.tree.get_children())
        self.progress['value'] = 0
        self.status_label.config(text="Getting current PC info...")

        def scan_thread():
            self.scanner.get_current_pc_info()
            if self.scanner.current_pc:
                self.root.after(0, lambda: self.tree.insert('', 'end', values=(
                    self.scanner.current_pc['ip'],
                    self.scanner.current_pc['mac'],
                    self.scanner.current_pc['hostname']
                ), tags=('current',)))

                self.tree.tag_configure('current', background='lightblue')

            self.scanner.scan_network(self.mask_var.get(), self.update_progress)

            results = self.scanner.get_results()[1:]
            for computer in results:
                self.root.after(0, lambda c=computer: self.tree.insert('', 'end', values=(
                    c['ip'], c['mac'], c['hostname']
                )))

            self.root.after(0, lambda: self.scan_button.config(state='normal'))
            self.root.after(0,
                            lambda: self.status_label.config(text=f"Found {len(self.scanner.get_results())} computers"))

        threading.Thread(target=scan_thread, daemon=True).start()

    def run(self):
        self.root.mainloop()


def console_version():
    print("Network Computer Scanner - Console Version")
    print("=" * 50)

    scanner = NetworkScanner()
    print("Getting current PC info...")
    scanner.get_current_pc_info()

    if not scanner.current_pc:
        print("Could not get current PC information")
        return

    print(f"Scanning network...")
    scanner.scan_network()

    results = scanner.get_results()

    print(f"\nFound {len(results)} computers in network:")
    print("-" * 70)
    print(f"{'IP Address':<15} {'MAC Address':<18} {'Host Name'}")
    print("-" * 70)

    for i, computer in enumerate(results):
        prefix = "Current PC" if i == 0 else "Network  "
        print(f"{computer['ip']:<15} {computer['mac']:<18} {computer['hostname']}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--console":
        console_version()
    else:
        app = NetworkScannerGUI()
        app.run()
