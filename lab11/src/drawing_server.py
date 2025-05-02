import socket
import threading
import tkinter as tk
from tkinter import messagebox


class DrawingServer:
    def __init__(self, host='0.0.0.0', port=5555):
        self.host = host
        self.port = port
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.clients = []
        self.is_running = False

        self.root = tk.Tk()
        self.root.title("Distance drawing server")
        self.root.geometry("600x500")

        self.info_frame = tk.Frame(self.root)
        self.info_frame.pack(pady=10)

        tk.Label(self.info_frame, text=f"Server is running on {host}:{port}").pack()

        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.canvas = tk.Canvas(self.canvas_frame, bg="white", bd=2, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.clear_button = tk.Button(self.root, text="Clear canvas", command=self.clear_canvas)
        self.clear_button.pack(pady=10)

        self.start_server()

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def start_server(self):
        try:
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.is_running = True
            accept_thread = threading.Thread(target=self.accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            print(f"Server is running on {self.host}:{self.port}")

        except Exception as e:
            messagebox.showerror("Error", f"Cannot start server: {e}")
            self.root.destroy()

    def accept_connections(self):
        while self.is_running:
            try:
                client_socket, client_address = self.server_socket.accept()
                self.clients.append(client_socket)
                client_thread = threading.Thread(target=self.handle_client, args=(client_socket,))
                client_thread.daemon = True
                client_thread.start()

                print(f"Connection from {client_address}")
            except:
                if self.is_running:
                    continue
                else:
                    break

    def handle_client(self, client_socket):
        last_x, last_y = None, None

        while self.is_running:
            try:
                data = client_socket.recv(1024).decode()
                if not data:
                    break

                if data == "CLEAR":
                    self.root.after(0, self.clear_canvas)
                    self.broadcast("CLEAR", exclude=client_socket)
                elif data.startswith("MOVE:"):
                    parts = data.split(":", 1)[1].split(",")
                    x, y = int(parts[0]), int(parts[1])
                    drawing = parts[2] == "True"

                    if drawing and last_x is not None and last_y is not None:
                        self.root.after(0, lambda: self.draw_line(last_x, last_y, x, y))

                    last_x, last_y = x, y
                    self.broadcast(data, exclude=client_socket)
                elif data == "PEN_UP":
                    last_x, last_y = None, None
                    self.broadcast(data, exclude=client_socket)
            except:
                break

        if client_socket in self.clients:
            self.clients.remove(client_socket)
            client_socket.close()

    def broadcast(self, message, exclude=None):
        for client in self.clients:
            if client != exclude:
                try:
                    client.send(message.encode())
                except:
                    if client in self.clients:
                        self.clients.remove(client)

    def draw_line(self, x1, y1, x2, y2):
        self.canvas.create_line(x1, y1, x2, y2, width=2, fill="black", smooth=True)

    def clear_canvas(self):
        self.canvas.delete("all")
        for client in self.clients:
            try:
                client.send("CLEAR".encode())
            except:
                if client in self.clients:
                    self.clients.remove(client)

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you actually want to quit?"):
            self.is_running = False
            for client in self.clients:
                try:
                    client.close()
                except:
                    pass

            try:
                self.server_socket.close()
            except:
                pass

            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    server = DrawingServer()
    server.run()
