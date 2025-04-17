import socket
import argparse
import sys
import concurrent.futures
from tqdm.auto import tqdm


def check_port(ip, port, timeout=0.5):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        sock.close()

        if result != 0:
            return port

        return None

    except socket.error:
        return None


def scan_ports(ip, start_port, end_port, max_workers=100):
    free_ports = []
    ports_to_scan = range(start_port, end_port + 1)
    print(f"Scanning ports from {start_port} to {end_port} on IP: {ip}")

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(check_port, ip, port) for port in ports_to_scan]

        for future in tqdm(concurrent.futures.as_completed(futures), total=len(futures), desc="Scanning"):
            result = future.result()
            if result is not None:
                free_ports.append(result)

    return sorted(free_ports)


def validate_ip(ip):
    try:
        socket.inet_aton(ip)
        return True

    except socket.error:
        return False


def validate_port_range(start_port, end_port):
    if not (0 <= start_port <= 65535) or not (0 <= end_port <= 65535):
        return False

    if start_port > end_port:
        return False

    return True


def main():
    parser = argparse.ArgumentParser(description='Scanner of free ports')
    parser.add_argument('ip', help='IP-address for scanning')
    parser.add_argument('start_port', type=int, help='Start port')
    parser.add_argument('end_port', type=int, help='End port')

    if len(sys.argv) == 1:
        ip = input("Enter IP-address: ")
        while not validate_ip(ip):
            print("Invalid IP-address. Please, enter again.")
            ip = input("Enter IP-address: ")

        start_port = int(input("Enter start port: "))
        end_port = int(input("Enter end port: "))

        while not validate_port_range(start_port, end_port):
            print("Invalid range of ports. Ports must be between 0 and 65535, and start port must be lesser or equal of end port.")
            start_port = int(input("Enter start port: "))
            end_port = int(input("Enter end port: "))
    else:
        args = parser.parse_args()
        ip = args.ip
        start_port = args.start_port
        end_port = args.end_port

        if not validate_ip(ip):
            print(f"Error: Invalid IP-address '{ip}'")
            sys.exit(1)

        if not validate_port_range(start_port, end_port):
            print("Error: Invalid range of ports. Ports must be between 0 and 65535, and start port must be lesser or equal of end port.")
            sys.exit(1)

    free_ports = scan_ports(ip, start_port, end_port)

    if free_ports:
        print(f"\nFound {len(free_ports)} free ports:")

        i = 0
        while i < len(free_ports):
            start = free_ports[i]
            end = start

            while i + 1 < len(free_ports) and free_ports[i + 1] == end + 1:
                end = free_ports[i + 1]
                i += 1

            if start == end:
                print(f"  {start}")
            else:
                print(f"  {start}-{end}")

            i += 1
    else:
        print("\nFree ports not found.")


if __name__ == "__main__":
    main()