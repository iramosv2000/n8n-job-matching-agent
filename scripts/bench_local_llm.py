"""M1-07 spike: benchmark local LLMs served by Ollama for the project's two LLM tasks.

Usage: python3 scripts/bench_local_llm.py MODEL [MODEL ...] [--out evals/results/m1-07-local-llm-bench.json]

Tasks (synthetic data only, see evals/synthetic/):
  1. Requirement extraction: 6 fictitious offers -> JSON constrained by
     evals/schemas/requirements.v0.json, scored against hand labels.
  2. CV adaptation: fictitious CV + generic protocol + target offer + market context ->
     JSON with LaTeX sections. Offer skills absent from the CV that appear in the sections
     are classified per sentence as "fabricated" (affirmative) or "gap leak" (negated mention,
     e.g. "no cuenta con experiencia en ..."), which also harms the candidate.
  3. Context probe: a >= 8k-token prompt with a verification code at the very beginning;
     the model must return the code, proving the start of the prompt was not truncated.

Measures per model: load time, latency, generation speed, schema validity, field accuracy,
skill recall, prompt size actually processed, resident model size and CPU/GPU split
(`ollama ps`), macOS memory pressure and swap. Run with the Docker stack up, as in real use.
Standard library only.
"""

from __future__ import annotations

import argparse
import json
import platform
import re
import subprocess
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OLLAMA = "http://127.0.0.1:11434"
REQUEST_TIMEOUT_S = 600
# Output caps per task: without them a model can generate until the context is full.
NUM_PREDICT = {"extraction": 768, "cv": 4096, "probe": 64}
SCALAR_FIELDS = [
    "years_required",
    "years_is_desirable",
    "contract",
    "modality",
    "salary_min_clp",
    "salary_max_clp",
    "salary_is_net",
]

EXTRACTION_SYSTEM = """Eres un extractor de requisitos de ofertas de empleo chilenas.
Devuelve SOLO un objeto JSON que cumpla el esquema. Reglas:
- years_required: mínimo de años de experiencia pedidos. 0 si dice explícitamente que no se exige
  experiencia; null si no se menciona. Si da un rango ("entre 4 y 6"), usa el mínimo.
- years_is_desirable: true solo si la experiencia se presenta como deseable/valorada, no exigida.
- contract: indefinido | plazo_fijo | plazo_fijo_a_indefinido (plazo fijo con paso a indefinido) |
  honorarios | no_indicado.
- modality: presencial | hibrido | remoto | no_indicado.
- salary_min_clp / salary_max_clp: enteros en pesos chilenos; si hay un solo monto, ambos iguales;
  null si no se informa o es "a convenir".
- salary_is_net: true si dice "líquido", false si dice "bruto"/"brutos", null si no se informa.
- key_skills: tecnologías, herramientas o técnicas explícitas en el texto (máximo 12), con el
  nombre tal como aparece. No inventes requisitos."""

CV_SYSTEM = """Eres un asistente que adapta un CV en LaTeX a una oferta de empleo.
Reglas obligatorias:
1. Solo puedes reordenar, reformular y priorizar hechos que YA están en el CV.
2. Está prohibido agregar herramientas, tecnologías, cargos, cifras o logros que no aparezcan en el CV.
3. Lo que la oferta pide y el CV no tiene va en "gaps", nunca dentro de las secciones.
4. Entrega secciones LaTeX completas (Resumen Profesional, Experiencia Profesional, Habilidades
   Técnicas) listas para pegar, manteniendo los comandos del CV original.
5. match_before y match_after son porcentajes (0-100) de ajuste antes y después de los cambios.
Devuelve SOLO un objeto JSON que cumpla el esquema."""

NEGATION_CUES = (
    "no cuenta",
    "sin experiencia",
    "no tiene",
    "no posee",
    "no ha ",
    "nota:",
    "carece",
    "falta de",
    "en aprendizaje",
    "por aprender",
    "desconoce",
    "no domina",
)

CV_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["match_before", "match_after", "keywords", "sections", "gaps"],
    "properties": {
        "match_before": {"type": "integer"},
        "match_after": {"type": "integer"},
        "keywords": {"type": "array", "items": {"type": "string"}},
        "sections": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "latex"],
                "properties": {"name": {"type": "string"}, "latex": {"type": "string"}},
            },
        },
        "gaps": {"type": "array", "items": {"type": "string"}},
    },
}


