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
`server_sock.accept()  → menunggu klien masuk (BLOCKING)
handle_client(conn)    → melayani klien sampai selesai (BLOCKING)
server_sock.accept()   → baru kemudian menerima klien berikutnya`
Ketika `handle_client()` sedang berjalan, loop `main()` tidak akan kembali ke `accept()`. Artinya, jika ada klien kedua yang mencoba connect, koneksinya akan masuk ke antrian OS (karena `listen(5)`) tapi tidak akan direspons oleh program sampai klien pertama `exit`.

Fungsi-fungsi Utama:

`main()` Membuat server socket, bind ke port 9090, lalu masuk ke loop `accept()` yang blocking. Setiap iterasi loop menangani tepat satu klien.
`handle_client(conn, addr)` Loop `recv()` yang terus membaca perintah dari satu klien. Fungsi ini baru return ketika klien mengirim `exit` atau koneksi putus. Selama fungsi ini berjalan, seluruh server "terkunci" untuk klien ini.
`handle_list(conn)` Membaca isi folder `server_files/` dengan `os.listdir()` lalu mengirimkan hasilnya sebagai string ke klien.
`handle_upload(conn, filename)` Mengikuti protokol: kirim READY → terima 8 byte ukuran file → terima isi file dalam loop chunk → kirim OK. File disimpan ke `server_files/`.
`handle_download(conn, filename)` Cek apakah file ada. Jika tidak, kirim NOTFOUND. Jika ada, kirim FOUND → kirim 8 byte ukuran → kirim isi file dalam loop chunk.

Kelebihan dan Keterbatasan
Kelebihan server ini adalah kodenya sangat sederhana dan mudah di-debug karena tidak ada state yang perlu dikelola antar klien. Keterbatasannya adalah tidak bisa melayani banyak klien secara bersamaan. 



## Screenshot Hasil
---
*Server_Thread*

