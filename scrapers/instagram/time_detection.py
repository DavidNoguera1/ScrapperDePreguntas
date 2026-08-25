"""Deteccion de duracion de reels de Instagram en CSVs de Metricool.

Funcionalidad independiente de la extraccion de comentarios: recorre los
enlaces /reel/ de un CSV exportado desde Metricool, visita cada contenido
con una sesion autenticada compartida (browser.instagram_session) y anade
la columna "Duracion" con la duracion del video.

Uso:
    TimeDetection(headless=True).detect_files(["data/ElexJuridico.csv"])
"""

import csv
import logging
from pathlib import Path

from scrapers.instagram.browser import instagram_session


LOGGER = logging.getLogger(__name__)

DURATION_COLUMN = "Duracion"

# Columnas que pueden contener el enlace al contenido segun el export de Metricool.
# Si ninguna existe, se busca cualquier celda con un enlace /reel/.
LINK_COLUMNS = ("PostLink", "URL")


def get_reel_link(row):
    """Devuelve el enlace al reel de una fila, o cadena vacia si no tiene."""
    for column in LINK_COLUMNS:
        value = (row.get(column) or "").strip()
        if value:
            return value
    for value in row.values():
        value = (value or "").strip()
        if value.startswith("http") and "/reel/" in value.split("?")[0]:
            return value
    return ""

_EXTRACT_DURATION_JS = """() => {
    const videos = Array.from(document.querySelectorAll('video'));
    for (const video of videos) {
        const duration = video.duration;
        if (typeof duration === 'number' && Number.isFinite(duration) && duration > 0) {
            return duration;
        }
    }
    return null;
}"""


def format_duration(seconds):
    """Convierte segundos a texto M:SS (ej. 95 -> '1:35')."""
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


class TimeDetection:
    """Anade la columna Duracion a CSVs de Metricool leyendo cada reel."""

    def __init__(self, headless=True, auth_file=None, logger=None):
        self.headless = headless
        self.auth_file = auth_file
        self.logger = logger or LOGGER

    def detect_files(self, csv_paths):
        """Procesa varios CSV con una sola sesion de navegador.

        Devuelve {ruta: reels_actualizados}.
        """
        results = {}
        with instagram_session(headless=self.headless, auth_file=self.auth_file) as page:
            for path in csv_paths:
                try:
                    results[str(path)] = self.detect_file(page, path)
                except Exception:
                    self.logger.exception(
                        "TimeDetection | error procesando archivo | ruta=%s", path
                    )
                    results[str(path)] = 0
        return results

    def detect_file(self, page, csv_path):
        """Anade/actualiza la columna Duracion de un CSV. Devuelve cuantos
        reels fueron visitados."""
        csv_path = Path(csv_path)
        if not csv_path.exists():
            raise FileNotFoundError(f"No existe el archivo: {csv_path}")

        raw = csv_path.read_bytes()
        newline = "\r\n" if b"\r\n" in raw else "\n"
        rows = list(csv.DictReader(raw.decode("utf-8-sig").splitlines(), delimiter=";"))
        if not rows:
            return 0

        fieldnames = list(rows[0].keys())
        if DURATION_COLUMN not in fieldnames:
            fieldnames.append(DURATION_COLUMN)

        updated = 0
        for index, row in enumerate(rows, 1):
            link = get_reel_link(row)
            if "/reel/" not in link:
                continue
            if row.get(DURATION_COLUMN, "").strip():
                continue
            try:
                seconds = self._get_reel_duration(page, link)
            except Exception:
                self.logger.exception(
                    "TimeDetection | error en reel | fila=%s | url=%s", index, link
                )
                continue
            if seconds is None:
                self.logger.warning(
                    "TimeDetection | sin duracion | fila=%s | url=%s", index, link
                )
                continue
            row[DURATION_COLUMN] = format_duration(seconds)
            updated += 1
            self.logger.info(
                "TimeDetection | fila=%s/%s | duracion=%s | url=%s",
                index, len(rows), row[DURATION_COLUMN], link,
            )

        self._write_csv(csv_path, fieldnames, rows, newline)
        total_reels = sum(1 for r in rows if "/reel/" in get_reel_link(r))
        self.logger.info(
            "TimeDetection | archivo=%s | reels_actualizados=%s/%s",
            csv_path.name, updated, total_reels,
        )
        return updated

    def _get_reel_duration(self, page, reel_url, attempts=20, wait_ms=500):
        page.goto(reel_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1_500)

        lowered = page.url.casefold()
        if "login" in lowered or "checkpoint" in lowered:
            raise RuntimeError("Instagram invalidó la sesión durante la extracción.")

        for _ in range(attempts):
            seconds = page.evaluate(_EXTRACT_DURATION_JS)
            if seconds is not None:
                return seconds
            page.wait_for_timeout(wait_ms)
        return None

    @staticmethod
    def _write_csv(csv_path, fieldnames, rows, newline="\n"):
        with csv_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter=";")
            writer.writeheader()
            writer.writerows(rows)
