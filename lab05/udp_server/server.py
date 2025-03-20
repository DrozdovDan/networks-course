import socket
import time
import datetime
import argparse


def start_broadcast_server(port, broadcast_ip='255.255.255.255', interval=1):
    """
    Запускает UDP сервер, который каждую секунду рассылает текущее время
    всем клиентам в сети через широковещательную рассылку.

    Args:
        port (int): Порт для широковещательной рассылки
        broadcast_ip (str): IP-адрес для широковещательной рассылки
        interval (float): Интервал между рассылками в секундах
    """
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    print(f"[+] UDP сервер запущен. Рассылка времени на {broadcast_ip}:{port}")
    print(f"[*] Интервал рассылки: {interval} секунд")
    print("[*] Для остановки сервера нажмите Ctrl+C")

    try:
        message_count = 0
        while True:
            current_time = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')[:-3]

            message = f"SERVER_TIME: {current_time}"

            server_socket.sendto(message.encode('utf-8'), (broadcast_ip, port))

            message_count += 1
            print(f"[+] Отправлено сообщение #{message_count}: {message}")

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[!] Сервер остановлен пользователем")
    except Exception as e:
        print(f"[!] Ошибка: {e}")
    finally:
        server_socket.close()
        print("[+] Сервер завершил работу")


def main():
    parser = argparse.ArgumentParser(description='UDP сервер для широковещательной рассылки времени')
    parser.add_argument('--port', '-p', type=int, default=12345,
                        help='Порт для широковещательной рассылки (по умолчанию: 12345)')
    parser.add_argument('--broadcast', '-b', default='127.0.0.1',
                        help='IP-адрес для широковещательной рассылки (по умолчанию: 127.0.0.1)')
    parser.add_argument('--interval', '-i', type=float, default=1.0,
                        help='Интервал между рассылками в секундах (по умолчанию: 1.0)')

    args = parser.parse_args()

    start_broadcast_server(args.port, args.broadcast, args.interval)


if __name__ == "__main__":
    main()