# Wizard Arena Online — WebSocket Relay (v3)

**Status:** File game dan server sudah dibuat. Duel *dua browser lokal* telah diuji langsung: create room, join invite, pilih Wizard, Ready, Start, bergerak, serangan, HP, hasil pertandingan, keluar, dan bergabung lagi. **Koneksi Chrome ↔ Work melalui internet belum diuji**; Work mungkin membatasi WebSocket atau file HTML.

## Isi paket

- `Wizard_Arena_Relay.html`: game lengkap (Campaign, PvP musuh komputer, pilihan Wizard, Pet) + **Online Duel v3**.
- `server.py`: server WebSocket kecil untuk membuat room privat dan meneruskan pesan game.
- `requirements.txt`: dependensi Python (`websockets`).
- `render.yaml`: contoh konfigurasi hosting server pada Render.
- `run_local.bat` / `run_local.sh`: menjalankan server di komputer untuk tes lokal.

**Game tetap file HTML lokal.** Kamu tidak wajib mengunggah HTML ke website. Tapi untuk menghubungkan **dua perangkat dari internet**, server relay harus tersedia di internet. Menyimpan file HTML saja tidak dapat menggantikan server tersebut.

## A. Cara bermain setelah server online

1. Buka **file HTML yang sama** di Chrome kamu dan browser Work.
2. Kalian pilih **Play → Online Duel**.
3. Pada kolom **RELAY SERVER ADDRESS**, keduanya pakai alamat relay yang sama, misalnya `https://nama-server.onrender.com` (game akan mengubahnya otomatis menjadi `wss://nama-server.onrender.com/ws`).
4. Satu orang klik **Create Room** → **Copy Invite**.
5. Kirim teks undangan utuh yang bentuknya `WIZARENA|wss://nama-server.onrender.com/ws|ABC234` (kode ini cuma contoh).
6. Orang kedua paste di **Or paste the full invite** → **Join Invite**. Alamat server & kode room terisi otomatis.
7. Pilih Wizard → kedua pemain **Ready** → host **Start Duel**.
8. Gerak: **WASD / tombol panah / joystick layar**. Sihir: **1–4** / empat tombol di layar. Target mengarah otomatis ke lawan.

**Peringatan:** Kalau Work menjalankan kontrol melalui otomasi browser, ia mungkin kesulitan menangani game real-time, meskipun koneksinya berhasil.

## B. Mengaktifkan server internet (sekali saja)

Alternatif praktis adalah hosting Python Web Service di [Render](https://render.com/). Ada opsi Free menurut dokumentasi mereka, tetapi syarat, batasan, dan ketersediaan layanan bisa berubah.

1. Buat repository GitHub berisi **`server.py`** dan **`requirements.txt`** (opsional `render.yaml`). Game HTML tidak perlu diunggah ke repo ini.
2. Di Render, pilih **New → Web Service**, hubungkan repository tersebut.
3. Konfigurasi: Runtime **Python**; Build Command `pip install -r requirements.txt`; Start Command `python server.py`; pilih paket yang sesuai.
4. Tunggu deployment sukses. Buka `https://nama-server.onrender.com/health`. Jika benar, tulisan akan berbunyi **Wizard Arena relay is running**.
5. Masukkan `https://nama-server.onrender.com` ke kolom relay dalam HTML pada **kedua** browser.

Jika memilih **New → Blueprint** (bukan Web Service manual), sertakan `render.yaml` di root repository dan pilih repository tersebut sebagai Blueprint. Nama service `wizard-arena-relay` mungkin perlu diganti jika sudah terpakai.

Server menyediakan hanya `/ws` dan `/health`, **bukan halaman game**. Semua data room ada di memori; bila server restart/tidur, buat room baru. Pada paket Free, Render dapat menghentikan layanan yang tidak aktif dan memerlukan waktu untuk bangun lagi. Gunakan alamat **HTTPS/WSS**, bukan `ws://` biasa, untuk relay publik.

## C. Tes lokal di komputer (tidak bisa langsung diakses Work Cloud)

**Windows:** jalankan `run_local.bat` dengan Python terpasang.

**macOS / Linux:** jalankan `sh run_local.sh` dengan Python 3.10+.

Atau secara manual:

```sh
python -m pip install -r requirements.txt
python server.py
```

Buka `http://127.0.0.1:8765/health` untuk cek server. Di dua jendela browser **pada komputer yang sama**, buka file HTML dan pakai `ws://127.0.0.1:8765/ws` pada kolom relay; lalu Create Room dan Join Invite.

Alamat `127.0.0.1` **tidak bisa dipakai Work Cloud**, karena itu hanya komputer masing-masing. Untuk Work, pakai alamat relay internet pada langkah B.

## D. Kalau ada error

| Pesan | Artinya / tindakan |
| --- | --- |
| `Enter a relay address first` | Alamat server masih kosong; perlu server online. |
| `Room not found` | Kode salah, host keluar, atau kalian masuk ke relay yang berbeda. |
| `This room already has two players` | Room penuh, host harus membuat room baru atau pemain lama keluar. |
| `Disconnected from relay` | Server mati, koneksi terputus, atau browser memblokir WebSocket. |
| `Could not reach relay` | Periksa URL dan endpoint `/health`, serta izin WebSocket browser. |

## Keamanan dan batasan

- Tidak ada sistem akun, password, chat, atau penyimpanan progres online.
- Kode room acak enam karakter dan berlaku selama host tetap terhubung serta server tidak restart.
- Room hanya untuk dua koneksi. Jangan membagikan undangan di tempat publik.
- Game *host-authoritative*: browser host menghitung damage dan posisi; ini cocok untuk duel teman, bukan sistem anti-cheat kompetitif.
- Server hanya meneruskan JSON game dan tidak menyimpan histori pertandingan.
- Versi ini tidak memakai PeerJS/WebRTC sama sekali; ia membutuhkan server WebSocket yang benar-benar aktif.

Dikembangkan sebagai ekstensi `Wizard_Arena.html` milik pengguna. Teks menu di dalam game tetap memakai bahasa Inggris, mengikuti ketentuan file asli.
