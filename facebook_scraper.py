import os
import re
import json
import time
import logging
from playwright.sync_api import sync_playwright


LOGGER = logging.getLogger(__name__)


QUESTION_PATTERN = re.compile(
    r'\b(?:'
    r'que\s*|qu[eé]\s*|qui[eé]n\s*|qui[eé]nes\s*|cu[aá]ndo\s*|d[oó]nde\s*|c[oó]mo\s*'
    r'|cu[aá]l\s*|cu[aá]les\s*|cu[aá]nt[oas]\s*|cu[aá]nt[oa]s\s*'
    r'|por\s+qu[eé]\s*|para\s+qu[eé]\s*|a\s+qu[eé]\s*'
    r')|(\?)', re.IGNORECASE
)


COMMENT_SELECTORS = [
    '[data-sigil="comment"]',
    'div[class*="comment"]',
    'article[class*="comment"]',
    'div[role="article"]',
    'div[class*="fbUserContent"]',
    'div[class*="story_body_container"]',
    'div[class*="inner"]',
]


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

                comments = self._extract_comments(page)
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
            comments = [c for c in comments if self._is_question(c)]

        return comments

    def _extract_comments(self, page):
        all_texts = set()

        for selector in COMMENT_SELECTORS:
            elements = page.query_selector_all(selector)
            for el in elements:
                text = el.inner_text().strip()
                if text and len(text) > 3:
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    comment_text = "\n".join(lines[1:]) if len(lines) > 1 else lines[0] if lines else text
                    all_texts.add(comment_text)
            if all_texts:
                break

        if not all_texts:
            try:
                raw = page.evaluate("""() => {
                    const items = document.querySelectorAll('[class*="comment"], [data-sigil*="comment"]');
                    return Array.from(items).map(el => el.innerText).filter(t => t.trim().length > 3);
                }""")
                all_texts.update(raw or [])
            except Exception:
                pass

        return sorted(all_texts)

    def _is_question(self, text):
        return bool(QUESTION_PATTERN.search(text))

    @staticmethod
    def extract_account_from_url(url):
        m = re.search(r"facebook\.com/([^/?#]+)", url)
        return m.group(1) if m else "Desconocido"
