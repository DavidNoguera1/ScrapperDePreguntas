import argparse
import logging
from datetime import datetime, timezone

from core.config import ask_yn
from core.csv_handler import open_csv, append_csv, save_csv, merge_csvs, CSV_FILE
from core.logger import setup_logging, LOG_FILE
from cli.menus import menu_instagram
from scrapers.instagram.scraper import InstagramScraper


LOGGER = logging.getLogger(__name__)


def _parse_instagram_cli_date(date_str):
    try:
        return datetime.strptime(date_str, "%d-%m-%Y").replace(tzinfo=timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(
            f"Fecha invalida: {date_str}. Usa el formato dd-mm-aaaa."
        ) from exc


def main():
    parser = argparse.ArgumentParser(description="Instagram Comment Scraper")
    parser.add_argument("--instagram", nargs="+", help="Cuentas de Instagram a scrapear")
    parser.add_argument("--months", type=int, default=2, help="Meses hacia atras (default: 2)")
    parser.add_argument(
        "--instagram-start-date",
        type=_parse_instagram_cli_date,
        default=None,
        help="Fecha inicial de publicaciones de Instagram (dd-mm-aaaa)",
    )
    parser.add_argument(
        "--instagram-end-date",
        type=_parse_instagram_cli_date,
        default=None,
        help="Fecha final de publicaciones de Instagram (dd-mm-aaaa, inclusiva)",
    )
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
    parser.add_argument(
        "--visible",
        action="store_true",
        help="Abrir navegador visible para el scraper de Instagram (Playwright)",
    )
    parser.add_argument("--merge", action="store_true", help="Mergear CSVs existentes")
    parser.add_argument(
        "--time-detection",
        nargs="+",
        metavar="CSV",
        help="CSVs de Metricool a los que anadir la columna Duracion de sus reels",
    )
    parser.add_argument(
        "--instagram-logout",
        action="store_true",
        help="Cerrar la sesion guardada de Instagram y borrar su archivo local",
    )
    args = parser.parse_args()

    instagram_start_date = args.instagram_start_date
    instagram_end_date = args.instagram_end_date
    if instagram_end_date:
        instagram_end_date = instagram_end_date.replace(
            hour=23, minute=59, second=59, microsecond=999999
        )
    if instagram_start_date and instagram_end_date and instagram_start_date > instagram_end_date:
        parser.error("--instagram-start-date no puede ser posterior a --instagram-end-date")

    setup_logging()
    print("=" * 55)
    print("  INSTAGRAM COMMENT SCRAPER")
    print("  Extrae comentarios de Instagram")
    print("=" * 55)

    if args.merge:
        merge_csvs()
        return

    if args.time_detection:
        scraper = InstagramScraper(headless=not args.visible)
        results = scraper.detect_reel_durations(args.time_detection)
        total = sum(results.values())
        print(f"\n  [OK] Duracion anadida a {total} reels en {len(results)} archivo(s)")
        for path, count in results.items():
            print(f"       {path}: {count} reels")
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
    if args.instagram:
        open_csv(args.output)

    if args.instagram:
        scraper = InstagramScraper()
        for acc in args.instagram:
            try:
                r = scraper.scrape_profile_comments(
                    acc,
                    months=args.months,
                    start_date=instagram_start_date,
                    end_date=instagram_end_date,
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

    if not args.instagram:
        while True:
            print("""
  --- MENU PRINCIPAL ---
    1. Instagram (por cuenta)
    2. Mergear CSVs existentes
    3. Salir
 """)
            choice = input("  Opcion [1-3]: ").strip()

            if choice == "1":
                all_results.extend(menu_instagram())
            elif choice == "2":
                merge_csvs()
                continue
            elif choice in ("3", "q", "salir"):
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
