#!/usr/bin/env python3
"""Builds the coded corpus from the catalog packages (502 zips).

Pipeline:
  1. Locates the canonical SKILL.md of each zip (variable depth), extracts
     the structural signals, and merges the catalog metadata (skills.json).
  2. Codes each skill with an LLM through an OpenAI-compatible endpoint:
     functional_domain, input/output_artifact, delegation_intent,
     user_interaction, interaction_evidence, risk_impact, side_effect_scope.
  3. Derives matrix_cell (declared x encoded) and writes corpus.csv and
     codebook.json.

The catalog is proprietary and not released, so this script documents the
pipeline and the coding prompt (SYSTEM_PROMPT, build_user_content); it cannot
be run without it. The catalog directory must contain zips/,
download_manifest.json, and skills.json. The released data/labels.csv keeps
the coded labels and structural signals of corpus.csv, without the catalog
text, after the manual review of the autonomous labels
(apply_autonomous_review.py).

Usage:
  python build_corpus.py --catalog DIR --smoke        # one call, checks the endpoint
  python build_corpus.py --catalog DIR --extract-only # extraction and signals only
  python build_corpus.py --catalog DIR                # full run (checkpoint/resume)

Environment: LLM_BASE_URL, LLM_API_KEY, LLM_MODEL (default gpt-4o-mini).
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import os
import random
import re
import sys
import zipfile
from collections import Counter
from pathlib import Path

import httpx

# --- Config ---------------------------------------------------------------

# set from --catalog in main()
ZIPS_DIR = MANIFEST_PATH = SKILLS_JSON_PATH = Path()
OUT_DIR = Path(__file__).resolve().parent.parent / "build"
SKILLS_OUT = OUT_DIR / "skills"
CORPUS_CSV = OUT_DIR / "corpus.csv"
CODEBOOK_JSON = OUT_DIR / "codebook.json"
CHECKPOINT = OUT_DIR / "coding.jsonl"

LLM_BASE_URL = os.getenv("LLM_BASE_URL", "").rstrip("/")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
MODEL = os.getenv("LLM_MODEL", "gpt-4o-mini")

POOL_SIZE = int(os.getenv("POOL_SIZE", "6"))
TIMEOUT = httpx.Timeout(connect=30.0, read=120.0, write=30.0, pool=30.0)


# --- Step 0: load manifest and skills.json --------------------------------

def load_manifest() -> dict[str, dict]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {m["slug"]: m for m in data}


def load_skills_json() -> dict[str, dict]:
    data = json.loads(SKILLS_JSON_PATH.read_text(encoding="utf-8"))
    return {s["slug"]: s for s in data}


# --- Step 1: extraction ---------------------------------------------------

def _slug_norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def split_frontmatter(text: str) -> tuple[str, str]:
    """Returns (frontmatter, body). Looks for the closing '---' on a line of
    its own, which is more robust than find('---')."""
    if not text.startswith("---"):
        return "", text
    lines = text.splitlines()
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[1:i]), "\n".join(lines[i + 1:])
    return "", text


def canonical_entry(names: list[str], slug: str) -> tuple[str, str] | None:
    """Locates the SKILL.md (or .mdc) entry most likely to be the skill.

    Returns (path, kind) with kind in {'md', 'mdc'}, or None if there is none.
    Prefers the shallowest SKILL.md and, on a tie, the one whose parent
    directory matches the slug.
    """
    candidates = []
    for n in names:
        clean = n.rstrip("/")
        if clean == "SKILL.md" or clean.endswith("/SKILL.md"):
            candidates.append((n, "md"))
        elif clean == "SKILL.mdc" or clean.endswith("/SKILL.mdc"):
            candidates.append((n, "mdc"))

    if not candidates:
        return None

    # md is preferred over mdc
    md = [c for c in candidates if c[1] == "md"]
    pool = md or candidates

    def key(c):
        n, kind = c
        depth = n.count("/")
        parent = (n.split("/")[-2] if "/" in n else "")
        slug_match = _slug_norm(parent) == _slug_norm(slug)
        return (depth, 0 if slug_match else 1, 0 if kind == "md" else 1)

    return min(pool, key=key)


def extract_one(slug: str, zip_path: Path) -> dict | None:
    """Extracts the structural signals of a zip. Returns a dict, or None if invalid."""
    with zipfile.ZipFile(zip_path) as zf:
        names = zf.namelist()
    entry = canonical_entry(names, slug)
    if entry is None:
        return None
    path, kind = entry

    with zipfile.ZipFile(zip_path) as zf:
        text = zf.read(path).decode("utf-8", errors="ignore")

    # skill root = parent directory of the canonical entry
    root = path.rsplit("/", 1)[0] if "/" in path else ""
    has_references = any(
        (n.startswith(root + "/references/") if root else n.startswith("references/"))
        for n in names
    )

    frontmatter, body = split_frontmatter(text)

    has_shell_commands = bool(re.search(r"```\s*(bash|sh|shell|zsh)", body, re.IGNORECASE))
    has_sql_block = bool(re.search(r"```\s*(sql|postgres|mysql)", body, re.IGNORECASE))
    has_python_block = bool(re.search(r"```\s*(python|py)", body, re.IGNORECASE))
    has_ask_user = "AskUserQuestion" in text
    has_always_apply = "alwaysApply" in text
    has_argument_hint = "argument-hint" in text
    solicits_input = bool(re.search(
        r"(ask\s+(the\s+)?user|gather.*information|collect.*answer|"
        r"prompt.*user|wait.*user|request.*user|perguntas.*usuário|"
        r"coletar.*respostas|ANTES\s+DE|before\s+(proceeding|creating|generating))",
        body, re.IGNORECASE,
    ))
    word_count = len(body.split())

    # Writes the normalized SKILL.md to skills/<slug>/
    out_file = SKILLS_OUT / slug / "SKILL.md"
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(text, encoding="utf-8")

    return {
        "entry": path,
        "entry_via_mdc": kind == "mdc",
        "has_references": has_references,
        "has_shell_commands": has_shell_commands,
        "has_sql_block": has_sql_block,
        "has_python_block": has_python_block,
        "has_ask_user_tool": has_ask_user,
        "has_always_apply": has_always_apply,
        "has_argument_hint": has_argument_hint,
        "solicits_input_structurally": solicits_input,
        "word_count": word_count,
        "body_preview": body[:600].replace("\n", " "),
    }


# --- Step 2: LLM coding ---------------------------------------------------

SYSTEM_PROMPT = """You are a qualitative researcher coding a corpus of LLM agent skill descriptions for a software engineering study.

