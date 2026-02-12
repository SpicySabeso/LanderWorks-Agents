from __future__ import annotations

import datetime as dt
import re
from pathlib import Path
from typing import Any, Literal

import yaml
from langdetect import detect
from unidecode import unidecode

# --------Config---------
_CFG: dict[str, Any] | None = None
_CFG_PATH = Path(__file__).resolve().parent / "data" / "clinic_config.yaml"
_CFG_MTIME: float | None = None


def _cfg() -> dict[str, Any]:
    global _CFG, _CFG_MTIME
    mtime = _CFG_PATH.stat().st_mtime
    if _CFG is None or _CFG_MTIME != mtime:
        with _CFG_PATH.open("r", encoding="utf-8") as f:
            _CFG = yaml.safe_load(f) or {}
        _CFG_MTIME = mtime
    return _CFG


SOURCE_MD = "backend/data/clinic_config.yaml"


def validate_config() -> list[str]:
    """
    Devuelve lista de errores humanos si falta algo crítico.
    No lanza excepción: sirve para loggear al arrancar.
    """
    c = _cfg()
    errs: list[str] = []

    # básicos para venta/demo
    for k in ["name", "phone", "email", "hours", "policies", "services"]:
        if k not in c or c.get(k) in (None, "", {}):
            errs.append(f"Falta '{k}' en clinic_config.yaml")

    # address y map_url pueden ser opcionales, pero si están deben ser string
    for k in ["address", "map_url"]:
        if k in c and c.get(k) is not None and not isinstance(c.get(k), str):
            errs.append(f"'{k}' debe ser string")

    # hours structure
    h = c.get("hours") or {}
    for hk in ["mon_fri", "sat", "sun"]:
        if hk not in h:
            errs.append(f"Falta hours.{hk}")

    # policies.emergency recomendado
    p = c.get("policies") or {}
    if "emergency" not in p:
        errs.append("Falta policies.emergency")

    return errs


# ---------- Tiempo / lenguaje ----------
def ahora_iso() -> str:
    return dt.datetime.now().isoformat(timespec="minutes")


def detect_lang(text: str) -> str:
    try:
        return detect(text or "")  # 'es', 'en', etc.
    except Exception:
        return "es"


# ---------- Intención ----------
def clasifica_intencion(msg: str) -> Literal["faq", "cita", "humano", "otro"]:
    m = unidecode((msg or "").lower())
    m = re.sub(r"\s+", " ", m).strip()

    # Marcadores FUERTES de humano (solo si explícito)
    if any(
        p in m
        for p in [
            "hablar con una persona",
            "hablar con alguien",
            "persona real",
            "humano",
            "recepcion",
            "recepción",
            "operador",
        ]
    ):
        return "humano"

    # Marcadores FUERTES de cita (evita falsos positivos)
    booking_markers = [
        "pedir cita",
        "quiero cita",
        "quiero una cita",
        "reservar cita",
        "agendar cita",
        "darme cita",
        "coger cita",
        "tienes hueco",
        "teneis hueco",
        "tenéis hueco",
        "cita urgente",
        "primera cita",
    ]

    if any(b in m for b in booking_markers):
        return "cita"

    # FAQ (amplio)
    faq_markers = [
        "precio",
        "coste",
        "cuanto",
        "cuánto",
        "seguro",
        "asegur",
        "horario",
        "abr",
        "cerr",
        "donde",
        "dónde",
        "direccion",
        "dirección",
        "telefono",
        "teléfono",
        "email",
        "correo",
        "mapa",
        "ubicacion",
        "ubicación",
        "pago",
        "bizum",
        "tarjeta",
        "financi",
        "politi",
        "cancel",
        "rgpd",
        "privacidad",
        "aparcamiento",
        "parking",
        "tratamiento",
        "limpieza",
        "ortodoncia",
        "implante",
        "endodoncia",
        "blanqueamiento",
        "invisalign",
    ]
    if any(w in m for w in faq_markers):
        return "faq"

    # Si el usuario pide que le llamen pero no lo ha pedido como "humano" explícito,
    # esto en tu producto es lead -> lo tratamos como cita (captura + handoff).
    if any(
        w in m
        for w in [
            "llamadme",
            "llamame",
            "llámame",
            "puedes llamarme",
            "me podeis llamar",
            "me podéis llamar",
        ]
    ):
        return "cita"

    return "otro"


