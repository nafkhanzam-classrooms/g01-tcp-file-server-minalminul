[![Review Assignment Due Date](https://classroom.github.com/assets/deadline-readme-button-22041afd0340ce965d47ae6ef1cefeee28c7c493a6346c4f15d667ab976d596c.svg)](https://classroom.github.com/a/mRmkZGKe)
# Network Programming - Assignment G01

## Anggota Kelompok
| Nama           | NRP        | Kelas     |
| ---            | ---        | ----------|
| Shafira Nauraishma Zahida | 5025241235 | Program Jaringan C |
| Najma Lail Arazy | 5025241243 | Program Jaringan C |

## Link Youtube (Unlisted)
Link ditaruh di bawah ini
```

```

## Penjelasan Program

**Server-sync.py — Server Sinkronus**

Cara Kerja:

Server ini bekerja dengan model blocking, satu klien dalam satu waktu. Inti dari cara kerjanya ada di fungsi `main()`:

```
server_sock.accept()   → menunggu klien masuk (BLOCKING)
handle_client(conn)    → melayani klien sampai selesai (BLOCKING)
server_sock.accept()   → baru kemudian menerima klien berikutnya
```

Ketika `handle_client()` sedang berjalan, loop `main()` tidak akan kembali ke `accept()`. Artinya, jika ada klien kedua yang mencoba connect, koneksinya akan masuk ke antrian OS (karena `listen(5)`) tapi tidak akan direspons oleh program sampai klien pertama `exit`.

Fungsi-fungsi Utama:

- `main()` Membuat server socket, bind ke port 9090, lalu masuk ke loop `accept()` yang blocking. Setiap iterasi loop menangani tepat satu klien.

- `handle_client(conn, addr)` Loop `recv()` yang terus membaca perintah dari satu klien. Fungsi ini baru return ketika klien mengirim `exit` atau koneksi putus. Selama fungsi ini berjalan, seluruh server "terkunci" untuk klien ini.

- `handle_list(conn)` Membaca isi folder `server_files/` dengan `os.listdir()` lalu mengirimkan hasilnya sebagai string ke klien.

- `handle_upload(conn, filename)` Mengikuti protokol: kirim READY → terima 8 byte ukuran file → terima isi file dalam loop chunk → kirim OK. File disimpan ke `server_files/`.

- `handle_download(conn, filename)` Cek apakah file ada. Jika tidak, kirim NOTFOUND. Jika ada, kirim FOUND → kirim 8 byte ukuran → kirim isi file dalam loop chunk.

Kelebihan dan Keterbatasan

Kelebihan server ini adalah kodenya sangat sederhana dan mudah di-debug karena tidak ada state yang perlu dikelola antar klien. Keterbatasannya adalah tidak bisa melayani banyak klien secara bersamaan. 


**server-select.py — Server dengan I/O Multiplexing**

Cara Kerja:

Server ini menggunakan `select.select()` untuk memonitor banyak socket sekaligus dalam satu thread. Teknik ini disebut I/O multiplexing. Ide dasarnya: daripada memblokir di satu `recv()`, tanya ke OS "socket mana yang sudah punya data siap dibaca?" lalu proses satu per satu.


```
inputs = [server_sock, client1, client2, client3, ...]

readable = select.select(inputs, ...)
→ OS mengembalikan: [client1, client3]  ← hanya yang siap

for sock in readable:
    proses sock ini
```

Semua ini terjadi dalam satu thread, satu proses. Tidak ada `threading.Thread` sama sekali.

Server-select tidak bisa menyimpan state di stack fungsi (karena tidak ada thread per klien). Jika klien sedang di tengah-tengah upload file dan select() dipanggil lagi, server harus tahu bahwa klien itu sedang dalam mode upload — bukan mode perintah biasa. Solusinya adalah dictionary client_state yang menyimpan state setiap koneksi:

```
pythonclient_state[conn] = {
    'addr'     : (ip, port),
    'mode'     : 'command',      # atau 'upload_wait_size', 'upload_data'
    'filename' : '',
    'file_size': 0,
    'received' : 0,
    'file_obj' : None,           # file handle yang sedang ditulis
}
```

Setiap kali ada data masuk dari suatu koneksi, `process_readable()` membaca `mode` dari `client_state` untuk menentukan cara memproses data tersebut.

Fungsi-fungsi Utama:

- `main()` Loop utama yang memanggil `select.select(inputs, [], inputs, timeout=1.0)`. Mengembalikan dua list: `readable` (socket siap dibaca) dan `exceptional` (socket error). Jika `readable` berisi `server_sock`, berarti ada klien baru yang connect. Jika berisi socket klien, berarti ada data masuk dari klien tersebut.

- `process_readable(conn, client_sockets)` Dispatcher utama. Membaca data dari socket lalu memeriksa `mode` di `client_state[conn]` untuk memutuskan apakah data ini adalah perintah teks, header ukuran file, atau isi file yang sedang di-upload.

- `handle_command(conn, message, client_sockets)` Memproses perintah teks (`/list`, `/upload`, `/download`, atau pesan broadcast). Mengembalikan `True` jika koneksi tetap hidup, `False` jika harus ditutup (ketika klien kirim `exit`).

- `start_upload(conn, filename)` Tidak langsung menerima file, tapi mengubah `mode` klien menjadi `upload_wait_size` dan membuka file handle. Penerimaan data aktual terjadi di iterasi `select()` berikutnya.

- `finish_upload(conn)` Menutup file handle, mencetak log, lalu mereset `mode` kembali ke `command`. Dipanggil ketika `received >= file_size`.

- `broadcast(sockets, sender_conn, message)` Mengirim pesan ke semua socket dalam list `client_sockets` kecuali `sender_conn`. Ini yang membuat server-select berfungsi sebagai chat room. 

- `close_client(conn, client_sockets, inputs)` Membersihkan semua referensi ke koneksi yang putus: hapus dari `client_sockets`, `inputs`, dan `client_state`, lalu tutup socket.

Kelebihan dan Keterbatasan

Kelebihan utamanya adalah mampu melayani banyak klien sekaligus tanpa overhead thread. Ini juga yang membuat broadcast pesan bisa bekerja. Server-sync tidak bisa melakukan broadcast karena tidak pernah punya lebih dari satu klien aktif. Keterbatasannya: kode lebih kompleks karena state harus dikelola secara eksplisit, dan operasi yang lama (seperti upload file besar) akan tetap memblokir server selama data diproses karena semuanya single-thread.

**Server-thread.py — Server using the threading**

Program ini merupakan server berbasis multithreading yang menggunakan modul socket dan threading pada Python. Server bekerja menggunakan protokol TCP dan mampu menangani lebih dari satu client secara bersamaan, di mana setiap client akan dilayani oleh satu thread terpisah.

Server menyediakan beberapa fitur utama, yaitu:

- Melihat daftar file (/list)
- Upload file (/upload)
- Download file (/download)
- Chat antar client (broadcast)

Cara Kerja Progaram:

- Inisialisasi Server
  
  Server dibuat menggunakan TCP socket dengan melakukan binding ke alamat dan port tertentu, kemudian masuk ke mode listening untuk menunggu koneksi dari client.
```
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)
```
- Penerimaan Client

```
conn, addr = server.accept()
t = ClientThread(conn, addr)
t.start()
```
  Setiap client akan ditangani oleh objek `ClientThread`, kemudian thread dijalankan menggunakan method `.start()` sehingga berjalan secara paralel.

- Penanganan Client (Thread)

  Setiap thread akan menjalankan method `run()` untuk menangani komunikasi dengan client.
```
while True:
    data = self.conn.recv(BUFFER)
```

- Perintah `/list`

  Server akan membaca isi folder penyimpanan file `(server_files)` dan mengirimkan daftar file ke client.
```
files = os.listdir(FILES_DIR)
self.conn.sendall(response.encode())
```

- Perintah `/upload`

  Server menerima file dari client dengan langkah sebagai berikut, server mengirimkan `READY` -> client mengirim ukuran file (8 byte) -> client mengirim isi file -> server menyimpan file dan mengirim `OK`.
```
self.conn.sendall(b'READY')
file_size = int.from_bytes(self.conn.recv(8), 'big')
```

- Perintah `/download`

  Server mengirim file ke client dengan langkah, jika file tidak ada (kirim `NOTFOUND`) -> jika ada (kirim `FOUND`) -> kirim ukuran file -> kirim isi file.
```
self.conn.sendall(b'FOUND')
self.conn.sendall(file_size.to_bytes(8, 'big'))
```

- Chat / Broadcast

  Jika client mengirim pesan biasa, server akan mengirim pesan tersebut ke semua client lain.
```
for c in clients:
    if c != self.conn:
        c.sendall(broadcast_msg)
```
Fungsi-Fungsi Program
- Fungsi `main()`

   Fungsi `main()` merupakan titik awal program server. Fungsi ini bertugas untuk membuat socket server, melakukan binding ke alamat dan port, serta menjalankan loop utama untuk menerima koneksi dari client. Setiap koneksi yang masuk akan dibuatkan thread baru agar dapat ditangani secara paralel.

- Kelas `ClientThread`

  Kelas ini merupakan turunan dari threading.Thread yang digunakan untuk menangani satu client. Setiap object dari kelas ini akan berjalan sebagai thread terpisah.

- Fungsi `run()`

   Method `run()` adalah fungsi utama yang dijalankan oleh setiap thread. Fungsi ini bertugas menerima data dari client, mengolah perintah, dan mengirimkan respon kembali ke client. Seluruh fitur seperti `/list`, `/upload`, `/download`, dan chat diproses di dalam fungsi ini.

- Fungsi Broadcast

   Fungsi broadcast dilakukan di dalam blok `else`, yaitu ketika pesan yang diterima bukan merupakan perintah. Server akan mengirim pesan tersebut ke semua client lain yang terhubung.
```
for c in clients:
    if c != self.conn:
        c.sendall(broadcast_msg)
```

Kelebihan dan Keterbatasan

Server ini mampu menangani banyak client secara bersamaan karena menggunakan thread terpisah untuk setiap client. Respon yang diberikan relatif cepat dan implementasinya cukup sederhana sehingga mudah dipahami dan dikembangkan. Namun, penggunaan thread untuk setiap client menyebabkan konsumsi memori dan CPU meningkat seiring bertambahnya jumlah client. Selain itu, penggunaan variabel global seperti clients berpotensi menimbulkan masalah sinkronisasi jika tidak dikelola dengan baik.

**Server-poll.py-Server using poll syscall**

Program ini merupakan server berbasis I/O multiplexing menggunakan modul `socket` dan `select` (khususnya `poll`) pada Python. Berbeda dengan server thread, server ini tidak menggunakan banyak thread, melainkan satu proses utama yang dapat menangani banyak client secara bersamaan dengan memantau aktivitas socket.

Cara Kerja Program:
- Inisialisasi Server
  
  Server dibuat menggunakan TCP socket, kemudian diatur menjadi non-blocking agar dapat digunakan dengan mekanisme `poll`.
```
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((HOST, PORT))
server.listen(5)
server.setblocking(False)
```
  Server kemudian didaftarkan ke objek `poll` untuk memantau event masuk.
```
poller = select.poll()
poller.register(server.fileno(), select.POLLIN)
```
- Struktur Data Pendukung
  
  Server menggunakan beberapa struktur data:
```
fd_map → memetakan file descriptor ke socket
clients → menyimpan daftar client yang terhubung
```
  Struktur ini penting untuk mengelola banyak koneksi dalam satu loop.

- Loop Utama (Polling)

  Server berjalan dalam loop utama yang terus memantau event menggunakan `poll()`.
```
events = poller.poll()
```
  Setiap event menunjukkan socket mana yang siap dibaca atau mengalami error.

- Penerimaan Client

  Jika event berasal dari socket server, berarti ada client baru yang terhubung.
```
conn, addr = server.accept()
conn.setblocking(True)
```
  Client kemudian didaftarkan ke `poller` dan disimpan dalam `fd_map` serta `clients`.

- Penanganan Data Client

  Jika event berasal dari client, server akan membaca data menggunakan `recv()`.
```
data = sock.recv(BUFFER)
```
  Data kemudian diproses sebagai perintah yang dikirimkan client.

- Perintah `/list`

  Server membaca isi folder `server_files` dan mengirimkan daftar file ke client.
```
files = os.listdir(FILES_DIR)
```
- Perintah `/upload`

  Server menerima file dari client dengan langkah, kirim `READY` -> terima ukuran file (8 byte) -> terima isi file -> simpan file dan kirim `OK`
```
file_size = int.from_bytes(raw_size, 'big')
```
- Perintah `/download`

  Server mengirim file ke client dengan langkah, jika file tidak ada (NOTFOUND) -> jika ada (FOUND) -> kirim ukuran file -> kirim isi file
  
- Chat / Broadcast

  Pesan biasa akan dikirim ke semua client lain.
```
for c in clients:
    if c != sock:
        c.sendall(broadcast_msg)
```
- Penanganan Disconnect

  Jika terjadi error atau client terputus, server akan unregister dari `poll` -> menutup socket -> menghapus dari `fd_map` dan `clients`
```
poller.unregister(fd)
sock.close()
del fd_map[fd]
```
Fungsi-Fungsi Program

- Fungsi `poll()`

  Fungsi `poll()` digunakan untuk memantau banyak socket sekaligus dalam satu thread. Server hanya akan membaca socket yang siap, sehingga lebih efisien dibandingkan membuat thread untuk setiap client.

- Fungsi Mapping `fd_map`

  Karena `poll()` bekerja dengan file descriptor, maka digunakan dictionary `fd_map` untuk menghubungkan descriptor dengan objek socket.

- Fungsi Penanganan Event

  Setiap event dicek apakah termasuk:
```
POLLIN → ada data masuk
POLLERR / POLLHUP → error atau disconnect
```

Kelebihan dan Keterbatasan

Server poll lebih efisien dibandingkan multithreading karena tidak membuat thread baru untuk setiap client. Penggunaan resource lebih hemat dan cocok untuk menangani banyak koneksi sekaligus dalam satu proses. Namun, Server poll lebih efisien dibandingkan multithreading karena tidak membuat thread baru untuk setiap client. Penggunaan resource lebih hemat dan cocok untuk menangani banyak koneksi sekaligus dalam satu proses.

**Client.py**

Program ini merupakan client berbasis terminal yang digunakan untuk berkomunikasi dengan server menggunakan protokol TCP. Client ini dapat terhubung ke berbagai jenis server seperti server synchronous, select, thread, maupun poll.

Client menyediakan beberapa fitur utama, yaitu:

- Melihat daftar file di server (/list)
- Upload file ke server (/upload)
- Download file dari server (/download)
- Mengirim pesan teks (chat)
- Keluar dari program (exit)

Cara Kerja Program:
- Inisialisasi Client

  Client membuat socket dan melakukan koneksi ke server berdasarkan host dan port yang diberikan melalui command line.
```
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect((host, port))
```
   Jika koneksi berhasil, client akan menerima pesan sambutan dari server.

- Input Perintah User

  Client membaca input dari user secara terus-menerus menggunakan loop.
```
cmd = input('>> ').strip()
```
   Perintah yang dimasukkan akan diproses sesuai jenisnya, seperti `/list`, `/upload`, `/download`, atau pesan biasa.

Fungsi-Fungsi Program:

- Fungsi `main()`

  Fungsi utama yang menjalankan program client. Fungsi ini bertugas untuk:
  - Mengatur alamat server (host dan port)
  - Membuat koneksi ke server
  - Menjalankan loop input user
  - Mengarahkan perintah ke fungsi yang sesuai
    
- Fungsi `send_command()`

  Fungsi ini digunakan untuk mengirim perintah dari client ke server dalam bentuk string yang sudah di-encode menjadi bytes.
```
sock.sendall(command.encode())
c. Fungsi do_list()
```
   Fungsi ini digunakan untuk meminta daftar file dari server.

   Alurnya:
   - Membersihkan buffer dengan `drain_socket()`
   - Mengirim perintah `/list`
   - Menerima respon dari server
   - Menampilkan daftar file

- Fungsi `do_upload()`

  Fungsi ini digunakan untuk mengirim file dari client ke server.

  Alurnya:
  - Mengecek apakah file ada di lokal
  - Mengirim perintah `/upload`
  - Menunggu respon `READY` dari server
  - Mengirim ukuran file (8 byte)
  - Mengirim isi file secara bertahap
  - Menampilkan progress upload
  - Menerima respon `OK` dari server
```
sock.sendall(file_size.to_bytes(8, 'big'))
```
- Fungsi `do_download()`
  
  Fungsi ini digunakan untuk mengunduh file dari server.

  Alurnya:
  - Mengirim perintah `/download`
  - Menerima status (`FOUND` atau `NOTFOUND`)
  - Jika file ada: Menerima ukuran file, Menerima isi file, dan Menyimpan file dengan nama `download_<filename>`

- Fungsi `drain_socket()`

  Fungsi ini digunakan untuk membersihkan buffer socket sebelum mengirim perintah baru.
```
sock.settimeout(0.1)
sock.recv(4096)
```
   Fungsi ini penting untuk mencegah data lama (misalnya sisa broadcast/chat) mengganggu komunikasi command seperti upload dan download.

Kelebihan dan Keterbatasan
Client ini fleksibel karena dapat digunakan untuk berbagai jenis server (sync, select, thread, poll). Selain itu, fitur upload dan download sudah dilengkapi dengan mekanisme pengiriman ukuran file sehingga lebih aman dan terstruktur. Namun, client ini fleksibel karena dapat digunakan untuk berbagai jenis server (sync, select, thread, poll). Selain itu, fitur upload dan download sudah dilengkapi dengan mekanisme pengiriman ukuran file sehingga lebih aman dan terstruktur.

## Screenshot Hasil
---
*Server-Thread.py-Server using the threading*
<img width="1027" height="548" alt="Screenshot 2026-03-25 174838" src="https://github.com/user-attachments/assets/e2ffbf2f-0c52-4f3f-802c-8ee2f26f07c6" />
<img width="169" height="116" alt="Screenshot 2026-03-25 174912" src="https://github.com/user-attachments/assets/1c20361f-ffa6-487a-9020-4a7fd7a7ad3e" />

*Server-Poll.py-Server using poll syscall*
<img width="1024" height="525" alt="Screenshot 2026-03-25 175114" src="https://github.com/user-attachments/assets/301241c4-d5c0-4212-a483-585dd83464b8" />
<img width="169" height="116" alt="Screenshot 2026-03-25 174912" src="https://github.com/user-attachments/assets/96913f06-1238-4c8e-b86e-a96d4baa7c77" />

