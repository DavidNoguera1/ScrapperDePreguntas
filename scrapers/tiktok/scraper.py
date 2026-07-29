import re
import json
import logging
from datetime import datetime, timezone

import requests
from playwright.sync_api import sync_playwright

from core.filters import is_question
from scrapers.tiktok.extractors import (
    extract_comments,
    extract_video_id,
    generate_console_script,
    extract_profile_videos,
    extract_username_from_url,
    extract_items_from_xhr_json,
    extract_videos_from_page_js,
    parse_video_metrics,
    filter_videos_by_date,
)


LOGGER = logging.getLogger(__name__)

TIKTOK_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/125.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Referer": "https://www.tiktok.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}


# Scroll JS que se ejecuta en el navegador para cargar más videos
SCROLL_JS = """
() => {
    const wait = ms => new Promise(r => setTimeout(r, ms));
    const container = document.querySelector('main') || document.scrollingElement || document.body;
    let lastHeight = 0;
    let noChange = 0;
    async function doScroll() {
        for (let i = 0; i < 20; i++) {
            const h = container.scrollHeight;
            if (h === lastHeight) {
                noChange++;
                if (noChange > 3) break;
            } else {
                noChange = 0;
            }
            lastHeight = h;
            container.scrollTo(0, h);
            await wait(2500);
        }
    }
    return doScroll();
}
"""


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

    def scrape_profile(self, username, start_date=None, end_date=None):
        """Scrapea los videos de un perfil de TikTok y devuelve sus métricas.

        Args:
            username: nombre de usuario (sin @) o URL completa del perfil
            start_date: datetime opcional (inclusive) para filtrar por fecha
            end_date: datetime opcional (inclusive) para filtrar por fecha
        Returns:
            Lista de dicts con: id, title, create_time, likes, comments,
            saves, shares, plays, duration, url
        """
        if "tiktok.com" in username:
            username = extract_username_from_url(username) or username

        profile_url = f"https://www.tiktok.com/@{username}"
        LOGGER.info("TikTok | scraping perfil | user=%s", username)

        # Intentar primero con Playwright (XHR interception = más datos)
        try:
            videos = self._scrape_profile_playwright(profile_url, start_date, end_date)
            if videos:
                return videos
        except Exception as e:
            LOGGER.warning("TikTok | Playwright fallo, intentando requests | user=%s error=%s", username, e)

        # Fallback: requests + HTML parsing
        html = self._fetch_profile_html_requests(profile_url)
        if html:
            LOGGER.info("TikTok | HTML obtenido via requests | user=%s", username)
            videos = extract_profile_videos(html, start_date, end_date)
            if videos:
                LOGGER.info(
                    "TikTok | videos_encontrados=%s | user=%s", len(videos), username
                )
                return videos
            LOGGER.warning("TikTok | HTML no contenía videos | user=%s", username)
        else:
            LOGGER.warning("TikTok | no se pudo obtener HTML | user=%s", username)

        return []

    def _fetch_profile_html_requests(self, profile_url):
        """Intenta obtener el HTML del perfil usando requests (método rápido)."""
        try:
            session = requests.Session()
            session.headers.update(TIKTOK_HEADERS)
            resp = session.get(
                profile_url,
                timeout=30,
                allow_redirects=True,
            )
            if resp.status_code == 200 and "__UNIVERSAL_DATA_FOR_REHYDRATION__" in resp.text:
                LOGGER.info(
                    "TikTok | HTML obtenido via requests (status=%s) | url=%s",
                    resp.status_code, profile_url,
                )
                return resp.text
            LOGGER.warning(
                "TikTok | requests fallo (status=%s, url=%s)",
                resp.status_code, profile_url,
            )
        except requests.RequestException:
            LOGGER.warning("TikTok | requests error | url=%s", profile_url)
        return None

    def _scrape_profile_playwright(self, profile_url, start_date=None, end_date=None):
        """Scrapea videos del perfil usando Playwright con XHR interception y scroll.
        
        Estrategia:
        1. Intercepta respuestas XHR a /api/post/item_list/ (contienen todos los videos)
        2. Hace scroll para gatillar la carga de más videos via el item_list API
        3. Si XHR no funciona, extrae desde JSON en el DOM
        4. Último recurso: parsea el HTML completo
        """
        all_items = []
        xhr_responses = []

        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=self.headless,
                proxy=self.proxy,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-dev-shm-usage",
                    "--no-sandbox",
                    "--disable-gpu-sandbox",
                    "--disable-web-security",
                ],
            )
            context = browser.new_context(
                viewport={"width": 1920, "height": 1080},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                locale="es-ES",
                timezone_id="America/Mexico_City",
                permissions=["geolocation"],
            )
            page = context.new_page()

            # Abortar recursos no críticos
            page.route(
                re.compile(r"\.(png|jpg|jpeg|gif|svg|css|woff2?|webp|ico)$"),
                lambda route: route.abort(),
            )

            # Interceptar XHR de item_list y user_detail
            page.on("response", lambda resp: self._on_item_list_response(resp, xhr_responses))

            try:
                LOGGER.info("TikTok | Playwright abriendo perfil | url=%s", profile_url)
                page.goto(profile_url, wait_until="domcontentloaded", timeout=45000)
                page.wait_for_timeout(5000)

                # Scroll para cargar más videos
                LOGGER.info("TikTok | haciendo scroll para cargar videos...")
                try:
                    page.evaluate(SCROLL_JS)
                except Exception:
                    LOGGER.warning("TikTok | scroll JS fallo, usando scroll basico")
                    for _ in range(12):
                        page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                        page.wait_for_timeout(2000)

                page.wait_for_timeout(3000)

                # 1. Extraer items desde XHR interceptados
                if xhr_responses:
                    LOGGER.info(
                        "TikTok | XHR interceptados=%s | url=%s",
                        len(xhr_responses), profile_url,
                    )
                    seen_ids = set()
                    for body in xhr_responses:
                        items = extract_items_from_xhr_json(body)
                        for item in items:
                            vid = item.get("id") or item.get("awemeId", "")
                            if vid and vid not in seen_ids:
                                seen_ids.add(vid)
                                all_items.append(item)
                    LOGGER.info(
                        "TikTok | items_desde_XHR=%s | url=%s",
                        len(all_items), profile_url,
                    )

                # 2. Si XHR no funcionó, intentar con JS directo desde el DOM
                if not all_items:
                    LOGGER.info("TikTok | XHR no disponible, extrayendo desde DOM...")
                    dom_items = extract_videos_from_page_js(page)
                    if dom_items:
                        seen_ids = set()
                        for item in dom_items:
                            vid = item.get("id") or item.get("awemeId", "")
                            if vid and vid not in seen_ids:
                                seen_ids.add(vid)
                                all_items.append(item)
                        LOGGER.info(
                            "TikTok | items_desde_DOM=%s | url=%s",
                            len(all_items), profile_url,
                        )

                # 3. Último recurso: intentar parsear HTML
                if not all_items:
                    LOGGER.info("TikTok | DOM fallo, intentando desde HTML...")
                    html = page.content()
                    videos = extract_profile_videos(html, start_date, end_date)
                    if videos:
                        LOGGER.info(
                            "TikTok | videos_desde_html=%s | url=%s",
                            len(videos), profile_url,
                        )
                        return videos

                # Parsear items recolectados a formato métricas
                if all_items:
                    videos = [parse_video_metrics(item) for item in all_items]
                    videos = [v for v in videos if v["id"]]
                    if start_date or end_date:
                        videos = filter_videos_by_date(videos, start_date, end_date)
                    LOGGER.info(
                        "TikTok | videos_final=%s | url=%s",
                        len(videos), profile_url,
                    )
                    return videos

                LOGGER.warning("TikTok | no se encontraron videos | url=%s", profile_url)
                return []

            except Exception:
                LOGGER.exception("TikTok | error en Playwright | url=%s", profile_url)
                raise
            finally:
                browser.close()

    def _on_item_list_response(self, response, xhr_responses):
        """Callback para interceptar respuestas XHR de /api/post/item_list/."""
        try:
            url = response.url
            if "/api/post/item_list/" in url or "/api/video/item_list/" in url:
                body = response.body()
                if body and len(body) > 10:
                    text = body.decode("utf-8", errors="replace")
                    if '"itemList"' in text or '"items"' in text:
                        xhr_responses.append(text)
                        LOGGER.debug("TikTok | XHR capturado | url=%s", url[:120])
        except Exception:
            pass

    @staticmethod
    def generate_console_script():
        return generate_console_script()
