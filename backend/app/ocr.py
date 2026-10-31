"""Lectura de remitos con la API de visión de Anthropic. La clave vive sólo en el servidor (.env)."""
import base64
import json
import logging
import re

from . import config

log = logging.getLogger("logistica.ocr")

PROMPT = """La imagen es la foto de un remito de transporte de rollos de madera (Argentina).
Extraé los datos y respondé solo con un objeto JSON con esta forma:
{"numero": string|null, "fecha": "AAAA-MM-DD"|null, "rodal": string|null,
 "destino": string|null, "toneladas": number|null, "patente": string|null}
numero = número de remito. fecha = fecha del remito (en Argentina se escribe día/mes/año).
rodal = código del rodal o punto de carga (códigos conocidos: {lista_rodales}).
destino = lugar de descarga (destinos conocidos: {lista_destinos}).
toneladas = toneladas netas transportadas como número (si figuran bruto, tara y neto usá el neto;
si está en kg convertí a toneladas).
Si un dato no se lee con claridad usá null; no inventes valores."""


def disponible():
    return bool(config.ANTHROPIC_API_KEY)


def leer_remito(jpeg_bytes, rodales, destinos):
    """Devuelve (dict|None, json_crudo|None). None si la API no está configurada o la lectura falla."""
    if not disponible():
        return None, None
    import anthropic

    client = anthropic.Anthropic(api_key=config.ANTHROPIC_API_KEY, timeout=60.0, max_retries=1)
    prompt = PROMPT.replace("{lista_rodales}", ", ".join(rodales) or "ninguno").replace("{lista_destinos}", ", ".join(destinos) or "ninguno")
    try:
        r = client.messages.create(
            model=config.VISION_MODEL,
            max_tokens=1024,
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": [
                {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.standard_b64encode(jpeg_bytes).decode()}},
                {"type": "text", "text": prompt},
            ]}],
        )
    except anthropic.RateLimitError:
        log.warning("visión: límite de uso de la API")
        return None, None
    except anthropic.APIStatusError as e:
        log.warning("visión: error de la API %s", e.status_code)
        return None, None
    except anthropic.APIConnectionError:
        log.warning("visión: sin conexión con la API")
        return None, None
    if r.stop_reason == "refusal":
        return None, None
    texto = "".join(b.text for b in r.content if b.type == "text")
    m = re.search(r"\{.*\}", texto, re.S)
    if not m:
        return None, texto
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None, texto
    if not isinstance(d, dict):
        return None, texto
    # Validación de tipos y rangos: nunca confiar en la respuesta cruda
    out = {"numero": None, "fecha": None, "rodal": None, "destino": None, "toneladas": None, "patente": None}
    if d.get("numero") not in (None, ""):
        out["numero"] = str(d["numero"]).strip()[:30]
    if isinstance(d.get("fecha"), str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d["fecha"]):
        out["fecha"] = d["fecha"]
    if d.get("rodal"):
        out["rodal"] = str(d["rodal"]).strip()[:40]
    if d.get("destino"):
        out["destino"] = str(d["destino"]).strip()[:120]
    try:
        tn = float(d.get("toneladas")) if d.get("toneladas") is not None else None
        if tn is not None and 0 < tn < 200:
            out["toneladas"] = round(tn, 1)
    except (TypeError, ValueError):
        pass
    if d.get("patente"):
        out["patente"] = str(d["patente"]).strip()[:12]
    return out, m.group(0)
