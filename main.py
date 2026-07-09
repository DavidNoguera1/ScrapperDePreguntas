import os
import argparse
import csv
import logging
from datetime import datetime

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

CSV_HEADERS = [
    "Dia", "Cuenta", "Red Social", "Tipo de publicacion", "Enlace",
    "Comentario", "Tema principal", "Mes",
]

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")
os.makedirs(LOG_DIR, exist_ok=True)

LOGGER = logging.getLogger(__name__)
LOG_FILE = None


MONTHS_ES = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}

MONTH_ABBR_ES = {
    1: "ene", 2: "feb", 3: "mar", 4: "abr",
    5: "may", 6: "jun", 7: "jul", 8: "ago",
    9: "sep", 10: "oct", 11: "nov", 12: "dic",
}


def fmt_dia(dt):
    return f"{dt.day:02d}-{MONTH_ABBR_ES[dt.month]}"


def fmt_mes(dt):
    return MONTHS_ES[dt.month]


def ask_yn(prompt, default=True):
    opts = " [Y/n]: " if default else " [y/N]: "
    resp = input(prompt + opts).strip().lower()
    if not resp:
        return default
    return resp in ("y", "yes", "s", "si")


CSV_FILE = None


def setup_logging():
    global LOG_FILE
    if LOG_FILE:
        return LOG_FILE

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    LOG_FILE = os.path.join(LOG_DIR, f"scraper_{timestamp}.log")
    root = logging.getLogger()
    root.setLevel(logging.DEBUG)
    root.handlers.clear()

    file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    ))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(message)s"))

    root.addHandler(file_handler)
    root.addHandler(console_handler)
    LOGGER.info("Log de ejecución: %s", LOG_FILE)
    return LOG_FILE


def open_csv(filename=None):
    global CSV_FILE
    if CSV_FILE:
        return CSV_FILE
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraping_{timestamp}.csv"
    filename = os.path.basename(filename)
    CSV_FILE = os.path.join(OUTPUT_DIR, filename)
    with open(CSV_FILE, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_HEADERS,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
            extrasaction="ignore",
        )
        writer.writeheader()
    LOGGER.info("CSV en vivo: %s", CSV_FILE)
    print(f"\n  [*] CSV en vivo: {CSV_FILE}")
    print(f"  [*] Abrelo en Excel mientras se llena!")
    return CSV_FILE


def append_csv(row_dict):
    if not CSV_FILE:
        raise RuntimeError("El CSV no ha sido inicializado.")
    with open(CSV_FILE, "a", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=CSV_HEADERS,
            delimiter=";",
            quoting=csv.QUOTE_MINIMAL,
            extrasaction="ignore",
        )
        writer.writerow({header: row_dict.get(header, "") for header in CSV_HEADERS})


def save_csv(results, filename=None):
    if not results:
        return None
    df = pd.DataFrame(results)
    available = [c for c in CSV_HEADERS if c in df.columns]
    df = df[available]
    if not filename:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"scraping_{timestamp}.csv"
    filepath = os.path.join(OUTPUT_DIR, filename)
    df.to_csv(filepath, index=False, encoding="utf-8-sig", sep=";")
    LOGGER.info("CSV final: %s | registros=%s", filepath, len(df))
    print(f"\n  [OK] CSV final: {filepath}")
    print(f"  [*] Total: {len(df)} comentarios")
    return filepath


def merge_csvs():
    files = [f for f in os.listdir(OUTPUT_DIR) if f.endswith(".csv")]
    if not files:
        print("  No hay CSVs en la carpeta output/")
        return

    print("\n  Archivos disponibles:")
    for i, f in enumerate(files, 1):
        print(f"    {i}. {f}")

    selected = input("\n  Numeros a mergear (ej: 1,2,3): ").strip()
    indices = [int(x.strip()) - 1 for x in selected.split(",") if x.strip().isdigit()]

    dfs = []
    for idx in indices:
        if 0 <= idx < len(files):
            filepath = os.path.join(OUTPUT_DIR, files[idx])
            try:
                df = pd.read_csv(
                    filepath,
                    encoding="utf-8-sig",
                    sep=None,
                    engine="python",
                )
                missing = [header for header in CSV_HEADERS if header not in df.columns]
                if missing:
                    LOGGER.warning(
                        "No se mergea %s: faltan columnas %s", filepath, missing
                    )
                    print(f"  [AVISO] Se omite {files[idx]}: formato incompatible.")
                    continue
                dfs.append(df[CSV_HEADERS])
            except Exception:
                LOGGER.exception("No se pudo leer el CSV para merge: %s", filepath)
                print(f"  [AVISO] Se omite {files[idx]}: no se pudo leer.")

    if not dfs:
        print("  No se seleccionaron archivos validos.")
        return

    merged = pd.concat(dfs, ignore_index=True)
    merged = merged[CSV_HEADERS]

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = os.path.join(OUTPUT_DIR, f"merged_{timestamp}.csv")
    merged.to_csv(filepath, index=False, encoding="utf-8-sig", sep=";")
    LOGGER.info("CSV mergeado: %s | registros=%s", filepath, len(merged))
    print(f"\n  [OK] Merge guardado: {filepath}")
    print(f"  [*] Total registros: {len(merged)}")


def menu_instagram():
    from instagram_scraper import InstagramScraper

    has_auth = InstagramScraper().has_saved_session()

    if not has_auth:
        print("\n  [i] Instagram requiere login. Abrire el navegador para que inicies sesion.")
        print("  [i] La sesion se guardara para no pedirla de nuevo.")
        if ask_yn("  Abrir navegador ahora?", default=True):
            s = InstagramScraper()
            s.register_manual_login()
        else:
            print("  Puedes crear la sesion despues con: python -c \"from instagram_scraper import InstagramScraper; InstagramScraper().register_manual_login()\"")

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
    from tiktok_scraper import TikTokScraper

    print("""
  TikTok - Modos disponibles:
    1. Automatico (Playwright) - Recomendado
    2. Script para consola del navegador
""")

    mode = input("  Modo [1]: ").strip() or "1"

    if mode == "2":
        from tiktok_scraper import TikTokScraper as T
        print("\n  --- Script para copiar en la consola del navegador ---")
        print(T.generate_console_script())
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
    from facebook_scraper import FacebookScraper

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
        from instagram_scraper import InstagramScraper
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
        from instagram_scraper import InstagramScraper
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
        from tiktok_scraper import TikTokScraper
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
        from facebook_scraper import FacebookScraper
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
                import os as _os
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
