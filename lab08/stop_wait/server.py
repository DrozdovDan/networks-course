import socket
import random
import struct
import os
import time
import argparse
from typing import Tuple, Optional, List

HEADER_SIZE = 8
PACKET_TYPES = {"DATA": 0, "ACK": 1}


def create_packet(seq_num: int, packet_type: int, is_last: bool, data: bytes) -> bytes:
    header = struct.pack('!BBHI', seq_num, packet_type, 1 if is_last else 0, len(data))
    return header + data


def parse_packet(packet: bytes) -> Tuple[int, int, bool, int, bytes]:
    header = packet[:HEADER_SIZE]
    seq_num, packet_type, is_last, data_size = struct.unpack('!BBHI', header)
    data = packet[HEADER_SIZE:HEADER_SIZE + data_size]
    return seq_num, packet_type, bool(is_last), data_size, data


def should_drop_packet(drop_rate: float) -> bool:
    return random.random() < drop_rate


def run_server(host: str, port: int, output_dir: str, drop_rate: float):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind((host, port))

    print(f"Server is running on {host}:{port}")
    print(f"Probability of package loss: {drop_rate * 100}%")
    print(f"Files will be saved to: {output_dir}")

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    try:
        while True:
            print("\nAwaiting new connection...")
            # Ждем первого пакета для получения имени файла
            while True:
                try:
                    packet, client_address = server_socket.recvfrom(65536)
                    seq_num, packet_type, _, _, filename_data = parse_packet(packet)
                    if packet_type == PACKET_TYPES["DATA"]:
                        filename = filename_data.decode('utf-8')
                        print(f"Received request for package receiving '{filename}' from {client_address}")
                        break
                except Exception as e:
                    print(f"Error while receiving filename: {e}")
                    continue

            if not should_drop_packet(drop_rate):
                ack = create_packet(seq_num, PACKET_TYPES["ACK"], False, b'')
                server_socket.sendto(ack, client_address)
                print(f"Sent ACK for filename (seq={seq_num})")
            else:
                print(f"ACK for filename was lost (seq={seq_num})")

            expected_seq = 1 - seq_num
            output_path = os.path.join(output_dir, filename)
            received_chunks = []
            last_received = False

            print(f"Starting file receiving '{filename}'")

            while not last_received:
                try:
                    packet, client_address = server_socket.recvfrom(65536)
                    seq_num, packet_type, is_last, data_size, data = parse_packet(packet)

                    if packet_type != PACKET_TYPES["DATA"]:
                        continue

                    print(f"Received package: seq={seq_num}, last={is_last}, size={data_size}")

                    if seq_num == expected_seq:
                        received_chunks.append(data)
                        expected_seq = 1 - expected_seq

                        if is_last:
                            last_received = True
                            print(f"Received last package of file '{filename}'")

                    if not should_drop_packet(drop_rate):
                        ack = create_packet(seq_num, PACKET_TYPES["ACK"], False, b'')
                        server_socket.sendto(ack, client_address)
                        print(f"Sent ACK (seq={seq_num})")
                    else:
                        print(f"ACK was lost (seq={seq_num})")

                except Exception as e:
                    print(f"Error while receiving package: {e}")

            try:
                with open(output_path, 'wb') as f:
                    for chunk in received_chunks:
                        f.write(chunk)
                file_size = os.path.getsize(output_path)
                print(f"File '{filename}' was saved successfully ({file_size} byte)")
            except Exception as e:
                print(f"Error while saving file: {e}")

    except KeyboardInterrupt:
        print("\nServer shutting down...")
    finally:
        server_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stop-and-Wait Protocol Server")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--output", default="server_files", help="Output directory")
    parser.add_argument("--drop-rate", type=float, default=0.3, help="Packet drop rate (0.0-1.0)")

    args = parser.parse_args()
    run_server(args.host, args.port, args.output, args.drop_rate)