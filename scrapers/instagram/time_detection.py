"""Deteccion de duracion y vistas de reels de Instagram en CSVs de Metricool.

Funcionalidad independiente de la extraccion de comentarios: recorre los
enlaces /reel/ de un CSV exportado desde Metricool, visita cada contenido
con una sesion autenticada compartida (browser.instagram_session) y anade:

- columna "Duracion" con la duracion del video (formato M:SS)
- columna "Vistas" con el numero de reproducciones del reel

Las vistas se leen del JSON interno de la pagina embed del reel, porque la
pagina normal y la API web no exponen `view_count` para cuentas ajenas.

Es reanudable: las filas que ya tienen los valores se omiten.

Uso:
    TimeDetection(headless=True).detect_files(["data/ElexJuridico.csv"])
"""

import csv
import logging
import re
from pathlib import Path

from scrapers.instagram.browser import instagram_session


LOGGER = logging.getLogger(__name__)

DURATION_COLUMN = "Duracion"
VIEWS_COLUMN = "Vistas"

# Columnas que pueden contener el enlace al contenido segun el export de Metricool.
# Si ninguna existe, se busca cualquier celda con un enlace /reel/.
LINK_COLUMNS = ("PostLink", "URL")

# El embed incluye el JSON escapado (\"clave\":valor), por eso el patron
# admite una barra invertida opcional antes de las comillas.
_DURATION_RE = re.compile(r'video_duration\\?"\s*:\s*([0-9.]+)')
_VIEWS_RE = re.compile(r'video_view_count\\?"\s*:\s*(\d+)')

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


def format_duration(seconds):
    """Convierte segundos a texto M:SS (ej. 95 -> '1:35')."""
    total = int(round(seconds))
    minutes, secs = divmod(total, 60)
    return f"{minutes}:{secs:02d}"


class TimeDetection:
    """Anade las columnas Duracion y Vistas a CSVs de Metricool."""

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
        """Anade/actualiza Duracion y Vistas de un CSV. Devuelve cuantos
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
        for column in (DURATION_COLUMN, VIEWS_COLUMN):
            if column not in fieldnames:
                fieldnames.append(column)

        updated = 0
        for index, row in enumerate(rows, 1):
            link = get_reel_link(row)
            if "/reel/" not in link:
                continue
            needs_duration = not row.get(DURATION_COLUMN, "").strip()
            needs_views = not row.get(VIEWS_COLUMN, "").strip()
            if not needs_duration and not needs_views:
                continue

            try:
                duration_seconds, views = self._get_reel_data(
                    page, link, need_duration=needs_duration
                )
            except Exception:
                self.logger.exception(
                    "TimeDetection | error en reel | fila=%s | url=%s", index, link
                )
                continue

            if needs_duration and duration_seconds is not None:
                row[DURATION_COLUMN] = format_duration(duration_seconds)
            if needs_views:
                if views is not None:
                    row[VIEWS_COLUMN] = views
                else:
                    self.logger.warning(
                        "TimeDetection | sin vistas | fila=%s | url=%s", index, link
                    )

            if needs_duration and duration_seconds is None:
                self.logger.warning(
                    "TimeDetection | sin duracion | fila=%s | url=%s", index, link
                )

            filled = (
                bool(row.get(DURATION_COLUMN, "").strip())
                or bool(row.get(VIEWS_COLUMN, "").strip())
            )
            if filled:
                updated += 1
            self.logger.info(
                "TimeDetection | fila=%s/%s | duracion=%s | vistas=%s | url=%s",
                index, len(rows),
                row.get(DURATION_COLUMN, "") or "-",
                row.get(VIEWS_COLUMN, "") or "-",
                link,
            )

        self._write_csv(csv_path, fieldnames, rows, newline)
        total_reels = sum(1 for r in rows if "/reel/" in get_reel_link(r))
        self.logger.info(
            "TimeDetection | archivo=%s | reels_actualizados=%s/%s",
            csv_path.name, updated, total_reels,
        )
        return updated

    def _get_reel_data(self, page, reel_url, need_duration=True,
                       attempts=20, wait_ms=500):
        """Devuelve (duracion_en_segundos|None, vistas_str|None).

        Lee ambos datos del JSON interno de la pagina embed. Si la duracion
        no aparece alli y se necesita, recurre a la pagina normal del reel.
        """
        match = re.search(r"/reel/([^/?#]+)", reel_url)
        if not match:
            return None, None

        page.goto(
            f"https://www.instagram.com/reel/{match.group(1)}/embed/captioned/",
            wait_until="domcontentloaded",
            timeout=30_000,
        )
        page.wait_for_timeout(1_500)

        lowered = page.url.casefold()
        if "login" in lowered or "checkpoint" in lowered:
            raise RuntimeError("Instagram invalidó la sesión durante la extracción.")

        html = page.content()
        views_match = _VIEWS_RE.search(html)
        views = views_match.group(1) if views_match else None

        seconds = None
        duration_match = _DURATION_RE.search(html)
        if duration_match:
            try:
                seconds = float(duration_match.group(1))
            except ValueError:
                seconds = None

        if need_duration and seconds is None:
            seconds = self._get_reel_duration_from_page(page, reel_url)

        return seconds, views

    def _get_reel_duration_from_page(self, page, reel_url, attempts=20, wait_ms=500):
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