For each skill, assign EXACTLY the following fields:

1. **functional_domain** — one of these categories (pick the SINGLE best fit):
   - Infrastructure/Deploy: deploying services, containers, K8s, CI/CD setup
   - Observability/Debug: logs, monitoring, error investigation, Sentry, K8s debug
   - Code Quality: tests, coverage, linting, static analysis, code review
   - Version Control: git, GitLab, MRs, branches
   - Data/ML: SQL queries, Databricks, ML pipelines, model evaluation, data products
   - Documentation: generating docs, postmortems, table contracts, dbt docs
   - Communication/Collaboration: presentations, slides, context sharing, Slack, ticketing
   - Process/Planning: brainstorming, ticket description, project management
   - Business Domain: company-specific tools, internal workflows, custom CLIs
   - Meta/Agent: skills about creating or managing skills/agents themselves

2. **input_artifact** — what the skill primarily consumes (e.g., code, log, ticket, SQL, PR, config, conversation, PDF, image, none)

3. **output_artifact** — what the skill primarily produces (e.g., code, YAML, report, comment, PR, slide, SQL, summary, none)

4. **delegation_intent** — one word:
   - assistive: guides the user or provides info/analysis WITHOUT committing irreversible actions
   - executive: produces real side effects (writes files, opens merge requests, runs deployments, mutates state)

