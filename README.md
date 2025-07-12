### 1. Simpan Kode Program
Simpan kode lengkap di atas dalam file dengan nama `v.py`

### 2. Instal Dependencies
Buka terminal/command prompt dan jalankan perintah:
```bash
pip install aiohttp aiohttp_socks fake_useragent
```

### 3. Menjalankan Program
Jalankan program dengan perintah:
```bash
python v.py
```

### 4. Mengikuti Panduan Input
Program akan meminta input berikut:

1. **Telegram channel URL**:  
   Masukkan URL lengkap channel atau username (contoh: `https://t.me/my_channel` atau `@my_channel`)

2. **Post ID**:  
   Masukkan ID post (angka setelah nama channel di URL)  
   Contoh: untuk URL `https://t.me/my_channel/123`, masukkan `123`

3. **Number of views**:  
   Masukkan jumlah viewer yang ingin dikirim (0 untuk tanpa batas)

4. **Select mode**:  
   Pilih mode operasi:
   - `1` Auto (download proxy otomatis)
   - `2` List (gunakan proxy dari file)
   - `3` Rotate (gunakan satu proxy dengan rotasi)

5. **Proxy input** (jika memilih mode 2 atau 3):
   - Untuk mode List: masukkan path file proxy (contoh: `proxies.txt`)
   - Untuk mode Rotate: masukkan proxy (contoh: `user:pass@ip:port` atau `ip:port`)

6. **Concurrency level**:  
   Masukkan jumlah request bersamaan (default 200)

### Contoh Penggunaan

**Mode Auto (unduh proxy otomatis):**
```
Telegram View Booster Configuration
-----------------------------------
Enter Telegram channel URL: https://t.me/my_awesome_channel
Enter post ID: 12345
Enter number of views to send: 1000

Available modes:
1. Auto (download and use proxies automatically)
2. List (use proxies from a file)
3. Rotate (use a single proxy with rotation)
Select mode (1-3): 1
Enter concurrency level (default 200): 300
```

**Mode List (gunakan proxy dari file):**
```
Telegram View Booster Configuration
-----------------------------------
Enter Telegram channel URL: @my_channel
Enter post ID: 6789
Enter number of views to send: 500

Available modes:
1. Auto (download and use proxies automatically)
2. List (use proxies from a file)
3. Rotate (use a single proxy with rotation)
Select mode (1-3): 2
Enter path to proxy file: my_proxies.txt
Enter concurrency level (default 200): 200
```

**Mode Rotate (satu proxy dengan rotasi):**
```
Telegram View Booster Configuration
-----------------------------------
Enter Telegram channel URL: my_channel
Enter post ID: 1011
Enter number of views to send: 0

Available modes:
1. Auto (download and use proxies automatically)
2. List (use proxies from a file)
3. Rotate (use a single proxy with rotation)
Select mode (1-3): 3
Enter proxy (user:pass@ip:port or ip:port): 123.45.67.89:8080
Enter concurrency level (default 200): 150
```

### 5. Memantau Proses
Setelah program berjalan, Anda akan melihat log real-time:
- Status download proxy
- Jumlah proxy yang berhasil di-load
- Status pengiriman view (sukses/gagal)
- Progress jumlah view yang telah dikirim

### 6. Menghentikan Program
Tekan `Ctrl + C` di terminal untuk menghentikan program kapan saja.

### Catatan Penting:
1. Pastikan koneksi internet stabil
2. Untuk mode Auto, program akan otomatis:
   - Mendownload proxy dari api.proxyscrape.com
   - Menyimpannya di `proxy.txt`
   - Menggunakan proxy tersebut untuk mengirim view
3. File `proxy.txt` akan terus diupdate setiap siklus
4. Program akan berhenti otomatis jika target view tercapai (jika diatur)
5. Semakin tinggi concurrency, semakin cepat proses tapi membutuhkan lebih banyak resource

Untuk masalah:
- Jika ada error SSL, pastikan sistem Anda memiliki sertifikat SSL terbaru
- Jika proxy tidak bekerja, coba gunakan proxy dari sumber lain
- Pastikan URL channel dan post ID benar
