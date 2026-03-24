"""
server-select.py — Non-blocking TCP server menggunakan select module

Cara kerja:
- Menggunakan select.select() untuk memonitor banyak socket sekaligus
  dalam satu thread tunggal (I/O multiplexing).
- Server bisa melayani banyak klien secara bersamaan tanpa threading.
- select() memblokir hingga ada socket yang siap dibaca/ditulis,
  lalu server memproses socket tersebut satu per satu dalam satu loop.

"""

import socket
import select
import os

HOST = '0.0.0.0'
PORT = 9091
BUFFER = 4096
FILES_DIR = 'server_files'

os.makedirs(FILES_DIR, exist_ok=True)


# ── State per klien ──────────────────────────────────────────────────────────
#
# Struktur client_state[conn] = {
#   'addr'     : (ip, port),
#   'mode'     : 'command' | 'upload' | 'download',
#   'filename' : str,           # sedang upload/download file ini
#   'file_size': int,           # total ukuran file (saat upload)
#   'received' : int,           # bytes yang sudah diterima (saat upload)
#   'file_obj' : file object,   # file yang sedang ditulis (saat upload)
#   'send_buf' : bytes,         # buffer data yang akan dikirim (saat download)
# }
client_state = {}


def broadcast(sockets, sender_conn, message: bytes):
    """Kirim pesan ke semua klien kecuali pengirim."""
    for sock in sockets:
        if sock is not sender_conn:
            try:
                sock.sendall(message)
            except Exception:
                pass


def start_upload(conn, filename):
    """Persiapkan state untuk menerima file dari klien."""
    filepath = os.path.join(FILES_DIR, filename)
    client_state[conn]['mode']     = 'upload_wait_size'
    client_state[conn]['filename'] = filename
    client_state[conn]['file_obj'] = open(filepath, 'wb')
    client_state[conn]['received'] = 0
    client_state[conn]['file_size'] = 0
    conn.sendall(b'READY')


def finish_upload(conn):
    """Tutup file dan reset state ke 'command' setelah upload selesai."""
    state = client_state[conn]
    if state.get('file_obj'):
        state['file_obj'].close()
        state['file_obj'] = None
    filename = state['filename']
    received = state['received']
    print(f"  [UPLOAD] {filename} ({received} bytes) dari {state['addr']} selesai.")
    state['mode']     = 'command'
    state['filename'] = ''
    state['file_size'] = 0
    state['received'] = 0
    conn.sendall(b'OK')


def prepare_download(conn, filename):
    """
    Cek file ada atau tidak, lalu siapkan data untuk dikirim.
    Pengiriman aktual dilakukan di loop utama saat socket siap tulis.
    """
    filepath = os.path.join(FILES_DIR, filename)
    if not os.path.isfile(filepath):
        conn.sendall(b'NOTFOUND')
        print(f"  [DOWNLOAD] {filename} tidak ditemukan.")
        return

    file_size = os.path.getsize(filepath)
    with open(filepath, 'rb') as f:
        file_data = f.read()

    # Kirim header: FOUND + ukuran file (8 byte) + isi file sekaligus
    header = b'FOUND' + file_size.to_bytes(8, 'big')
    conn.sendall(header + file_data)
    print(f"  [DOWNLOAD] {filename} ({file_size} bytes) dikirim ke {client_state[conn]['addr']}.")


def handle_command(conn, message, client_sockets):
    """Proses perintah teks dari klien."""
    state = client_state[conn]
    addr  = state['addr']
    print(f"  [RECV] {addr} -> {message!r}")

    if message.lower() == 'exit':
        conn.sendall(b'Bye!')
        return False  # sinyal untuk tutup koneksi

    elif message == '/list':
        files = os.listdir(FILES_DIR)
        response = '\n'.join(files) if files else '(tidak ada file)'
        conn.sendall(response.encode())

    elif message.startswith('/upload '):
        filename = message[len('/upload '):].strip()
        if filename:
            start_upload(conn, filename)
        else:
            conn.sendall(b'ERROR: nama file kosong')

    elif message.startswith('/download '):
        filename = message[len('/download '):].strip()
        if filename:
            prepare_download(conn, filename)
        else:
            conn.sendall(b'ERROR: nama file kosong')

    else:
        # Broadcast pesan teks ke semua klien lain
        broadcast_msg = f'[{addr[0]}:{addr[1]}] {message}\n'.encode()
        broadcast(client_sockets, conn, broadcast_msg)
        conn.sendall(f'[Server] pesan dikirim ke {len(client_sockets)-1} klien lain.\n'.encode())

    return True  # koneksi tetap terbuka


