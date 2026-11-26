"""Download the Kokoro fallback voice (Apache-2.0) once; GitHub Actions caches it. A failed download only warns:
edge-tts does not need it, and a run where both voices fail stops with a clear message in voice.py.

Integrity: models/kokoro.lock (committed) pins each file's SHA-256. When the lock has a hash, a file that does not
match is deleted and the voice is reported unavailable. Record hashes once with:  python -m flatframe.fetch_models --lock
"""
import hashlib
import json
import sys
import urllib.request

from .common import MODELS, ROOT, log

BASE = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = {"kokoro.onnx": "kokoro-v1.0.int8.onnx", "voices.bin": "voices-v1.0.bin"}
LOCK = ROOT / "kokoro.lock.json"


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main(argv):
    MODELS.mkdir(exist_ok=True)
    lock = json.loads(LOCK.read_text()) if LOCK.exists() else {}
    for local, remote in FILES.items():
        dest = MODELS / local
        if not (dest.exists() and dest.stat().st_size > 1_000_000):
            tmp = dest.with_suffix(".part")
            try:
                log(f"Downloading {remote}")
                urllib.request.urlretrieve(BASE + remote, tmp)
                tmp.replace(dest)
            except OSError as e:
                tmp.unlink(missing_ok=True)
                log(f"Kokoro download failed ({e}); the fallback voice is unavailable this run", "WARN")
                continue
        digest = sha256(dest)
        want = lock.get(local)
        if want and digest != want:
            dest.unlink()
            log(f"{local}: SHA-256 {digest[:12]} does not match the lock {want[:12]}; deleted (fallback voice off)", "WARN")
        elif not want:
            log(f"{local}: no pinned hash yet (sha256 {digest}); run with --lock to pin it", "WARN")
            lock[local] = digest
    if "--lock" in argv:
        LOCK.write_text(json.dumps(lock, indent=2) + "\n")
        log(f"wrote {LOCK.name}")


if __name__ == "__main__":
    main(sys.argv[1:])
