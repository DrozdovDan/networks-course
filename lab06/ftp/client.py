import argparse
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

    def download_file(self, file):
        with open(file, 'wb') as f:
            self.ftp.retrbinary('RETR ' + file, f.write)

    def upload_file(self, file):
        with open(file, 'rb') as f:
            self.ftp.storbinary('STOR ' + file, f)

    def quit(self):
        self.ftp.quit()

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', type=str, help='FTP host', default='127.0.0.1')
    parser.add_argument('--port', type=int, help='FTP port', default=21)
    parser.add_argument('--username', type=str, help='FTP username', default='TestUser')
    parser.add_argument('--password', type=str, help='FTP password', default='12345678')

    args = parser.parse_args()
    client = FTPClient(args.host, args.port, args.username, args.password)
    client.connect()

    print('Available actions:')
    print('exit')
    print('ls')
    print('get <filename>')
    print('send <filename>')
    print('rm <filename>')
    print('cd <foldername>')
    print('rmd <foldername>')
    print('mkdir <foldername>')

    while True:
        action = input('> ').split()

        cmd = action[0]
        args = None
        arg = None

        if len(action) > 1:
            args = action[1:]
            if len(args) > 1:
                print(args)
                print('Unknown command')
                continue
            arg = args[0]
        if cmd == 'exit':
            break
        elif cmd == 'ls':
            print(*client.list_files(), end='\n')
        elif cmd == 'get':
            if not arg:
                print('Unknown command')
                continue
            file = arg
            client.download_file(file)
            print(f'File {file} downloaded successfully')
        elif cmd == 'send':
            if not arg:
                print('Unknown command')
                continue
            file = arg
            client.upload_file(file)
            print(f'File {file} uploaded successfully')
        elif cmd == 'rm':
            if not arg:
                print('Unknown command')
                continue
            file = arg
            client.delete_file(file)
            print(f'File {file} deleted successfully')
        elif cmd == 'rmd':
            if not arg:
                print('Unknown command')
                continue
            folder = arg
            client.delete_folder(folder)
            print(f'Folder {folder} deleted successfully')
        elif cmd == 'mkdir':
            if not arg:
                print('Unknown command')
                continue
            folder = arg
            client.create_folder(folder)
            print(f'Folder {folder} created successfully')
        elif cmd == 'cd':
            if not arg:
                print('Unknown command')
                continue
            folder = arg
            client.go_to_folder(folder)
            print(f'Folder {folder} going to')
        else:
            print('Unknown command')

    client.quit()
    print('Goodby!')

if __name__ == '__main__':
    main()