# ---------- Validadores ----------
def normaliza_tel(text: str) -> str | None:
    if not text:
        return None
    digits = re.sub(r"\D", "", text)

    # si viene con +34 delante
    if digits.startswith("34") and len(digits) >= 11:
        digits = digits[2:]

    if len(digits) == 11 and digits.startswith("34"):
        digits = digits[2:]

    # Si son 10 dígitos y empieza por 6/7/8/9, probablemente metió un dígito extra al final:
    if len(digits) == 10 and digits[0] in "6789":
        digits = digits[:9]

    # Si siguen siendo >9 por prefijos raros, ahí sí me quedo con los últimos 9
    if len(digits) > 9:
        digits = digits[-9:]

    if len(digits) == 9 and digits[0] in "6789":
        return digits

    return None


TRATAMIENTOS_MAP = [
    ("invisalign", "ortodoncia_invisible"),
    ("ortodoncia invisible", "ortodoncia_invisible"),
    ("brackets", "ortodoncia"),
    ("ortodoncia", "ortodoncia"),
    ("implante", "implantes"),
    ("implantes", "implantes"),
    ("endodoncia", "endodoncia"),
    ("conducto", "endodoncia"),
    ("blanqueamiento", "blanqueamiento"),
    ("limpieza", "limpieza"),
    ("revision", "revisión"),
    ("revisión", "revisión"),
    ("caries", "empaste"),
    ("empaste", "empaste"),
    ("extraccion", "extracción"),
    ("extracción", "extracción"),
    ("dolor", "dolor"),
    ("duele", "dolor"),
    ("me duele", "dolor"),
    ("dolor de muela", "dolor"),
    ("muela", "dolor"),
]


def clasifica_tratamiento(msg: str) -> str | None:
    m = unidecode((msg or "").lower())
    for needle, label in TRATAMIENTOS_MAP:
        if needle in m:
            return label
    return None


def clasifica_urgencia(msg: str) -> str:
    m = unidecode((msg or "").lower())

    # Negaciones primero
    if any(
        p in m
        for p in [
            "no es urgente",
            "no urgente",
            "no tengo urgencia",
            "sin prisa",
            "no tengo prisa",
        ]
    ):
        return "baja"

    # Síntomas claros = alta
    if any(
        k in m
        for k in [
            "sangra",
            "sangrado",
            "mucho dolor",
            "dolor fuerte",
            "no aguanto",
            "flemon",
            "flemón",
            "hinchado",
            "hinchazon",
            "hinchazón",
            "golpe fuerte",
            "se me ha roto",
            "se me ha partido",
        ]
    ):
        return "alta"

    # “urgente” sin síntomas -> baja (porque recepción ya prioriza al llamar)
    return "baja"


def detectar_sintomas_urgentes(msg: str) -> dict:
    m = (msg or "").lower()
    return {
        "sangrado": any(k in m for k in ["sangra", "sangrado"]),
        "dolor_fuerte": any(k in m for k in ["dolor fuerte", "mucho dolor", "no aguanto"]),
        "flemon": any(k in m for k in ["flemón", "flemon", "hinchado"]),
    }


# ---------- Datos “duros” de clínica ----------
_TIME_PAD_RE = re.compile(r"\b(\d):(\d{2})\b")  # 9:00 -> 09:00


def _pad_times(s: str) -> str:
    if not s:
        return s
    return _TIME_PAD_RE.sub(r"0\1:\2", s)


def get_hours() -> str:
    c = _cfg()
    h = c.get("hours") or {}

    mon_fri = _pad_times(h.get("mon_fri", ""))
    sat = _pad_times(h.get("sat", ""))
    sun = h.get("sun", "")

    # OJO: usa guion normal "-" para que "l-v" matchee si quieres
    # y conserva el 09:00 para que matchee "09:"
    out = f"L-V: {mon_fri}. Sábado: {sat}. Domingo: {sun}."
    return out


