"""Klavar scan server: turns a photo or PDF of printed sheet music into MusicXML.

Uses oemer (MIT licensed optical music recognition). Run with Docker (see README)
or directly with:  uvicorn app:app --host 0.0.0.0 --port 8000
"""
import asyncio
import glob
import io
import os
import shutil
import subprocess
import tempfile

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

TOKEN = os.environ.get("SCAN_TOKEN", "")            # optional access key
MAX_MB = int(os.environ.get("MAX_UPLOAD_MB", "25"))
WORKERS = int(os.environ.get("SCAN_WORKERS", "1"))   # scans are heavy; run one at a time by default
TIMEOUT = int(os.environ.get("SCAN_TIMEOUT", "900"))

app = FastAPI(title="Klavar scan server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
slots = asyncio.Semaphore(WORKERS)


@app.get("/health")
def health():
    return {"ok": True}


def run_oemer(image_path: str, out_dir: str) -> str:
    proc = subprocess.run(["oemer", image_path, "-o", out_dir],
                          capture_output=True, text=True, timeout=TIMEOUT)
    found = glob.glob(os.path.join(out_dir, "*.musicxml")) + glob.glob(os.path.join(out_dir, "*.xml"))
    if not found:
        tail = (proc.stderr or proc.stdout or "no output").strip()[-600:]
        raise RuntimeError(tail)
    with open(found[0], encoding="utf-8") as f:
        return f.read()


@app.post("/scan")
async def scan(file: UploadFile = File(...), x_scan_token: str | None = Header(default=None)):
    if TOKEN and x_scan_token != TOKEN:
        raise HTTPException(401, "Wrong or missing access key")
    data = await file.read()
    if not data:
        raise HTTPException(400, "The upload was empty")
    if len(data) > MAX_MB * 1024 * 1024:
        raise HTTPException(413, f"The file is larger than {MAX_MB} MB")

    work = tempfile.mkdtemp(prefix="klavar-")
    try:
        if data[:4] == b"%PDF":
            from pdf2image import convert_from_bytes
            pages = convert_from_bytes(data, dpi=300, first_page=1, last_page=1)
            image_path = os.path.join(work, "page1.png")
            pages[0].convert("RGB").save(image_path)
        else:
            from PIL import Image, ImageOps
            try:
                im = Image.open(io.BytesIO(data))
            except Exception:
                raise HTTPException(415, "That file is not an image or PDF")
            im = ImageOps.exif_transpose(im).convert("RGB")   # respect phone rotation
            im.thumbnail((3000, 3000))                         # very large photos only slow things down
            image_path = os.path.join(work, "photo.png")
            im.save(image_path)

        async with slots:
            xml = await run_in_threadpool(run_oemer, image_path, work)
        return Response(content=xml, media_type="application/vnd.recordare.musicxml+xml")
    except HTTPException:
        raise
    except subprocess.TimeoutExpired:
        raise HTTPException(504, "Reading the music took too long. Try a smaller or clearer photo.")
    except Exception as e:
        raise HTTPException(422, f"Could not read music from this image: {e}")
    finally:
        shutil.rmtree(work, ignore_errors=True)
