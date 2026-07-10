import re
from urllib.parse import urlparse


QUESTION_PATTERN = re.compile(
    r"(?:"
    r"\bqui[eé]n(?:es)?\b|\bcu[aá]ndo\b|\bd[oó]nde\b|\bc[oó]mo\b"
    r"|\bcu[aá]l(?:es)?\b|\bcu[aá]nt[oa]s?\b"
    r"|\bpor\s+qu[eé]\b|\bpara\s+qu[eé]\b|\ba\s+qu[eé]\b"
    r"|\bqu[eé]\s+(?:es|hay|tal|significa|quier|pasa|necesit|debo|deb|"
    r"pued|hag|va[ya]|diferencia|requisito|paso|documento|tiempo|"
    r"cost[oó]|vale|opini[oó]n)"
    r")|(\?)|¿|❓",
    re.IGNORECASE,
)

UI_NOISE = {
    "follow", "seguir", "reply", "responder", "like", "me gusta",
    "see translation", "ver traducción", "view replies", "ver respuestas",
    "edited", "editado",
}

COMMENT_METADATA_PATTERN = re.compile(
    r"^(?:"
    r"\d+\s*(?:s|sec|m|min|h|hr|d|day|w|wk|sem|mes|mo|y|yr)"
    r"(?:\s*[·•]\s*(?:edited|editado))?"
    r"|\d+\s*(?:like|likes|me gusta)"
    r")$",
    re.IGNORECASE,
)

INTEREST_KEYWORDS = {
    "nie", "tie", "residencia", "permiso", "visado", "visa",
    "expediente", "trámite", "tramite", "solicitud", "documento",
    "regularización", "regularizacion", "homologación", "homologacion",
    "nacionalidad", "extranjería", "extranjeria", "tasa", "huella",
    "asilo", "arraigo", "cita", "apostilla", "antecedente",
    "certificado digital", "seguridad social", "contrato", "empresa",
    "trabajar", "trabajo", "legal", "ley", "abogado", "padrón",
    "padron", "reagrupación", "reagrupacion", "renovar", "renovación",
    "renovacion", "recurso", "subsanación", "subsanacion", "notificación",
    "notificacion", "razones humanitarias", "admisión", "admision",
}


def normalize_username(username):
    username = (username or "").strip()
    if "instagram.com/" in username:
        username = urlparse(username).path.strip("/").split("/")[0]
    return username.lstrip("@").strip()


def normalize_comment(text):
    return re.sub(r"\s+", " ", text or "").strip()


def is_user_comment(text, account_name=""):
    text = normalize_comment(text)
    if len(text) < 2 or len(text) > 2_000:
        return False
    if text.casefold() in UI_NOISE:
        return False
    if COMMENT_METADATA_PATTERN.fullmatch(text):
        return False
    if account_name and text.casefold() == account_name.casefold():
        return False
    return True


def is_interesting_comment(text):
    text = normalize_comment(text)
    if not is_user_comment(text):
        return False
    lowered = text.casefold()
    if QUESTION_PATTERN.search(text) and len(text) >= 10:
        return True
    if ("http://" in lowered or "https://" in lowered) and len(text) >= 30:
        return True
    return len(text) >= 25 and any(
        keyword in lowered for keyword in INTEREST_KEYWORDS
    )


def is_question(text):
    return bool(QUESTION_PATTERN.search(text))