def get_hours_on(d: dt.date) -> str:
    h = _cfg()["hours"]
    if d.isoformat() in set(_cfg().get("holidays", [])) or d.weekday() == 6:
        return "Cerrado por festivo."
    if d.weekday() < 5:
        return f"L–V: {h['mon_fri']}"
    if d.weekday() == 5:
        return f"Sábado: {h['sat']}"
    return "Cerrado"


def get_insurances() -> str:
    return "Aceptamos: " + ", ".join(_cfg()["insurances"]) + "."


def get_payments() -> str:
    return "Métodos de pago: " + ", ".join(_cfg()["payments"]) + "."


def get_financing() -> str:
    return _cfg()["financing"]


def get_address() -> str:
    c = _cfg()
    return (c.get("address") or "").strip()


def get_map_url() -> str:
    return (_cfg().get("map_url") or "").strip()


def get_contact() -> str:
    c = _cfg()
    name = c.get("name") or "La clínica"
    addr = (c.get("address") or "").strip()
    tel = c.get("phone") or "Teléfono no configurado"
    mail = c.get("email") or "Email no configurado"
    url = (c.get("map_url") or "").strip()

    s = f"{name}. Tel: {tel}. Email: {mail}."
    if addr:
        s = f"{name}. Dirección: {addr}. Tel: {tel}. Email: {mail}."
    if url:
        s += f" Mapa: {url}"
    return s


def get_services() -> str:
    s = _cfg().get("services") or {}

    treatments = s.get("treatments") or []
    names: list[str] = []
    for t in treatments:
        if isinstance(t, str):
            if t.strip():
                names.append(t.strip())
        elif isinstance(t, dict):
            n = (t.get("name") or "").strip()
            if n:
                names.append(n)

    extras = []
    if s.get("pediatric"):
        extras.append("Atención pediátrica")
    if s.get("sedation"):
        extras.append(str(s["sedation"]).strip())
    if s.get("languages"):
        extras.append(
            "Idiomas: " + ", ".join([str(x).strip() for x in s["languages"] if str(x).strip()])
        )
    if s.get("accessibility"):
        extras.append("Accesibilidad: " + str(s["accessibility"]).strip())

    base = "Tratamientos: " + (", ".join(names) if names else "consultar con recepción")
    return base + (". " + ". ".join(extras) if extras else "")


def get_price(item: str | None) -> str | None:
    if not item:
        return None

    raw = item.lower().strip()

    aliases = {
        "ortodoncia": "ortodoncia_invisible",
        "invisalign": "ortodoncia_invisible",
        "ortodoncia invisible": "ortodoncia_invisible",
        "brackets": "ortodoncia_invisible",
        "implante": "implante_unitario",
        "implantes": "implante_unitario",
        "extraccion": "extraccion_simple",
        "extracción": "extraccion_simple",
        "extraccion simple": "extraccion_simple",
        "extracción simple": "extraccion_simple",
    }

    key = aliases.get(raw, raw)
    return (_cfg().get("prices") or {}).get(key)


def get_policies() -> str:
    p = _cfg()["policies"]
    return f"Cancelación: {p['cancellation']} RGPD: {p['privacy']} Esterilización: {p['sterilization']}"


def get_emergency_policy() -> str:
    return _cfg()["policies"]["emergency"]


