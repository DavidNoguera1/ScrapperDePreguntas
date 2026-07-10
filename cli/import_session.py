"""
Administra la sesión aislada de Instagram usada por el scraper.

Iniciar o renovar:
    python -m cli.import_session

Consultar si existe una sesión local:
    python -m cli.import_session --status

Cerrar la sesión y eliminarla de este equipo:
    python -m cli.import_session --logout
"""

import argparse
import logging

from scrapers.instagram.scraper import InstagramScraper


def main():
    parser = argparse.ArgumentParser(
        description="Administra la sesión de Instagram del scraper"
    )
    action = parser.add_mutually_exclusive_group()
    action.add_argument(
        "--logout",
        action="store_true",
        help="Cerrar la sesión en Instagram y eliminar el archivo local",
    )
    action.add_argument(
        "--status",
        action="store_true",
        help="Indicar si existe un archivo de sesión local",
    )
    args = parser.parse_args()

    logging.basicConfig(
        level=logging.INFO,
        format="%(message)s",
    )
    scraper = InstagramScraper()

    if args.status:
        if scraper.has_saved_session():
            print(f"  [OK] Hay una sesión local guardada en: {scraper.auth_file}")
        else:
            print("  [i] No hay una sesión local guardada.")
        return

    if args.logout:
        status = scraper.logout_saved_session()
        if status["server_revoked"]:
            print("  [OK] Instagram confirmó el cierre remoto de la sesión.")
        else:
            print("  [AVISO] Instagram no confirmó el cierre remoto.")
        if status["local_deleted"]:
            print("  [OK] El archivo de sesión local fue eliminado.")
        else:
            print("  [i] No había un archivo de sesión local.")
        print("  [OK] Navegador de Playwright cerrado.")
        return

    scraper.register_manual_login()


if __name__ == "__main__":
    main()
