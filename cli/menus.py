import logging
from datetime import datetime, timezone

from core.config import ask_yn
from core.csv_handler import open_csv, append_csv
from core.logger import LOGGER
from scrapers.instagram.scraper import InstagramScraper



def _parse_date_input(date_str, end_of_day=False):
    """Parsea una fecha de Instagram en el formato amigable DD-MM-AAAA."""
    if not date_str:
        return None
    try:
        parsed = datetime.strptime(date_str.strip(), "%d-%m-%Y").replace(
            tzinfo=timezone.utc
        )
        if end_of_day:
            parsed = parsed.replace(hour=23, minute=59, second=59, microsecond=999999)
        return parsed
    except ValueError:
        print(f"  [AVISO] Formato de fecha invalido: '{date_str}'. Usa dd-mm-aaaa.")
        return None


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

    start_input = input(
        "  Fecha inicial (dd-mm-aaaa, Enter = usar meses): "
    ).strip()
    start_date = _parse_date_input(start_input)
    if start_input and start_date is None:
        return []

    end_input = input(
        "  Fecha final (dd-mm-aaaa, Enter = hoy): "
    ).strip()
    end_date = _parse_date_input(end_input, end_of_day=True)
    if end_input and end_date is None:
        return []
    if start_date and end_date and start_date > end_date:
        print("  [AVISO] La fecha inicial es posterior a la fecha final.")
        return []

    months = 2
    if not start_date:
        months_input = input("  Cuantos meses hacia atras? [2]: ").strip()
        months = int(months_input) if months_input.isdigit() else 2

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
                start_date=start_date,
                end_date=end_date,
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
