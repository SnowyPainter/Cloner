# 🚀 Quick Start

---

## ✨ Why Source Code?

> _This pipeline is provided as source code instead of a standalone executable, intentionally:_

- **No massive binaries:** Avoids huge (4–8GB) executables  
- **Seamless GPU/CUDA support:** Easy to match your hardware  
- **Simple model upgrades:** Update models as you wish  
- **Studio-proven workflow:** Mirrors internal studio tools  

---

## 🛠️ Requirements

- **Python:** 3.10+
- **Tools:** `yt-dlp` and `ffmpeg` on your `PATH`
- **PyAV deps:** ffmpeg libraries for your OS
- **NLLB translation (optional):**  
  `transformers`, `torch`, `sentencepiece`

---

## ⚡ Install

```bash
pip install -e .
```

---

## ▶️ Basic Usage

```bash
reels ingest https://www.youtube.com/watch?v=VIDEO_ID
reels build VIDEO_ID
```

---

## 🌏 With Translation

```bash
# Ingest and translate to Korean (ko)
reels ingest https://www.youtube.com/watch?v=VIDEO_ID --translate ko

# Build with translated subtitles
reels build VIDEO_ID --translated-lang ko
```

---

## 📂 Output

Output video:  
```
workspace/assets/<ASSET_ID>/output/reel_60s.mp4
```

_All other files (subtitles, metadata, etc.) are stored under `workspace/assets/<ASSET_ID>/`._

---
