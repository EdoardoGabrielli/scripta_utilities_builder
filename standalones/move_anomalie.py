#!/usr/bin/env python3
"""
move_anomalie.py

Moves files matching anomaly object IDs into an Anomalie/ subfolder,
preserving the original directory structure.

Input file format: one entry per line as "OBJ_ID | STATO"
Only the OBJ_ID (before the pipe) is used for matching.

Usage:
    python move_anomalie.py          # opens GUI, uses anomalie.txt in script dir
    python move_anomalie.py --smoke  # headless self-test (used by CI)
"""
from __future__ import annotations

import shutil
import sys
import tempfile
import threading
from datetime import datetime
from pathlib import Path

import tkinter as tk
from tkinter import filedialog, messagebox, ttk


# ── Pure functions (unit-testable, no side effects) ───────────────────────────

def load_ids(id_file: Path) -> set:
    """Parse ID file and return a lowercase set of IDs (part before '|')."""
    ids = set()
    with id_file.open(encoding="utf-8") as fh:
        for line in fh:
            part = line.split("|")[0].strip()
            if part:
                ids.add(part.lower())
    return ids


def get_target(src: Path, base_dir: Path, anomalie_dir: Path) -> Path:
    """Compute destination path inside anomalie_dir, preserving subdirectory."""
    return anomalie_dir / src.relative_to(base_dir)


def find_matches(
    base_dir: Path,
    ids: set,
    anomalie_dir: Path,
    on_progress=None,
) -> tuple:
    """
    Scan base_dir for files whose stem (case-insensitive) is in ids.
    Skips files already inside anomalie_dir.
    Calls on_progress(n) every 500 files scanned if provided.

    Returns:
        matches    - list of (src, dst) Path pairs
        scan_count - total files examined
    """
    matches = []
    scan_count = 0

    for src in base_dir.rglob("*"):
        if not src.is_file():
            continue
        # Skip files already inside Anomalie/
        try:
            src.relative_to(anomalie_dir)
            continue
        except ValueError:
            pass

        scan_count += 1
        if on_progress and scan_count % 500 == 0:
            on_progress(scan_count)

        if src.stem.lower() in ids:
            matches.append((src, get_target(src, base_dir, anomalie_dir)))

    return matches, scan_count


def move_files(matches: list) -> tuple:
    """
    Move each (src, dst) pair. Creates destination directories as needed.
    Uses shutil.move for cross-platform safety (handles cross-filesystem moves).

    Returns:
        success_count - number of successfully moved files
        errors        - list of error messages for failed moves
    """
    success = 0
    errors = []
    for src, dst in matches:
        dst.parent.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(src), str(dst))
            success += 1
        except (OSError, shutil.Error) as exc:
            errors.append(f"{src}: {exc}")
    return success, errors


# ── GUI ───────────────────────────────────────────────────────────────────────

