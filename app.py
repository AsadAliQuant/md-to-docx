"""
md-to-docx: API backend for the bidirectional Markdown <-> DOCX converter.
Backend uses pandoc (must be installed: winget install --id JohnMacFarlane.Pandoc).
UI lives in frontend/ (Astro, deployed separately - see DEPLOY.md).
Run: python app.py  ->  API at http://127.0.0.1:5000 (/health, /convert)
"""
import io
import os
import shutil
import subprocess
import uuid
import zipfile
from pathlib import Path
from flask import Flask, request, send_file, jsonify
from flask_cors import CORS

BASE_DIR = Path(__file__).parent.resolve()
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "outputs"
UPLOAD_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

ALLOWED_EXT = {".md", ".markdown", ".txt", ".docx"}
MAX_FILE_MB = 25       # per-file limit (also enforced client-side)
MAX_REQUEST_MB = 200   # overall request cap, so bulk uploads of many files aren't blocked

# Astro frontend is hosted separately (Cloudflare Pages), so /convert and /health
# need CORS. Set ALLOWED_ORIGINS (comma-separated) in prod; defaults cover local dev.
ALLOWED_ORIGINS = os.environ.get(
    "ALLOWED_ORIGINS", "http://localhost:4321,http://127.0.0.1:4321"
).split(",")

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = MAX_REQUEST_MB * 1024 * 1024
CORS(app, resources={r"/convert": {"origins": ALLOWED_ORIGINS}, r"/health": {"origins": ALLOWED_ORIGINS}})


def pandoc_available() -> bool:
    return shutil.which("pandoc") is not None


def unique_output_name(stem: str, out_ext: str, used_lower: set) -> str:
    """Return '<stem><out_ext>', or '<stem> (1)<out_ext>', '<stem> (2)<out_ext>', ...
    if that name was already used earlier in this batch (case-insensitive match)."""
    name = f"{stem}{out_ext}"
    if name.lower() not in used_lower:
        used_lower.add(name.lower())
        return name
    n = 1
    while True:
        candidate = f"{stem} ({n}){out_ext}"
        if candidate.lower() not in used_lower:
            used_lower.add(candidate.lower())
            return candidate
        n += 1


@app.route("/")
def index():
    # UI is the separately-hosted Astro frontend (see DEPLOY.md); this backend is API-only.
    return jsonify({"service": "md-to-docx-api", "pandoc": pandoc_available()})


@app.route("/health")
def health():
    return jsonify({"pandoc": pandoc_available()})


@app.route("/convert", methods=["POST"])
def convert():
    if not pandoc_available():
        return jsonify({"error": "Pandoc not found. Install: winget install --id JohnMacFarlane.Pandoc"}), 500

    # Accept the new multi-file field ("files") and fall back to the old
    # single-file field ("file") for backward compatibility.
    files = request.files.getlist("files") or request.files.getlist("file")
    files = [f for f in files if f and f.filename]
    if not files:
        return jsonify({"error": "No file uploaded"}), 400

    for f in files:
        ext = Path(f.filename).suffix.lower()
        if ext not in ALLOWED_EXT:
            return jsonify({"error": f"Unsupported file type: {f.filename}"}), 400

    job_id = uuid.uuid4().hex[:8]
    job_upload_dir = UPLOAD_DIR / job_id
    job_output_dir = OUTPUT_DIR / job_id
    job_upload_dir.mkdir(parents=True, exist_ok=True)
    job_output_dir.mkdir(parents=True, exist_ok=True)

    used_names = set()
    converted = []  # list of (dst_path, download_name)

    try:
        for f in files:
            ext = Path(f.filename).suffix.lower()
            stem = Path(f.filename).stem
            src = job_upload_dir / f"{uuid.uuid4().hex[:8]}{ext}"
            f.save(src)

            if ext == ".docx":
                from_fmt, to_fmt, out_ext = "docx", "markdown", ".md"
            else:  # .md, .markdown, .txt
                from_fmt, to_fmt, out_ext = "markdown", "docx", ".docx"

            out_name = unique_output_name(stem, out_ext, used_names)
            dst = job_output_dir / out_name

            try:
                result = subprocess.run(
                    ["pandoc", str(src), "-o", str(dst), f"--from={from_fmt}", f"--to={to_fmt}"],
                    capture_output=True, text=True, timeout=60,
                )
            except subprocess.TimeoutExpired:
                return jsonify({"error": f"Conversion timed out: {f.filename}"}), 500

            if result.returncode != 0:
                return jsonify({"error": f"Pandoc failed on {f.filename}", "stderr": result.stderr}), 500

            converted.append((dst, out_name))

        # Single file: read it into memory and remove the on-disk copy right
        # away, then stream from memory. (send_file(path) on Windows keeps
        # the file open across the response, so on-disk cleanup can't happen
        # via after_this_request without racing a PermissionError.)
        if len(converted) == 1:
            dst, out_name = converted[0]
            data = dst.read_bytes()
            return send_file(io.BytesIO(data), as_attachment=True, download_name=out_name)

        # Multiple files: bundle into one zip, each entry named after its source file.
        zip_path = OUTPUT_DIR / f"{job_id}.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for dst, out_name in converted:
                zf.write(dst, arcname=out_name)

        zip_data = zip_path.read_bytes()
        zip_path.unlink(missing_ok=True)
        return send_file(io.BytesIO(zip_data), as_attachment=True, download_name="converted-files.zip")
    finally:
        # Source uploads are only needed while pandoc runs synchronously above.
        # Output is read into memory before this runs (both success branches
        # above), so it's always safe to remove here too - this also covers
        # the error paths (pandoc failure/timeout), which return early and
        # would otherwise leak a partially-populated job_output_dir.
        shutil.rmtree(job_upload_dir, ignore_errors=True)
        shutil.rmtree(job_output_dir, ignore_errors=True)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    print("=" * 60)
    print(" md-to-docx running")
    print(f" Pandoc detected: {pandoc_available()}")
    print(f" Open: http://127.0.0.1:{port}")
    print("=" * 60)
    app.run(host="0.0.0.0", port=port, debug=False)
