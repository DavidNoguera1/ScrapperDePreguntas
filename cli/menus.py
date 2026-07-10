import os
import logging
from datetime import datetime

from core.config import fmt_dia, fmt_mes, ask_yn
from core.csv_handler import open_csv, append_csv, CSV_FILE
from core.logger import LOGGER
from scrapers.instagram.scraper import InstagramScraper
from scrapers.tiktok.scraper import TikTokScraper
from scrapers.facebook.scraper import FacebookScraper


def menu_instagram():
    has_auth = InstagramScraper().has_saved_session()

    if not has_auth:
        print("\n  [i] Instagram requiere login. Abrire el navegador para que inicies sesion.")
        print("  [i] La sesion se guardara para no pedirla de nuevo.")
        if ask_yn("  Abrir navegador ahora?", default=True):
            s = InstagramScraper()
            s.register_manual_login()
        else:
            print("  Puedes crear la sesion despues con: python -c \"from scrapers.instagram.scraper import InstagramScraper; InstagramScraper().register_manual_login()\"")

    accounts = input("\n  Cuentas de Instagram a escanear (separadas por coma): ").strip()
    if not accounts:
        print("  Debes ingresar al menos una cuenta.")
        return []

    accounts = [a.strip() for a in accounts.split(",") if a.strip()]

    months = input("  Cuantos meses hacia atras? [2]: ").strip()
    months = int(months) if months.isdigit() else 2

    interest_only = ask_yn(
        "  Solo comentarios de interes legal (preguntas y casos de tramites)?",
        default=True,
    )
    only_q = ask_yn("  Dentro de esos, solo preguntas?", default=False)

    raw_max = input("  Limite de posts por cuenta? (Enter = sin limite): ").strip()
    max_posts = int(raw_max) if raw_max.isdigit() else None

    visible = not ask_yn("  Ejecutar en segundo plano (headless)?", default=True)
    open_csv()
    print(f"\n  Iniciando scraper de Instagram...")

    scraper = InstagramScraper(headless=not visible)
    all_results = []

    for acc in accounts:
        try:
            results = scraper.scrape_profile_comments(
                username=acc,
                months=months,
                max_posts=max_posts,
                only_questions=only_q,
                interest_only=interest_only,
                on_comment=append_csv,
            )
            all_results.extend(results)
            print(f"  [OK] {acc}: {len(results)} comentarios extraidos")
        except Exception as e:
            LOGGER.exception("Error extrayendo cuenta de Instagram: %s", acc)
            print(f"  [ERROR] {acc}: {e}")

    return all_results


def menu_tiktok():
    print("""
  TikTok - Modos disponibles:
    1. Automatico (Playwright) - Recomendado
    2. Script para consola del navegador
""")

    mode = input("  Modo [1]: ").strip() or "1"

    if mode == "2":
        print("\n  --- Script para copiar en la consola del navegador ---")
        print(TikTokScraper.generate_console_script())
        print("  ---")
        print("\n  Instrucciones:")
        print("  1. Abre el video de TikTok en Chrome/Edge/Brave")
        print("  2. Presiona F12, luego pestana 'Console'")
        print("  3. Pega el script y presiona Enter")
        print("  4. Se descargara un CSV con los comentarios")
        input("\n  Presiona Enter para continuar...")
        return []

    videos = input("\n  URLs de videos TikTok (separadas por coma): ").strip()
    urls = [u.strip() for u in videos.split(",") if u.strip()]

    if not urls:
        print("  Debes ingresar al menos una URL.")
        return []

    only_q = ask_yn("  Solo comentarios que sean preguntas?", default=False)
    visible = not ask_yn("  Ejecutar en segundo plano (headless)?", default=True)

    account = input("  Nombre de la cuenta (para el CSV): ").strip()
    if not account and "/@" in urls[0]:
        account = urls[0].split("/@")[1].split("/")[0]
    elif not account:
        account = "TikTok"

    open_csv()
    print(f"\n  Iniciando scraper de TikTok...")
    scraper = TikTokScraper(headless=not visible)
    all_results = []

    for url in urls:
        try:
            comments = scraper.scrape_video_comments(url, only_questions=only_q)
            now = datetime.now()
            for c in comments:
                row = {
                    "Dia": fmt_dia(now),
                    "Cuenta": account,
                    "Red Social": "TikTok",
                    "Tipo de publicacion": "Video",
                    "Enlace": url,
                    "Comentario": c,
                    "Tema principal": "",
                    "Mes": fmt_mes(now),
                }
                all_results.append(row)
                append_csv(row)
            print(f"  [OK] {len(comments)} comentarios del video")
        except Exception as e:
            LOGGER.exception("Error extrayendo video de TikTok: %s", url)
            print(f"  [ERROR] {url}: {e}")

    return all_results


def menu_facebook():
    cookies_file = os.getenv("FACEBOOK_COOKIES_FILE")

    print("""
  Facebook: extraccion por URL de post
  (Necesitas cookies de sesion activa para ver comentarios)
""")

    posts_input = input("  URLs de posts de Facebook (separadas por coma): ").strip()
    urls = [u.strip() for u in posts_input.split(",") if u.strip()]

    if not urls:
        print("  Debes ingresar al menos una URL.")
        return []

    only_q = ask_yn("  Solo comentarios que sean preguntas?", default=False)
    visible = not ask_yn("  Ejecutar en segundo plano (headless)?", default=True)

    if not cookies_file or not os.path.exists(cookies_file):
        print("\n  [i] No hay archivo de cookies. El scraper abrira el navegador visible.")
        print("  [i] Deberas iniciar sesion manualmente en la ventana que se abra.")
        if not ask_yn("  Continuar de todas formas?", default=False):
            return []

    open_csv()
    print(f"\n  Iniciando scraper de Facebook...")
    scraper = FacebookScraper(
        cookies_file=cookies_file if cookies_file and os.path.exists(cookies_file) else None,
        headless=not visible,
    )
    all_results = []

    for url in urls:
        try:
            account = FacebookScraper.extract_account_from_url(url)
            comments = scraper.scrape_post_comments(url, only_questions=only_q)
            now = datetime.now()
            for c in comments:
                row = {
                    "Dia": fmt_dia(now),
                    "Cuenta": account,
                    "Red Social": "Facebook",
                    "Tipo de publicacion": "Post",
                    "Enlace": url,
                    "Comentario": c,
                    "Tema principal": "",
                    "Mes": fmt_mes(now),
                }
                all_results.append(row)
                append_csv(row)
            print(f"  [OK] {len(comments)} comentarios del post")
        except Exception as e:
            LOGGER.exception("Error extrayendo post de Facebook: %s", url)
            print(f"  [ERROR] {url}: {e}")

    return all_results
