import socket
import struct
import time
import sys
import argparse
import select
import os
import random


def calculate_checksum(packet):
    if len(packet) % 2 != 0:
        packet += b'\0'

    s = 0
    for i in range(0, len(packet), 2):
        w = (packet[i] << 8) + packet[i + 1]
        s = s + w

    s = (s >> 16) + (s & 0xffff)
    s = s + (s >> 16)

    return ~s & 0xffff


def create_icmp_echo_packet(id_num=0, seq_num=0):
    type_code = 8
    checksum = 0
    header = struct.pack("!BBHHH", type_code, 0, checksum, id_num, seq_num)
    data = bytes(range(48))
    packet = header + data
    checksum = calculate_checksum(packet)
    header = struct.pack("!BBHHH", type_code, 0, checksum, id_num, seq_num)

    return header + data


def resolve_hostname(ip_address):
    try:
        hostname = socket.gethostbyaddr(ip_address)[0]
        return hostname
    except (socket.herror, socket.gaierror):
        return ip_address


def perform_traceroute(destination, max_hops=30, timeout=2, packets_per_hop=3, resolve_names=False):
    icmp_socket = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
    icmp_socket.settimeout(timeout)

    try:
        dest_ip = socket.gethostbyname(destination)
        print(f"Tracing route to {destination} [{dest_ip}] over a maximum of {max_hops} hops:")
        print()
    except socket.gaierror:
        print(f"Could not resolve hostname: {destination}")
        return

    pid = os.getpid() & 0xFFFF

    for ttl in range(1, max_hops + 1):
        print(f"{ttl}", end="\t")

        reached_destination = False
        responses = []

        for seq in range(packets_per_hop):
            seq_num = random.randint(0, 65535)
            icmp_packet = create_icmp_echo_packet(pid, seq_num)
            icmp_socket.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, ttl)
            send_time = time.time()

            try:
                icmp_socket.sendto(icmp_packet, (dest_ip, 0))
                ready = select.select([icmp_socket], [], [], timeout)

                if ready[0]:
                    recv_packet, addr = icmp_socket.recvfrom(1024)
                    recv_time = time.time()
                    icmp_type = recv_packet[20]
                    rtt = (recv_time - send_time) * 1000
                    responses.append((addr[0], rtt, icmp_type))

                    if icmp_type == 0:
                        reached_destination = True
                else:
                    responses.append(("*", 0, None))

            except socket.timeout:
                responses.append(("*", 0, None))

            except Exception as e:
                print(f"\nError: {e}")
                responses.append(("!", 0, None))

        ip_addresses = set()
        for i, (ip, rtt, icmp_type) in enumerate(responses):
            if ip != "*" and ip != "!":
                ip_addresses.add(ip)

                if resolve_names and ip != "*" and ip != "!":
                    hostname = resolve_hostname(ip)
                    if hostname != ip:
                        print(f"{ip} ({hostname})", end="")
                    else:
                        print(f"{ip}", end="")
                else:
                    print(f"{ip}", end="")

                print(f"\t{rtt:.2f} ms", end="")
            else:
                print(f"{ip}", end="\t")

            if i < len(responses) - 1:
                print("\t", end="")

        print()

        if reached_destination:
            print(f"\nTrace complete. Destination {destination} reached in {ttl} hops.")
            break

    icmp_socket.close()


def main():
    parser = argparse.ArgumentParser(description="ICMP Traceroute Tool")
    parser.add_argument("destination", help="Destination hostname or IP address")
    parser.add_argument("-m", "--max-hops", type=int, default=30, help="Maximum number of hops (default: 30)")
    parser.add_argument("-w", "--timeout", type=float, default=2, help="Timeout in seconds for each hop (default: 2)")
    parser.add_argument("-n", "--packets", type=int, default=3, help="Number of packets per hop (default: 3)")
    parser.add_argument("-r", "--resolve", action="store_true", help="Resolve IP addresses to hostnames")
    args = parser.parse_args()

    try:
        perform_traceroute(
            args.destination,
            max_hops=args.max_hops,
            timeout=args.timeout,
            packets_per_hop=args.packets,
            resolve_names=args.resolve
        )
    except KeyboardInterrupt:
        print("\nTraceroute stopped by user.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    main()
