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

Server ini bekerja dengan model blocking, satu klien dalam satu waktu. Inti dari cara kerjanya ada di fungsi main():

```
server_sock.accept()  → menunggu klien masuk (BLOCKING)
handle_client(conn)    → melayani klien sampai selesai (BLOCKING)
server_sock.accept()   → baru kemudian menerima klien berikutnya
```

Ketika `handle_client()` sedang berjalan, loop `main()` tidak akan kembali ke `accept()`. Artinya, jika ada klien kedua yang mencoba connect, koneksinya akan masuk ke antrian OS (karena `listen(5)`) tapi tidak akan direspons oleh program sampai klien pertama `exit`.

Fungsi-fungsi Utama:

`main()` Membuat server socket, bind ke port 9090, lalu masuk ke loop `accept()` yang blocking. Setiap iterasi loop menangani tepat satu klien.

`handle_client(conn, addr)` Loop `recv()` yang terus membaca perintah dari satu klien. Fungsi ini baru return ketika klien mengirim `exit` atau koneksi putus. Selama fungsi ini berjalan, seluruh server "terkunci" untuk klien ini.

`handle_list(conn)` Membaca isi folder `server_files/` dengan `os.listdir()` lalu mengirimkan hasilnya sebagai string ke klien.

`handle_upload(conn, filename)` Mengikuti protokol: kirim READY → terima 8 byte ukuran file → terima isi file dalam loop chunk → kirim OK. File disimpan ke `server_files/`.

`handle_download(conn, filename)` Cek apakah file ada. Jika tidak, kirim NOTFOUND. Jika ada, kirim FOUND → kirim 8 byte ukuran → kirim isi file dalam loop chunk.

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

Kelebihan utamanya adalah mampu **melayani banyak klien sekaligus** tanpa overhead thread. Ini juga yang membuat **broadcast pesan** bisa bekerja — server-sync tidak bisa melakukan broadcast karena tidak pernah punya lebih dari satu klien aktif. Keterbatasannya: kode lebih kompleks karena state harus dikelola secara eksplisit, dan operasi yang lama (seperti upload file besar) akan tetap memblokir server selama data diproses karena semuanya single-thread.

## Screenshot Hasil
---
*Server_Thread*

