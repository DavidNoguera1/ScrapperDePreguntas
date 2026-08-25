"""Scraper de comentarios por perfil de Instagram.

Flujo: abre una sesion compartida (browser.instagram_session), descubre
los posts/reels del perfil, expande y extrae los comentarios de cada uno
y aplica los filtros del dominio (preguntas / interes legal).
"""

import logging
from datetime import datetime, timedelta, timezone

from core.config import MONTHS_ES, MONTH_ABBR_ES
from scrapers.instagram.browser import instagram_session
from scrapers.instagram.navigation import discover_profile_links
from scrapers.instagram.comments.filters import (
    normalize_username,
    normalize_comment,
    is_user_comment,
    is_interesting_comment,
    is_question,
)
from scrapers.instagram.comments.extractors import (
    expand_comments,
    extract_comments,
)
from scrapers.instagram.extractors import extract_post_date


LOGGER = logging.getLogger(__name__)


class CommentScraper:
    """Extrae comentarios publicos de los posts de un perfil."""

    def __init__(self, headless=True, auth_file=None, logger=None):
        self.headless = headless
        self.auth_file = auth_file
        self.logger = logger or LOGGER
        self._seen_comments = set()

    def scrape_profile_comments(
        self,
        username,
        months=1,
        start_date=None,
        end_date=None,
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
        if start_date and start_date.tzinfo is None:
            raise ValueError("start_date debe incluir zona horaria.")
        if end_date and end_date.tzinfo is None:
            raise ValueError("end_date debe incluir zona horaria.")

        effective_end_date = end_date or datetime.now(timezone.utc)
        effective_start_date = start_date or (
            effective_end_date - timedelta(days=30 * months)
        )
        if effective_start_date > effective_end_date:
            raise ValueError("La fecha inicial no puede ser posterior a la fecha final.")

        self.logger.info(
            "Instagram | cuenta=%s | meses=%s | max_posts=%s | solo_preguntas=%s",
            username, months, max_posts or "sin_límite", only_questions,
        )
        self.logger.info(
            "Instagram | cuenta=%s | solo_interes=%s", username, interest_only
        )
        self.logger.info(
            "Instagram | cuenta=%s | fecha_inicio=%s | fecha_fin=%s",
            username,
            effective_start_date.date().isoformat(),
            effective_end_date.date().isoformat(),
        )
        results = []
        self._seen_comments = set()

        with instagram_session(headless=self.headless, auth_file=self.auth_file) as page:
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
                        start_date=effective_start_date,
                        end_date=effective_end_date,
                        only_questions=only_questions,
                        interest_only=interest_only,
                        results=results,
                        on_comment=on_comment,
                    )
                    self.logger.info(
                        "Instagram | cuenta=%s | recurso=%s/%s | comentarios=%s | fuera_rango=%s | url=%s",
                        username, index, len(post_links), count, old_post, link,
                    )
                except Exception:
                    self.logger.exception(
                        "Instagram | error procesando recurso | cuenta=%s | url=%s",
                        username, link,
                    )

        self.logger.info(
            "Instagram | cuenta=%s | total_exportado=%s", username, len(results)
        )
        return results

    @staticmethod
    def _is_post_in_range(post_date, start_date, end_date):
        """Permite procesar publicaciones sin fecha y filtra las fechas conocidas."""
        return post_date is None or start_date <= post_date <= end_date

    def _scrape_post_comments(
        self,
        page,
        post_url,
        username,
        start_date,
        end_date,
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
        if not self._is_post_in_range(post_date, start_date, end_date):
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
