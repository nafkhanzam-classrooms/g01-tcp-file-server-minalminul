import socket
import threading
import os

HOST = '0.0.0.0'
PORT = 9092
BUFFER = 4096
FILES_DIR = 'server_files'

os.makedirs(FILES_DIR, exist_ok=True)

clients = []

class ClientThread(threading.Thread):
    def __init__(self, conn, addr):
        super().__init__()
        self.conn = conn
        self.addr = addr

    def run(self):
        print(f'[+] Client connected: {self.addr}')
        self.conn.sendall(b'Selamat datang!\n')
        clients.append(self.conn)

        try:

            mode = "command"
            
            while True:
                data = self.conn.recv(BUFFER)
                if not data:
                    break

                msg = data.decode(errors='ignore').split('\n')[0].strip()
                print(f'[RECV] {self.addr} -> {msg!r}')

                if msg.startswith('/list'):
                    files = os.listdir(FILES_DIR)
                    response = '\n'.join(files) if files else '(tidak ada file)'
                    self.conn.sendall(response.encode())

                elif msg.startswith('/upload '):
                    filename = msg.split()[1]
                    filepath = os.path.join(FILES_DIR, filename)

                    # kirim READY
                    self.conn.sendall(b'READY')

                    # 🔥 WAJIB: terima size secara pasti
                    raw_size = b''
                    while len(raw_size) < 8:
                        raw_size += self.conn.recv(8 - len(raw_size))

                    file_size = int.from_bytes(raw_size, 'big')

                    # 🔥 terima file
                    received = 0
                    with open(filepath, 'wb') as f:
                        while received < file_size:
                            chunk = self.conn.recv(min(BUFFER, file_size - received))
                            if not chunk:
                                break
                            f.write(chunk)
                            received += len(chunk)

                    self.conn.sendall(b'OK')
                    print(f'[UPLOAD] {filename} ({received} bytes)')

                elif msg.startswith('/download '):
                    filename = msg.split()[1]
                    filepath = os.path.join(FILES_DIR, filename)

                    if not os.path.exists(filepath):
                        self.conn.sendall(b'NOTFOUND')
                    else:
                        self.conn.sendall(b'FOUND')
                        file_size = os.path.getsize(filepath)
                        self.conn.sendall(file_size.to_bytes(8, 'big'))

                        with open(filepath, 'rb') as f:
                            while True:
                                chunk = f.read(BUFFER)
                                if not chunk:
                                    break
                                self.conn.sendall(chunk)

                else:
                    broadcast_msg = f'[{self.addr[0]}:{self.addr[1]}] {msg}\n'.encode()

                    count = 0
                    for c in clients:
                        if c != self.conn:
                            try:
                                c.sendall(broadcast_msg)
                                count += 1
                            except:
                                pass

                    self.conn.sendall(f'[Server] pesan dikirim ke {count} klien lain.\n'.encode())

        finally:
            print(f'[-] Client disconnected: {self.addr}')
            self.conn.close()
            clients.remove(self.conn)


def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen(5)

    print(f'[THREAD SERVER] Running on {HOST}:{PORT}')

    while True:
        conn, addr = server.accept()
        t = ClientThread(conn, addr)
        t.start()


if __name__ == "__main__":
    main()
