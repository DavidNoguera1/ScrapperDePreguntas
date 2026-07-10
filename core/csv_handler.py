import csv
import os
import logging
from datetime import datetime

import pandas as pd

from core.config import CSV_HEADERS, OUTPUT_DIR


LOGGER = logging.getLogger(__name__)
CSV_FILE = None


def open_csv(filename=None):
    global CSV_FILE
    if CSV_FILE:
        return CSV_FILE
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraping_{timestamp}.csv"
    filename = os.path.basename(filename)
    CSV_FILE = os.path.join(OUTPUT_DIR, filename)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_HEADERS,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
            extrasaction="ignore",
        )
        writer.writeheader()
    LOGGER.info("CSV en vivo: %s", CSV_FILE)
    print(f"\n  [*] CSV en vivo: {CSV_FILE}")
    print(f"  [*] Abrelo en Excel mientras se llena!")
    return CSV_FILE


def append_csv(row_dict):
    if not CSV_FILE:
        raise RuntimeError("El CSV no ha sido inicializado.")
    with open(CSV_FILE, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_HEADERS,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
            extrasaction="ignore",
        )
        writer.writerow({header: row_dict.get(header, "") for header in CSV_HEADERS})


def save_csv(results, filename=None):
    if not results:
        return None
    df = pd.DataFrame(results)
    available = [c for c in CSV_HEADERS if c in df.columns]
    df = df[available]
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraping_{timestamp}.csv"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False, encoding="utf-8-sig", sep=";")
    LOGGER.info("CSV final: %s | registros=%s", filepath, len(df))
    print(f"\n  [OK] CSV final: {filepath}")
    print(f"  [*] Total: {len(df)} comentarios")
    return filepath


def merge_csvs():
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv")]
    if not files:
        print("  No hay CSVs en la carpeta output/")
        return

    print("\n  Archivos disponibles:")
    for i, f in enumerate(files, 1):
        print(f"    {i}. {f}")

    selected = input("\n  Numeros a mergear (ej: 1,2,3): ").strip()
    indices = [int(x.strip()) - 1 for x in selected.split(",") if x.strip().isdigit()]

    dfs = []
    for idx in indices:
        if 0 <= idx < len(files):
            filepath = os.path.join(OUTPUT_DIR, files[idx])
            try:
                df = pd.read_csv(
                    filepath,
                    encoding="utf-8-sig",
                    sep=None,
                    engine="python",
                )
                missing = [header for header in CSV_HEADERS if header not in df.columns]
                if missing:
                    LOGGER.warning(
                        "No se mergea %s: faltan columnas %s", filepath, missing
                    )
                    print(f"  [AVISO] Se omite {files[idx]}: formato incompatible.")
                    continue
                dfs.append(df[CSV_HEADERS])
            except Exception:
                LOGGER.exception("No se pudo leer el CSV para merge: %s", filepath)
                print(f"  [AVISO] Se omite {files[idx]}: no se pudo leer.")

    if not dfs:
        print("  No se seleccionaron archivos validos.")
        return

    merged = pd.concat(dfs, ignore_index=True)
    merged = merged[CSV_HEADERS]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(OUTPUT_DIR, f"merged_{timestamp}.csv")
    merged.to_csv(filepath, index=False, encoding="utf-8-sig", sep=";")
    LOGGER.info("CSV mergeado: %s | registros=%s", filepath, len(merged))
    print(f"\n  [OK] Merge guardado: {filepath}")
    print(f"  [*] Total registros: {len(merged)}")