# ----------------------------------------------------------------------------- helpers


def norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().lower()
    return re.sub(r"\s+", " ", text).strip()


def validate(value, schema) -> list[str]:
    """Minimal JSON Schema check for the subset used here (type, enum, required, items...)."""
    errors: list[str] = []
    types = schema.get("type")
    if types:
        allowed = types if isinstance(types, list) else [types]
        checks = {
            "object": lambda v: isinstance(v, dict),
            "array": lambda v: isinstance(v, list),
            "string": lambda v: isinstance(v, str),
            "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
            "boolean": lambda v: isinstance(v, bool),
            "null": lambda v: v is None,
        }
        if not any(checks[t](value) for t in allowed):
            return [f"type {type(value).__name__} not in {allowed}"]
    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{value!r} not in enum")
    if isinstance(value, dict):
        props = schema.get("properties", {})
        errors += [f"missing '{k}'" for k in schema.get("required", []) if k not in value]
        if schema.get("additionalProperties") is False:
            errors += [f"extra '{k}'" for k in value if k not in props]
        for key, sub in props.items():
            if key in value:
                errors += [f"{key}: {e}" for e in validate(value[key], sub)]
    if isinstance(value, list):
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(f"{len(value)} items > maxItems {schema['maxItems']}")
        for i, item in enumerate(value):
            errors += [f"[{i}]: {e}" for e in validate(item, schema.get("items", {}))]
    return errors


def post(path: str, payload: dict, timeout: int = 900) -> dict:
    req = urllib.request.Request(
        OLLAMA + path, data=json.dumps(payload).encode(), headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read())


def chat(
    model: str, system: str, user: str, schema: dict, num_ctx: int, num_predict: int
) -> tuple[dict, float]:
    """One schema-constrained chat call. Errors and timeouts are returned as {"error": ...}."""
    payload = {
        "model": model,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "format": schema,
        "stream": False,
        "think": False,
        "options": {"temperature": 0, "num_ctx": num_ctx, "num_predict": num_predict, "seed": 7},
    }
    start = time.time()
    try:
        try:
            data = post("/api/chat", payload, timeout=REQUEST_TIMEOUT_S)
        except urllib.error.HTTPError as exc:
            if exc.code == 400 and b"think" in exc.read():
                payload.pop("think")
                data = post("/api/chat", payload, timeout=REQUEST_TIMEOUT_S)
            else:
                raise
    except (urllib.error.URLError, TimeoutError, ConnectionError) as exc:
        data = {"error": f"{type(exc).__name__}: {exc}"[:200]}
    return data, time.time() - start


def sh(cmd: list[str]) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ""


def system_memory() -> dict:
    free = re.search(r"free percentage:\s*(\d+)%", sh(["memory_pressure", "-Q"]))
    swap = re.search(r"used = ([\d.]+)M", sh(["sysctl", "vm.swapusage"]))
    return {
        "free_pct": int(free.group(1)) if free else None,
        "swap_used_mb": float(swap.group(1)) if swap else None,
    }


def ollama_ps(model: str) -> dict:
    for line in sh(["ollama", "ps"]).splitlines()[1:]:
        if line.startswith(model):
            size = re.search(r"(\d+(?:\.\d+)?\s*[GM]B)", line)
            proc = re.search(r"(\d+%\s*(?:GPU|CPU)(?:/\d+%\s*(?:GPU|CPU))?)", line)
            return {"size": size.group(1) if size else None, "processor": proc.group(1) if proc else None}
    return {}


def speed(data: dict) -> dict:
    ns = 1e9
    return {
        "done_reason": data.get("done_reason"),
        "error": data.get("error"),
        "prompt_tokens": data.get("prompt_eval_count"),
        "output_tokens": data.get("eval_count"),
        "load_s": round(data.get("load_duration", 0) / ns, 2),
        "prompt_tok_s": round(data["prompt_eval_count"] / (data["prompt_eval_duration"] / ns), 1)
        if data.get("prompt_eval_duration")
        else None,
        "gen_tok_s": round(data["eval_count"] / (data["eval_duration"] / ns), 1)
        if data.get("eval_duration")
        else None,
    }


# ----------------------------------------------------------------------------- tasks


