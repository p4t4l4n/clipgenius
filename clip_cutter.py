#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ClipGenius Cutter - Windows
Ambil link YouTube + daftar klip hasil analisis website, lalu potong jadi file MP4 siap upload.

Cara pakai:
  1. Dari website ClipGenius, klik tombol "Salin JSON" di bawah daftar klip.
  2. Simpan hasilnya ke file clips.json di folder yang sama dengan script ini.
  3. Jalankan:  python clip_cutter.py
     (atau)     python clip_cutter.py clips.json
     (atau)     python clip_cutter.py --url "https://youtube.com/watch?v=xxx"
                -> tanpa clips.json, akan minta input timestamp manual

Butuh: Python 3.8+, ffmpeg & yt-dlp di PATH.
"""

import json, os, re, subprocess, sys, shutil, platform

# ---------- Konfigurasi ----------
OUT_DIR   = "hasil_klip"
PAD_START = 2      # detik tambahan sebelum klip (biar hook nggak kepotong)
PAD_END   = 2      # detik tambahan sesudah klip
VERTICAL  = True   # True = crop ke 9:16 (YouTube Shorts). False = potong apa adanya
CRF       = "20"   # kualitas (18-23 bagus, makin kecil makin bagus & besar)
# ----------------------------------

C = {"g":"\033[92m","y":"\033[93m","r":"\033[91m","c":"\033[96m","w":"\033[0m"}
if platform.system() == "Windows":
    os.system("")  # aktifkan warna ANSI di Windows 10+

def warn(t): print(C["y"] + t + C["w"])
def ok(t):   print(C["g"] + t + C["w"])
def err(t):  print(C["r"] + t + C["w"])
def info(t): print(C["c"] + t + C["w"])

def have(cmd):
    return shutil.which(cmd) is not None

def run(cmd, **kw):
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", **kw)

def check_deps():
    missing = []
    if not have("ffmpeg"): missing.append("ffmpeg")
    if not have("yt-dlp"): missing.append("yt-dlp")
    if missing:
        err("ERROR: alat berikut belum terpasang: " + ", ".join(missing))
        print()
        info("Cara pasang di Windows:")
        if "yt-dlp" in missing:
            print("  yt-dlp  ->  pip install -U yt-dlp")
        if "ffmpeg" in missing:
            print("  ffmpeg  ->  winget install ffmpeg")
            print("            atau download di https://ffmpeg.org/download.html")
            print("            lalu tambahkan folder bin-nya ke PATH")
        print()
        sys.exit(1)

def hhmmss(s):
    s = max(0, int(s))
    h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f"{h:02d}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"

def safe(name, maxlen=60):
    name = re.sub(r'[<>:"/\\|?*]', "", str(name))
    name = re.sub(r"\s+", " ", name).strip().rstrip(".")
    return (name[:maxlen] or "klip")

def load_clips(path):
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, list):
        url, clips = None, data
    else:
        url = data.get("url") or data.get("video_url")
        clips = data.get("clips", [])
    out = []
    for c in clips:
        st = c.get("start_sec", c.get("start"))
        en = c.get("end_sec", c.get("end"))
        if st is None or en is None: continue
        st, en = float(st), float(en)
        if en <= st: continue
        out.append({
            "start": st, "end": en,
            "score": c.get("score", 0),
            "type":  (c.get("type") or "klip").lower(),
            "title": c.get("title") or f"Klip {len(out)+1}",
        })
    return url, out

def get_video(url, tmp="source_video"):
    info("Mengunduh video dari YouTube...")
    tmpl = tmp + ".%(ext)s"
    cmd = ["yt-dlp", "-f", "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best",
           "-o", tmpl, "--no-playlist", "--merge-output-format", "mp4", url]
    r = run(cmd)
    if r.returncode != 0:
        err("Gagal mengunduh video:")
        print((r.stderr or r.stdout)[-1500:])
        sys.exit(1)
    found = [f for f in os.listdir(".") if f.startswith(tmp + ".")]
    if not found:
        err("File video tidak ditemukan setelah unduh.")
        sys.exit(1)
    ok("Video berhasil diunduh: " + found[0])
    return found[0]

def duration(path):
    r = run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", path])
    try: return float(r.stdout.strip())
    except: return None

def cut(src, clip, idx, total, outdir):
    total_dur = duration(src)
    st = max(0, clip["start"] - PAD_START)
    en = clip["end"] + PAD_END
    if total_dur and en > total_dur: en = total_dur
    if total_dur and st >= total_dur:
        err(f"  [{idx}/{total}] dilewati: timestamp melebihi durasi video")
        return None
    dur = en - st
    if dur < 1:
        err(f"  [{idx}/{total}] dilewati: durasi terlalu pendek")
        return None

    name = safe(f"{idx:02d}_{clip['score']}_{clip['type']}_{clip['title']}") + ".mp4"
    out  = os.path.join(outdir, name)

    vf = []
    if VERTICAL:
        # crop tengah ke 9:16 lalu scale 1080x1920
        vf.append("crop=ih*9/16:ih,scale=1080:1920:flags=lanczos")
        vf.append("setsar=1")

    cmd = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
           "-ss", hhmmss(st), "-i", src, "-t", str(int(dur))]
    if vf:
        cmd += ["-vf", ",".join(vf)]
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-crf", CRF,
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out]

    print(f"  [{idx}/{total}] {clip['title'][:45]} ({hhmmss(st)}-{hhmmss(en)}, {int(dur)}s) skor {clip['score']}")
    r = run(cmd)
    if r.returncode != 0 or not os.path.exists(out):
        err("     gagal memotong: " + (r.stderr or "")[:300])
        return None
    size = os.path.getsize(out) / (1024*1024)
    ok(f"     OK -> {name}  ({size:.1f} MB)")
    return out

def main():
    print(C["c"] + "="*60 + C["w"])
    print(C["c"] + "   ClipGenius Cutter - Potong Video Shorts Otomatis" + C["w"])
    print(C["c"] + "="*60 + C["w"] + "\n")

    check_deps()
    os.makedirs(OUT_DIR, exist_ok=True)

    arg_file = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else "clips.json"
    data = load_clips(arg_file)

    if data is None:
        warn(f"File '{arg_file}' tidak ditemukan.\n")
        info("Mode manual: kamu akan diminta mengisi data klip sendiri.")
        url = input("Link YouTube      : ").strip()
        if not url:
            err("Link tidak boleh kosong."); sys.exit(1)
        clips = []
        print("\nMasukkan klip (kosongkan judul untuk selesai):")
        n = 1
        while True:
            print(f"\n--- Klip #{n} ---")
            t = input("Judul (enter=selesai): ").strip()
            if not t: break
            try:
                s = input("Mulai (detik atau m:ss): ").strip()
                e = input("Selesai (detik atau m:ss): ").strip()
                def pv(x):
                    return float(x) if ":" not in x else sum(int(p)*60**i for i,p in enumerate(reversed(x.split(":"))))
                st, en = pv(s), pv(e)
                if en <= st:
                    err("  Selesai harus lebih besar dari mulai."); continue
                typ = input("Tipe (hook/komedi/emosi) [klip]: ").strip() or "klip"
                clips.append({"start": st, "end": en, "score": 0, "type": typ, "title": t})
                n += 1
            except ValueError:
                err("  Format waktu salah, coba lagi.")
        if not clips:
            err("Tidak ada klip yang dimasukkan."); sys.exit(1)
    else:
        url, clips = data
        if not url:
            url = input("Link YouTube : ").strip()
        if not clips:
            err("Tidak ada klip di file JSON."); sys.exit(1)
        ok(f"Memuat {len(clips)} klip dari {arg_file}\n")

    src = get_video(url)
    print()
    info(f"Memotong {len(clips)} klip (mode {'VERTIKAL 9:16' if VERTICAL else 'ORIGINAL'})...\n")

    made = []
    for i, c in enumerate(clips, 1):
        p = cut(src, c, i, len(clips), OUT_DIR)
        if p: made.append(p)

    print()
    print(C["c"] + "="*60 + C["w"])
    if made:
        ok(f"SELESAI! {len(made)}/{len(clips)} klip berhasil dibuat.")
        info(f"Lokasi: {os.path.abspath(OUT_DIR)}")
        try:
            if platform.system() == "Windows": os.startfile(os.path.abspath(OUT_DIR))
            elif platform.system() == "Darwin": subprocess.run(["open", OUT_DIR])
            else: subprocess.run(["xdg-open", OUT_DIR])
        except Exception: pass
    else:
        err("Tidak ada klip yang berhasil dibuat.")
    keep = input("\nHapus video sumber yang besar? (y/n) [n]: ").strip().lower()
    if keep == "y":
        try:
            os.remove(src); ok("Video sumber dihapus.")
        except Exception as e: err("Gagal menghapus: " + str(e))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nDibatalkan.")
