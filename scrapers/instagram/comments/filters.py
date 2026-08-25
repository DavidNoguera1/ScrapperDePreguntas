import re
from urllib.parse import urlparse


import re

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

# ---------------------------------------------------------------------------
# INTEREST_KEYWORDS
# Ampliado a partir de "Precios_ET_2026 -- a_2027.xlsx" (7 hojas: Accounting,
# LegalLaboral, LegalExtranjería, LegalSetUp, LegalCivil, Advisory, Consultas).
# Organizado por área de negocio para facilitar mantenimiento futuro.
# ---------------------------------------------------------------------------
INTEREST_KEYWORDS = {

    # --- Genéricos / trámites en general (original) ---
    "nie", "tie", "residencia", "permiso", "visado", "visa",
    "expediente", "trámite", "tramite", "trámites", "tramites",
    "solicitud", "documento", "regularización", "regularizacion",
    "homologación", "homologacion", "nacionalidad", "extranjería",
    "extranjeria", "tasa", "huella", "asilo", "arraigo", "cita",
    "apostilla", "antecedente", "antecedentes", "certificado digital",
    "seguridad social", "contrato", "empresa", "trabajar", "trabajo",
    "legal", "ley", "abogado", "padrón", "padron", "reagrupación",
    "reagrupacion", "renovar", "renovación", "renovacion", "recurso",
    "subsanación", "subsanacion", "notificación", "notificacion",
    "razones humanitarias", "admisión", "admision",

    # --- Consultas / precios (relevante para todas las áreas) ---
    "consulta", "consultas", "asesoría", "asesoria", "asesor", "gestor",
    "precio", "precios", "coste", "costes", "cuánto cuesta",
    "cuanto cuesta", "presupuesto", "cita previa", "urgente", "urgencia",

    # --- Fiscal / Contable / Autónomos y PYMES (hoja Accounting) ---
    "autónomo", "autonomo", "autónomos", "autonomos", "pyme", "pymes",
    "gestoría mensual", "factura", "facturas", "facturación", "facturacion",
    "iva", "impuesto", "impuestos", "declaración", "declaracion",
    "declaración de la renta", "declaracion de la renta", "renta", "irpf",
    "modelo 036", "modelo 037", "modelo 100", "modelo 130", "modelo 151",
    "modelo 210", "modelo 600", "modelo 650", "modelo 651", "modelo 714",
    "modelo 720", "modelo 721", "modelo d6", "modelo d5a", "modelo 149",
    "modelo 030", "ley beckham", "beckham", "impatriado", "impatriados",
    "no residente", "no residentes", "cuentas anuales",
    "impuesto de sociedades", "sociedad limitada", "alta autónomo",
    "alta autonomo", "alta como autónomo", "baja autónomo",
    "baja autonomo", "baja como autónomo", "cese de actividad",
    "trimestral", "trimestre", "certificado digital",
    "subvención", "subvencion", "kit digital", "eori", "aduana", "aduanas",
    "sucesión", "sucesiones", "donación", "donaciones", "herencia",
    "herencias", "patrimonio", "domicilio social",
    "devolución de impuestos", "devolucion de impuestos",

    # --- Laboral (hoja LegalLaboral) ---
    "nómina", "nomina", "nóminas", "nominas", "contrato laboral",
    "número de la seguridad social", "numero de la seguridad social",
    "alta de trabajador", "baja de trabajador", "empleada de hogar",
    "empleado del hogar", "paro", "desempleo", "prestación contributiva",
    "prestacion contributiva", "subsidio de desempleo",
    "capitalización del paro", "capitalizacion del paro",
    "tarjeta sanitaria", "tarjeta sanitaria europea", "familia numerosa",
    "maternidad", "paternidad", "baja por maternidad", "baja por paternidad",
    "despido", "disputas laborales", "convenio especial",

    # --- Extranjería (hoja LegalExtranjería) ---
    "empadronamiento", "arraigo social", "arraigo familiar",
    "arraigo laboral", "arraigo socio laboral", "arraigo formativo",
    "reagrupación familiar", "reagrupacion familiar",
    "tarjeta comunitaria", "pareja de hecho", "parejas de hecho",
    "residencia temporal", "residencia larga duración",
    "residencia larga duracion", "nacionalidad española",
    "nacionalidad espanola", "nacionalidad por residencia",
    "carta de naturaleza", "expulsión", "expulsion", "alegaciones",
    "contencioso administrativo", "nómada digital", "nomada digital",
    "teletrabajador", "golden visa", "inversor", "inversores",
    "emprendedor", "emprendedores", "altamente cualificado",
    "investigador", "traslado intraempresarial", "convalidación",
    "convalidacion", "traducción jurada", "traduccion jurada", "dni",
    "cue", "nie blanco", "jura de nacionalidad", "cuenta propia",
    "cuenta ajena", "plan de empresa", "enisa", "permiso de estudios",
    "visado de estudios", "búsqueda de empleo", "busqueda de empleo",
    "brexit", "prórroga de estudios", "prorroga de estudios",
    "consulado", "schengen", "residencia no lucrativa", "pasaporte",
    "autorización de menor", "autorizacion de menor",

    # --- Civil (hoja LegalCivil) ---
    "divorcio", "divorcios", "testamento", "testamentos",
    "contrato de alquiler", "contrato de arras", "compraventa",
    "registro civil", "certificado de nacimiento",
    "certificado de matrimonio", "certificado de defunción",
    "certificado de defuncion", "cambio de nombre", "accidente de tráfico",
    "accidente de trafico", "indemnización", "indemnizacion", "inmueble",
    "inmuebles",

    # --- Advisory / Mercantil / Set Up (hojas LegalSetUp y Advisory) ---
    "constitución de empresa", "constitucion de empresa", "circe",
    "notaría", "notaria", "cambio de administrador", "cese de administrador",
    "cambio de domicilio social", "denominación social",
    "denominacion social", "poderes", "plan de negocio", "marca",
    "registro de marca", "dgt", "carnet de conducir", "carné de conducir",
    "matriculación", "matriculacion", "cambio de titularidad",
    "jubilación", "jubilacion", "pensión", "pension", "pensiones",
    "plan de pensiones", "relocación", "relocacion", "costo de vida",
    "coste de vida",
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