def get_base_dir() -> Path:
    """Return the directory containing the executable (or script)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent


_HEADER  = "#2c3e50"
_BG      = "#f5f5f0"
_CARD    = "#ffffff"
_BORDER  = "#dde1e7"
_TEXT    = "#2d3748"
_MUTED   = "#8a9bb0"
_FG      = "#ffffff"
_BTN_DRY = "#5b7fa6"   # muted steel blue
_BTN_DRY2= "#4a6d91"
_BTN_EXE = "#4a8c6f"   # muted sage green
_BTN_EXE2= "#3a7a5e"


class App(tk.Tk):
    def __init__(self, base_dir: Path) -> None:
        super().__init__()
        self.base_dir = base_dir
        self.title("DIGISCRIPTA – Spostamento Anomalie")
        self.resizable(True, True)
        self.minsize(580, 480)
        self.configure(bg=_BG)

        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("Slim.Vertical.TScrollbar",
            troughcolor=_BG, background=_BORDER,
            arrowcolor=_MUTED, bordercolor=_BG, lightcolor=_BG, darkcolor=_BG,
        )
        style.map("Slim.Vertical.TScrollbar",
            background=[("active", _MUTED)],
        )
        self._build_ui()

    def _build_ui(self) -> None:
        # ── Header ────────────────────────────────────────────────────────────
        header = tk.Frame(self, bg=_HEADER, pady=16)
        header.pack(fill="x")
        tk.Label(header, text="Digiscripta", bg=_HEADER, fg=_FG,
                 font=("Helvetica", 16, "bold")).pack()
        tk.Label(header, text="Spostamento file Anomalie", bg=_HEADER, fg=_MUTED,
                 font=("Helvetica", 9)).pack()

        body = tk.Frame(self, bg=_BG)
        body.pack(fill="both", expand=True, padx=20, pady=14)

        # ── Working folder ────────────────────────────────────────────────────
        tk.Label(body, text="Cartella di lavoro", bg=_BG, fg=_MUTED,
                 font=("Helvetica", 8)).pack(anchor="w")
        folder_card = tk.Frame(body, bg=_CARD,
                               highlightthickness=1, highlightbackground=_BORDER)
        folder_card.pack(fill="x", pady=(3, 12))
        tk.Label(folder_card, text=str(self.base_dir), bg=_CARD, fg=_TEXT,
                 font=("Helvetica", 10), anchor="w", padx=12, pady=9).pack(fill="x")

        # ── File picker ───────────────────────────────────────────────────────
        tk.Label(body, text="File anomalie", bg=_BG, fg=_MUTED,
                 font=("Helvetica", 8)).pack(anchor="w")
        picker_frame = tk.Frame(body, bg=_BG)
        picker_frame.pack(fill="x", pady=(3, 14))

        self._id_file_var = tk.StringVar(value=str(self.base_dir / "anomalie.txt"))
        tk.Entry(
            picker_frame, textvariable=self._id_file_var,
            font=("Helvetica", 10), relief="flat", bg=_CARD, fg=_TEXT,
            highlightthickness=1, highlightbackground=_BORDER,
            highlightcolor=_BTN_DRY, insertbackground=_TEXT,
        ).pack(side="left", fill="x", expand=True, ipady=7, padx=(0, 6))
        tk.Button(
            picker_frame, text="Sfoglia…", command=self._browse,
            bg=_CARD, fg=_TEXT, relief="flat", font=("Helvetica", 10),
            highlightthickness=1, highlightbackground=_BORDER,
            activebackground=_BG, cursor="hand2", padx=10,
        ).pack(side="left", ipady=7)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_frame = tk.Frame(body, bg=_BG)
        btn_frame.pack(fill="x", pady=(0, 14))
        self._btn_dry = tk.Button(
            btn_frame, text="Dry run", command=self._start_dry,
            bg=_BTN_DRY, fg=_FG, activebackground=_BTN_DRY2, activeforeground=_FG,
            relief="flat", font=("Helvetica", 10), cursor="hand2", padx=22,
        )
        self._btn_dry.pack(side="left", ipady=8, padx=(0, 8))
        self._btn_exec = tk.Button(
            btn_frame, text="Esegui spostamento", command=self._start_exec,
            bg=_BTN_EXE, fg=_FG, activebackground=_BTN_EXE2, activeforeground=_FG,
            relief="flat", font=("Helvetica", 10), cursor="hand2", padx=22,
        )
        self._btn_exec.pack(side="left", ipady=8)

        # ── Log ───────────────────────────────────────────────────────────────
        tk.Label(body, text="Log", bg=_BG, fg=_MUTED,
                 font=("Helvetica", 8)).pack(anchor="w")
        log_outer = tk.Frame(body, bg=_CARD,
                             highlightthickness=1, highlightbackground=_BORDER)
        log_outer.pack(fill="both", expand=True, pady=(3, 0))
        log_inner = tk.Frame(log_outer, bg=_CARD)
        log_inner.pack(fill="both", expand=True)

        self._log = tk.Text(
            log_inner, state="disabled", wrap="word",
            font=("Courier", 10), bg=_CARD, fg=_TEXT,
            relief="flat", borderwidth=0, padx=10, pady=8,
            selectbackground=_BTN_DRY, selectforeground=_FG,
        )
        scrollbar = ttk.Scrollbar(log_inner, orient="vertical",
                                  style="Slim.Vertical.TScrollbar",
                                  command=self._log.yview)
        self._log.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y", padx=(0, 2), pady=4)
        self._log.pack(side="left", fill="both", expand=True)

        # ── Status bar ────────────────────────────────────────────────────────
        self._status_var = tk.StringVar(value="Pronto.")
        status_bar = tk.Frame(self, bg=_HEADER)
        status_bar.pack(fill="x", side="bottom")
        tk.Label(status_bar, textvariable=self._status_var,
                 bg=_HEADER, fg=_MUTED, font=("Helvetica", 9),
                 anchor="w", padx=14, pady=5).pack(fill="x")

    def _browse(self) -> None:
        path = filedialog.askopenfilename(
            title="Seleziona file anomalie",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")],
        )
        if path:
            self._id_file_var.set(path)

    def _log_append(self, text: str) -> None:
        self._log.configure(state="normal")
        self._log.insert("end", text + "\n")
        self._log.see("end")
        self._log.configure(state="disabled")

    def _set_busy(self, busy: bool) -> None:
        if busy:
            self._btn_dry.configure(state="disabled", bg=_MUTED, cursor="")
            self._btn_exec.configure(state="disabled", bg=_MUTED, cursor="")
        else:
            self._btn_dry.configure(state="normal", bg=_BTN_DRY, cursor="hand2")
            self._btn_exec.configure(state="normal", bg=_BTN_EXE, cursor="hand2")

    def _load_ids(self) -> set | None:
        id_file = Path(self._id_file_var.get())
        if not id_file.is_absolute():
            id_file = self.base_dir / id_file
        if not id_file.exists():
            messagebox.showerror("Errore", f"File non trovato:\n{id_file}")
            return None
        ids = load_ids(id_file)
        if not ids:
            messagebox.showerror("Errore", f"Nessun ID trovato in:\n{id_file}")
            return None
        return ids

    def _start_dry(self) -> None:
        ids = self._load_ids()
        if ids is None:
            return
        self._set_busy(True)
        threading.Thread(target=self._dry_worker, args=(ids,), daemon=True).start()

    def _dry_worker(self, ids: set) -> None:
        anomalie_dir = self.base_dir / "Anomalie"
        results_file = self.base_dir / "risultati_anomalie.txt"

        self.after(0, self._log_append, f"Dry run — {len(ids)} ID caricati. Scansione...")
        self.after(0, self._status_var.set, "Scansione in corso…")

        matches, scan_count = find_matches(
            self.base_dir, ids, anomalie_dir,
            on_progress=lambda n: self.after(0, self._log_append, f"  {n} file scansionati…"),
        )

        with results_file.open("w", encoding="utf-8") as fh:
            fh.write(f"RISULTATI DRY-RUN - {datetime.now():%Y-%m-%d %H:%M:%S}\n")
            fh.write(f"Cartella: {self.base_dir}\n\n")
            for i, (src, dst) in enumerate(matches, 1):
                fh.write(f"{i}. {src.name}  -->  {dst}\n")
            fh.write(f"\nTotale: {len(matches)} file da spostare su {len(ids)} ID in lista\n")

        self.after(0, self._log_append, f"  {scan_count} file scansionati, {len(matches)} trovati.")
        self.after(0, self._log_append, f"  Risultati in: {results_file.name}")
        self.after(0, self._status_var.set, f"Dry run completato — {len(matches)} file trovati.")
        self.after(0, self._set_busy, False)

    def _start_exec(self) -> None:
        ids = self._load_ids()
        if ids is None:
            return
        if not messagebox.askyesno(
            "Conferma",
            'I file verranno spostati nella cartella "Anomalie/".\n\nConfermi?',
        ):
            return
        self._set_busy(True)
        threading.Thread(target=self._exec_worker, args=(ids,), daemon=True).start()

    def _exec_worker(self, ids: set) -> None:
        anomalie_dir = self.base_dir / "Anomalie"

        self.after(0, self._log_append, f"Spostamento — {len(ids)} ID caricati. Scansione...")
        self.after(0, self._status_var.set, "Spostamento in corso…")

        matches, scan_count = find_matches(
            self.base_dir, ids, anomalie_dir,
            on_progress=lambda n: self.after(0, self._log_append, f"  {n} file scansionati…"),
        )
        success, errors = move_files(matches)

        for err in errors:
            self.after(0, self._log_append, f"  ERRORE: {err}")

        self.after(0, self._log_append, f"  {scan_count} file scansionati, {success} spostati in Anomalie/.")
        if errors:
            self.after(0, self._log_append, f"  Errori: {len(errors)}")
        self.after(0, self._status_var.set, f"Completato — {success} file spostati.")
        self.after(0, self._set_busy, False)


# ── Headless smoke test (CI) ──────────────────────────────────────────────────

def _run_smoke() -> None:
    """
    Self-contained headless test: creates a temp dir with fake files,
    runs find_matches + move_files, asserts expected outcome, cleans up.
    No GUI, no display needed. Exit code 0 = pass, non-zero = fail.
    """
    with tempfile.TemporaryDirectory() as tmp:
        base = Path(tmp)
        (base / "subdir").mkdir()
        (base / "IMG_ABC123.jpg").touch()
        (base / "IMG_ABC123.tif").touch()
        (base / "subdir" / "IMG_ABC123.cr2").touch()
        (base / "IMG_OTHER.jpg").touch()

        ids = {"img_abc123"}
        anomalie_dir = base / "Anomalie"

        matches, scan_count = find_matches(base, ids, anomalie_dir)
        assert scan_count == 4, f"Expected 4 files scanned, got {scan_count}"
        assert len(matches) == 3, f"Expected 3 matches, got {len(matches)}"

        success, errors = move_files(matches)
        assert success == 3, f"Expected 3 moves, got {success}"
        assert not errors, f"Unexpected errors: {errors}"

        assert (base / "Anomalie" / "IMG_ABC123.jpg").exists(), "jpg not moved"
        assert (base / "Anomalie" / "IMG_ABC123.tif").exists(), "tif not moved"
        assert (base / "Anomalie" / "subdir" / "IMG_ABC123.cr2").exists(), "subdir file not moved"
        assert (base / "IMG_OTHER.jpg").exists(), "non-matching file was moved"

    print("Smoke test passed.")


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    if "--smoke" in sys.argv:
        _run_smoke()
        return

    base_dir = get_base_dir()

    file_count = sum(1 for p in base_dir.rglob("*") if p.is_file())
    if file_count > 400_000:
        root = tk.Tk()
        root.withdraw()
        go = messagebox.askyesno(
            "Attenzione",
            f"Questa cartella contiene {file_count} file.\n"
            "Sembra che lo script non sia nella cartella corretta.\n\n"
            "Vuoi continuare comunque?",
        )
        root.destroy()
        if not go:
            sys.exit(1)

    App(base_dir).mainloop()


if __name__ == "__main__":
    main()
