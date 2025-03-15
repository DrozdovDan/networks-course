import socket
import threading
import logging
import re
import os
import hashlib
import json
from datetime import datetime
import time
import shutil

# Настройка логирования
if not os.path.exists('logs'):
    os.makedirs('logs')
logging.basicConfig(filename='logs/proxy.log', level=logging.INFO,
                    format='%(asctime)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

# Папка для хранения кэша
CACHE_DIR = 'cache'
if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

# Файл с метаданными кэша
CACHE_INDEX_FILE = os.path.join(CACHE_DIR, 'cache_index.json')


class ProxyServer:
    def __init__(self, host='localhost', port=8888):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.bind((self.host, self.port))
        self.server_socket.listen(5)
        self.cache_index = self.load_cache_index()
        self.cache_lock = threading.Lock()
        print(f"Прокси-сервер запущен на {self.host}:{self.port}")

    def load_cache_index(self):
        """Загрузка индекса кэша с диска"""
        if os.path.exists(CACHE_INDEX_FILE):
            try:
                with open(CACHE_INDEX_FILE, 'r') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                print("Ошибка чтения индекса кэша. Создаем новый.")
        return {}

    def save_cache_index(self):
        """Сохранение индекса кэша на диск"""
        with open(CACHE_INDEX_FILE, 'w') as f:
            json.dump(self.cache_index, f)

    def get_cache_filename(self, url):
        """Создание имени файла для кэша на основе URL"""
        return hashlib.md5(url.encode()).hexdigest()

    def is_cacheable(self, headers, status_code):
        """Проверка, можно ли кэшировать ответ"""
        # Проверяем код ответа
        if status_code != 200:
            return False

        # Проверяем заголовки Cache-Control
        cache_control = headers.get('Cache-Control', '').lower()
        if 'no-store' in cache_control or 'no-cache' in cache_control or 'private' in cache_control:
            return False

        # Проверяем наличие заголовков для валидации
        if 'Last-Modified' in headers or 'ETag' in headers:
            return True

        return False

    def store_in_cache(self, url, response_data):
        """Сохранение ответа в кэш"""
        try:
            # Парсим заголовки из ответа
            response_parts = response_data.split(b'\r\n\r\n', 1)
            if len(response_parts) != 2:
                return False

            headers_data = response_parts[0].decode('utf-8', errors='ignore')
            headers_lines = headers_data.split('\r\n')
            status_line = headers_lines[0]
            status_code = int(status_line.split(' ')[1])

            # Разбираем заголовки
            headers = {}
            for i in range(1, len(headers_lines)):
                line = headers_lines[i]
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key] = value

            # Проверяем, можно ли кэшировать ответ
            if not self.is_cacheable(headers, status_code):
                return False

            # Создаем кэш-файл и сохраняем ответ
            cache_filename = self.get_cache_filename(url)
            cache_path = os.path.join(CACHE_DIR, cache_filename)

            with open(cache_path, 'wb') as f:
                f.write(response_data)

            # Сохраняем информацию о кэше
            with self.cache_lock:
                self.cache_index[url] = {
                    'filename': cache_filename,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'etag': headers.get('ETag', None),
                    'last_modified': headers.get('Last-Modified', None)
                }
                self.save_cache_index()

            logging.info(f"Закэширован URL: {url}")
            return True

        except Exception as e:
            logging.error(f"Ошибка при сохранении в кэш для {url}: {e}")
            return False

    def get_from_cache(self, url):
        """Получение ответа из кэша"""
        with self.cache_lock:
            if url not in self.cache_index:
                return None, None

            cache_info = self.cache_index[url]
            cache_path = os.path.join(CACHE_DIR, cache_info['filename'])

            if not os.path.exists(cache_path):
                # Файл кэша не найден, удаляем запись из индекса
                del self.cache_index[url]
                self.save_cache_index()
                return None, None

            # Чтение данных из кэша
            try:
                with open(cache_path, 'rb') as f:
                    cached_data = f.read()

                return cached_data, cache_info
            except Exception as e:
                logging.error(f"Ошибка при чтении из кэша для {url}: {e}")
                return None, None

    def start(self):
        print(f"Ожидание подключений... Используйте http://{self.host}:{self.port}/example.com для доступа к сайтам")
        while True:
            try:
                client_socket, client_address = self.server_socket.accept()
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket, client_address))
                client_thread.daemon = True
                client_thread.start()
            except KeyboardInterrupt:
                print("Сервер остановлен.")
                break
            except Exception as e:
                print(f"Ошибка при принятии соединения: {e}")

    def handle_client(self, client_socket, client_address):
        try:
            # Получаем запрос от клиента
            request_data = b''
            while True:
                chunk = client_socket.recv(4096)
                request_data += chunk
                if len(chunk) < 4096 or not chunk:
                    break

            if not request_data:
                client_socket.close()
                return

            # Декодируем запрос с обработкой ошибок
            try:
                request = request_data.decode('utf-8', errors='ignore')
            except UnicodeDecodeError:
                print("Ошибка декодирования запроса")
                client_socket.close()
                return

            # Анализ запроса
            try:
                first_line = request.split('\r\n')[0]
                method = first_line.split(' ')[0]
                url = self.parse_url(request)

                if not url:
                    error_response = "HTTP/1.1 400 Bad Request\r\nContent-Type: text/html\r\n\r\n"
                    error_response += "<html><body><h1>400 Bad Request</h1><p>Неверный формат URL</p></body></html>"
                    client_socket.sendall(error_response.encode())
                    client_socket.close()
                    return

                host, port, path = self.extract_host_port_path(url)

                # Получаем заголовки и тело запроса
                headers, body = self.parse_headers_and_body(request)

                print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {method} {url}")

                # Обработка метода запроса
                if method == "GET":
                    self.handle_get_request(client_socket, host, port, path, headers, url)
                elif method == "POST":
                    self.handle_post_request(client_socket, host, port, path, headers, body, url)
                else:
                    error_response = "HTTP/1.1 501 Not Implemented\r\nContent-Type: text/html\r\n\r\n"
                    error_response += f"<html><body><h1>501 Not Implemented</h1><p>Метод {method} не поддерживается.</p></body></html>"
                    client_socket.sendall(error_response.encode())
            except Exception as e:
                print(f"Ошибка при обработке запроса: {e}")
                error_response = "HTTP/1.1 500 Internal Server Error\r\nContent-Type: text/html\r\n\r\n"
                error_response += f"<html><body><h1>500 Internal Server Error</h1><p>{str(e)}</p></body></html>"
                client_socket.sendall(error_response.encode())
        except Exception as e:
            print(f"Общая ошибка при обработке запроса: {e}")
        finally:
            client_socket.close()

    def handle_get_request(self, client_socket, host, port, path, headers, url):
        try:
            # Проверяем наличие объекта в кэше
            cached_response, cache_info = self.get_from_cache(url)

            if cached_response:
                # Если объект найден в кэше, отправляем условный GET запрос для проверки актуальности
                conditional_headers = {}
                if cache_info.get('etag'):
                    conditional_headers['If-None-Match'] = cache_info['etag']
                if cache_info.get('last_modified'):
                    conditional_headers['If-Modified-Since'] = cache_info['last_modified']

                # Если есть условные заголовки, проверяем актуальность
                if conditional_headers:
                    # Создаём условный HTTP запрос для сервера
                    server_request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
                    for header, value in conditional_headers.items():
                        server_request += f"{header}: {value}\r\n"
                    server_request += "\r\n"

                    # Отправляем условный запрос
                    try:
                        # Создаем сокет для подключения к целевому серверу
                        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        server_socket.settimeout(10)

                        # Подключаемся к серверу
                        server_socket.connect((host, port))
                        server_socket.sendall(server_request.encode())

                        # Получаем ответ от сервера
                        response = b''
                        while True:
                            try:
                                data = server_socket.recv(4096)
                                if not data:
                                    break
                                response += data
                            except socket.timeout:
                                break

                        # Проверяем статус код ответа
                        if response:
                            try:
                                status_line = response.split(b'\r\n')[0].decode('utf-8')
                                status_code = int(status_line.split(' ')[1])

                                if status_code == 304:  # Not Modified
                                    # Данные в кэше актуальны, отправляем клиенту из кэша
                                    logging.info(f"Отправка из кэша (304 Not Modified): {url}")
                                    print(f"Отправка из кэша (304 Not Modified): {url}")
                                    client_socket.sendall(cached_response)
                                    server_socket.close()
                                    return
                                else:
                                    # Данные изменились, обновляем кэш
                                    logging.info(f"Обновление кэша для: {url}")
                                    self.store_in_cache(url, response)
                                    client_socket.sendall(response)
                                    server_socket.close()
                                    return
                            except Exception as e:
                                logging.error(f"Ошибка при обработке ответа от сервера: {e}")

                        server_socket.close()
                    except Exception as e:
                        logging.error(f"Ошибка при выполнении условного запроса: {e}")

                # Если не удалось проверить актуальность или нет условных заголовков, отправляем из кэша
                logging.info(f"Отправка из кэша (без проверки актуальности): {url}")
                print(f"Отправка из кэша (без проверки актуальности): {url}")
                client_socket.sendall(cached_response)
                return

            # Если объекта нет в кэше, отправляем обычный запрос
            server_request = f"GET {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
            for header, value in headers.items():
                if header.lower() not in ['host', 'connection', 'proxy-connection']:
                    server_request += f"{header}: {value}\r\n"
            server_request += "\r\n"

            # Подключение к целевому серверу и отправка запроса
            self.forward_request_to_server(client_socket, host, port, server_request.encode(), url)
        except Exception as e:
            print(f"Ошибка при обработке GET запроса: {e}")
            self.send_error_response(client_socket, 500, f"Internal Server Error: {str(e)}")

    def handle_post_request(self, client_socket, host, port, path, headers, body, url):
        try:
            # POST запросы не кэшируем, просто перенаправляем
            server_request = f"POST {path} HTTP/1.1\r\nHost: {host}\r\nConnection: close\r\n"
            for header, value in headers.items():
                if header.lower() not in ['host', 'connection', 'proxy-connection']:
                    server_request += f"{header}: {value}\r\n"
            server_request += "\r\n"
            if body:
                server_request += body

            # Подключение к целевому серверу и отправка запроса
            self.forward_request_to_server(client_socket, host, port, server_request.encode(), url)
        except Exception as e:
            print(f"Ошибка при обработке POST запроса: {e}")
            self.send_error_response(client_socket, 500, f"Internal Server Error: {str(e)}")

    def forward_request_to_server(self, client_socket, host, port, request_data, url):
        server_socket = None
        try:
            # Создаем сокет для подключения к целевому серверу
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.settimeout(10)

            # Подключаемся к серверу
            server_socket.connect((host, port))
            server_socket.sendall(request_data)

            # Получаем ответ от сервера
            response = b''
            while True:
                try:
                    data = server_socket.recv(4096)
                    if not data:
                        break
                    response += data
                except socket.timeout:
                    break

            # Проверяем статус код ответа
            try:
                status_line = response.split(b'\r\n')[0].decode('utf-8')
                status_code = int(status_line.split(' ')[1])
                logging.info(f"URL: {url}, Код ответа: {status_code}")
                print(f"URL: {url}, Код ответа: {status_code}")

                # Если это GET запрос и ответ можно кэшировать, сохраняем в кэш
                if request_data.startswith(b'GET') and status_code == 200:
                    self.store_in_cache(url, response)
            except Exception as e:
                logging.warning(f"Не удалось определить код ответа для {url}: {e}")

            # Отправляем ответ клиенту
            if response:
                client_socket.sendall(response)
            else:
                self.send_error_response(client_socket, 502, "Bad Gateway: Нет ответа от сервера")

        except socket.gaierror as e:
            error_msg = f"DNS ошибка при подключении к {host}: {e}"
            print(error_msg)
            logging.error(error_msg)
            self.send_error_response(client_socket, 502, f"Bad Gateway: {error_msg}")

        except socket.timeout as e:
            error_msg = f"Timeout при подключении к {host}: {e}"
            print(error_msg)
            logging.error(error_msg)
            self.send_error_response(client_socket, 504, f"Gateway Timeout: {error_msg}")

        except Exception as e:
            error_msg = f"Ошибка при запросе {url}: {e}"
            print(error_msg)
            logging.error(error_msg)
            self.send_error_response(client_socket, 500, f"Internal Server Error: {error_msg}")

        finally:
            if server_socket:
                server_socket.close()

    def send_error_response(self, client_socket, code, message):
        status_messages = {
            400: "Bad Request",
            404: "Not Found",
            500: "Internal Server Error",
            502: "Bad Gateway",
            503: "Service Unavailable",
            504: "Gateway Timeout"
        }
        status_text = status_messages.get(code, "Unknown Error")

        response = f"HTTP/1.1 {code} {status_text}\r\n"
        response += "Content-Type: text/html\r\n\r\n"
        response += f"<html><body><h1>{code} {status_text}</h1><p>{message}</p></body></html>"

        try:
            client_socket.sendall(response.encode())
        except:
            pass

    def parse_url(self, request):
        try:
            first_line = request.split('\r\n')[0]
            url_part = first_line.split(' ')[1]

            # Если URL уже содержит полный адрес с протоколом
            if url_part.startswith('http'):
                return url_part

            # Если URL начинается с '/', значит это запрос к самому прокси-серверу
            # Формат: /hostname/path или /hostname:port/path
            if url_part.startswith('/'):
                # Удаляем начальный слеш
                url_part = url_part[1:]

                # Если нет второго слеша, то путь не указан
                if '/' not in url_part:
                    return f"http://{url_part}/"

                return f"http://{url_part}"

            return None
        except Exception as e:
            print(f"Ошибка при парсинге URL: {e}")
            return None

    def extract_host_port_path(self, url):
        try:
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
        except Exception as e:
            print(f"Ошибка при извлечении host, port, path: {e}")
            return "localhost", 80, "/"

    def parse_headers_and_body(self, request):
        try:
            # Проверяем наличие двойного перевода строки, разделяющего заголовки и тело
            if '\r\n\r\n' in request:
                headers_part, body = request.split('\r\n\r\n', 1)
            else:
                headers_part = request
                body = ''

            # Разделяем строки заголовков
            header_lines = headers_part.split('\r\n')

            # Пропускаем первую строку (с методом, URL и версией HTTP)
            headers = {}
            for i in range(1, len(header_lines)):
                line = header_lines[i]
                if ': ' in line:
                    key, value = line.split(': ', 1)
                    headers[key] = value

            return headers, body
        except Exception as e:
            print(f"Ошибка при парсинге заголовков и тела: {e}")
            return {}, ''

    def clear_cache(self):
        """Очистка кэша"""
        try:
            with self.cache_lock:
                self.cache_index = {}
                self.save_cache_index()

                # Удаляем все файлы в директории кэша
                for filename in os.listdir(CACHE_DIR):
                    file_path = os.path.join(CACHE_DIR, filename)
                    if os.path.isfile(file_path) and filename != 'cache_index.json':
                        os.unlink(file_path)

            logging.info("Кэш очищен")
            print("Кэш очищен")
            return True
        except Exception as e:
            logging.error(f"Ошибка при очистке кэша: {e}")
            print(f"Ошибка при очистке кэша: {e}")
            return False

if __name__ == "__main__":
    proxy = ProxyServer()
    proxy.start()
