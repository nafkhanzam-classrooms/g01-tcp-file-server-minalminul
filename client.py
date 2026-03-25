"""
client.py — Terminal client untuk server-sync dan server-select

Cara pakai:
  python client.py                       # default localhost:9090
  python client.py 127.0.0.1 9091        # ke server-select
  python client.py 127.0.0.1 9092        # ke server-thread
  python client.py 127.0.0.1 9093        # ke server-poll

Perintah:
  /list                  — lihat file di server
  /upload <path_file>    — upload file lokal ke server
  /download <filename>   — download file dari server
  exit                   — keluar
"""

import socket
import os
import sys

BUFFER = 4096


def send_command(sock, command: str):
    sock.sendall(command.encode())


def do_list(sock):
    drain_socket(sock)

    send_command(sock, '/list')
    response = sock.recv(4096).decode()
    print('[File di server]')
    print(response)


def do_upload(sock, filepath: str):
    if not os.path.isfile(filepath):
        print(f'[ERROR] File tidak ditemukan: {filepath}')
        return

    filename  = os.path.basename(filepath)
    file_size = os.path.getsize(filepath)

    # Kirim perintah upload
    drain_socket(sock)
    send_command(sock, f'/upload {filename}')

    # Tunggu READY dari server
    ack = sock.recv(16)
    if ack != b'READY':
        print(f'[ERROR] Server tidak siap: {ack}')
        return

    # Kirim ukuran file (8 byte big-endian)
    sock.sendall(file_size.to_bytes(8, 'big'))

    # Kirim isi file
    sent = 0
    with open(filepath, 'rb') as f:
        while True:
            chunk = f.read(BUFFER)
            if not chunk:
                break
            sock.sendall(chunk)
            sent += len(chunk)
            print(f'\r  Mengupload... {sent}/{file_size} bytes', end='', flush=True)

    # Tunggu konfirmasi OK
    result = sock.recv(16)
    print(f'\n[UPLOAD] {filename} -> {"Berhasil" if result == b"OK" else "Gagal"}')


def do_download(sock, filename: str):
    drain_socket(sock)
    send_command(sock, f'/download {filename}')

    # Terima status
    status = sock.recv(16)

    if status.startswith(b'NOTFOUND'):
        print(f'[DOWNLOAD] File "{filename}" tidak ditemukan di server.')
        return

    if not status.startswith(b'FOUND'):
        print(f'[ERROR] Respons tidak dikenal: {status}')
        return

    # Status bisa "FOUND" + 8 byte ukuran + data awal (semua dalam satu recv)
    raw = status[len(b'FOUND'):]

    # Kumpulkan data sampai dapat 8 byte ukuran
    while len(raw) < 8:
        raw += sock.recv(BUFFER)

    file_size = int.from_bytes(raw[:8], 'big')
    data      = raw[8:]  # sisa setelah 8 byte ukuran

    # Terima sisa data
    while len(data) < file_size:
        chunk = sock.recv(min(BUFFER, file_size - len(data)))
        if not chunk:
            break
        data += chunk
        print(f'\r  Mengunduh... {len(data)}/{file_size} bytes', end='', flush=True)

    # Simpan file
    save_path = "download_" + filename
    with open(save_path, 'wb') as f:
        f.write(data)
    print(f'\n[DOWNLOAD] {filename} ({len(data)} bytes) disimpan ke {os.path.abspath(save_path)}')

def drain_socket(sock):
    sock.settimeout(0.1)
    try:
        while True:
            sock.recv(4096)
    except:
        pass
    sock.settimeout(None)

def main():
    host = sys.argv[1] if len(sys.argv) > 1 else '127.0.0.1'
    port = int(sys.argv[2]) if len(sys.argv) > 2 else 9090

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
        print(f'[client] Terhubung ke {host}:{port}')
    except ConnectionRefusedError:
        print(f'[ERROR] Tidak bisa terhubung ke {host}:{port}. Pastikan server sudah berjalan.')
        return

    # Tampilkan pesan sambutan dari server
    welcome = sock.recv(BUFFER).decode()
    print(welcome.strip())

    try:
        while True:
            try:
                cmd = input('>> ').strip()
            except EOFError:
                break

            if not cmd:
                continue

            if cmd.lower() == 'exit':
                send_command(sock, 'exit')
                print(sock.recv(64).decode())
                break

            elif cmd == '/list':
                do_list(sock)

            elif cmd.startswith('/upload '):
                filepath = cmd[len('/upload '):].strip()
                do_upload(sock, filepath)

            elif cmd.startswith('/download '):
                filename = cmd[len('/download '):].strip()
                do_download(sock, filename)

            else:
                # Kirim pesan teks biasa
                send_command(sock, cmd)
                response = sock.recv(BUFFER).decode()
                print(response)

    except KeyboardInterrupt:
        print('\n[client] Keluar.')
    finally:
        sock.close()


if __name__ == '__main__':
    main()
