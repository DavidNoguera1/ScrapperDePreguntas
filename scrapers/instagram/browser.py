"""Infraestructura compartida de navegador para cualquier scraper de Instagram.

Aqui vive todo lo que NO es logica de negocio: lanzamiento de Chromium,
carga de la sesion guardada, bloqueo de recursos pesados y verificacion
de autenticacion. Las funciones concretas de scrapping (comentarios,
metricas, seguidores, etc.) deben usar `instagram_session` en vez de
lanzar su propio navegador.
"""

from contextlib import contextmanager
from pathlib import Path

from playwright.sync_api import sync_playwright

from core.config import DEFAULT_AUTH_FILE
from scrapers.instagram.navigation import route_lightweight, is_authenticated


USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/125.0.0.0 Safari/537.36"
)


@contextmanager
def instagram_session(headless=True, auth_file=None):
    """Abre un navegador autenticado de Instagram y cede una pagina lista.

    Uso:
        with instagram_session(headless=True) as page:
            page.goto("https://www.instagram.com/<usuario>/")

    Lanza RuntimeError si la sesion guardada no esta autenticada.
    """
    auth_file = Path(auth_file or DEFAULT_AUTH_FILE).resolve()

    with sync_playwright() as playwright:
        browser = None
        context = None
        try:
            browser = playwright.chromium.launch(headless=headless)
            context_options = {
                "viewport": {"width": 1280, "height": 900},
                "user_agent": USER_AGENT,
            }
            if auth_file.exists():
                context_options["storage_state"] = str(auth_file)

            context = browser.new_context(**context_options)
            page = context.new_page()
            page.route("**/*", route_lightweight)

            page.goto("https://www.instagram.com/", wait_until="domcontentloaded", timeout=30_000)
            page.wait_for_timeout(2_000)

            mode = "oculto" if headless else "visible"
            if not is_authenticated(context, page):
                raise RuntimeError(
                    "La sesion de Instagram no esta autenticada "
                    f"(navegador {mode}). Ejecuta: python import_session.py"
                )

            yield page
        finally:
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()
