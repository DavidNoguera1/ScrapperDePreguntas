import logging
from pathlib import Path

from playwright.sync_api import sync_playwright

from core.config import DEFAULT_AUTH_FILE


LOGGER = logging.getLogger(__name__)


def has_saved_session(auth_file=None):
    path = Path(auth_file or DEFAULT_AUTH_FILE).resolve()
    return path.exists()


def register_manual_login(auth_file=None):
    auth_path = Path(auth_file or DEFAULT_AUTH_FILE).resolve()
    print(
        """
  Abriendo un navegador aislado de Playwright para Instagram...

  INSTRUCCIONES:
  1. Ingresa tu usuario y contraseña directamente en Instagram
  2. Completa cualquier verificación solicitada
  3. Cuando veas tu cuenta iniciada, vuelve aquí y presiona ENTER
  4. El navegador se cerrará siempre y la sesión quedará guardada

  La etiqueta "Chrome for Testing" es normal y no almacena tu contraseña.
"""
    )
    with sync_playwright() as playwright:
        browser = None
        context = None
        try:
            browser = playwright.chromium.launch(headless=False)
            context = browser.new_context(viewport={"width": 1280, "height": 900})
            page = context.new_page()
            page.goto(
                "https://www.instagram.com/accounts/login/",
                wait_until="domcontentloaded",
                timeout=30_000,
            )
            input("  Presiona ENTER después de iniciar sesión en Instagram...")

            cookie_names = {cookie["name"] for cookie in context.cookies()}
            if "sessionid" not in cookie_names:
                raise RuntimeError(
                    "No se detectó una sesión iniciada. No se guardó ningún archivo."
                )

            context.storage_state(path=str(auth_path))
            LOGGER.info("Instagram | sesión guardada | archivo=%s", auth_path)
            print(f"  Sesión guardada en {auth_path}")
        finally:
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()
            print("  Navegador de Playwright cerrado.")


def logout_saved_session(auth_file=None):
    auth_path = Path(auth_file or DEFAULT_AUTH_FILE).resolve()
    if not auth_path.exists():
        LOGGER.info("Instagram | no hay sesión guardada para cerrar")
        return {"server_revoked": False, "local_deleted": False}

    server_revoked = False
    with sync_playwright() as playwright:
        browser = None
        context = None
        try:
            browser = playwright.chromium.launch(headless=True)
            context = browser.new_context(storage_state=str(auth_path))
            page = context.new_page()
            page.goto(
                "https://www.instagram.com/",
                wait_until="domcontentloaded",
                timeout=30_000,
            )

            cookies = {cookie["name"]: cookie for cookie in context.cookies()}
            csrf = cookies.get("csrftoken", {}).get("value")
            user_id = cookies.get("ds_user_id", {}).get("value", "")
            if csrf and "sessionid" in cookies:
                try:
                    response = context.request.post(
                        "https://www.instagram.com/accounts/logout/ajax/",
                        form={
                            "one_tap_app_login": "0",
                            "user_id": user_id,
                        },
                        headers={
                            "X-CSRFToken": csrf,
                            "X-Requested-With": "XMLHttpRequest",
                            "Referer": "https://www.instagram.com/",
                        },
                        timeout=20_000,
                    )
                    server_revoked = response.ok
                    if not response.ok:
                        LOGGER.warning(
                            "Instagram | logout remoto respondió HTTP %s",
                            response.status,
                        )
                except Exception:
                    LOGGER.exception(
                        "Instagram | no se pudo confirmar el logout remoto"
                    )
            context.clear_cookies()
        finally:
            if context is not None:
                context.close()
            if browser is not None:
                browser.close()

    local_deleted = False
    try:
        auth_path.unlink(missing_ok=True)
        local_deleted = not auth_path.exists()
    finally:
        LOGGER.info(
            "Instagram | sesión cerrada | remoto=%s | archivo_local_eliminado=%s",
            server_revoked, local_deleted,
        )

    return {
        "server_revoked": server_revoked,
        "local_deleted": local_deleted,
    }
