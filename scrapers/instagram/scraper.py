import logging
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright

from core.config import DEFAULT_AUTH_FILE, MONTHS_ES, MONTH_ABBR_ES
from core.filters import normalize_username, normalize_comment, is_user_comment, is_interesting_comment, is_question
from scrapers.instagram.auth import has_saved_session as _has_saved_session
from scrapers.instagram.auth import register_manual_login as _register_manual_login
from scrapers.instagram.auth import logout_saved_session as _logout_saved_session
from scrapers.instagram.navigation import route_lightweight, is_authenticated, discover_profile_links
from scrapers.instagram.extractors import extract_post_date, expand_comments, extract_comments


LOGGER = logging.getLogger(__name__)


class InstagramScraper:
    def __init__(self, headless=True, auth_file=None, logger=None):
        self.headless = headless
        self.auth_file = Path(auth_file or DEFAULT_AUTH_FILE).resolve()
        self.logger = logger or LOGGER
        self._seen_comments = set()

    def has_saved_session(self):
        return _has_saved_session(self.auth_file)

    def register_manual_login(self):
        _register_manual_login(self.auth_file)

    def logout_saved_session(self):
        return _logout_saved_session(self.auth_file)

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
                page.route("**/*", route_lightweight)

                profile_url = f"https://www.instagram.com/{username}/"
                page.goto(profile_url, wait_until="domcontentloaded", timeout=30_000)
                page.wait_for_timeout(2_000)

                if not is_authenticated(context, page):
                    mode = "oculto" if self.headless else "visible"
                    raise RuntimeError(
                        "La sesión de Instagram no está autenticada "
                        f"(navegador {mode}). Ejecuta: python import_session.py"
                    )

                post_links = discover_profile_links(
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

        post_date = extract_post_date(page)
        if post_date and post_date < cutoff:
            return 0, True
        if post_date is None:
            self.logger.warning(
                "Instagram | no se pudo determinar la fecha | url=%s", post_url
            )

        expand_comments(page)
        comments = extract_comments(page)
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
            question = is_question(text)
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