# ---------- FAQ determinista ----------
FAQ_MAP = {
    "horario": [
        "horario",
        "abrís",
        "abris",
        "abrís el",
        "abiertos",
        "a qué hora",
        "a que hora",
        "sáb",
        "sabado",
        "sábado",
        "abre",
        "abren",
        "cerráis",
        "cerrais",
        "cierra",
        "cierran",
    ],
    "urgencias": [
        "urgencias",
        "cita urgente",
        "sangra",
        "sangrado",
        "dolor fuerte",
        "mucho dolor",
        "emergencia",
    ],
    "tratamientos": [
        "tratamiento",
        "limpieza",
        "ortodoncia",
        "implante",
        "implantes",
        "endodoncia",
        "blanqueamiento",
        "invisalign",
    ],
    "seguros": ["seguros", "aseguradora", "adeslas", "sanitas", "asisa"],
    "pagos": [
        "pago",
        "pagáis",
        "pagais",
        "bizum",
        "tarjeta",
        "financiación",
        "financi",
    ],
    "direccion": [
        "direccion",
        "dirección",
        "ubicados",
        "ubicación",
        "ubicacion",
        "dónde estáis",
        "donde estais",
        "donde estáis",
        "donde estais",
        "mapa",
        "cómo llegar",
        "como llegar",
        "donde",
    ],
    "contacto": [
        "contacto",
        "whatsapp",
        "correo",
        "email",
        "teléfono",
        "telefono",
        "mapa",
    ],
    "políticas": [
        "política",
        "politica",
        "cancelación",
        "cancelacion",
        "rgpd",
        "privacidad",
    ],
    "parking": ["parking", "aparcamiento"],
    "precios": [
        "precio",
        "precios",
        "cuanto cuesta",
        "cuánto cuesta",
        "cuanto vale",
        "cuánto vale",
        "tarifa",
        "coste",
        "costo",
        "importe",
    ],
}


def detect_faq_keys(msg: str, max_keys: int = 5) -> list[str]:
    """
    Devuelve las claves FAQ detectadas (hasta max_keys),
    ordenadas según el orden en que aparecen en el mensaje.
    """

    def _norm(s: str) -> str:
        s = unidecode((s or "").lower())
        s = re.sub(r"\s+", " ", s).strip()
        return s

    m = _norm(msg)

    def _has(tok: str) -> int:
        t = _norm(tok)
        # si el token tiene espacios, lo tratamos como frase
        if " " in t:
            return m.find(t)
        # si es una palabra, buscamos límites de palabra
        match = re.search(rf"\b{re.escape(t)}\b", m)
        return match.start() if match else -1

    found: list[tuple[int, str]] = []  # (posición, key)

    for key, tokens in FAQ_MAP.items():
        positions = []
        for tok in tokens:
            idx = _has(tok)
            if idx != -1:
                positions.append(idx)

        if positions:
            first_pos = min(positions)
            found.append((first_pos, key))

    PRIORITY = {
        "precios": 0,
        "urgencias": 1,
        "contacto": 2,
        "horario": 3,
        "direccion": 4,
        "pagos": 5,
        "seguros": 6,
        "tratamientos": 7,
        "políticas": 8,
        "parking": 9,
    }

    # ordenamos por prioridad en el mensaje
    found.sort(key=lambda t: (PRIORITY.get(t[1], 99), t[0]))

    return [key for _pos, key in found[:max_keys]]