def run_extraction(model: str, offers: list[dict], schema: dict) -> dict:
    rows = []
    for offer in offers:
        user = f"{offer['title']}\n\n{offer['text']}"
        data, wall = chat(model, EXTRACTION_SYSTEM, user, schema, 8192, NUM_PREDICT["extraction"])
        raw = data.get("message", {}).get("content", "")
        try:
            out = json.loads(raw)
            schema_errors = validate(out, schema)
        except json.JSONDecodeError:
            out, schema_errors = None, ["invalid JSON"]
        truth = offer["truth"]
        fields = {f: (out or {}).get(f) == truth[f] for f in SCALAR_FIELDS}
        got = [norm(s) for s in (out or {}).get("key_skills", []) if isinstance(s, str)]
        hits = [s for s in truth["key_skills"] if any(norm(s) in g or g in norm(s) for g in got if g)]
        rows.append(
            {
                "offer": offer["id"],
                "wall_s": round(wall, 2),
                **speed(data),
                "valid_json": out is not None,
                "schema_errors": schema_errors,
                "fields_correct": fields,
                "skill_recall": round(len(hits) / len(truth["key_skills"]), 3),
                "output": out,
            }
        )
    n = len(rows)
    return {
        "per_offer": rows,
        "schema_valid_rate": sum(not r["schema_errors"] for r in rows) / n,
        "field_accuracy": round(
            sum(sum(r["fields_correct"].values()) for r in rows) / (n * len(SCALAR_FIELDS)), 3
        ),
        "field_accuracy_by_field": {f: sum(r["fields_correct"][f] for r in rows) / n for f in SCALAR_FIELDS},
        "skill_recall_mean": round(sum(r["skill_recall"] for r in rows) / n, 3),
        "wall_s_mean": round(sum(r["wall_s"] for r in rows) / n, 2),
        "wall_s_max": max(r["wall_s"] for r in rows),
        "gen_tok_s_mean": round(sum(r["gen_tok_s"] or 0 for r in rows) / n, 1),
        "hit_output_cap": sum(r["done_reason"] == "length" for r in rows),
        "errors": sum(bool(r["error"]) for r in rows),
    }


def run_cv(model: str, offers: list[dict], cv: str, protocol: str) -> dict:
    target, context = offers[0], offers[1:]
    market = "\n\n".join(f"### {o['title']}\n{o['text']}" for o in context)
    user = (
        f"## CV maestro (LaTeX)\n{cv}\n\n## Oferta objetivo\n### {target['title']}\n{target['text']}\n\n"
        f"## Contexto de mercado (otras ofertas vistas; NO son la oferta objetivo)\n{market}"
    )
    data, wall = chat(model, f"{CV_SYSTEM}\n\n{protocol}", user, CV_SCHEMA, 16384, NUM_PREDICT["cv"])
    raw = data.get("message", {}).get("content", "")
    try:
        out = json.loads(raw)
        schema_errors = validate(out, CV_SCHEMA)
    except json.JSONDecodeError:
        out, schema_errors = None, ["invalid JSON"]
    cv_norm = norm(cv)
    missing_in_cv = [s for s in target["truth"]["key_skills"] if norm(s) not in cv_norm]
    latex = " ".join(s.get("latex", "") for s in (out or {}).get("sections", []) if isinstance(s, dict))
    sentences = [norm(x) for x in re.split(r"\\n|\n|\\item|(?<=\.)\s", latex) if x.strip()]
    fabricated, leaked = [], []
    for skill in missing_in_cv:
        pattern = r"\b" + re.escape(norm(skill)) + r"\b"
        hits = [x for x in sentences if re.search(pattern, x)]
        if any(not any(cue in x for cue in NEGATION_CUES) for x in hits):
            fabricated.append(skill)
        elif hits:
            leaked.append(skill)
    gaps = norm(" ".join(g for g in (out or {}).get("gaps", []) if isinstance(g, str)))
    return {
        "wall_s": round(wall, 2),
        **speed(data),
        "valid_json": out is not None,
        "schema_errors": schema_errors,
        "sections": len((out or {}).get("sections", [])),
        "offer_skills_absent_from_cv": missing_in_cv,
        "fabricated_in_sections": fabricated,
        "gap_leaks_in_sections": leaked,
        "gaps_recall": round(sum(norm(s) in gaps for s in missing_in_cv) / max(1, len(missing_in_cv)), 3),
        "output": out,
    }


