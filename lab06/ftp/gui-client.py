import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, simpledialog
import os
from ftplib import FTP
import tempfile
from ftplib import FTP

class FTPClient:

    def __init__(self, host, port, username, password):
        self.ftp = FTP()
        self.host = host
        self.port = port
        self.username = username
        self.password = password

    def connect(self):
        self.ftp.connect(self.host, self.port)
        self.ftp.login(self.username, self.password)

    def go_to_folder(self, folder):
        self.ftp.cwd(folder)

    def create_folder(self, folder):
        self.ftp.mkd(folder)

    def delete_file(self, file):
        self.ftp.delete(file)

    def delete_folder(self, folder):
        self.ftp.rmd(folder)

    def list_files(self):
        files = []
        self.ftp.dir(files.append)
        return files

    def download_file(self, filename,  file):
        with open(file, 'wb') as f:
            self.ftp.retrbinary('RETR ' + filename, f.write)

    def upload_file(self, filename, file):
        with open(file, 'rb') as f:
            self.ftp.storbinary('STOR ' + filename, f)

    def quit(self):
        self.ftp.quit()

class FTPClientGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("FTP Client")
        self.root.geometry("900x600")
        self.client = None
        self.current_path = "/"
        self.temp_dir = tempfile.mkdtemp()
        self.create_connection_frame()
        self.create_file_list_frame()
        self.create_operations_frame()
        self.create_content_frame()
        self.create_status_bar()

    def create_connection_frame(self):
        frame = ttk.LabelFrame(self.root, text="Connection Settings")
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="Server:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.server_entry = ttk.Entry(frame, width=30)
        self.server_entry.insert(0, "127.0.0.1")
        self.server_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(frame, text="Port:").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        self.port_entry = ttk.Entry(frame, width=10)
        self.port_entry.insert(0, "21")
        self.port_entry.grid(row=0, column=3, padx=5, pady=5, sticky="w")

        ttk.Label(frame, text="Username:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.username_entry = ttk.Entry(frame, width=30)
        self.username_entry.insert(0, "TestUser")
        self.username_entry.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        ttk.Label(frame, text="Password:").grid(row=1, column=2, padx=5, pady=5, sticky="w")
        self.password_entry = ttk.Entry(frame, width=30, show="*")
        self.password_entry.insert(0, "12345678")
        self.password_entry.grid(row=1, column=3, padx=5, pady=5, sticky="w")

        self.connect_button = ttk.Button(frame, text="Connect", command=self.connect_to_server)
        self.connect_button.grid(row=1, column=4, padx=5, pady=5, sticky="e")

        self.disconnect_button = ttk.Button(frame, text="Disconnect", command=self.disconnect, state="disabled")
        self.disconnect_button.grid(row=1, column=5, padx=5, pady=5, sticky="e")

    def create_file_list_frame(self):
        frame = ttk.LabelFrame(self.root, text="File Browser")
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        path_frame = ttk.Frame(frame)
        path_frame.pack(fill="x", padx=5, pady=5)

        self.path_var = tk.StringVar(value="/")
        ttk.Label(path_frame, text="Current Path:").pack(side="left", padx=5)
        self.path_entry = ttk.Entry(path_frame, textvariable=self.path_var, width=50)
        self.path_entry.pack(side="left", padx=5, fill="x", expand=True)

        self.go_button = ttk.Button(path_frame, text="Go", command=self.navigate_to_path, state="disabled")
        self.go_button.pack(side="left", padx=5)

        self.up_button = ttk.Button(path_frame, text="Up", command=self.go_up, state="disabled")
        self.up_button.pack(side="left", padx=5)

        list_frame = ttk.Frame(frame)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)

        columns = ("name", "type", "size", "date")
        self.file_list = ttk.Treeview(list_frame, columns=columns, show="headings")
        self.file_list.heading("name", text="Name")
        self.file_list.heading("type", text="Type")
        self.file_list.heading("size", text="Size")
        self.file_list.heading("date", text="Date Modified")
        self.file_list.column("name", width=300)
        self.file_list.column("type", width=80)
        self.file_list.column("size", width=100)
        self.file_list.column("date", width=150)
        self.file_list.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=self.file_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.file_list.configure(yscrollcommand=scrollbar.set)
        self.file_list.bind("<Double-1>", self.on_file_double_click)

    def create_operations_frame(self):
        frame = ttk.LabelFrame(self.root, text="Operations")
        frame.pack(fill="x", padx=10, pady=5)

        ttk.Label(frame, text="File Name:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.file_entry = ttk.Entry(frame, width=40)
        self.file_entry.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.create_button = ttk.Button(frame, text="Create", command=self.create_file, state="disabled")
        self.create_button.grid(row=0, column=2, padx=5, pady=5)

        self.retrieve_button = ttk.Button(frame, text="Retrieve", command=self.retrieve_file, state="disabled")
        self.retrieve_button.grid(row=0, column=3, padx=5, pady=5)

        self.update_button = ttk.Button(frame, text="Update", command=self.update_file, state="disabled")
        self.update_button.grid(row=0, column=4, padx=5, pady=5)

        self.delete_button = ttk.Button(frame, text="Delete", command=self.delete_file, state="disabled")
        self.delete_button.grid(row=0, column=5, padx=5, pady=5)

        self.mkdir_button = ttk.Button(frame, text="Create Directory", command=self.create_directory, state="disabled")
        self.mkdir_button.grid(row=1, column=2, padx=5, pady=5)

        self.rmdir_button = ttk.Button(frame, text="Delete Directory", command=self.delete_directory, state="disabled")
        self.rmdir_button.grid(row=1, column=3, padx=5, pady=5)

        self.refresh_button = ttk.Button(frame, text="Refresh", command=self.refresh_files, state="disabled")
        self.refresh_button.grid(row=1, column=4, padx=5, pady=5)

    def create_content_frame(self):
        frame = ttk.LabelFrame(self.root, text="File Content")
        frame.pack(fill="both", expand=True, padx=10, pady=5)

        self.content_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD)
        self.content_text.pack(fill="both", expand=True, padx=5, pady=5)

    def create_status_bar(self):
        self.status_var = tk.StringVar()
        self.status_var.set("Not connected")

        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

    def connect_to_server(self):
        server = self.server_entry.get()
        try:
            port = int(self.port_entry.get())
        except ValueError:
            messagebox.showerror("Error", "Port must be a number")
            return

        username = self.username_entry.get()
        password = self.password_entry.get()

        try:
            self.status_var.set("Connecting...")
            self.root.update_idletasks()

            self.client = FTPClient(server, port, username, password)
            self.client.connect()

            self.enable_controls(True)
            self.status_var.set(f"Connected to {server}:{port}")

            self.current_path = "/"
            self.path_var.set(self.current_path)
            self.refresh_files()

        except Exception as e:
            messagebox.showerror("Connection Error", str(e))
            self.status_var.set("Connection failed")
            self.client = None

    def disconnect(self):
        if self.client:
            try:
                self.client.quit()
            except:
                pass
            finally:
                self.client = None

        self.enable_controls(False)
        self.clear_file_list()
        self.content_text.delete(1.0, tk.END)
        self.status_var.set("Disconnected")

    def enable_controls(self, enable):
        state = "normal" if enable else "disabled"
        self.disconnect_button.config(state=state)
        self.go_button.config(state=state)
        self.up_button.config(state=state)
        self.create_button.config(state=state)
        self.retrieve_button.config(state=state)
        self.update_button.config(state=state)
        self.delete_button.config(state=state)
        self.mkdir_button.config(state=state)
        self.rmdir_button.config(state=state)
        self.refresh_button.config(state=state)

        self.connect_button.config(state="disabled" if enable else "normal")

    def clear_file_list(self):
        for item in self.file_list.get_children():
            self.file_list.delete(item)

    def refresh_files(self):
        if not self.client:
            return

        self.clear_file_list()
        self.status_var.set(f"Listing files in {self.current_path}")
        self.root.update_idletasks()

        try:
            file_lines = self.client.list_files()
            file_data = []

            for line in file_lines:
                parts = line.split()
                if len(parts) < 9:
                    continue

                permissions = parts[0]
                size = parts[4]
                date = ' '.join(parts[5:8])
                name = ' '.join(parts[8:])

                is_dir = permissions.startswith('d')
                file_type = "Directory" if is_dir else "File"

                file_data.append((name, file_type, size, date))

            directories = [f for f in file_data if f[1] == "Directory"]
            files = [f for f in file_data if f[1] == "File"]

            for name, file_type, size, date in sorted(directories) + sorted(files):
                self.file_list.insert("", "end", values=(name, file_type, size, date))

            self.status_var.set(f"Found {len(file_data)} items in {self.current_path}")

        except Exception as e:
            messagebox.showerror("Error", f"Failed to list files: {str(e)}")
            self.status_var.set("Failed to list files")

    def navigate_to_path(self):
        if not self.client:
            return

        path = self.path_var.get()

        try:
            self.client.go_to_folder(path)
            self.current_path = path
            self.refresh_files()
        except Exception as e:
            messagebox.showerror("Navigation Error", str(e))
            self.path_var.set(self.current_path)

    def go_up(self):
        if not self.client or self.current_path == "/":
            return

        path_parts = self.current_path.split("/")
        if len(path_parts) <= 2:
            new_path = "/"
        else:
            new_path = "/".join(path_parts[:-1])
            if not new_path:
                new_path = "/"

        try:
            self.client.go_to_folder(new_path)
            self.current_path = new_path
            self.path_var.set(new_path)
            self.refresh_files()
        except Exception as e:
            messagebox.showerror("Navigation Error", str(e))

    def on_file_double_click(self, event):
        if not self.client:
            return

        selected = self.file_list.focus()
        if not selected:
            return

        values = self.file_list.item(selected, "values")
        if not values:
            return

        name, file_type = values[0], values[1]

        if file_type == "Directory":
            new_path = self.current_path
            if new_path.endswith("/"):
                new_path += name
            else:
                new_path += "/" + name

            try:
                self.client.go_to_folder(new_path)
                self.current_path = new_path
                self.path_var.set(new_path)
                self.refresh_files()
            except Exception as e:
                messagebox.showerror("Navigation Error", str(e))
        else:
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, name)
            self.retrieve_file()

    def create_file(self):
        if not self.client:
            return

        filename = self.file_entry.get()
        if not filename:
            messagebox.showerror("Error", "Please enter a file name")
            return

        editor = tk.Toplevel(self.root)
        editor.title(f"Create File: {filename}")
        editor.geometry("600x400")

        editor_text = scrolledtext.ScrolledText(editor, wrap=tk.WORD)
        editor_text.pack(fill="both", expand=True, padx=10, pady=10)

        def save_file():
            content = editor_text.get(1.0, tk.END)
            try:
                temp_file = os.path.join(self.temp_dir, filename)
                with open(temp_file, 'w') as f:
                    f.write(content)

                self.client.upload_file(filename, temp_file)

                messagebox.showinfo("Success", f"File {filename} created successfully")
                self.refresh_files()
                self.retrieve_file()
                editor.destroy()

                try:
                    os.remove(temp_file)
                except:
                    pass

            except Exception as e:
                messagebox.showerror("Error", f"Failed to create file: {str(e)}")

        buttons_frame = ttk.Frame(editor)
        buttons_frame.pack(fill="x", side="bottom", padx=10, pady=5)

        save_button = ttk.Button(buttons_frame, text="Save", command=save_file)
        save_button.pack(side="right", padx=5)

        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=editor.destroy)
        cancel_button.pack(side="right", padx=5)

    def retrieve_file(self):
        if not self.client:
            return

        filename = self.file_entry.get()
        if not filename:
            selected = self.file_list.focus()
            if selected:
                values = self.file_list.item(selected, "values")
                if values and values[1] == "File":
                    filename = values[0]
                    self.file_entry.delete(0, tk.END)
                    self.file_entry.insert(0, filename)

        if not filename:
            messagebox.showerror("Error", "Please enter a file name")
            return

        self.content_text.delete(1.0, tk.END)

        try:
            temp_file = os.path.join(self.temp_dir, filename)

            self.client.download_file(filename, temp_file)

            with open(temp_file, 'r') as f:
                content = f.read()
                self.content_text.insert(1.0, content)

            self.status_var.set(f"Retrieved file {filename}")

            try:
                os.remove(temp_file)
            except:
                pass

        except Exception as e:
            messagebox.showerror("Error", f"Failed to retrieve file: {str(e)}")
            self.status_var.set("Failed to retrieve file")

    def update_file(self):
        if not self.client:
            return

        filename = self.file_entry.get()
        if not filename:
            messagebox.showerror("Error", "Please enter a file name")
            return

        current_content = ""
        try:
            temp_file = os.path.join(self.temp_dir, filename)

            try:
                self.client.download_file(filename, temp_file)

                with open(temp_file, 'r') as f:
                    current_content = f.read()
            except:
                pass

        except Exception as e:
            pass

        editor = tk.Toplevel(self.root)
        editor.title(f"Update File: {filename}")
        editor.geometry("600x400")

        editor_text = scrolledtext.ScrolledText(editor, wrap=tk.WORD)
        editor_text.pack(fill="both", expand=True, padx=10, pady=10)

        if current_content:
            editor_text.insert(1.0, current_content)

        def save_file():
            content = editor_text.get(1.0, tk.END)
            try:
                temp_file = os.path.join(self.temp_dir, filename)
                with open(temp_file, 'w') as f:
                    f.write(content)

                self.client.upload_file(filename, temp_file)

                messagebox.showinfo("Success", f"File {filename} updated successfully")
                self.refresh_files()
                self.retrieve_file()
                editor.destroy()

                try:
                    os.remove(temp_file)
                except:
                    pass

            except Exception as e:
                messagebox.showerror("Error", f"Failed to update file: {str(e)}")

        buttons_frame = ttk.Frame(editor)
        buttons_frame.pack(fill="x", padx=10, pady=5)

        save_button = ttk.Button(buttons_frame, text="Save", command=save_file)
        save_button.pack(side="right", padx=5)

        cancel_button = ttk.Button(buttons_frame, text="Cancel", command=editor.destroy)
        cancel_button.pack(side="right", padx=5)

    def delete_file(self):
        if not self.client:
            return

        filename = self.file_entry.get()
        if not filename:
            messagebox.showerror("Error", "Please enter a file name")
            return

        confirm = messagebox.askyesno("Confirm", f"Are you sure you want to delete {filename}?")
        if not confirm:
            return

        try:
            self.client.delete_file(filename)
            messagebox.showinfo("Success", f"File {filename} deleted successfully")
            self.refresh_files()
            self.content_text.delete(1.0, tk.END)
            self.file_entry.delete(0, tk.END)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete file: {str(e)}")

    def create_directory(self):
        if not self.client:
            return

        dirname = simpledialog.askstring("Create Directory", "Enter directory name:")
        if not dirname:
            return

        try:
            self.client.create_folder(dirname)
            messagebox.showinfo("Success", f"Directory {dirname} created successfully")
            self.refresh_files()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create directory: {str(e)}")

    def delete_directory(self):
        if not self.client:
            return

        dirname = simpledialog.askstring("Delete Directory", "Enter directory name:")
        if not dirname:
            return

        confirm = messagebox.askyesno("Confirm", f"Are you sure you want to delete directory {dirname}?")
        if not confirm:
            return

        try:
            self.client.delete_folder(dirname)
            messagebox.showinfo("Success", f"Directory {dirname} deleted successfully")
            self.refresh_files()
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete directory: {str(e)}")


def main():
    root = tk.Tk()
    app = FTPClientGUI(root)
    root.mainloop()

    if hasattr(app, 'temp_dir') and os.path.exists(app.temp_dir):
        try:
            for file in os.listdir(app.temp_dir):
                os.remove(os.path.join(app.temp_dir, file))
            os.rmdir(app.temp_dir)
        except:
            pass


if __name__ == "__main__":
    main()