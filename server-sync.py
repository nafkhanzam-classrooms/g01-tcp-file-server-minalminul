"""
server-sync.py — Synchronous TCP server (one client at a time)

Cara kerja:
- Server menerima satu koneksi klien, melayaninya sampai selesai,
  baru kemudian menerima koneksi berikutnya.
- Tidak ada konkurensi: klien kedua harus menunggu klien pertama selesai.

"""

import socket
import os

HOST = '0.0.0.0'
PORT = 9090
BUFFER  = 4096
FILES_DIR = 'server_files'  

os.makedirs(FILES_DIR, exist_ok=True)


def handle_list(conn):
    """Kirim daftar file yang ada di server."""
    files = os.listdir(FILES_DIR)
    if files:
        response = '\n'.join(files)
    else:
        response = '(tidak ada file)'
    conn.sendall(response.encode())


def handle_upload(conn, filename):
    """
    Terima file dari klien dan simpan ke FILES_DIR.
    Protokol:
      1. Server kirim 'READY'
      2. Klien kirim ukuran file (8 byte, big-endian)
      3. Klien kirim isi file
      4. Server kirim 'OK' setelah selesai
    """
    conn.sendall(b'READY')

    raw_size = conn.recv(8)
    file_size = int.from_bytes(raw_size, 'big')

    filepath = os.path.join(FILES_DIR, filename)
    received = 0
    with open(filepath, 'wb') as f:
        while received < file_size:
            chunk = conn.recv(min(BUFFER, file_size - received))
            if not chunk:
                break
            f.write(chunk)
            received += len(chunk)

    conn.sendall(b'OK')
    print(f'  [UPLOAD] {filename} ({received} bytes) tersimpan.')


def handle_download(conn, filename):
    """
    Kirim file dari server ke klien.
    Protokol:
      1. Cek file ada atau tidak
         - Jika tidak ada: kirim 'NOTFOUND'
         - Jika ada: kirim 'FOUND', lalu ukuran file (8 byte), lalu isi file
    """
    filepath = os.path.join(FILES_DIR, filename)
    if not os.path.isfile(filepath):
        conn.sendall(b'NOTFOUND')
        print(f'  [DOWNLOAD] {filename} tidak ditemukan.')
        return

    conn.sendall(b'FOUND')
    file_size = os.path.getsize(filepath)

    conn.sendall(file_size.to_bytes(8, 'big'))

    sent = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(BUFFER)
            if not chunk:
                break
            conn.sendall(chunk)
            sent += len(chunk)

    print(f'  [DOWNLOAD] {filename} ({sent} bytes) dikirim.')


def handle_client(conn, addr):
    """
    Loop utama menangani perintah dari satu klien.
    Perintah yang didukung:
      /list
      /upload <filename>
      /download <filename>
    Koneksi berakhir jika klien mengirim pesan kosong atau 'exit'.
    """
    print(f'[+] Klien terhubung: {addr}')
   
    conn.sendall(b'Selamat datang! Perintah: /list | /upload <file> | /download <file>\n')

    try:
        while True:
            data = conn.recv(BUFFER)
            if not data:
                break  

            message = data.decode().strip()
            print(f'  [RECV] {addr} -> {message!r}')

            if message.lower() == 'exit':
                conn.sendall(b'Bye!')
                break

            elif message == '/list':
                handle_list(conn)

            elif message.startswith('/upload '):
                filename = message[len('/upload '):].strip()
                if filename:
                    handle_upload(conn, filename)
                else:
                    conn.sendall(b'ERROR: nama file kosong')

            elif message.startswith('/download '):
                filename = message[len('/download '):].strip()
                if filename:
                    handle_download(conn, filename)
                else:
                    conn.sendall(b'ERROR: nama file kosong')

            else:
                response = f'[Server] pesan diterima: {message}'
                conn.sendall(response.encode())

    except ConnectionResetError:
        print(f'[-] Koneksi {addr} terputus secara paksa.')
    finally:
        conn.close()
        print(f'[-] Klien {addr} disconnected.')


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.bind((HOST, PORT))
    server_sock.listen(5)
    print(f'[server-sync] Listening on {HOST}:{PORT} ...')
    print(f'[server-sync] Mode: SYNCHRONOUS (satu klien dalam satu waktu)')
    print(f'[server-sync] Folder file: {os.path.abspath(FILES_DIR)}\n')

    try:
        while True:
            print('[*] Menunggu koneksi klien...')
            conn, addr = server_sock.accept()  
            handle_client(conn, addr)   
    except KeyboardInterrupt:
        print('\n[server-sync] Server dihentikan.')
    finally:
        server_sock.close()


if __name__ == '__main__':
    main()
