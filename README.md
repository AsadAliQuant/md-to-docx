# md-to-docx

Local Markdown -> DOCX converter. Web UI in the browser, Pandoc under the hood.

## Prerequisites

Pandoc (you already have this):

```
winget install --id JohnMacFarlane.Pandoc
```

Python 3.9+.

## Run it

Double-click **`start.bat`**. First run creates a venv and installs Flask; every run after that just starts the server and opens the browser to `http://127.0.0.1:5000`.

Or manually:

```
pip install -r requirements.txt
python app.py
```

## Use

1. Open http://127.0.0.1:5000
2. Drag a `.md` file onto the drop zone (or click to pick one)
3. `.docx` downloads automatically

Nothing leaves your machine. Files are 127.0.0.1 only.

## What's happening

The backend runs exactly the command you tested manually:

```
pandoc input.md -o output.docx
```

## Files

```
md-to-docx/
├── app.py              # Flask backend
├── requirements.txt    # Flask
├── start.bat           # One-click launcher
├── templates/
│   └── index.html      # UI
├── uploads/            # temp
└── outputs/            # generated .docx
```

## Stop the server

Ctrl+C in the terminal window.
