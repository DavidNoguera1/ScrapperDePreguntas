import re
import logging


LOGGER = logging.getLogger(__name__)


COMMENT_SELECTORS = [
    '[data-sigil="comment"]',
    'div[class*="comment"]',
    'article[class*="comment"]',
    'div[role="article"]',
    'div[class*="fbUserContent"]',
    'div[class*="story_body_container"]',
    'div[class*="inner"]',
]


def extract_comments(page):
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


def extract_account_from_url(url):
    m = re.search(r"facebook\.com/([^/?#]+)", url)
    return m.group(1) if m else "Desconocido"
