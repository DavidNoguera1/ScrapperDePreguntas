import re
import logging

from playwright.sync_api import sync_playwright

from core.filters import is_question
from scrapers.tiktok.extractors import extract_comments, extract_video_id, generate_console_script


LOGGER = logging.getLogger(__name__)


class TikTokScraper:
    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy

    def scrape_video_comments(self, video_url, max_comments=200, only_questions=False):
        comments = []
        video_id = extract_video_id(video_url)

        if not video_id:
            raise ValueError(f"No se pudo extraer el ID del video: {video_url}")

        LOGGER.info("TikTok | abriendo video | id=%s | url=%s", video_id, video_url)

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                proxy=self.proxy,
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
            )
            page = context.new_page()

            page.route(re.compile(r"\.(png|jpg|jpeg|gif|svg|css|woff2?)$"), lambda route: route.abort())

            try:
                page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                page.wait_for_timeout(4000)

                for _ in range(15):
                    page.evaluate("window.scrollBy(0, 500)")
                    page.wait_for_timeout(1500)

                comments = extract_comments(page)
                LOGGER.info(
                    "TikTok | comentarios_encontrados=%s | url=%s",
                    len(comments), video_url,
                )

            except Exception:
                LOGGER.exception(
                    "TikTok | error durante la extracción | url=%s", video_url
                )
                raise
            finally:
                browser.close()

        if only_questions:
            comments = [c for c in comments if is_question(c)]

        return comments

    @staticmethod
    def generate_console_script():
        return generate_console_script()
