"""Fachada principal de scraping de Instagram.

`InstagramScraper` agrupa la gestion de sesion (login/logout) y delega
cada funcionalidad concreta en su modulo:

- Comentarios y preguntas: scrapers/instagram/comments/
- Duracion de reels en CSVs: scrapers/instagram/time_detection.py
- Sesion/navegador compartido: scrapers/instagram/browser.py

Para agregar una nueva funcion de scrapping crea un modulo hermano
(p. ej. metrics.py) que use `instagram_session`, exponla aqui como un
metodo delegado y no la mezcles con comments/ ni time_detection/.
"""

from pathlib import Path

from core.config import DEFAULT_AUTH_FILE
from scrapers.instagram.comments.scraper import CommentScraper
from scrapers.instagram.time_detection import TimeDetection, format_duration
from scrapers.instagram.auth import (
    has_saved_session as _has_saved_session,
    register_manual_login as _register_manual_login,
    logout_saved_session as _logout_saved_session,
)


class InstagramScraper(CommentScraper):
    """Punto de entrada unico para scrapear Instagram."""

    def __init__(self, headless=True, auth_file=None, logger=None):
        super().__init__(headless=headless, auth_file=auth_file, logger=logger)
        self._auth_path = Path(auth_file or DEFAULT_AUTH_FILE).resolve()

    def has_saved_session(self):
        return _has_saved_session(self._auth_path)

    def register_manual_login(self):
        _register_manual_login(self._auth_path)

    def logout_saved_session(self):
        return _logout_saved_session(self._auth_path)

    def detect_reel_durations(self, csv_paths):
        """Anade la columna Duracion a CSVs de Metricool (ver time_detection.py).

        Devuelve {ruta: reels_actualizados}.
        """
        detector = TimeDetection(
            headless=self.headless,
            auth_file=self._auth_path,
            logger=self.logger,
        )
        return detector.detect_files(csv_paths)
