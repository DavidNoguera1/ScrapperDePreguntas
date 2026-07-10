import argparse
import logging
import os
from datetime import datetime

from core.config import fmt_dia, fmt_mes, ask_yn
from core.csv_handler import open_csv, append_csv, save_csv, merge_csvs, CSV_FILE
from core.logger import setup_logging, LOG_FILE
from cli.menus import menu_instagram, menu_tiktok, menu_facebook
from scrapers.instagram.scraper import InstagramScraper


LOGGER = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(description="Social Media Comment Scraper")
    parser.add_argument("--instagram", nargs="+", help="Cuentas de Instagram a scrapear")
    parser.add_argument("--tiktok", nargs="+", help="URLs de videos TikTok")
    parser.add_argument("--facebook", nargs="+", help="URLs de posts de Facebook")
    parser.add_argument("--months", type=int, default=2, help="Meses hacia atras (default: 2)")
    parser.add_argument(
        "--max-posts",
        type=int,
        default=None,
        help="Limite de posts/reels por cuenta de Instagram",
    )
    parser.add_argument(
        "--questions-only",
        action=argparse.BooleanOptionalAction,
        default=False,
        help="Filtrar solo preguntas (por defecto: no filtrar)",
    )
    parser.add_argument(
        "--interest-only",
        action=argparse.BooleanOptionalAction,
        default=True,
        help="Filtrar preguntas y casos legales sustantivos (por defecto: si)",
    )
    parser.add_argument("--output", help="Nombre del archivo CSV de salida")
    parser.add_argument("--merge", action="store_true", help="Mergear CSVs existentes")
    parser.add_argument(
        "--instagram-logout",
        action="store_true",
        help="Cerrar la sesion guardada de Instagram y borrar su archivo local",
    )
    args = parser.parse_args()

    setup_logging()
    print("=" * 55)
    print("  SOCIAL MEDIA COMMENT SCRAPER")
    print("  Extrae comentarios de Instagram, TikTok y Facebook")
    print("=" * 55)

    if args.merge:
        merge_csvs()
        return

    if args.instagram_logout:
        status = InstagramScraper().logout_saved_session()
        if status["local_deleted"]:
            print("  [OK] Sesion local de Instagram eliminada.")
        else:
            print("  [i] No habia una sesion local guardada.")
        if status["server_revoked"]:
            print("  [OK] Instagram confirmo el cierre remoto.")
        else:
            print("  [AVISO] No se pudo confirmar el cierre remoto.")
        return

    all_results = []
    cli_extraction = any([args.instagram, args.tiktok, args.facebook])
    if cli_extraction:
        open_csv(args.output)

    if args.instagram:
        scraper = InstagramScraper()
        for acc in args.instagram:
            try:
                r = scraper.scrape_profile_comments(
                    acc,
                    months=args.months,
                    max_posts=args.max_posts,
                    only_questions=args.questions_only,
                    interest_only=args.interest_only,
                    on_comment=append_csv,
                )
                all_results.extend(r)
                print(f"  [OK] {acc}: {len(r)} comentarios")
            except Exception as e:
                LOGGER.exception("Error extrayendo cuenta de Instagram: %s", acc)
                print(f"  [ERROR] {acc}: {e}")

    if args.tiktok:
        from scrapers.tiktok.scraper import TikTokScraper
        scraper = TikTokScraper()
        for url in args.tiktok:
            try:
                comments = scraper.scrape_video_comments(url, only_questions=args.questions_only)
                account = url.split("/@")[1].split("/")[0] if "/@" in url else "TikTok"
                now = datetime.now()
                for c in comments:
                    row = {
                        "Dia": fmt_dia(now),
                        "Cuenta": account, "Red Social": "TikTok",
                        "Tipo de publicacion": "Video", "Enlace": url,
                        "Comentario": c, "Tema principal": "",
                        "Mes": fmt_mes(now),
                    }
                    all_results.append(row)
                    append_csv(row)
                print(f"  [OK] Video: {len(comments)} comentarios")
            except Exception as e:
                LOGGER.exception("Error extrayendo video de TikTok: %s", url)
                print(f"  [ERROR] {url}: {e}")

    if args.facebook:
        from scrapers.facebook.scraper import FacebookScraper
        cookies = os.getenv("FACEBOOK_COOKIES_FILE")
        scraper = FacebookScraper(cookies_file=cookies)
        for url in args.facebook:
            try:
                account = FacebookScraper.extract_account_from_url(url)
                comments = scraper.scrape_post_comments(url, only_questions=args.questions_only)
                now = datetime.now()
                for c in comments:
                    row = {
                        "Dia": fmt_dia(now),
                        "Cuenta": account, "Red Social": "Facebook",
                        "Tipo de publicacion": "Post", "Enlace": url,
                        "Comentario": c, "Tema principal": "",
                        "Mes": fmt_mes(now),
                    }
                    all_results.append(row)
                    append_csv(row)
                print(f"  [OK] Post: {len(comments)} comentarios")
            except Exception as e:
                LOGGER.exception("Error extrayendo post de Facebook: %s", url)
                print(f"  [ERROR] {url}: {e}")

    if not any([args.instagram, args.tiktok, args.facebook]):
        while True:
            print("""
  --- MENU PRINCIPAL ---
    1. Instagram (por cuenta)
    2. TikTok (por URL de video)
    3. Facebook (por URL de post)
    4. Mergear CSVs existentes
    5. Salir
""")
            choice = input("  Opcion [1-5]: ").strip()

            if choice == "1":
                all_results.extend(menu_instagram())
            elif choice == "2":
                all_results.extend(menu_tiktok())
            elif choice == "3":
                all_results.extend(menu_facebook())
            elif choice == "4":
                merge_csvs()
                continue
            elif choice in ("5", "q", "salir"):
                break
            else:
                print("  Opcion invalida")
                continue

            if CSV_FILE:
                with open(CSV_FILE, encoding="utf-8-sig") as _f:
                    lines = sum(1 for _ in _f) - 1
                print(f"\n  [*] CSV en vivo: {CSV_FILE} ({lines} comentarios)")

            if not ask_yn("\n  Quieres hacer otra extraccion?", default=False):
                break

    if CSV_FILE:
        print(f"\n  [OK] Reporte terminado: {CSV_FILE}")
        print(f"  [*] Total exportado en esta ejecucion: {len(all_results)} comentarios")
        print(f"  [*] Log detallado: {LOG_FILE}")
    elif all_results:
        save_csv(all_results, args.output)


if __name__ == "__main__":
    main()
