import os
import re
import json
import logging

from playwright.sync_api import sync_playwright

from core.filters import is_question
from scrapers.facebook.extractors import extract_comments, extract_account_from_url as _extract_account_from_url


LOGGER = logging.getLogger(__name__)


class FacebookScraper:
    def __init__(self, cookies_file=None, headless=True):
        self.cookies_file = cookies_file
        self.headless = headless

    def scrape_post_comments(self, post_url, only_questions=False):
        comments = []

        LOGGER.info("Facebook | abriendo post | url=%s", post_url)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=self.headless)
            context = browser.new_context(
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            page.route(re.compile(r"\.(png|jpg|jpeg|gif|svg|css|woff2?)$"), lambda route: route.abort())

            if self.cookies_file and os.path.exists(self.cookies_file):
                with open(self.cookies_file, encoding="utf-8") as f:
                    cookies = json.load(f)
                context.add_cookies(cookies)
                LOGGER.info("Facebook | cookies cargadas=%s", len(cookies))

            try:
                page.goto(post_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(5000)

                if "login" in page.url.lower() or "checkpoint" in page.url.lower():
                    LOGGER.warning(
                        "Facebook | se requiere una sesión activa | url=%s",
                        post_url,
                    )

                for _ in range(20):
                    page.evaluate("window.scrollBy(0, 400)")
                    page.wait_for_timeout(1000)
                    more = page.query_selector('text="View more comments"')
                    if more:
                        more.click()
                        page.wait_for_timeout(2000)

                comments = extract_comments(page)
                LOGGER.info(
                    "Facebook | comentarios_extraidos=%s | url=%s",
                    len(comments), post_url,
                )

            except Exception:
                LOGGER.exception(
                    "Facebook | error durante la extracción | url=%s", post_url
                )
                raise
            finally:
                browser.close()

        if only_questions:
            comments = [c for c in comments if is_question(c)]

        return comments

    @staticmethod
    def extract_account_from_url(url):
        return _extract_account_from_url(url)
