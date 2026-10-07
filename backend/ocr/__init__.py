"""Scanner OCR — offline Hindi + English text extraction via Tesseract.

Bridge label ``tesseract-ocr`` (v5.5.x on this box), fully local, no API.
Devnagari + Latin both enabled (``hin+eng``); trained data is vendored inside
``ocr/tessdata/`` so the venue machine never phones home.

PDFs are rasterized to a first-page PNG via macOS ``sips`` before OCR; images go
straight to Tesseract. Everything is disclosed on the response, and callers can
feed the resulting text into the hybrid entity extractor unchanged.
"""
from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

# deterministic '' for stable import in tests
BASE_DIR = Path(__file__).resolve().parent
TESSDATA_DIR = BASE_DIR / "tessdata"
LANGS = "hin+eng"
ENGINE = "tesseract-ocr"
_DISCLOSURE = (
    f"{ENGINE} — offline Tesseract 5 Devanagari+Latin OCR; "
    "no external API, no data leaves the box. Vendored tessdata."
)


def _version() -> str:
    try:
        out = subprocess.run(["tesseract", "--version"], capture_output=True,
                             text=True, timeout=10).stdout or ""
        return out.splitlines()[0].strip() if out.strip() else ENGINE
    except Exception:                                     # noqa: BLE001
        return ENGINE


def extract_image_text(image_path: str | Path) -> dict:
    """Run Tesseract over one image; return text + honest metadata."""
    img = Path(image_path)
    with tempfile.TemporaryDirectory() as td:
        base = Path(td) / "out"
        proc = subprocess.run(
            ["tesseract", str(img), str(base), "-l", LANGS,
             "--tessdata-dir", str(TESSDATA_DIR)],
            capture_output=True, text=True, timeout=120)
        if proc.returncode != 0:
            raise OSError(proc.stderr.strip() or "tesseract failed")
        out = base.with_suffix(".txt")
        text = out.read_text(encoding="utf-8") if out.exists() else ""
    return {"text": text.strip(), "lang": LANGS, "engine": ENGINE,
            "version": _version(), "disclosure": _DISCLOSURE}


def pdf_to_image_png(pdf_path: str | Path, out_png: str | Path) -> Path:
    """Rasterise the first page of a PDF to PNG (macOS ``sips``)."""
    out = Path(out_png)
    proc = subprocess.run(
        ["sips", "-s", "format", "png", str(pdf_path), "--out", str(out)],
        capture_output=True, text=True, timeout=120)
    if proc.returncode != 0 or not out.exists():
        raise OSError(proc.stderr.strip() or "sips rasterize failed")
    return out


def extract_file_text(path: str | Path) -> dict:
    """OCR an image, or rasterise a PDF first page then OCR it."""
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".pdf":
        with tempfile.TemporaryDirectory() as td:
            png = pdf_to_image_png(p, Path(td) / "page.png")
            return extract_image_text(png)
    if suffix not in {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff"}:
        raise ValueError(f"unsupported image type '{suffix}'")
    return extract_image_text(p)


def available() -> bool:
    return bool(shutil.which("tesseract")) and (TESSDATA_DIR / "hin.traineddata").exists()