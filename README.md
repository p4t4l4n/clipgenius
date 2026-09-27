# ClipGenius Cutter (Windows)

Potong video YouTube jadi klip Shorts otomatis berdasarkan hasil analisis website ClipGenius.

## Persiapan (sekali saja)

1. Install Python 3.8+ (centang "Add Python to PATH" saat instalasi)
2. Install yt-dlp — buka CMD/PowerShell:
   ```
   pip install -U yt-dlp
   ```
3. Install ffmpeg:
   ```
   winget install ffmpeg
   ```
   (buka ulang CMD setelah selesai agar PATH terbaca)

Cek instalasi:
```
ffmpeg -version
yt-dlp --version
```

## Cara pakai

### Cara A — otomatis dari website (disarankan)
1. Buka https://p4t4l4n.github.io/clipgenius/ dan analisis videomu
2. Klik tombol **"Salin JSON"** di bawah daftar klip
3. Simpan isinya ke file `clips.json` di folder script ini
4. Jalankan:
   ```
   python clip_cutter.py
   ```

### Cara B — manual
```
python clip_cutter.py
```
Lalu isi link YouTube dan timestamp klip satu per satu.

## Hasil
File MP4 ada di folder `hasil_klip/`, sudah:
- Format vertikal 9:16 (1080x1920) — siap upload ke Shorts
- Ada padding 2 detik di awal & akhir
- Penamaan: `01_95_komedi_Judul Klip.mp4`

## Pengaturan
Edit bagian atas `clip_cutter.py`:
- `VERTICAL = False`  -> potong tanpa crop vertikal
- `PAD_START / PAD_END` -> ubah padding detik
- `CRF = "18"` -> kualitas lebih tinggi (file lebih besar)

## Catatan
- Semua berjalan di komputermu sendiri, gratis, tanpa batas
- Video sumber diunduh dulu (butuh ruang disk), bisa dihapus di akhir