def process_readable(conn, client_sockets):
    """
    Dipanggil saat select() mendeteksi conn siap dibaca.
    Mengembalikan False jika koneksi harus ditutup.
    """
    state = client_state[conn]
    mode  = state['mode']

    try:
        data = conn.recv(BUFFER)
    except ConnectionResetError:
        return False

    if not data:
        return False  # koneksi ditutup oleh klien

    # ── Mode: menunggu ukuran file (8 byte pertama setelah READY) ──
    if mode == 'upload_wait_size':
        if len(data) >= 8:
            state['file_size'] = int.from_bytes(data[:8], 'big')
            state['mode']      = 'upload_data'
            # Sisa data setelah 8 byte ukuran adalah awal isi file
            payload = data[8:]
            if payload:
                state['file_obj'].write(payload)
                state['received'] += len(payload)
            if state['received'] >= state['file_size']:
                finish_upload(conn)
        return True

    # ── Mode: menerima isi file ──
    if mode == 'upload_data':
        state['file_obj'].write(data)
        state['received'] += len(data)
        if state['received'] >= state['file_size']:
            finish_upload(conn)
        return True

    # ── Mode: perintah biasa ──
    message = data.decode(errors='replace').strip()
    return handle_command(conn, message, client_sockets)


def close_client(conn, client_sockets, inputs):
    """Bersihkan state dan tutup koneksi klien."""
    addr = client_state[conn]['addr']
    # Tutup file jika sedang upload
    if client_state[conn].get('file_obj'):
        client_state[conn]['file_obj'].close()
    print(f'[-] Klien {addr} disconnected.')
    client_sockets.remove(conn)
    inputs.remove(conn)
    del client_state[conn]
    conn.close()


def main():
    server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server_sock.setblocking(False)  # server socket non-blocking
    server_sock.bind((HOST, PORT))
    server_sock.listen(10)

    print(f'[server-select] Listening on {HOST}:{PORT} ...')
    print(f'[server-select] Mode: SELECT / I/O Multiplexing (multi-klien, single-thread)')
    print(f'[server-select] Folder file: {os.path.abspath(FILES_DIR)}\n')

    # inputs = semua socket yang dimonitor select() untuk READ
    inputs         = [server_sock]
    client_sockets = []   # hanya socket klien (tanpa server_sock)

    try:
        while True:
            # select() blokir sampai ada socket yang siap dibaca
            readable, _, exceptional = select.select(inputs, [], inputs, 1.0)

            for sock in readable:

                # ── Ada koneksi masuk baru ──
                if sock is server_sock:
                    conn, addr = server_sock.accept()
                    conn.setblocking(False)
                    inputs.append(conn)
                    client_sockets.append(conn)
                    client_state[conn] = {
                        'addr'     : addr,
                        'mode'     : 'command',
                        'filename' : '',
                        'file_size': 0,
                        'received' : 0,
                        'file_obj' : None,
                    }
                    conn.sendall(b'Selamat datang! Perintah: /list | /upload <file> | /download <file>\n')
                    print(f'[+] Klien baru: {addr} | Total klien: {len(client_sockets)}')

                # ── Data masuk dari klien yang sudah terhubung ──
                else:
                    keep_alive = process_readable(sock, client_sockets)
                    if not keep_alive:
                        close_client(sock, client_sockets, inputs)

            # ── Socket error ──
            for sock in exceptional:
                if sock in client_sockets:
                    close_client(sock, client_sockets, inputs)
                else:
                    inputs.remove(sock)
                    sock.close()

    except KeyboardInterrupt:
        print('\n[server-select] Server dihentikan.')
    finally:
        for sock in inputs:
            sock.close()


if __name__ == '__main__':
    main()
