"""Chilean region detection from free-text locations.

Ported from the As-Is tool (analisis.py: REGIONES, _region_de, extraer_region) with identical
behaviour; parity is covered by tests. Keys are normalised (lower case, no accents).
"""

import re

from matcher.text import contains, normalize

REGIONS: list[tuple[str, list[str]]] = [
    ("Arica y Parinacota", ["arica"]),
    ("Tarapacá", ["tarapaca", "iquique", "alto hospicio", "pozo almonte", "pica"]),
    (
        "Antofagasta",
        [
            "antofagasta",
            "calama",
            "mejillones",
            "tocopilla",
            "taltal",
            "san pedro de atacama",
            "sierra gorda",
            "maria elena",
        ],
    ),
    (
        "Atacama",
        ["atacama", "copiapo", "vallenar", "caldera", "chanaral", "diego de almagro", "tierra amarilla"],
    ),
    ("Coquimbo", ["coquimbo", "la serena", "ovalle", "illapel", "los vilos", "salamanca", "andacollo"]),
    (
        "Valparaíso",
        [
            "valparaiso",
            "vina del mar",
            "quilpue",
            "villa alemana",
            "concon",
            "con con",
            "san antonio",
            "quillota",
            "los andes",
            "san felipe",
            "la calera",
            "limache",
            "casablanca",
            "quintero",
            "puchuncavi",
            "llay llay",
        ],
    ),
    (
        "O'Higgins",
        [
            "o'higgins",
            "ohiggins",
            "libertador",
            "rancagua",
            "machali",
            "san fernando",
            "rengo",
            "santa cruz",
            "pichilemu",
            "graneros",
        ],
    ),
    ("Maule", ["maule", "talca", "curico", "linares", "constitucion", "cauquenes", "molina"]),
    ("Ñuble", ["nuble", "chillan"]),
    (
        "Biobío",
        [
            "biobio",
            "bio bio",
            "bio-bio",
            "concepcion",
            "talcahuano",
            "los angeles",
            "coronel",
            "san pedro de la paz",
            "hualpen",
            "chiguayante",
            "lota",
            "tome",
            "penco",
            "arauco",
            "lebu",
            "nacimiento",
            "mulchen",
            "hualqui",
        ],
    ),
    (
        "Araucanía",
        ["araucania", "temuco", "padre las casas", "angol", "villarrica", "pucon", "victoria", "lautaro"],
    ),
    ("Los Ríos", ["los rios", "valdivia", "la union", "panguipulli", "rio bueno"]),
    (
        "Los Lagos",
        [
            "los lagos",
            "puerto montt",
            "osorno",
            "puerto varas",
            "castro",
            "ancud",
            "chiloe",
            "calbuco",
            "frutillar",
        ],
    ),
    ("Aysén", ["aysen", "aisen", "coyhaique", "coihaique"]),
    ("Magallanes", ["magallanes", "punta arenas", "puerto natales", "porvenir"]),
    (
        "Metropolitana",
        [
            "metropolitana",
            "santiago",
            "r.m",
            "region rm",
            " rm",
            "las condes",
            "providencia",
            "vitacura",
            "lo barnechea",
            "nunoa",
            "la reina",
            "penalolen",
            "macul",
            "la florida",
            "puente alto",
            "san bernardo",
            "maipu",
            "pudahuel",
            "quilicura",
            "renca",
            "huechuraba",
            "conchali",
            "independencia",
            "recoleta",
            "estacion central",
            "cerrillos",
            "lo espejo",
            "san miguel",
            "san joaquin",
            "la cisterna",
            "el bosque",
            "la granja",
            "la pintana",
            "lampa",
            "colina",
            "buin",
            "paine",
            "talagante",
            "penaflor",
            "padre hurtado",
            "melipilla",
            "quinta normal",
            "lo prado",
            "cerro navia",
            "san ramon",
            "pedro aguirre cerda",
            "til til",
            "calera de tango",
            "pirque",
            "isla de maipo",
        ],
    ),
]


def _region_of(fragment: str) -> str | None:
    padded = " " + fragment.strip()
    for region, keys in REGIONS:
        for key in keys:
            stripped = key.strip()
            if contains(padded, stripped) if len(stripped) > 3 else (key in padded):
                return region
    return None


def extract_region(location: str | None) -> str:
    """Scan comma/dash-separated segments from last to first, because boards usually end with
    'Comuna, Región'; an address such as 'Lautaro 123, Santiago' is therefore not mistaken for
    the commune of Lautaro."""
    text = normalize(location)
    if not text:
        return "No indicada"
    for fragment in reversed(re.split(r"[,|/;-]", text)):
        if fragment.strip() in ("cl", "chile"):
            continue
        region = _region_of(fragment)
        if region:
            return region
    if contains(text, "remoto") or contains(text, "remote"):
        return "Remoto"
    return "Otra / no identificada"
