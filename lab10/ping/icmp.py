import socket
import struct
import time
import select
import sys
import argparse
from statistics import mean, stdev
import os


class ICMPPing:
    def __init__(self, dest_host, count=4, timeout=1, packet_size=56):
        self.dest_host = dest_host
        self.count = count
        self.timeout = timeout
        self.packet_size = packet_size
        self.rtts = []
        self.sent_packets = 0
        self.received_packets = 0
        self.seq_number = 0

        self.ICMP_ECHO_REQUEST = 8

        try:
            self.dest_addr = socket.gethostbyname(self.dest_host)
        except socket.gaierror:
            print(f"Ping: Unknown host: {self.dest_host}")
            sys.exit(1)

        print(f"PING {self.dest_host} ({self.dest_addr}): {self.packet_size} data bytes")

    def checksum(self, data):
        if len(data) % 2:
            data += b'\x00'

        sum = 0
        for i in range(0, len(data), 2):
            sum += (data[i] << 8) + data[i + 1]

        sum = (sum >> 16) + (sum & 0xFFFF)
        sum += (sum >> 16)

        return ~sum & 0xFFFF

    def create_packet(self):
        icmp_type = self.ICMP_ECHO_REQUEST
        icmp_code = 0
        icmp_checksum = 0
        icmp_id = os.getpid() & 0xFFFF
        icmp_seq = self.seq_number

        header = struct.pack("!BBHHH", icmp_type, icmp_code, icmp_checksum, icmp_id, icmp_seq)
        time_bytes = struct.pack("!d", time.time())
        padding = bytes((self.packet_size - 8) * 'Q', 'ascii')
        data = time_bytes + padding
        checksum = self.checksum(header + data)
        header = struct.pack("!BBHHH", icmp_type, icmp_code, checksum, icmp_id, icmp_seq)

        return header + data

    def receive_ping(self, sock, timeout):
        time_left = timeout

        while True:
            started_select = time.time()
            ready = select.select([sock], [], [], time_left)
            select_time = time.time() - started_select

            if not ready[0]:
                return None, 0, None, None

            received_time = time.time()
            recv_packet, addr = sock.recvfrom(1024)

            ip_header = recv_packet[:20]
            icmp_header = recv_packet[20:28]

            icmp_type, icmp_code, _, _, icmp_seq = struct.unpack("!BBHHH", icmp_header)

            if icmp_type == 0 and icmp_seq == self.seq_number:
                icmp_data = recv_packet[28:36]
                sent_time = struct.unpack("!d", icmp_data)[0]
                rtt = (received_time - sent_time) * 1000
                ip_ttl = struct.unpack("!B", ip_header[8:9])[0]

                return received_time, rtt, addr, ip_ttl
            elif icmp_type != 0:
                return received_time, 0, addr, None, (icmp_type, icmp_code)

            time_left -= select_time
            if time_left <= 0:
                return None, 0, None, None

    def ping_once(self):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket.IPPROTO_ICMP)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        except socket.error as e:
            raise

        packet = self.create_packet()

        sock.sendto(packet, (self.dest_addr, 0))
        self.sent_packets += 1

        result = self.receive_ping(sock, self.timeout)
        sock.close()

        if result[0] is None:
            print(f"Request timeout for icmp_seq {self.seq_number}")
            return None

        else:
            received_time, rtt, addr, ip_ttl = result
            self.received_packets += 1
            self.rtts.append(rtt)

            print(f"{self.packet_size} bytes from {addr[0]}: icmp_seq={self.seq_number} ttl={ip_ttl} time={rtt:.3f} ms")

            if len(self.rtts) > 0:
                print(f"min/avg/max = {min(self.rtts):.3f}/{mean(self.rtts):.3f}/{max(self.rtts):.3f} ms")

            return rtt

    def ping(self):
        try:
            for i in range(self.count):
                self.seq_number = i
                self.ping_once()

                if i < self.count - 1:
                    time.sleep(1)

            loss_percent = 100 - (self.received_packets / self.sent_packets * 100) if self.sent_packets > 0 else 100

            print(f"\n--- {self.dest_host} ping statistics ---")
            print(f"{self.sent_packets} packets transmitted, {self.received_packets} received, {loss_percent:.1f}% packet loss")

            if self.rtts:
                print(f"round-trip min/avg/max/stddev = {min(self.rtts):.3f}/{mean(self.rtts):.3f}/{max(self.rtts):.3f}/{(stdev(self.rtts) if len(self.rtts) > 1 else 0):.3f} ms")

        except KeyboardInterrupt:
            loss_percent = 100 - (self.received_packets / self.sent_packets * 100) if self.sent_packets > 0 else 100

            print(f"\n--- {self.dest_host} ping statistics ---")
            print(f"{self.sent_packets} packets transmitted, {self.received_packets} received, {loss_percent:.1f}% packet loss")

            if self.rtts:
                print(f"round-trip min/avg/max/stddev = {min(self.rtts):.3f}/{mean(self.rtts):.3f}/{max(self.rtts):.3f}/{(stdev(self.rtts) if len(self.rtts) > 1 else 0):.3f} ms")


def main():
    parser = argparse.ArgumentParser(description='Python ICMP Ping Tool')
    parser.add_argument('host', help='Target host to ping')
    parser.add_argument('-c', '--count', type=int, default=4, help='Number of packets to send (default: 4)')
    parser.add_argument('-t', '--timeout', type=float, default=1, help='Timeout in seconds (default: 1)')
    parser.add_argument('-s', '--size', type=int, default=56, help='Size of data packet (default: 56)')

    args = parser.parse_args()

    pinger = ICMPPing(args.host, args.count, args.timeout, args.size)
    pinger.ping()


if __name__ == "__main__":
    main()