def run_context_probe(model: str, offers: list[dict], cv: str, protocol: str) -> dict:
    code = "VERIF-7Q4-ANDES"
    block = "\n\n".join([cv, protocol] + [f"### {o['title']}\n{o['text']}" for o in offers])
    filler = "\n\n".join([block] * 3)
    user = (
        f"Código de verificación: {code}. Recuérdalo.\n\n{filler}\n\n"
        "Pregunta: ¿cuál es el código de verificación indicado al comienzo de este mensaje?"
    )
    schema = {
        "type": "object",
        "additionalProperties": False,
        "required": ["code"],
        "properties": {"code": {"type": "string"}},
    }
    data, wall = chat(model, "Responde solo con JSON.", user, schema, 16384, NUM_PREDICT["probe"])
    try:
        answer = json.loads(data.get("message", {}).get("content", "")).get("code", "")
    except (json.JSONDecodeError, AttributeError):
        answer = ""
    return {"wall_s": round(wall, 2), **speed(data), "code_recovered": code in answer, "answer": answer[:60]}


def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("models", nargs="+")
    parser.add_argument("--out", default=str(ROOT / "evals/results/m1-07-local-llm-bench.json"))
    args = parser.parse_args()

    offers = json.loads((ROOT / "evals/synthetic/offers.json").read_text(encoding="utf-8"))["offers"]
    schema = json.loads((ROOT / "evals/schemas/requirements.v0.json").read_text(encoding="utf-8"))
    schema = {k: v for k, v in schema.items() if not k.startswith("$") and k != "title"}
    cv = (ROOT / "evals/synthetic/cv_example.tex").read_text(encoding="utf-8")
    protocol = (ROOT / "evals/synthetic/protocol_example.md").read_text(encoding="utf-8")
    try:
        with urllib.request.urlopen(OLLAMA + "/api/tags", timeout=30) as resp:
            tags = {m["name"]: m for m in json.loads(resp.read())["models"]}
        with urllib.request.urlopen(OLLAMA + "/api/version", timeout=30) as resp:
            ollama_version = json.loads(resp.read())["version"]
    except urllib.error.URLError as exc:
        raise SystemExit(f"Ollama is not reachable at {OLLAMA}: {exc}") from exc

    report = {
        "date": time.strftime("%Y-%m-%d %H:%M %Z"),
        "machine": {
            "chip": sh(["sysctl", "-n", "machdep.cpu.brand_string"]).strip(),
            "ram_gb": round(int(sh(["sysctl", "-n", "hw.memsize"]) or 0) / 2**30),
            "macos": platform.mac_ver()[0],
        },
        "ollama_version": ollama_version,
        "docker_containers_running": len(sh(["docker", "ps", "-q"]).split()),
        "models": {},
    }
    for model in args.models:
        print(f"== {model}", flush=True)
        before = system_memory()
        extraction = run_extraction(model, offers, schema)
        resident = ollama_ps(model)
        during = system_memory()
        cv_task = run_cv(model, offers, cv, protocol)
        probe = run_context_probe(model, offers, cv, protocol)
        after = system_memory()
        post("/api/generate", {"model": model, "keep_alive": 0}, 120)
        report["models"][model] = {
            "digest": tags.get(model, {}).get("digest", "")[:12],
            "download_gb": round(tags.get(model, {}).get("size", 0) / 1e9, 2),
            "resident": resident,
            "memory": {"before": before, "after_extraction": during, "after_cv": after},
            "extraction": extraction,
            "cv_adaptation": cv_task,
            "context_probe": probe,
        }
        e, c = extraction, cv_task
        print(
            f"   extraction: schema-valid {e['schema_valid_rate']:.0%}, fields {e['field_accuracy']:.0%}, "
            f"skills recall {e['skill_recall_mean']:.0%}, mean {e['wall_s_mean']} s, "
            f"{e['gen_tok_s_mean']} tok/s"
        )
        print(
            f"   cv: valid {c['valid_json'] and not c['schema_errors']}, prompt {c['prompt_tokens']} tok, "
            f"{c['wall_s']} s, fabricated {c['fabricated_in_sections']}, leaks {c['gap_leaks_in_sections']}, "
            f"gaps recall {c['gaps_recall']:.0%}"
        )
        print(
            f"   probe: {probe['prompt_tokens']} tok, "
            f"code recovered {probe['code_recovered']}, {probe['wall_s']} s"
        )
        print(
            f"   resident {resident}, free mem {after['free_pct']}%, swap {after['swap_used_mb']} MB",
            flush=True,
        )

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {args.out}")


if __name__ == "__main__":
    main()
