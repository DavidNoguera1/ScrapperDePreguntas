import re
import json
import logging
from datetime import datetime, timezone


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


def _find_items_in_user_detail(user_detail):
    """Busca items de video en múltiples rutas posibles del JSON de user-detail."""
    paths = [
        ("items", lambda d: d.get("items", [])),
        ("itemList", lambda d: d.get("itemList", [])),
        ("userInfo.items", lambda d: d.get("userInfo", {}).get("items", [])),
        ("userInfo.itemList", lambda d: d.get("userInfo", {}).get("itemList", [])),
        ("posts", lambda d: d.get("posts", [])),
    ]
    for name, path_fn in paths:
        try:
            items = path_fn(user_detail)
            if items and len(items) > 0:
                LOGGER.info("Items encontrados via: %s", name)
                return items, name
        except Exception:
            continue
    return [], None


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


def extract_rehydration_json(html):
    """Extrae el JSON __UNIVERSAL_DATA_FOR_REHYDRATION__ del HTML de una página de TikTok."""
    if not html:
        return None
    try:
        script = re.search(
            r'<script[^>]*id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>',
            html,
            re.DOTALL,
        )
        if not script:
            return None
        return json.loads(script.group(1))
    except (json.JSONDecodeError, AttributeError):
        return None


def _find_items_in_other_scopes(default_scope):
    """Busca items en otros scopes del JSON (video-feed, mc-feed, etc)."""
    scope_paths = [
        "webapp.video-feed",
        "webapp.mc-feed",
        "webapp.search-detail",
    ]
    for scope_key in scope_paths:
        scope_data = default_scope.get(scope_key, {})
        if not scope_data:
            continue
        for list_key in ("items", "itemList", "videos", "data"):
            try:
                items = scope_data.get(list_key, [])
                if items and len(items) > 0:
                    LOGGER.info("Items encontrados via scope=%s list=%s", scope_key, list_key)
                    return items
            except Exception:
                continue
    return []


def extract_profile_data_from_html(html):
    """Extrae datos del perfil (userInfo + items) del HTML de la página de perfil.
    
    Busca items en múltiples rutas posibles porque TikTok cambia la estructura JSON frecuentemente.
    """
    data = extract_rehydration_json(html)
    if not data:
        return None

    default_scope = data.get("__DEFAULT_SCOPE__", {})
    user_detail = default_scope.get("webapp.user-detail", {})

    items, source = _find_items_in_user_detail(user_detail)

    if not items:
        items = _find_items_in_other_scopes(default_scope)
        if items:
            source = "other_scope"

    return {
        "userInfo": user_detail.get("userInfo", {}),
        "items": items,
        "_source": source,
    }


def parse_video_metrics(video):
    """Extrae las métricas de un video de TikTok desde el objeto JSON del perfil.

    Campos extraídos:
      - id: ID del video
      - title: título / descripción del video
      - create_time: timestamp Unix de creación
      - likes: número de me gustas
      - comments: número de comentarios
      - saves: número de guardados
      - shares: número de compartidos
      - plays: número de reproducciones (opcional)
      - url: URL directa al video
    """
    stats = video.get("stats", {}) or {}
    video_info = video.get("video", {}) or {}

    video_id = video.get("id") or video.get("awemeId", "")
    title = video.get("desc", "") or video.get("caption", "")
    create_time = video.get("createTime", 0)

    likes = stats.get("diggCount", 0)
    comments = stats.get("commentCount", 0)
    saves = stats.get("collectCount", 0)
    shares = stats.get("shareCount", 0)
    plays = stats.get("playCount", 0)

    url = ""
    if video_id:
        username = video.get("author", {}).get("uniqueId", "")
        if username:
            url = f"https://www.tiktok.com/@{username}/video/{video_id}"

    return {
        "id": video_id,
        "title": title,
        "create_time": create_time,
        "likes": likes,
        "comments": comments,
        "saves": saves,
        "shares": shares,
        "plays": plays,
        "url": url,
    }


def filter_videos_by_date(videos, start_date=None, end_date=None):
    """Filtra una lista de videos por rango de fechas.

    Args:
        videos: lista de dicts con al menos 'create_time' (timestamp Unix)
        start_date: datetime (inclusive) o None
        end_date: datetime (inclusive) o None
    Returns:
        Lista filtrada de videos
    """
    filtered = []
    for v in videos:
        ct = v.get("create_time", 0)
        if not ct:
            continue
        try:
            video_dt = datetime.fromtimestamp(int(ct), tz=timezone.utc)
        except (ValueError, OSError):
            continue

        if start_date and video_dt < start_date:
            continue
        if end_date and video_dt > end_date:
            continue
        filtered.append(v)

    return filtered


def extract_profile_videos(html, start_date=None, end_date=None):
    """Extrae y filtra los videos de un perfil desde el HTML.

    Args:
        html: HTML de la página de perfil de TikTok
        start_date: datetime opcional (inclusive)
        end_date: datetime opcional (inclusive)
    Returns:
        Lista de dicts con métricas de cada video (filtrados por fecha)
    """
    profile_data = extract_profile_data_from_html(html)
    if not profile_data:
        return []

    items = profile_data.get("items", [])
    if not items:
        return []

    videos = [parse_video_metrics(item) for item in items]
    videos = [v for v in videos if v["id"]]

    if start_date or end_date:
        videos = filter_videos_by_date(videos, start_date, end_date)

    return videos


def extract_items_from_xhr_json(response_body):
    """Extrae items de video desde la respuesta XHR de /api/post/item_list/."""
    if not response_body:
        return []
    try:
        data = json.loads(response_body)
        items = data.get("itemList", []) or data.get("items", []) or data.get("data", [])
        return items
    except (json.JSONDecodeError, TypeError, AttributeError):
        return []


def extract_videos_from_page_js(page):
    """Extrae items de video desde el DOM usando JavaScript (fallback cuando XHR no se intercepta)."""
    try:
        raw = page.evaluate("""() => {
            const scripts = document.querySelectorAll('script');
            const results = [];
            for (const s of scripts) {
                if (s.id === '__UNIVERSAL_DATA_FOR_REHYDRATION__' && s.text) {
                    try {
                        const d = JSON.parse(s.text);
                        const scope = d.__DEFAULT_SCOPE__ || {};
                        const ud = scope['webapp.user-detail'] || {};
                        const list = ud.items || ud.itemList || (ud.userInfo && (ud.userInfo.itemList || ud.userInfo.items)) || [];
                        if (list.length) results.push(...list);
                    } catch(e) {}
                }
                // Buscar en state modules
                if (s.type === 'application/json' && s.text) {
                    try {
                        const d = JSON.parse(s.text);
                        const items = d.itemList || d.items || [];
                        if (items.length) results.push(...items);
                    } catch(e) {}
                }
            }
            // Buscar en atributos data-* de divs
            const divs = document.querySelectorAll('div[data-items]');
            for (const div of divs) {
                try { const items = JSON.parse(div.getAttribute('data-items')); if (items.length) results.push(...items); } catch(e) {}
            }
            return results;
        }""")
        if raw:
            return raw
    except Exception:
        pass
    return []


def extract_username_from_url(url):
    """Extrae el username de una URL de perfil de TikTok."""
    match = re.search(r"tiktok\.com/@([\w.-]+)", url)
    if match:
        return match.group(1)
    return None
