import logging
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


LOGGER = logging.getLogger(__name__)
BASE_DIR = Path(__file__).resolve().parent
DEFAULT_AUTH_FILE = BASE_DIR / "instagram_auth.json"

MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

MONTH_ABBR_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic",
}

QUESTION_PATTERN = re.compile(
    r"(?:"
    r"\bqui[eé]n(?:es)?\b|\bcu[aá]ndo\b|\bd[oó]nde\b|\bc[oó]mo\b"
    r"|\bcu[aá]l(?:es)?\b|\bcu[aá]nt[oa]s?\b"
    r"|\bpor\s+qu[eé]\b|\bpara\s+qu[eé]\b|\ba\s+qu[eé]\b"
    r"|\bqu[eé]\s+(?:es|hay|tal|significa|quier|pasa|necesit|debo|deb|"
    r"pued|hag|va[ya]|diferencia|requisito|paso|documento|tiempo|"
    r"cost[oó]|vale|opini[oó]n)"
    r")|(\?)",
    re.IGNORECASE,
)

UI_NOISE = {
    "follow", "seguir", "reply", "responder", "like", "me gusta",
    "see translation", "ver traducción", "view replies", "ver respuestas",
    "edited", "editado",
}

COMMENT_METADATA_PATTERN = re.compile(
    r"^(?:"
    r"\d+\s*(?:s|sec|m|min|h|hr|d|day|w|wk|sem|mes|mo|y|yr)"
    r"(?:\s*[·•]\s*(?:edited|editado))?"
    r"|\d+\s*(?:like|likes|me gusta)"
    r")$",
    re.IGNORECASE,
)

INTEREST_KEYWORDS = {
    "nie", "tie", "residencia", "permiso", "visado", "visa",
    "expediente", "trámite", "tramite", "solicitud", "documento",
    "regularización", "regularizacion", "homologación", "homologacion",
    "nacionalidad", "extranjería", "extranjeria", "tasa", "huella",
    "asilo", "arraigo", "cita", "apostilla", "antecedente",
    "certificado digital", "seguridad social", "contrato", "empresa",
    "trabajar", "trabajo", "legal", "ley", "abogado", "padrón",
    "padron", "reagrupación", "reagrupacion", "renovar", "renovación",
    "renovacion", "recurso", "subsanación", "subsanacion", "notificación",
    "notificacion", "razones humanitarias", "admisión", "admision",
}


def normalize_username(username):
    username = (username or "").strip()
    if "instagram.com/" in username:
        username = urlparse(username).path.strip("/").split("/")[0]
    return username.lstrip("@").strip()


def normalize_comment(text):
    return re.sub(r"\s+", " ", text or "").strip()


def is_user_comment(text, account_name=""):
    text = normalize_comment(text)
    if len(text) < 2 or len(text) > 2_000:
        return False
    if text.casefold() in UI_NOISE:
        return False
    if COMMENT_METADATA_PATTERN.fullmatch(text):
        return False
    if account_name and text.casefold() == account_name.casefold():
        return False
    return True


def is_interesting_comment(text):
    text = normalize_comment(text)
    if not is_user_comment(text):
        return False
    lowered = text.casefold()
    if QUESTION_PATTERN.search(text) and len(text) >= 10:
        return True
    if ("http://" in lowered or "https://" in lowered) and len(text) >= 30:
        return True
    return len(text) >= 25 and any(
        keyword in lowered for keyword in INTEREST_KEYWORDS
    )


