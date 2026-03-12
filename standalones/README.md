# move_anomalie — Standalone utility

Moves digitization files matching anomaly object IDs into an `Anomalie/` subfolder,
preserving the original directory structure.

Replaces the old `move_anomalie.bat` (Windows) and `move_anomalie.command` (macOS)
with a single Python source that builds to a standalone binary on any platform.

---

## What it does

1. Reads `anomalie.txt` — one entry per line, format: `OBJ_ID | STATO`
2. Scans the folder it lives in, recursively
3. Matches files by stem (case-insensitive) against the ID list
4. Offers a menu:
   - **Dry-run** — lists matches, writes `risultati_anomalie.txt`, moves nothing
   - **Execute** — moves matched files into `Anomalie/<original_path>/`
   - **Exit**

### Example

```
images/
  E033006.jpg        →  images/Anomalie/E033006.jpg
  subdir/F041332.tif →  images/Anomalie/subdir/F041332.tif
  unrelated.jpg      →  (untouched)
```

---

## For operators (no Python required)

Download the pre-built binary for your platform and place it **in the same folder as the images**:

| Platform | Binary          |
|----------|-----------------|
| macOS    | `move_anomalie` |
| Windows  | `move_anomalie.exe` |
| Linux    | `move_anomalie` |

Also place `anomalie.txt` in the same folder, then run the binary.

> Binaries are platform-specific — the macOS build won't run on Windows and vice versa.

---

## For developers

### Project layout

```
standalones/
  move_anomalie.py          # single source of truth
  move_anomalie.spec        # PyInstaller build config
  build.sh                  # build script for macOS / Linux
  build.bat                 # build script for Windows
  requirements-build.txt    # build dependencies (pyinstaller only)
  tests/
    conftest.py
    test_move_anomalie.py   # 26 unit tests
```

### Setup

```bash
cd standalones/
python -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install pytest pyinstaller    # or: pip install -r requirements-build.txt
```

### Run tests

```bash
python -m pytest tests/ -v
```

### Build the binary

**macOS / Linux:**
```bash
bash build.sh
# → dist/move_anomalie
```

**Windows:**
```bat
build.bat
# → dist\move_anomalie.exe
```

Build artifacts (`build/`, `dist/`) are local only — not committed to the repo.

### Run directly (no build needed)

```bash
python move_anomalie.py                # uses anomalie.txt in the same folder
python move_anomalie.py my_ids.txt    # custom input file
```
