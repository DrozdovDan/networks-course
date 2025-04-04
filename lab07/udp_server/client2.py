import socket
import time
import statistics


def run_ping_client():
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    client_socket.settimeout(1.0)
    server_address = ('localhost', 9999)
    sent_packets = 0
    received_packets = 0
    rtt_values = []

    print(f"PING {server_address[0]}:{server_address[1]}")

    for seq in range(1, 11):
        sent_packets += 1
        send_time = time.time()
        message = f"Ping {seq} {send_time}"

        try:
            client_socket.sendto(message.encode('utf-8'), server_address)
            data, server = client_socket.recvfrom(1024)
            recv_time = time.time()
            rtt = recv_time - send_time
            rtt_ms = rtt * 1000
            rtt_values.append(rtt_ms)
            received_packets += 1

            print(f"{len(data)} bytes from {server[0]}:{server[1]}: icmp_seq={seq} time={rtt_ms:.3f} ms")

        except socket.timeout:
            print(f"Request timeout for icmp_seq {seq}")

        time.sleep(0.5)

    client_socket.close()

    print("\n--- ping statistics ---")

    if sent_packets > 0:
        loss_rate = (sent_packets - received_packets) / sent_packets * 100
    else:
        loss_rate = 0

    print(f"{sent_packets} packets transmitted, {received_packets} received, {loss_rate:.1f}% packet loss")

    if rtt_values:
        min_rtt = min(rtt_values)
        max_rtt = max(rtt_values)
        avg_rtt = statistics.mean(rtt_values)
        mdev_rtt = statistics.stdev(rtt_values) if len(rtt_values) > 1 else 0

        print(f"rtt min/avg/max/mdev = {min_rtt:.3f}/{avg_rtt:.3f}/{max_rtt:.3f}/{mdev_rtt:.3f} ms")


if __name__ == "__main__":
    run_ping_client()