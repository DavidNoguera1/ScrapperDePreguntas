import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent

OUTPUT_DIR = os.path.join(str(BASE_DIR), "output")
LOG_DIR = os.path.join(OUTPUT_DIR, "logs")

DEFAULT_AUTH_FILE = BASE_DIR / "instagram_auth.json"

CSV_HEADERS = [
    "Dia", "Cuenta", "Red Social", "Tipo de publicacion", "Enlace",
    "Comentario", "Tema principal", "Mes",
]

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