5. **user_interaction** — classify how the skill interacts with the user before/during execution:
   - autonomous: acts on its own without requiring user input (fires automatically, fixed pipeline, no questions)
   - interactive: explicitly solicits structured input before/during execution (asks questions, collects answers, prompts for missing info)
   - reactive: triggered by user request but executes to completion without further interaction

6. **interaction_evidence** — one short phrase (max 10 words) justifying the user_interaction choice

7. **risk_impact** — ordinal estimate of worst-case consequence if the skill runs end-to-end unattended:
   - none: read/analysis only; no external side effect
   - low: writes local files or a reversible artifact (pptx, csv, report)
   - medium: opens MR/issue, sends message, incurs metered cost, mutates service-scoped state (Jira, Sentry, Slack, Databricks table)
   - high: production change, schema migration, ML training/deploy on shared infra, write to org-shared regulated system

8. **side_effect_scope** — where side effects land:
   - local: developer filesystem only
   - service: bounded service state (Jira ticket, Sentry issue, Databricks table, Slack canvas)
   - org: shared organizational asset (MR on production repo, cluster resource, ML infra)
   - external: third-party service outside organizational boundary

Respond ONLY with valid JSON, no explanation:
{"functional_domain":"...","input_artifact":"...","output_artifact":"...","delegation_intent":"...","user_interaction":"...","interaction_evidence":"...","risk_impact":"...","side_effect_scope":"..."}
"""


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {LLM_API_KEY}",
        "Content-Type": "application/json",
    }


def build_user_content(rec: dict) -> str:
    return f"""Skill name: {rec['name']}
