import re
import json
import logging


LOGGER = logging.getLogger(__name__)


TIKTOK_SELECTORS = [
    '[data-e2e="comment-item"]',
    '[data-e2e="comment-level-1"]',
    '.tiktok-comment-item',
    '[class*="CommentItem"]',
    '[class*="DivCommentItem"]',
    '[class*="comment"]',
    'div[class*="Comment"]',
]


def extract_comments(page):
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


def extract_video_id(url):
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
