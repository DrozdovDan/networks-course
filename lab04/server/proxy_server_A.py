import socket
import threading
import logging
import re
import os

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(filename='logs/proxy.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')


class ProxyServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        print(f"Прокси-сервер запущен на {self.host}:{self.port}")

    def start(self):
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                threading.Thread(target=self.handle_client, args=(client_socket, client_address)).start()
            except KeyboardInterrupt:
                print("Сервер остановлен.")
                break
            except Exception as e:
                print(f"Ошибка при принятии соединения: {e}")

    def handle_client(self, client_socket, client_address):
        try:
            request = client_socket.recv(4096).decode('utf-8', errors='ignore')

            if not request:
                client_socket.close()
                return

            # Анализ запроса
            request_method = request.split(' ')[0]
            url = self.parse_url(request)

            if not url:
                client_socket.close()
                return

            host, port, path = self.extract_host_port_path(url)

            # Получаем заголовки и тело запроса
            headers, body = self.parse_headers_and_body(request)

            # Создаём HTTP запрос для сервера
            if request_method == "GET":
                server_request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
                for header, value in headers.items():
                    if header.lower() not in ['host', 'connection']:
                        server_request += f"{header}: {value}\r\n"
                server_request += "\r\n"
            elif request_method == "POST":
                server_request = f"POST {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
                for header, value in headers.items():
                    if header.lower() not in ['host', 'connection']:
                        server_request += f"{header}: {value}\r\n"
                server_request += "\r\n"
                if body:
                    server_request += body
            else:
                # Отправляем сообщение об ошибке для неподдерживаемых методов
                error_response = "HTTP/1.1 501 Not Implemented\r\nContent-Type: text/html\r\n\r\n"
                error_response += f"<html><body><h1>501 Not Implemented</h1><p>Метод {request_method} не поддерживается.</p></body></html>"
                client_socket.sendall(error_response.encode())
                client_socket.close()
                return

            # Подключение к целевому серверу
            try:
                server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                server_socket.settimeout(10)
                server_socket.connect((host, port))
                server_socket.sendall(server_request.encode())

                # Получение ответа от сервера
                response = b''
                while True:
                    data = server_socket.recv(4096)
                    if not data:
                        break
                    response += data

                # Проверка на наличие статус-кода в ответе
                try:
                    status_line = response.split(b'\r\n')[0].decode('utf-8')
                    status_code = int(status_line.split(' ')[1])
                    logging.info(f"URL: {url}, Код ответа: {status_code}")
                except (IndexError, ValueError) as e:
                    logging.warning(f"Не удалось определить код ответа для {url}: {e}")

                # Отправка ответа клиенту
                client_socket.sendall(response)

            except socket.gaierror as e:
                error_msg = f"DNS ошибка при подключении к {host}: {e}"
                print(error_msg)
                logging.error(error_msg)
                error_response = "HTTP/1.1 502 Bad Gateway\r\nContent-Type: text/html\r\n\r\n"
                error_response += f"<html><body><h1>502 Bad Gateway</h1><p>{error_msg}</p></body></html>"
                client_socket.sendall(error_response.encode())

            except socket.timeout as e:
                error_msg = f"Timeout при подключении к {host}: {e}"
                print(error_msg)
                logging.error(error_msg)
                error_response = "HTTP/1.1 504 Gateway Timeout\r\nContent-Type: text/html\r\n\r\n"
                error_response += f"<html><body><h1>504 Gateway Timeout</h1><p>{error_msg}</p></body></html>"
                client_socket.sendall(error_response.encode())

            except Exception as e:
                error_msg = f"Ошибка при запросе {url}: {e}"
                print(error_msg)
                logging.error(error_msg)
                error_response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/html\r\n\r\n"
                error_response += f"<html><body><h1>500 Internal Server Error</h1><p>{error_msg}</p></body></html>"
                client_socket.sendall(error_response.encode())

            finally:
                if 'server_socket' in locals():
                    server_socket.close()

        except Exception as e:
            print(f"Ошибка при обработке запроса от {client_address}: {e}")

        finally:
            client_socket.close()

    def parse_url(self, request):
        try:
            first_line = request.split('\r\n')[0]
            url = first_line.split(' ')[1]

            # Проверка, содержит ли URL полный адрес или только путь
            if url.startswith('http'):
                return url

            # Если URL начинается с '/', значит это запрос к самому прокси-серверу
            # Ищем хост в формате /www.example.com или /www.example.com/path
            if url.startswith('/'):
                match = re.match(r'^/([^/]+)(.*)', url)
                if match:
                    host = match.group(1)
                    path = match.group(2) if match.group(2) else '/'
                    return f"http://{host}{path}"

            return None
        except Exception as e:
            print(f"Ошибка при парсинге URL: {e}")
            return None

    def extract_host_port_path(self, url):
        # Убираем схему (http:// или https://)
        if '://' in url:
            url = url.split('://', 1)[1]

        # Находим хост и путь
        if '/' in url:
            host_port, path = url.split('/', 1)
            path = '/' + path
        else:
            host_port = url
            path = '/'

        # Проверяем, указан ли порт
        if ':' in host_port:
            host, port_str = host_port.split(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = 80
        else:
            host = host_port
            port = 80

        return host, port, path

    def parse_headers_and_body(self, request):
        try:
            # Разделяем строки запроса
            lines = request.split('\r\n')

            # Пропускаем первую строку (с методом, URL и версией HTTP)
            headers_end = lines.index('')
            header_lines = lines[1:headers_end]

            # Парсим заголовки
            headers = {}
            for line in header_lines:
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key] = value

            # Получаем тело запроса, если оно есть
            body = '\r\n'.join(lines[headers_end + 1:]) if headers_end + 1 < len(lines) else ''

            return headers, body
        except Exception as e:
            print(f"Ошибка при парсинге заголовков и тела: {e}")
            return {}, ''


if __name__ == "__main__":
    proxy = ProxyServer()
    proxy.start()