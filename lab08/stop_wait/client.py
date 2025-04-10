import socket
import random
import struct
import os
import time
import argparse
from typing import List, Optional, Tuple

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


def send_file(client_socket: socket.socket, server_address: Tuple[str, int],
              filename: str, chunk_size: int, timeout: float, drop_rate: float) -> bool:
    if not os.path.exists(filename):
        print(f"Error: File '{filename}' doesn't exist.")
        return False

    file_size = os.path.getsize(filename)
    print(f"Sending file '{filename}' ({file_size} byte) with package size {chunk_size} byte")

    try:
        base_filename = os.path.basename(filename)
        filename_packet = create_packet(0, PACKET_TYPES["DATA"], False, base_filename.encode('utf-8'))

        ack_received = False
        retries = 0
        max_retries = 10

        while not ack_received and retries < max_retries:
            if not should_drop_packet(drop_rate):
                client_socket.sendto(filename_packet, server_address)
                print(f"Filename package was sent (seq=0)")
            else:
                print(f"Filename package was lost (seq=0)")

            client_socket.settimeout(timeout)
            try:
                response, _ = client_socket.recvfrom(65536)
                seq_num, packet_type, _, _, _ = parse_packet(response)

                if packet_type == PACKET_TYPES["ACK"] and seq_num == 0:
                    ack_received = True
                    print(f"Received ACK for filename (seq={seq_num})")
                else:
                    print(f"Received unexpected package: type={packet_type}, seq={seq_num}")
            except socket.timeout:
                print(f"Timeout while waiting ACK for filename. Sending again...")
                retries += 1

        if not ack_received:
            print(f"Limit of attempts to send filename exceeded")
            return False

        with open(filename, 'rb') as f:
            chunks = []
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                chunks.append(chunk)

        total_chunks = len(chunks)
        print(f"File was split into {total_chunks} chunks")

        seq_num = 1
        chunk_index = 0

        while chunk_index < total_chunks:
            chunk = chunks[chunk_index]
            is_last = chunk_index == total_chunks - 1

            data_packet = create_packet(seq_num, PACKET_TYPES["DATA"], is_last, chunk)

            ack_received = False
            retries = 0

            while not ack_received and retries < max_retries:
                if not should_drop_packet(drop_rate):
                    client_socket.sendto(data_packet, server_address)
                    print(
                        f"Data package was sent: seq={seq_num}, chunk={chunk_index + 1}/{total_chunks}, size={len(chunk)}, last={is_last}")
                else:
                    print(f"Data package was lost: seq={seq_num}, chunk={chunk_index + 1}/{total_chunks}")

                client_socket.settimeout(timeout)
                try:
                    response, _ = client_socket.recvfrom(65536)
                    resp_seq, packet_type, _, _, _ = parse_packet(response)

                    if packet_type == PACKET_TYPES["ACK"] and resp_seq == seq_num:
                        ack_received = True
                        print(f"Received ACK: seq={resp_seq}, chunk={chunk_index + 1}/{total_chunks}")
                    else:
                        print(f"Received unexpected package: type={packet_type}, seq={resp_seq}, expected ACK={seq_num}")
                except socket.timeout:
                    print(f"Timeout while waiting ACK. Sending again chunk {chunk_index + 1}/{total_chunks}...")
                    retries += 1

            if not ack_received:
                print(f"Limit of attempts to send chunk {chunk_index + 1} exceeded")
                return False

            chunk_index += 1
            seq_num = 1 - seq_num

        print(f"File '{filename}' was successfully sent")
        return True

    except Exception as e:
        print(f"Error while sending file: {e}")
        return False


def run_client(server_host: str, server_port: int, filename: str,
               chunk_size: int, timeout: float, drop_rate: float):
    server_address = (server_host, server_port)

    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    try:
        print(f"Connecting to server {server_host}:{server_port}")
        print(f"Probability of package loss: {drop_rate * 100}%")
        print(f"Timeout: {timeout} s")

        start_time = time.time()
        success = send_file(client_socket, server_address, filename, chunk_size, timeout, drop_rate)
        end_time = time.time()

        if success:
            elapsed_time = end_time - start_time
            file_size = os.path.getsize(filename)
            avg_speed = file_size / elapsed_time / 1024

            print(f"\nTransition statistic:")
            print(f"Transition time: {elapsed_time:.2f} s")
            print(f"File size: {file_size} byte")
            print(f"Average speed: {avg_speed:.2f} KB/s")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        client_socket.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stop-and-Wait Protocol Client")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=5000, help="Server port")
    parser.add_argument("--file", required=True, help="File to send")
    parser.add_argument("--chunk-size", type=int, default=1024, help="Chunk size in bytes")
    parser.add_argument("--timeout", type=float, default=1.0, help="Timeout in seconds")
    parser.add_argument("--drop-rate", type=float, default=0.3, help="Packet drop rate (0.0-1.0)")

    args = parser.parse_args()
    run_client(args.host, args.port, args.file, args.chunk_size, args.timeout, args.drop_rate)