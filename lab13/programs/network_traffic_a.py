import psutil
import time
import os


def format_bytes(bytes_value):
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_value < 1024.0:
            return f"{bytes_value:.2f} {unit}"
        bytes_value /= 1024.0
    return f"{bytes_value:.2f} PB"


def get_network_stats():
    stats = psutil.net_io_counters()
    return stats.bytes_sent, stats.bytes_recv


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def main():
    print("Network Traffic Monitor")
    print("Press Ctrl+C to exit")
    print("-" * 50)

    initial_sent, initial_recv = get_network_stats()
    start_time = time.time()

    try:
        while True:
            current_sent, current_recv = get_network_stats()
            current_time = time.time()

            total_sent = current_sent - initial_sent
            total_recv = current_recv - initial_recv
            elapsed_time = current_time - start_time

            sent_rate = total_sent / elapsed_time if elapsed_time > 0 else 0
            recv_rate = total_recv / elapsed_time if elapsed_time > 0 else 0

            clear_screen()
            print("Network Traffic Monitor")
            print("Press Ctrl+C to exit")
            print("-" * 50)
            print(f"Session Duration: {int(elapsed_time)} seconds")
            print("-" * 50)
            print("TOTAL TRAFFIC:")
            print(f"Outgoing: {format_bytes(total_sent)}")
            print(f"Incoming: {format_bytes(total_recv)}")
            print(f"Combined: {format_bytes(total_sent + total_recv)}")
            print("-" * 50)
            print("CURRENT RATES:")
            print(f"Upload Speed: {format_bytes(sent_rate)}/s")
            print(f"Download Speed: {format_bytes(recv_rate)}/s")
            print("-" * 50)
            print("SYSTEM TOTALS:")
            print(f"Total Sent: {format_bytes(current_sent)}")
            print(f"Total Received: {format_bytes(current_recv)}")

            time.sleep(1)

    except KeyboardInterrupt:
        print("\n\nTraffic monitoring stopped.")
        print("Final Statistics:")
        print(f"Session Duration: {int(elapsed_time)} seconds")
        print(f"Total Outgoing: {format_bytes(total_sent)}")
        print(f"Total Incoming: {format_bytes(total_recv)}")
        print(f"Total Combined: {format_bytes(total_sent + total_recv)}")


if __name__ == "__main__":
    main()