Description: {rec['description']}
Catalog category: {rec.get('category', '')} / {rec.get('subcategory', '')}
Output: {rec.get('output', '')} | Area: {rec.get('area', '')} | Goal: {rec.get('goal', '')}
Tags: {rec.get('tags', '')}
Has shell commands in body: {rec['has_shell_commands']}
Has SQL block in body: {rec['has_sql_block']}
Has Python block in body: {rec['has_python_block']}
Uses AskUserQuestion tool: {rec['has_ask_user_tool']}
Body explicitly solicits user input: {rec['solicits_input_structurally']}
Word count: {rec['word_count']}
Body preview: {rec['body_preview']}"""


async def chat_completion(client: httpx.AsyncClient, content: str) -> str:
    url = f"{LLM_BASE_URL}/chat/completions"
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": content},
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }
    max_retries = 4
    for attempt in range(1, max_retries + 1):
        try:
            resp = await client.post(url, headers=_headers(), json=payload)
            if resp.status_code == 401:
                raise RuntimeError("401: invalid or expired API key")
            if resp.status_code == 429 or resp.status_code >= 500:
                if attempt < max_retries:
                    await asyncio.sleep((2 ** attempt) + random.uniform(0, 1))
                    continue
                raise RuntimeError(f"HTTP {resp.status_code} after {max_retries} attempts")
            resp.raise_for_status()
            return resp.json()["choices"][0]["message"]["content"].strip()
        except httpx.TimeoutException:
            if attempt < max_retries:
                await asyncio.sleep(2 ** attempt)
                continue
            raise


def parse_coding(raw: str) -> dict:
    raw = re.sub(r"^```[a-z]*\n?", "", raw.strip())
    raw = re.sub(r"\n?```$", "", raw.strip())
    # keeps only the JSON object (the model may add text around it)
    m = re.search(r"\{.*\}", raw, re.DOTALL)
    if m:
        raw = m.group(0)
    return json.loads(raw)


def matrix_cell(intent: str, has_shell: bool, interaction: str) -> str:
    intent = (intent or "").strip().lower()
    interaction = (interaction or "").strip().lower()
    if intent == "assistive":
        return "Under-declared" if has_shell else "Aligned-Assistive"
    if intent == "executive":
        return "Over-declared" if interaction == "interactive" else "Aligned-Executive"
    return "UNCODED"


# --- Codebook -------------------------------------------------------------

def build_codebook(rows: list[dict]) -> dict:
    def dist(key):
        return dict(Counter((r.get(key) or "") for r in rows).most_common())

    def crosstab(k1, k2):
        c = Counter((r.get(k1), r.get(k2)) for r in rows)
        return {f"{a} × {b}": v for (a, b), v in sorted(c.items(), key=lambda x: -x[1])}

    wc = [int(r["word_count"]) for r in rows if str(r.get("word_count", "")).strip()]
    return {
        "total_skills": len(rows),
        "functional_domain_distribution": dist("functional_domain"),
        "delegation_intent_distribution": dist("delegation_intent"),
        "user_interaction_distribution": dist("user_interaction"),
        "risk_impact_distribution": dist("risk_impact"),
        "side_effect_scope_distribution": dist("side_effect_scope"),
        "matrix_cell_distribution": dist("matrix_cell"),
        "interaction_x_intent_crosstab": crosstab("user_interaction", "delegation_intent"),
        "risk_x_intent_crosstab": crosstab("risk_impact", "delegation_intent"),
        "word_count": {
            "n": len(wc), "min": min(wc), "max": max(wc),
            "median": sorted(wc)[len(wc) // 2],
            "mean": round(sum(wc) / len(wc)),
        },
        "has_shell_commands": sum(1 for r in rows if r.get("has_shell_commands")),
        "has_ask_user_tool": sum(1 for r in rows if r.get("has_ask_user_tool")),
    }


CSV_FIELDS = [
    "dir", "name", "description", "category", "subcategory", "output", "area",
    "goal", "tags", "version", "download_count",
    "has_references", "has_shell_commands", "has_sql_block", "has_python_block",
    "has_ask_user_tool", "has_always_apply", "has_argument_hint",
    "solicits_input_structurally", "word_count",
    "functional_domain", "input_artifact", "output_artifact",
    "delegation_intent", "user_interaction", "interaction_evidence",
    "risk_impact", "side_effect_scope", "matrix_cell", "entry_via_mdc",
    "body_preview",
]


# --- Main -----------------------------------------------------------------

def build_records(manifest: dict, skills_json: dict) -> list[dict]:
    records = []
    missing_zip = []
    for slug in sorted(skills_json.keys()):
        meta = skills_json[slug]
        man = manifest.get(slug)
        if not man:
            missing_zip.append(slug)
            continue
        zip_path = ZIPS_DIR / man["file"]
        if not zip_path.exists():
            missing_zip.append(slug)
            continue
        ext = extract_one(slug, zip_path)
        if ext is None:
            print(f"  [skip] {slug}: sem SKILL.md/SKILL.mdc no zip", file=sys.stderr)
            continue
        rec = {
            "dir": slug,
            "name": meta.get("display_name") or slug,
            "description": (meta.get("description") or "").strip(),
            "category": (meta.get("category") or {}).get("name", ""),
            "subcategory": (meta.get("subcategory") or {}).get("name", ""),
            "output": meta.get("output", ""),
            "area": meta.get("area", ""),
            "goal": meta.get("goal", ""),
            "tags": ",".join(meta.get("tags") or []),
            "version": meta.get("current_version", ""),
            "download_count": meta.get("download_count", ""),
        }
        rec.update(ext)
        records.append(rec)
    if missing_zip:
        print(f"  [warn] {len(missing_zip)} slugs sem zip:", missing_zip[:10], file=sys.stderr)
    return records


async def run_coding(records: list[dict], limit: int | None) -> None:
    # resume from the checkpoint
    done: dict[str, dict] = {}
    if CHECKPOINT.exists():
        for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                d = json.loads(line)
                done[d["dir"]] = d
            except json.JSONDecodeError:
                pass

    todo = [r for r in records if r["dir"] not in done]
    if limit:
        todo = todo[:limit]
    print(f"  already coded: {len(done)} | to code: {len(todo)}", file=sys.stderr)

    sem = asyncio.Semaphore(POOL_SIZE)
    checkpoint_fh = CHECKPOINT.open("a", encoding="utf-8")

    async def worker(rec: dict):
        async with sem:
            raw = await chat_completion(
                httpx.AsyncClient(timeout=TIMEOUT, trust_env=False),
                build_user_content(rec),
            )
        coding = parse_coding(raw)
        full = dict(rec)
        full.update(coding)
        full["matrix_cell"] = matrix_cell(
            coding.get("delegation_intent"),
            bool(rec.get("has_shell_commands")),
            coding.get("user_interaction"),
        )
        # incremental checkpoint
        checkpoint_fh.write(json.dumps(full, ensure_ascii=False) + "\n")
        checkpoint_fh.flush()
        done[rec["dir"]] = full
        return full

    results = await asyncio.gather(*(worker(r) for r in todo), return_exceptions=True)
    failures = [r for r in results if isinstance(r, Exception)]
    if failures:
        print(f"  [warn] {len(failures)} coding failures", file=sys.stderr)
        for f in failures[:5]:
            print(f"    {f}", file=sys.stderr)
    checkpoint_fh.close()
    print(f"  checkpoint: {CHECKPOINT} ({len(done)} registros)", file=sys.stderr)


def main():
    global ZIPS_DIR, MANIFEST_PATH, SKILLS_JSON_PATH
    ap = argparse.ArgumentParser()
    ap.add_argument("--catalog", required=True, type=Path,
                    help="directory with zips/, download_manifest.json, and skills.json")
    ap.add_argument("--smoke", action="store_true", help="one test call")
    ap.add_argument("--extract-only", action="store_true", help="extraction only, no LLM")
    ap.add_argument("--limit", type=int, default=None, help="maximum number of skills to code")
    args = ap.parse_args()
    ZIPS_DIR = args.catalog / "zips"
    MANIFEST_PATH = args.catalog / "download_manifest.json"
    SKILLS_JSON_PATH = args.catalog / "skills.json"
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = load_manifest()
    skills_json = load_skills_json()
    print(f"manifest: {len(manifest)} | skills.json: {len(skills_json)}", file=sys.stderr)

    if args.smoke:
        if not LLM_API_KEY:
            sys.exit("LLM_API_KEY is not set")
        async def _s():
            async with httpx.AsyncClient(timeout=TIMEOUT, trust_env=False) as c:
                raw = await chat_completion(c, "Reply only with: ok")
            print("SMOKE OK ->", raw)
        asyncio.run(_s())
        return

    records = build_records(manifest, skills_json)
    print(f"records extracted: {len(records)}", file=sys.stderr)

    if args.extract_only:
        with open(CORPUS_CSV, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
            w.writeheader()
            for r in records:
                r.setdefault("functional_domain", "")
                w.writerow(r)
        print(f"corpus (uncoded) -> {CORPUS_CSV}", file=sys.stderr)
        return

    if not LLM_API_KEY:
        sys.exit("LLM_API_KEY is not set (needed for coding)")

    asyncio.run(run_coding(records, args.limit))

    # reassemble the final corpus from the checkpoint (stable order)
    done = {}
    for line in CHECKPOINT.read_text(encoding="utf-8").splitlines():
        if line.strip():
            d = json.loads(line)
            done[d["dir"]] = d
    final = [done.get(r["dir"], r) for r in records]

    with open(CORPUS_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=CSV_FIELDS, extrasaction="ignore")
        w.writeheader()
        w.writerows(final)
    print(f"corpus -> {CORPUS_CSV} ({len(final)} rows)", file=sys.stderr)

    codebook = build_codebook(final)
    CODEBOOK_JSON.write_text(json.dumps(codebook, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"codebook -> {CODEBOOK_JSON}", file=sys.stderr)
    print(json.dumps(codebook, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
