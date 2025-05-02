import socket
import threading
import tkinter as tk
from tkinter import messagebox, simpledialog


class DrawingClient:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Distance drawing client")
        self.root.geometry("600x500")
        self.client_socket = None
        self.is_connected = False

        self.control_frame = tk.Frame(self.root)
        self.control_frame.pack(fill=tk.X, pady=5, padx=5)

        self.connect_button = tk.Button(self.control_frame, text="Connect", command=self.connect_to_server)
        self.connect_button.pack(side=tk.LEFT, padx=5)

        self.clear_button = tk.Button(self.control_frame, text="Clear canvas", command=self.clear_canvas,
                                      state=tk.DISABLED)
        self.clear_button.pack(side=tk.LEFT, padx=5)

        self.status_var = tk.StringVar(value="Disconnected")
        self.status_label = tk.Label(self.control_frame, textvariable=self.status_var, fg="red")
        self.status_label.pack(side=tk.RIGHT, padx=10)

        self.canvas_frame = tk.Frame(self.root)
        self.canvas_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        self.canvas = tk.Canvas(self.canvas_frame, bg="white", bd=2, relief=tk.SUNKEN)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        self.drawing = False
        self.last_x = None
        self.last_y = None
        self.canvas.bind("<Button-1>", self.on_mouse_down)
        self.canvas.bind("<B1-Motion>", self.on_mouse_move)
        self.canvas.bind("<ButtonRelease-1>", self.on_mouse_up)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def connect_to_server(self):
        if self.is_connected:
            return

        server_ip = simpledialog.askstring("Connection", "Enter IP address:", initialvalue="127.0.0.1")
        if not server_ip:
            return

        try:
            port = 5555
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((server_ip, port))
            self.is_connected = True
            self.status_var.set(f"Connected to {server_ip}:{port}")
            self.status_label.config(fg="green")
            self.connect_button.config(text="Disconnect", command=self.disconnect_from_server)
            self.clear_button.config(state=tk.NORMAL)
            receive_thread = threading.Thread(target=self.receive_data)
            receive_thread.daemon = True
            receive_thread.start()

            print(f"Connected to server {server_ip}:{port}")
        except Exception as e:
            messagebox.showerror("Error", f"Cannot connect to server: {e}")

    def disconnect_from_server(self):
        if not self.is_connected:
            return

        try:
            self.is_connected = False
            if self.client_socket:
                self.client_socket.close()
                self.client_socket = None

            self.status_var.set("Disconnected")
            self.status_label.config(fg="red")
            self.connect_button.config(text="Connect", command=self.connect_to_server)
            self.clear_button.config(state=tk.DISABLED)

            print("Disconnected from server")
        except Exception as e:
            print(f"Error while disconnecting: {e}")

    def receive_data(self):
        while self.is_connected:
            try:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    break

                if data == "CLEAR":
                    self.root.after(0, self.clear_canvas_without_notify)
                elif data.startswith("MOVE:"):
                    parts = data.split(":", 1)[1].split(",")
                    x, y = int(parts[0]), int(parts[1])
                    drawing = parts[2] == "True"

                    if drawing and hasattr(self, 'remote_last_x') and hasattr(self, 'remote_last_y'):
                        if self.remote_last_x is not None and self.remote_last_y is not None:
                            self.root.after(0, lambda: self.draw_line(self.remote_last_x, self.remote_last_y, x, y))

                    self.remote_last_x, self.remote_last_y = x, y
                elif data == "PEN_UP":
                    self.remote_last_x, self.remote_last_y = None, None
            except:
                if self.is_connected:
                    self.root.after(0, self.disconnect_from_server)
                break

    def on_mouse_down(self, event):
        self.drawing = True
        self.last_x, self.last_y = event.x, event.y

        if self.is_connected:
            try:
                self.client_socket.send(f"MOVE:{event.x},{event.y},{self.drawing}".encode())
            except:
                self.disconnect_from_server()

    def on_mouse_move(self, event):
        if self.drawing and self.last_x is not None and self.last_y is not None:
            self.draw_line(self.last_x, self.last_y, event.x, event.y)

            if self.is_connected:
                try:
                    self.client_socket.send(f"MOVE:{event.x},{event.y},{self.drawing}".encode())
                except:
                    self.disconnect_from_server()

            self.last_x, self.last_y = event.x, event.y

    def on_mouse_up(self, event):
        self.drawing = False
        self.last_x, self.last_y = None, None

        if self.is_connected:
            try:
                self.client_socket.send("PEN_UP".encode())
            except:
                self.disconnect_from_server()

    def draw_line(self, x1, y1, x2, y2):
        self.canvas.create_line(x1, y1, x2, y2, width=2, fill="black", smooth=True)

    def clear_canvas(self):
        self.canvas.delete("all")

        if self.is_connected:
            try:
                self.client_socket.send("CLEAR".encode())
            except:
                self.disconnect_from_server()

    def clear_canvas_without_notify(self):
        self.canvas.delete("all")

    def on_closing(self):
        if messagebox.askokcancel("Quit", "Do you actually want to quit?"):
            self.disconnect_from_server()
            self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    client = DrawingClient()
    client.run()
