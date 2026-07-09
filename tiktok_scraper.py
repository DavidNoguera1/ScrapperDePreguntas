import re
import time
import json
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


TIKTOK_SELECTORS = [
    '[data-e2e="comment-item"]',
    '[data-e2e="comment-level-1"]',
    '.tiktok-comment-item',
    '[class*="CommentItem"]',
    '[class*="DivCommentItem"]',
    '[class*="comment"]',
    'div[class*="Comment"]',
]


class TikTokScraper:
    def __init__(self, headless=True, proxy=None):
        self.headless = headless
        self.proxy = proxy

    def scrape_video_comments(self, video_url, max_comments=200, only_questions=False):
        comments = []
        video_id = self._extract_video_id(video_url)

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

                comments = self._extract_comments(page)
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
            comments = [c for c in comments if self._is_question(c)]

        return comments

    def _extract_comments(self, page):
        all_texts = set()

        for selector in TIKTOK_SELECTORS:
            elements = page.query_selector_all(selector)
            if elements:
                for el in elements:
                    text = el.inner_text().strip()
                    if text and len(text) > 2:
                        all_texts.add(text)
                if all_texts:
                    break

        if not all_texts:
            try:
                script = page.query_selector('script#__UNIVERSAL_DATA_FOR_REHYDRATION__')
                if script:
                    data = json.loads(script.inner_text())
                    for item in data.get("__DEFAULT_SCOPE__", {}).get("webapp.comment-list", {}).get("comments", []):
                        t = item.get("text", "").strip()
                        if t:
                            all_texts.add(t)
            except Exception:
                pass

        if not all_texts:
            try:
                raw = page.evaluate("""() => {
                    const items = document.querySelectorAll('[class*="comment"]');
                    return Array.from(items).map(el => el.innerText).filter(t => t.trim().length > 2);
                }""")
                all_texts.update(raw or [])
            except Exception:
                pass

        return sorted(all_texts)

    def _is_question(self, text):
        return bool(QUESTION_PATTERN.search(text))

    @staticmethod
    def _extract_video_id(url):
        patterns = [
            r"tiktok\.com/@[\w.-]+/video/(\d+)",
            r"vm\.tiktok\.com/([\w]+)",
            r"tiktok\.com/v/(\d+)",
        ]
        for p in patterns:
            m = re.search(p, url)
            if m:
                return m.group(1)
        return None

    @staticmethod
    def generate_console_script():
        return """// TikTok Comment Scraper - Pega esto en la consola del navegador
// 1. Abre el video de TikTok
// 2. Presiona F12 → Consola
// 3. Pega y ejecuta este script

(async () => {
    const delay = ms => new Promise(r => setTimeout(r, ms));
    let comments = new Set();

    for (let i = 0; i < 30; i++) {
        window.scrollBy(0, 500);
        await delay(1500);

        document.querySelectorAll('[data-e2e="comment-item"], [class*="comment"]').forEach(el => {
            const t = el.innerText?.trim();
            if (t && t.length > 2) comments.add(t);
        });
    }

    const csv = Array.from(comments).map(c => `"${c.replace(/"/g, '""')}"`).join('\\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'tiktok_comments.csv';
    a.click();
    console.log(`✅ ${comments.size} comentarios exportados`);
})();
"""
