# DermaScan Desktop (offline)

Python + PySide6 + OpenCV + Pillow + TFLite. Two tabs: **Learn** (offline feed) and **Scan** (upload / drag-drop / webcam).

## Before building
1. Put your model at `model/model_quant_fp16.tflite` (not included).
2. Put lesion photos in `assets/feed_images/<class>/` and paper PDFs in `assets/papers/`.
3. Edit `disease_feed.json`: fill each post's `images` and `paper` fields (paths are relative, e.g. `assets/feed_images/mel/mel_001.jpg`). Add more posts per class by copying a post and changing `id`.

## Run / build (Windows)
- `run_dev.bat` – run from source.
- `build_exe.bat` – creates `dist\DermaScan\DermaScan.exe` (folder build; ship the whole `DermaScan` folder).
  Files placed next to the .exe (e.g. a newer `disease_feed.json` or `model\`) override the bundled ones.

## Notes
- Preprocessing: 224x224 RGB, `(pixel/127.5) - 1`. Label order in `labels.txt`: akiec, bcc, bkl, df, mel, nv, vasc.
- Result below 50% confidence shows "Inconclusive" (`CONFIDENCE_THRESHOLD` in `ui.py`).
- If `ai-edge-litert` won't install on your Python version, replace it in `requirements.txt` with `tensorflow` (and drop `--collect-all ai_edge_litert` from `build_exe.bat`).
- Educational tool only; not a diagnostic device.
