import socket
import argparse
import time
import datetime


def start_broadcast_client(port, bind_ip='0.0.0.0'):
    """
    Запускает UDP клиент, который принимает широковещательные сообщения
    с текущим временем от сервера.

    Args:
        port (int): Порт для приема широковещательных сообщений
        bind_ip (str): IP-адрес для привязки (0.0.0.0 принимает со всех интерфейсов)
    """
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    client_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    client_socket.bind((bind_ip, port))

    print(f"[+] UDP клиент запущен. Ожидание сообщений на {bind_ip}:{port}")
    print("[*] Для остановки клиента нажмите Ctrl+C")

    try:
        message_count = 0
        while True:
            data, addr = client_socket.recvfrom(1024)

            local_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            message = data.decode('utf-8')

            message_count += 1
            print(f"[+] Сообщение #{message_count} от {addr[0]}:{addr[1]}")
            print(f"[+] Время сервера: {message}")
            print(f"[+] Локальное время: {local_time}")
            print("-" * 50)

    except KeyboardInterrupt:
        print("\n[!] Клиент остановлен пользователем")
    except Exception as e:
        print(f"[!] Ошибка: {e}")
    finally:
        client_socket.close()
        print("[+] Клиент завершил работу")


def main():
    parser = argparse.ArgumentParser(description='UDP клиент для приема широковещательных сообщений')
    parser.add_argument('--port', '-p', type=int, default=12345,
                        help='Порт для приема широковещательных сообщений (по умолчанию: 12345)')
    parser.add_argument('--bind', '-b', default='0.0.0.0',
                        help='IP-адрес для привязки (по умолчанию: 0.0.0.0)')

    args = parser.parse_args()

    start_broadcast_client(args.port, args.bind)


if __name__ == "__main__":
    main()