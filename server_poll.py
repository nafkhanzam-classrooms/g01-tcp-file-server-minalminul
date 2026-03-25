import socket
import select
import os

HOST = '0.0.0.0'
PORT = 9093
BUFFER = 4096
FILES_DIR = 'server_files'

os.makedirs(FILES_DIR, exist_ok=True)

fd_map = {}
clients = []

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
server.bind((HOST, PORT))
server.listen(5)
server.setblocking(False)

poller = select.poll()
poller.register(server.fileno(), select.POLLIN)

fd_map[server.fileno()] = server

print(f'[POLL SERVER] Running on {HOST}:{PORT}')

while True:
    events = poller.poll()

    for fd, event in events:
        sock = fd_map[fd]

        if sock is server:
            conn, addr = server.accept()
            conn.setblocking(True)  

            fd_map[conn.fileno()] = conn
            poller.register(conn.fileno(), select.POLLIN)

            clients.append(conn)

            print(f'[+] Client connected: {addr}')
            conn.sendall(b'Selamat datang!\n')

        elif event & select.POLLIN:
            try:
                data = sock.recv(BUFFER)
                if not data:
                    raise ConnectionResetError

                msg = data.decode(errors='ignore').split('\n')[0].strip()
                addr = sock.getpeername()

                print(f'[RECV] {addr} -> {msg!r}')

                if msg.startswith('/list'):
                    files = os.listdir(FILES_DIR)
                    response = '\n'.join(files) if files else '(tidak ada file)'
                    sock.sendall(response.encode())

                elif msg.startswith('/upload '):
                    filename = msg.split()[1]
                    filepath = os.path.join(FILES_DIR, filename)

                    sock.sendall(b'READY')

                    # terima ukuran file (8 byte)
                    raw_size = b''
                    while len(raw_size) < 8:
                        raw_size += sock.recv(8 - len(raw_size))

                    file_size = int.from_bytes(raw_size, 'big')

                    received = 0
                    with open(filepath, 'wb') as f:
                        while received < file_size:
                            chunk = sock.recv(min(BUFFER, file_size - received))
                            if not chunk:
                                break
                            f.write(chunk)
                            received += len(chunk)

                    sock.sendall(b'OK')
                    print(f'[UPLOAD] {filename} ({received} bytes)')

                elif msg.startswith('/download '):
                    filename = msg.split()[1]
                    filepath = os.path.join(FILES_DIR, filename)

                    if not os.path.exists(filepath):
                        sock.sendall(b'NOTFOUND')
                    else:
                        sock.sendall(b'FOUND')

                        file_size = os.path.getsize(filepath)
                        sock.sendall(file_size.to_bytes(8, 'big'))

                        with open(filepath, 'rb') as f:
                            while True:
                                chunk = f.read(BUFFER)
                                if not chunk:
                                    break
                                sock.sendall(chunk)

                else:
                    broadcast_msg = f'[{addr[0]}:{addr[1]}] {msg}\n'.encode()

                    count = 0
                    for c in clients:
                        if c != sock:
                            try:
                                c.sendall(broadcast_msg)
                                count += 1
                            except:
                                pass

                    sock.sendall(f'[Server] pesan dikirim ke {count} klien lain.\n'.encode())

            except:
                addr = sock.getpeername()
                print(f'[-] Client disconnected: {addr}')

                poller.unregister(fd)
                sock.close()
                clients.remove(sock)
                del fd_map[fd]

        if event & (select.POLLERR | select.POLLHUP):
            poller.unregister(fd)
            sock.close()
            if fd in fd_map:
                del fd_map[fd]
