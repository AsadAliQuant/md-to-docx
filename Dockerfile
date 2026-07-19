FROM python:3.12-slim

# Pandoc is the actual conversion engine (app.py shells out to it) — apt has a
# recent-enough build for markdown->docx, no need for the upstream .deb.
RUN apt-get update && apt-get install -y --no-install-recommends pandoc \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

# app.py also creates these at import time (UPLOAD_DIR/OUTPUT_DIR .mkdir),
# but they live on Cloud Run's ephemeral in-memory filesystem either way —
# nothing written here survives a restart or scale-to-zero.
RUN mkdir -p uploads outputs

# Cloud Run injects $PORT (defaults to 8080 locally); gunicorn must bind to it.
# --workers 1 --threads 4: pandoc subprocess calls release the GIL while
# waiting, so threads handle modest concurrency without multiplying memory.
# --timeout 90: exceeds the 60s pandoc subprocess timeout in app.py so gunicorn
# never kills a worker mid-conversion.
CMD exec gunicorn --bind 0.0.0.0:${PORT:-8080} --workers 1 --threads 4 --timeout 90 app:app