def _norm_q(s: str) -> str:
    s = unidecode((s or "").lower())
    s = re.sub(r"[^\w\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def canned_faq_answer(key: str, msg: str = "") -> tuple[str, list[str]]:
    # --- Canonicaliza keys para que el resto del bot sea consistente ---
    k = (key or "").strip().lower()
    KEY_CANON = {
        # horario
        "horarios": "horario",
        "hora": "horario",
        "horas": "horario",
        # precios
        "precio": "precios",
        "tarifas": "precios",
        "tarifa": "precios",
        # políticas
        "politicas": "políticas",
    }
    key = KEY_CANON.get(k, k)

    q = _norm_q(msg)

    is_question = "?" in msg or any(
        w in q for w in ["cual", "cuál", "dime", "decidme", "pasame", "pásame"]
    )

    # helpers de detección rápida
    wants_phone = any(w in q for w in ["telefono", "tel", "llamar", "numero"])
    wants_email = any(w in q for w in ["email", "correo", "mail"])
    wants_map = any(w in q for w in ["mapa", "google maps", "maps", "ubicacion"])
    wants_financing = any(w in q for w in ["financi", "pagar a plazos", "plazos"])
    wants_cancel = any(w in q for w in ["cancel", "anular", "cambiar cita"])
    wants_privacy = any(w in q for w in ["rgpd", "privacidad", "datos"])

    ans = ""

    if key == "horario":
        # SOLO horario, nada más
        ans = get_hours()

    elif key == "seguros":
        # Si pregunta por una aseguradora concreta, responde solo sí/no
        ins = [unidecode(x).lower() for x in (_cfg().get("insurances") or [])]
        qn = unidecode(q).lower()

        # detectar marca concreta en la pregunta
        asked = None
        for brand in ["adeslas", "sanitas", "asisa", "dkv", "mapfre", "cigna", "aegon"]:
            if brand in qn:
                asked = brand
                break

        if asked:
            ans = (
                f"Sí, aceptamos {asked.title()}."
                if asked in ins
                else f"No trabajamos con {asked.title()}."
            )
        else:
            # Si no concreta, entonces sí: lista
            ans = get_insurances()

    elif key == "pagos":
        if wants_financing:
            fin = get_financing()
            ans = (
                fin
                or "Sí, disponemos de opciones de financiación. Recepción te lo explica según el tratamiento."
            )
        else:
            pays = [unidecode(x).lower() for x in (_cfg().get("payments") or [])]
            qn = unidecode(q).lower()

            asked = None
            for method in ["bizum", "tarjeta", "efectivo", "transferencia"]:
                if method in qn:
                    asked = method
                    break

            if asked:
                label = {
                    "bizum": "Bizum",
                    "tarjeta": "tarjeta",
                    "efectivo": "efectivo",
                    "transferencia": "transferencia",
                }.get(asked, asked)
                ans = (
                    f"Sí, se puede pagar con {label}."
                    if asked in pays
                    else f"No aceptamos {label}."
                )
            else:
                ans = get_payments()

    elif key == "direccion":
        # SOLO lo que pide: dirección o mapa
        addr = get_address()
        url = get_map_url()
        if wants_map and url:
            ans = f"Te paso el mapa: {url}"
        elif addr and url:
            ans = f"Nuestra dirección es {addr}. Mapa: {url}"
        elif addr:
            ans = f"Nuestra dirección es {addr}."
        elif url:
            ans = f"Te paso el mapa: {url}"
        else:
            ans = "Ahora mismo no tengo la dirección configurada. Si quieres, te lo confirma recepción."

    elif key == "contacto":
        # SOLO el dato pedido (tel/email). Si no especifica, dar ambos pero en 1 frase.
        if not is_question and not (wants_phone or wants_email):
            return ("", [])
        c = _cfg()
        tel = c.get("phone") or ""
        mail = c.get("email") or ""
        if wants_phone and tel:
            ans = f"Nuestro teléfono es {tel}."
        elif wants_email and mail:
            ans = f"Nuestro email es {mail}."
        else:
            # compacto
            if tel and mail:
                ans = f"Tel: {tel}. Email: {mail}."
            elif tel:
                ans = f"Tel: {tel}."
            elif mail:
                ans = f"Email: {mail}."
            else:
                ans = "Ahora mismo no tengo el contacto configurado. Te lo confirma recepción."

    elif key == "políticas" or key == "politicas":
        p = _cfg().get("policies", {}) or {}
        if wants_cancel and p.get("cancellation"):
            ans = f"Cancelación: {p['cancellation']}"
        elif wants_privacy and p.get("privacy"):
            ans = f"RGPD/Privacidad: {p['privacy']}"
        else:
            # 1 frase, no folleto
            parts = []
            if p.get("cancellation"):
                parts.append(f"Cancelación: {p['cancellation']}")
            if p.get("privacy"):
                parts.append(f"RGPD: {p['privacy']}")
            ans = (
                " ".join(parts) if parts else "Si me dices qué política necesitas, te lo confirmo."
            )

    elif key == "urgencias":
        # corto y accionable
        pol = get_emergency_policy()
        ans = (
            "Si hay dolor intenso, sangrado abundante o hinchazón, conviene valorarlo cuanto antes. "
            + pol
        )

    elif key == "tratamientos":
        # Respuesta específica: “sí/no” + siguiente paso
        if "invisalign" in q:
            ans = "Sí, hacemos ortodoncia invisible (Invisalign). Si quieres, te recojo nombre y teléfono y recepción te llama."
        elif "limpieza" in q:
            ans = "Sí, hacemos limpiezas dentales. Si quieres, te llamamos para coordinar la cita."
        elif "implante" in q:
            ans = "Sí, realizamos implantes. Si me cuentas tu caso, te orientamos y recepción puede llamarte."
        elif "endodon" in q or "conducto" in q:
            ans = "Sí, hacemos endodoncias. Si quieres, te recojo los datos y te llamamos."
        elif "blanque" in q:
            ans = (
                "Sí, realizamos blanqueamiento dental. Si quieres, te llamamos para darte opciones."
            )
        else:
            t = (_cfg().get("services", {}) or {}).get("treatments", [])
            if t:
                names = []
                for it in t:
                    if isinstance(it, str):
                        if it.strip():
                            names.append(it.strip())
                    elif isinstance(it, dict):
                        n = (it.get("name") or "").strip()
                        if n:
                            names.append(n)
                ans = "Tratamientos principales: " + ", ".join(names) + "."
            else:
                ans = "Dime qué tratamiento necesitas y te informo."

    elif key == "precios":
        # Si quieres mantener “precios” como key separada (recomendado)
        mm = q
        item = None
        if "limpieza" in mm:
            item = "limpieza"
        elif "blanque" in mm:
            item = "blanqueamiento"
        elif "invisalign" in mm or "ortodoncia invisible" in mm:
            item = "ortodoncia_invisible"
        elif "ortodoncia" in mm or "brackets" in mm:
            item = "ortodoncia"
        elif "implante" in mm:
            item = "implantes"
        elif "endodoncia" in mm or "conducto" in mm:
            item = "endodoncia"

        price = get_price(item) if item else None
        if price and item:
            ans = f"El precio de {item.replace('_',' ')} es {price}."
        else:
            ans = "Depende del caso. Si me dices qué necesitas, te doy un precio orientativo o te lo confirma recepción."

    elif key == "parking":
        ans = "Hay zona OTA cercana y un parking público a unos minutos andando."

    else:
        return ("", [])

    final_text = replace_placeholders(ans) if ans else ""
    return (final_text, [SOURCE_MD] if final_text else [])


def get_md_address() -> str:
    p = Path("backend/data/dental_faq.md")
    if not p.exists():
        return ""
    text = p.read_text(encoding="utf-8")
    # Busca la sección "Dirección y Contacto"
    m = re.search(
        r"(?mi)^#\s*Direcci[oó]n(?:\s+y\s+Contacto)?\s*\n(.*?)(?:\n#\s|\Z)",
        text,
        flags=re.S,
    )
    if m:
        lines = [line.strip() for line in m.group(1).splitlines() if line.strip()]
        return " ".join(lines)
    # Fallback sencillo: busca línea que contenga "Mapa:" o "WhatsApp:" o un email/telefono
    m2 = re.search(r"(?mi)^(.*C/.*\d+.*)$", text, flags=re.M)
    if m2:
        return m2.group(1).strip()
    return ""


def replace_placeholders(text: str) -> str:
    """
    Reemplaza placeholders entre corchetes por los valores reales de config (o de dental_faq.md).
    Tests pueden inyectar _CFG directamente, por eso usamos _CFG si ya existe.
    """
    if not text:
        return text
    # Usa _CFG si ya fue asignado (p. ej. por tests) o carga config real
    c = globals().get("_CFG") or _cfg()
    address = (c.get("address") or "").strip()
    # Si la config contiene un placeholder evidente, ignóralo
    if re.match(r"^\[.*\]$", address):
        address = ""
    # Fallback a MD si no hay address en config
    if not address:
        address = get_md_address()
    phone = c.get("phone") or "Teléfono no configurado"
    email = c.get("email") or "Email no configurado"
    map_url = c.get("map_url") or ""

    # patrones comunes
    replacements = {
        r"\[[^\]]*tu ?direcci[oó]n[^\]]*\]": address or "No configurada",
        r"\[[^\]]*direccion[^\]]*\]": address or "No configurada",
        r"\[[^\]]*tel[eé]fono[^\]]*\]": phone,
        r"\[[^\]]*telefono[^\]]*\]": phone,
        r"\[[^\]]*email[^\]]*\]": email,
        r"\[[^\]]*mapa[^\]]*\]": map_url or "",
    }

    out = text
    for patt, repl in replacements.items():
        out = re.sub(patt, repl, out, flags=re.IGNORECASE)
    return out


_NAME_PATTERNS = [
    r"\bme llamo\s+([a-záéíóúüñ]{2,}(?:\s+[a-záéíóúüñ]{2,})?)\b",
    r"\bsoy\s+([a-záéíóúüñ]{2,}(?:\s+[a-záéíóúüñ]{2,})?)\b",
    r"\bmi nombre es\s+([a-záéíóúüñ]{2,}(?:\s+[a-záéíóúüñ]{2,})?)\b",
    r"\bme llamo\s+([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+){0,2})(?=[,\.!\?]|$)",
    r"\bmi nombre es\s+([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+){0,2})(?=[,\.!\?]|$)",
    r"\bsoy\s+([a-záéíóúüñ]+(?:\s+[a-záéíóúüñ]+){0,2})(?=[,\.!\?]|$)",
]


def extract_booking_fields(text: str) -> dict:
    """
    Extrae campos típicos de cita desde un solo mensaje:
    - nombre (heurística)
    - telefono (normaliza_tel)
    - tratamiento (clasifica_tratamiento)
    - urgencia (clasifica_urgencia)
    - preferencia (hoy/mañana/mañanas/tardes)
    """
    msg = (text or "").strip()

    # Normalización mínima robusta (mantiene acentos)
    msg = re.sub(r"\s+", " ", msg).strip()
    low = msg.lower()
    low = re.sub(r"[^\w\sáéíóúüñ]", " ", low)  # quita puntuación pero conserva letras
    low = re.sub(r"\s+", " ", low).strip()

    out = {
        "nombre": None,
        "telefono": None,
        "tratamiento": None,
        "urgencia": None,
        "preferencia": None,
    }

    # Teléfono: acepta +34, espacios, guiones
    tel = normaliza_tel(msg)
    if tel:
        out["telefono"] = tel

    # Nombre (si el usuario lo escribe de forma explícita)
    for patt in _NAME_PATTERNS:
        m = re.search(patt, low, flags=re.IGNORECASE)
        if m:
            name_raw = m.group(1).strip()
            if name_raw:
                out["nombre"] = name_raw.title()
                break

    # Tratamiento
    out["tratamiento"] = clasifica_tratamiento(msg)

    # Urgencia (nivel)
    if any(
        p in low
        for p in [
            "no es urgente",
            "no urgente",
            "nada urgente",
            "tranqui",
            "tranquilo",
            "sin prisa",
            "no tengo prisa",
        ]
    ):
        out["urgencia"] = "baja"

    # 2) Urgencia explícita alta
    elif any(
        w in low
        for w in [
            "urgente",
            "urgencia",
            "de urgencia",
            "lo antes posible",
            "cuanto antes",
            "ya",
        ]
    ):
        out["urgencia"] = "alta"

    # 3) Si no hay pistas, usa clasificador pero SOLO si no es baja
    else:
        urg = clasifica_urgencia(msg)
        if urg != "baja":
            out["urgencia"] = urg

    # Preferencia simple
    t = low

    pref_parts = []

    # 1) Detectar día "hoy" / "mañana" (día siguiente)
    # Nota: si dice "por la mañana" NO implica "mañana (día siguiente)"
    wants_today = bool(re.search(r"\bhoy\b", t))
    wants_tomorrow_day = bool(re.search(r"\b(mañana|manana)\b", t)) and not bool(
        re.search(r"\bpor\s+la\s+mañana\b|\bpor\s+las\s+mañanas\b|\bmañanas\b|\bmananas\b", t)
    )

    if wants_today:
        pref_parts.append("hoy")
    if wants_tomorrow_day:
        pref_parts.append("mañana")

    # 2) Franja: mañana/tarde
    wants_morning_slot = bool(
        re.search(r"\bpor\s+la\s+mañana\b|\bpor\s+las\s+mañanas\b|\bmañanas\b|\bmananas\b", t)
    )
    wants_afternoon_slot = bool(
        re.search(r"\bpor\s+la\s+tarde\b|\bpor\s+las\s+tardes\b|\btardes\b|\btarde\b", t)
    )

    if wants_morning_slot:
        pref_parts.append("por la mañana")
    if wants_afternoon_slot:
        pref_parts.append("por la tarde")

    # 3) Hora exacta tipo 18:00 o 18.00
    m_time = re.search(r"\b([01]?\d|2[0-3])[:.][0-5]\d\b", t)
    if m_time:
        pref_parts.append(m_time.group(0).replace(".", ":"))

    # 4) "sobre las 10" / "a eso de las 10" / "hacia las 10"
    m_about = re.search(r"\b(sobre|hacia|a\s+eso\s+de)\s+las?\s+([01]?\d|2[0-3])\b", t)
    if m_about:
        pref_parts.append(f"sobre las {m_about.group(2)}:00")

    # 5) "a partir de las 18" / "desde las 18"
    m_from = re.search(r"\b(a\s+partir\s+de|desde)\s+las?\s+([01]?\d|2[0-3])\b", t)
    if m_from:
        pref_parts.append(f"a partir de las {m_from.group(2)}:00")

    # 6) "antes de las 12"
    m_before = re.search(r"\b(antes\s+de)\s+las?\s+([01]?\d|2[0-3])\b", t)
    if m_before:
        pref_parts.append(f"antes de las {m_before.group(2)}:00")

    # 7) Rango "entre 4 y 6" / "entre las 16 y las 18"
    m_between = re.search(
        r"\bentre\s+las?\s+([01]?\d|2[0-3])(?:[:.][0-5]\d)?\s+y\s+las?\s+([01]?\d|2[0-3])(?:[:.][0-5]\d)?\b",
        t,
    )
    if m_between:
        h1 = int(m_between.group(1))
        h2 = int(m_between.group(2))
        pref_parts.append(f"entre {h1:02d}:00 y {h2:02d}:00")
    else:
        # Variante corta: "entre 4 y 6"
        m_between_short = re.search(r"\bentre\s+([0-9]{1,2})\s+y\s+([0-9]{1,2})\b", t)
        if m_between_short:
            h1 = int(m_between_short.group(1))
            h2 = int(m_between_short.group(2))
            # Heurística: si habla de horas pequeñas (1-7) suele ser tarde (16-19) en España
            if h1 <= 7 and h2 <= 9 and ("tarde" in t or "tardes" in t or "por la tarde" in t):
                h1 += 12
                h2 += 12
            pref_parts.append(f"entre {h1:02d}:00 y {h2:02d}:00")

    # 8) Si hemos capturado algo, consolidar (sin duplicados)
    if pref_parts:
        out["preferencia"] = " ".join(dict.fromkeys(pref_parts)).strip()

    return out


def user_tried_phone_but_invalid(text: str) -> bool:
    """
    True si el usuario ha escrito algo que parece un teléfono (hay dígitos y/o dice 'tel/numero')
    pero no pasa normaliza_tel().
    """
    t = (text or "").lower()
    digits = re.sub(r"\D", "", text or "")

    # Si no hay suficientes dígitos, no es un intento claro de teléfono
    if len(digits) < 6:
        return False

    # Señales típicas de que está dando un teléfono
    hints = any(
        k in t for k in ["tel", "telefono", "teléfono", "número", "numero", "+34", "llamar"]
    )

    # Si parece teléfono o hay muchos dígitos y NO valida -> intentó pero es inválido
    if hints or len(digits) >= 7:
        return normaliza_tel(text) is None

    return False
