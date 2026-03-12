#!/usr/bin/env python3
"""
move_anomalie.py

Moves files matching anomaly object IDs into an Anomalie/ subfolder,
preserving the original directory structure.

Input file format: one entry per line as "OBJ_ID | STATO"
Only the OBJ_ID (before the pipe) is used for matching.

Usage:
    python move_anomalie.py             # uses anomalie.txt in script dir
    python move_anomalie.py my_ids.txt  # custom input file
"""
from __future__ import annotations

import shutil
import sys
from datetime import datetime
from pathlib import Path


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


# ── UI helpers ────────────────────────────────────────────────────────────────

SEP = "=" * 58


def _pause(msg="  Premi Invio per continuare..."):
    input(msg)


def _confirm(prompt: str) -> bool:
    return input(prompt).strip().lower() == "s"


def run_dry_run(
    base_dir: Path, ids: set, anomalie_dir: Path, results_file: Path
) -> None:
    print("\n  Scansione in corso...\n")

    matches, scan_count = find_matches(
        base_dir,
        ids,
        anomalie_dir,
        on_progress=lambda n: print(f"  Scansionati {n} file..."),
    )

    with results_file.open("w", encoding="utf-8") as fh:
        fh.write(f"RISULTATI DRY-RUN - {datetime.now():%Y-%m-%d %H:%M:%S}\n")
        fh.write(f"Cartella: {base_dir}\n\n")
        for i, (src, dst) in enumerate(matches, 1):
            print(f"  Trovato: {src.name}")
            fh.write(f"{i}. {src.name}  -->  {dst}\n")
        fh.write(f"\nTotale: {len(matches)} file da spostare su {len(ids)} ID in lista\n")

    print(f"\n  {SEP}")
    print(f"  Scansione completata. {scan_count} file scansionati, {len(matches)} trovati.")
    print(f"  Risultati salvati in: {results_file.name}")
    print(f"  {SEP}\n")
    _pause("  Premi Invio per tornare al menu...")


def run_execute(base_dir: Path, ids: set, anomalie_dir: Path) -> None:
    print(f"\n  ATTENZIONE: I file verranno spostati nella cartella \"{anomalie_dir.name}/\".\n")
    if not _confirm("  Confermi? [s/n]: "):
        return

    print("\n  Spostamento in corso...\n")

    matches, scan_count = find_matches(
        base_dir,
        ids,
        anomalie_dir,
        on_progress=lambda n: print(f"  Scansionati {n} file..."),
    )

    success, errors = move_files(matches)

    for i, (src, _) in enumerate(matches, 1):
        # errors already printed inline via move_files; show successes here
        pass

    for err in errors:
        print(f"  ERRORE: {err}")

    print(f"\n  {SEP}")
    print(f"  Completato. {scan_count} file scansionati, {success} spostati in {anomalie_dir.name}/.")
    if errors:
        print(f"  Errori: {len(errors)}")
    print(f"  {SEP}\n")
    _pause("  Premi Invio per tornare al menu...")


def menu(base_dir: Path, ids: set) -> None:
    anomalie_dir = base_dir / "Anomalie"
    results_file = base_dir / "risultati_anomalie.txt"

    while True:
        print(f"\n  {SEP}")
        print("   DIGISCRIPTA - Spostamento file Anomalie")
        print(f"  {SEP}")
        print(f"\n   File caricato: {len(ids)} ID\n")
        print("   [1] Provare senza eseguire (dry-run)")
        print(f"       Genera \"{results_file.name}\" con l'elenco dei file trovati.\n")
        print("   [2] Eseguire lo spostamento")
        print(f"       Sposta i file nella cartella \"{anomalie_dir.name}/\".\n")
        print("   [3] Esci")
        print(f"\n  {SEP}\n")

        choice = input("  Scegli un'opzione [1/2/3]: ").strip()

        if choice == "1":
            run_dry_run(base_dir, ids, anomalie_dir, results_file)
        elif choice == "2":
            run_execute(base_dir, ids, anomalie_dir)
        elif choice == "3":
            break
        else:
            print("  Opzione non valida.")


# ── Entry point ───────────────────────────────────────────────────────────────

def get_base_dir() -> Path:
    """Return the directory containing the executable (or script)."""
    if getattr(sys, "frozen", False):
        # Running as a PyInstaller bundle: use executable location
        return Path(sys.executable).parent
    return Path(__file__).parent


def main() -> None:
    base_dir = get_base_dir()
    id_file = Path(sys.argv[1]) if len(sys.argv) > 1 else base_dir / "anomalie.txt"

    # Resolve relative paths against base_dir
    if not id_file.is_absolute():
        id_file = base_dir / id_file

    if not id_file.exists():
        print(f"\n  ERRORE: File \"{id_file.name}\" non trovato.")
        print("  Assicurati che anomalie.txt sia nella stessa cartella dello script.\n")
        _pause("  Premi Invio per uscire...")
        sys.exit(1)

    ids = load_ids(id_file)

    if not ids:
        print(f"\n  ERRORE: Nessun ID trovato in \"{id_file.name}\".\n")
        _pause("  Premi Invio per uscire...")
        sys.exit(1)

    # Safety check: warn if the folder looks unexpectedly large
    file_count = sum(1 for p in base_dir.rglob("*") if p.is_file())
    if file_count > 400_000:
        print(f"\n  ATTENZIONE: Questa cartella contiene {file_count} file.")
        print("  Sembra che lo script non sia nella cartella corretta.")
        if not _confirm("  Vuoi continuare comunque? [s/n]: "):
            sys.exit(1)

    menu(base_dir, ids)


if __name__ == "__main__":
    main()