class InstagramScraper:
    def __init__(self, headless=True, auth_file=None, logger=None):
        self.headless = headless
        self.auth_file = Path(auth_file or DEFAULT_AUTH_FILE).resolve()
        self.logger = logger or LOGGER
        self._seen_comments = set()

    def has_saved_session(self):
        return self.auth_file.exists()

    def scrape_profile_comments(
        self,
        username,
        months=1,
        max_posts=None,
        only_questions=False,
        interest_only=False,
        on_comment=None,
    ):
        username = normalize_username(username)
        if not username:
            raise ValueError("La cuenta de Instagram está vacía.")
        if months < 1:
            raise ValueError("months debe ser al menos 1.")
        if max_posts is not None and max_posts < 1:
            raise ValueError("max_posts debe ser positivo o None.")

        self.logger.info(
            "Instagram | cuenta=%s | meses=%s | max_posts=%s | solo_preguntas=%s",
            username, months, max_posts or "sin_límite", only_questions,
        )
        self.logger.info(
            "Instagram | cuenta=%s | solo_interes=%s", username, interest_only
        )
        results = []
        self._seen_comments = set()
        cutoff = datetime.now(timezone.utc) - timedelta(days=30 * months)

        with sync_playwright() as playwright:
            browser = None
            context = None
            try:
                browser = playwright.chromium.launch(headless=self.headless)
                context_options = {
                    "viewport": {"width": 1280, "height": 900},
                    "user_agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/125.0.0.0 Safari/537.36"
                    ),
                }
                if self.auth_file.exists():
                    context_options["storage_state"] = str(self.auth_file)

                context = browser.new_context(**context_options)
                page = context.new_page()
                page.route("**/*", self._route_lightweight)

                profile_url = f"https://www.instagram.com/{username}/"
                page.goto(profile_url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(2_000)

                if not self._is_authenticated(context, page):
                    mode = "oculto" if self.headless else "visible"
                    raise RuntimeError(
                        "La sesión de Instagram no está autenticada "
                        f"(navegador {mode}). Ejecuta: python import_session.py"
                    )

                post_links = self._discover_profile_links(
                    page, username, max_posts=max_posts
                )
                if max_posts is not None:
                    post_links = post_links[:max_posts]

                self.logger.info(
                    "Instagram | cuenta=%s | recursos_propios_encontrados=%s",
                    username, len(post_links),
                )

                for index, link in enumerate(post_links, 1):
                    try:
                        count, old_post = self._scrape_post_comments(
                            page=page,
                            post_url=link,
                            username=username,
                            cutoff=cutoff,
                            only_questions=only_questions,
                            interest_only=interest_only,
                            results=results,
                            on_comment=on_comment,
                        )
                        self.logger.info(
                            "Instagram | cuenta=%s | recurso=%s/%s | comentarios=%s | antiguo=%s | url=%s",
                            username, index, len(post_links), count, old_post, link,
                        )
                    except Exception:
                        self.logger.exception(
                            "Instagram | error procesando recurso | cuenta=%s | url=%s",
                            username, link,
                        )
            finally:
                if context is not None:
                    context.close()
                if browser is not None:
                    browser.close()

        self.logger.info(
            "Instagram | cuenta=%s | total_exportado=%s", username, len(results)
        )
        return results

    @staticmethod
    def _route_lightweight(route):
        if route.request.resource_type in {"image", "media", "font"}:
            route.abort()
        else:
            route.continue_()

    @staticmethod
    def _is_authenticated(context, page):
        cookie_names = {cookie["name"] for cookie in context.cookies()}
        return (
            "sessionid" in cookie_names
            and "login" not in page.url.casefold()
            and "checkpoint" not in page.url.casefold()
        )

    def _discover_profile_links(self, page, username, max_posts=None):
        username_re = re.escape(username)
        own_resource = re.compile(
            rf"^https://www\.instagram\.com/{username_re}/(?:p|reel)/[^/?#]+/?$",
            re.IGNORECASE,
        )
        ordered_links = {}
        stable_rounds = 0

        for _ in range(30):
            raw_links = page.locator("main a[href]").evaluate_all(
                """elements => elements.map(element => element.href)"""
            )
            before = len(ordered_links)
            for link in raw_links:
                canonical = link.split("?")[0].rstrip("/") + "/"
                if own_resource.match(canonical):
                    ordered_links.setdefault(canonical, None)

            if len(ordered_links) == before:
                stable_rounds += 1
            else:
                stable_rounds = 0

            if max_posts is not None and len(ordered_links) >= max_posts:
                break
            if stable_rounds >= 3 and ordered_links:
                break

            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(900)

        return list(ordered_links)

    def _scrape_post_comments(
        self,
        page,
        post_url,
        username,
        cutoff,
        only_questions,
        interest_only,
        results,
        on_comment=None,
    ):
        post_type = "Reel" if "/reel/" in post_url else "Post"
        page.goto(post_url, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(1_500)

        if "login" in page.url.casefold() or "checkpoint" in page.url.casefold():
            raise RuntimeError("Instagram invalidó la sesión durante la extracción.")

        post_date = self._extract_post_date(page)
        if post_date and post_date < cutoff:
            return 0, True
        if post_date is None:
            self.logger.warning(
                "Instagram | no se pudo determinar la fecha | url=%s", post_url
            )

        self._expand_comments(page)
        comments = self._extract_comments(page)
        self.logger.debug(
            "Instagram | candidatos_estructurados=%s | url=%s",
            len(comments), post_url,
        )

        count = 0
        valid_count = 0
        interesting_count = 0
        question_count = 0
        for item in comments:
            text = normalize_comment(item.get("text"))
            if not is_user_comment(text, username):
                continue
            valid_count += 1
            interesting = is_interesting_comment(text)
            question = self._is_question(text)
            if interesting:
                interesting_count += 1
            if question:
                question_count += 1
            if interest_only and not interesting:
                continue
            if only_questions and not question:
                continue

            dedup_key = item.get("id") or (
                post_url,
                item.get("datetime", ""),
                text.casefold(),
            )
            if dedup_key in self._seen_comments:
                continue
            self._seen_comments.add(dedup_key)

            row = {
                "Dia": (
                    f"{post_date.day:02d}-{MONTH_ABBR_ES[post_date.month]}"
                    if post_date else ""
                ),
                "Cuenta": username,
                "Red Social": "Instagram",
                "Tipo de publicacion": post_type,
                "Enlace": post_url,
                "Comentario": text,
                "Tema principal": "",
                "Mes": MONTHS_ES[post_date.month] if post_date else "",
            }
            results.append(row)
            if on_comment:
                on_comment(row)
            count += 1

        self.logger.info(
            "Instagram | candidatos=%s | comentarios_validos=%s | interes=%s | preguntas=%s | exportados=%s | url=%s",
            len(comments), valid_count, interesting_count, question_count,
            count, post_url,
        )
        return count, False

    @staticmethod
    def _extract_post_date(page):
        value = page.evaluate(
            """() => {
                const times = Array.from(document.querySelectorAll('time'));
                const postTime = times.find(time => {
                    const link = time.closest('a');
                    return !link || !String(link.getAttribute('href') || '').includes('/c/');
                });
                return postTime ? postTime.getAttribute('datetime') : null;
            }"""
        )
        if not value:
            return None
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None

    @staticmethod
    def _expand_comments(page):
        patterns = (
            "load more comments", "view more comments", "view all comments",
            "view replies", "load more replies",
            "cargar más comentarios", "ver más comentarios",
            "ver todos los comentarios", "ver respuestas",
            "ver más respuestas",
        )
        stable_rounds = 0
        previous_count = -1

        for _ in range(12):
            comment_count = page.locator('a[href*="/c/"] time').count()
            clicked = page.evaluate(
                """patterns => {
                    const normalized = value => String(value || '')
                        .trim().toLocaleLowerCase();
                    const candidates = Array.from(
                        document.querySelectorAll('[role="button"], button')
                    );
                    let clicks = 0;
                    for (const element of candidates) {
                        if (clicks >= 12) break;
                        const svgLabels = Array.from(element.querySelectorAll('svg'))
                            .map(svg => svg.getAttribute('aria-label') || '')
                            .join(' ');
                        const label = normalized(
                            `${element.innerText || ''} ${element.getAttribute('aria-label') || ''} ${svgLabels}`
                        );
                        if (patterns.some(pattern => label.includes(pattern))) {
                            element.click();
                            clicks += 1;
                        }
                    }
                    return clicks;
                }""",
                patterns,
            )

            if comment_count == previous_count and clicked == 0:
                stable_rounds += 1
            else:
                stable_rounds = 0
            if stable_rounds >= 2:
                break

            previous_count = comment_count
            page.wait_for_timeout(700 if clicked else 350)

    @staticmethod
    def _extract_comments(page, account_name=None):
        # Cada comentario tiene un enlace permanente /c/<id>/ con su <time>.
        # Se usa ese ancla estable en lugar de clases CSS privadas de Instagram.
        return page.evaluate(
            """() => {
                const output = [];
                const seen = new Set();
                const timeNodes = Array.from(
                    document.querySelectorAll('a[href*="/c/"] time')
                );

                for (const time of timeNodes) {
                    const permalink = time.closest('a[href*="/c/"]');
                    if (!permalink) continue;
                    const href = permalink.href || permalink.getAttribute('href') || '';
                    if (seen.has(href)) continue;

                    let node = permalink.parentElement;
                    let text = '';
                    let author = '';
                    const timeText = (time.innerText || '').trim();
                    const metadataPattern = /^(?:\\d+\\s*(?:s|sec|m|min|h|hr|d|day|w|wk|sem|mes|mo|y|yr)(?:\\s*[·•]\\s*(?:edited|editado))?|\\d+\\s*(?:like|likes|me gusta))$/i;
                    const uiNoise = new Set([
                        'follow', 'seguir', 'reply', 'responder', 'like',
                        'me gusta', 'see translation', 'ver traducción',
                        'view replies', 'ver respuestas', 'edited', 'editado'
                    ]);

                    for (let level = 0; node && level < 7; level++, node = node.parentElement) {
                        const profileLink = Array.from(node.querySelectorAll('a[href]'))
                            .find(link => {
                                const path = link.getAttribute('href') || '';
                                return /^\\/[A-Za-z0-9._]+\\/$/.test(path);
                            });
                        if (profileLink) author = (profileLink.innerText || '').trim();

                        const candidates = Array.from(
                            node.querySelectorAll('span[dir="auto"]')
                        ).filter(span => {
                            if (span.closest('a')) return false;
                            if (span.querySelector('span[dir="auto"]')) return false;
                            const value = (span.innerText || '').trim();
                            const normalized = value.toLocaleLowerCase();
                            return value
                                && value !== author
                                && value !== timeText
                                && !metadataPattern.test(value)
                                && !uiNoise.has(normalized);
                        });

                        if (candidates.length) {
                            text = (candidates[candidates.length - 1].innerText || '').trim();
                            break;
                        }
                    }

                    if (!text) continue;
                    seen.add(href);
                    output.push({
                        id: href,
                        text,
                        author,
                        datetime: time.getAttribute('datetime') || '',
                    });
                }
                return output;
            }"""
        )

    @staticmethod
    def _is_question(text):
        return bool(QUESTION_PATTERN.search(text))

    def register_manual_login(self):
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

                context.storage_state(path=str(self.auth_file))
                self.logger.info(
                    "Instagram | sesión guardada | archivo=%s", self.auth_file
                )
                print(f"  Sesión guardada en {self.auth_file}")
            finally:
                if context is not None:
                    context.close()
                if browser is not None:
                    browser.close()
                print("  Navegador de Playwright cerrado.")

    def logout_saved_session(self):
        """Revoca la sesión en Instagram y elimina la copia local."""
        if not self.auth_file.exists():
            self.logger.info("Instagram | no hay sesión guardada para cerrar")
            return {"server_revoked": False, "local_deleted": False}

        server_revoked = False
        with sync_playwright() as playwright:
            browser = None
            context = None
            try:
                browser = playwright.chromium.launch(headless=True)
                context = browser.new_context(storage_state=str(self.auth_file))
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
                            self.logger.warning(
                                "Instagram | logout remoto respondió HTTP %s",
                                response.status,
                            )
                    except Exception:
                        self.logger.exception(
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
            self.auth_file.unlink(missing_ok=True)
            local_deleted = not self.auth_file.exists()
        finally:
            self.logger.info(
                "Instagram | sesión cerrada | remoto=%s | archivo_local_eliminado=%s",
                server_revoked, local_deleted,
            )

        return {
            "server_revoked": server_revoked,
            "local_deleted": local_deleted,
        }
