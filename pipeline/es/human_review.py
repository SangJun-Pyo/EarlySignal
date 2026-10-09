"""Offline blind review preparation. No API, credential, or .env access."""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import tempfile

from .config import CATEGORIES, Config
from . import label_llm
from .privacy import redact_text, sensitive_values

REVIEW_SEED = "human-review-v1"
REVIEW_SIZE = 30
DEVELOPMENT_SEED = "seed42"
DEVELOPMENT_SIZE = 50
VERSION = "earlysignal-human-review-v1"
BLIND_FIELDS = ["review_id", "text", "gold_primary", "review_status", "gold_evidence", "human_notes"]
MAPPING_FIELDS = ["review_id", "odino", "input_hash"]
STATUSES = {"", "clear", "ambiguous", "unjudgeable"}


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def selected_ids(rows):
    ids = [str(row["odino"]) for row in rows]
    if len(set(ids)) != len(ids) or any(not i.isascii() or not i.isdigit() for i in ids):
        raise ValueError("Review population requires unique numeric complaint IDs")
    development = set(sorted(ids, key=lambda i: digest(f"{DEVELOPMENT_SEED}:{i}"))[:DEVELOPMENT_SIZE])
    eligible = set(ids) - development
    if len(eligible) < REVIEW_SIZE or len(development) != DEVELOPMENT_SIZE:
        raise ValueError("Population cannot support 50 development plus 30 independent rows")
    selected = sorted(eligible, key=lambda i: digest(f"{REVIEW_SEED}:{i}"))[:REVIEW_SIZE]
    return selected, development


def _write_private(path, content):
    with path.open("w", encoding="utf-8", newline="") as handle:
        os.chmod(path, 0o600)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())


def _csv_text(fields, rows):
    import io
    handle = io.StringIO(newline="")
    writer = csv.DictWriter(handle, fieldnames=fields)
    writer.writeheader()
    writer.writerows(rows)
    return handle.getvalue()


def _read_csv(path, fields):
    with path.open(encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != fields:
            raise ValueError("Existing review columns changed; original answers are unchanged")
        rows = list(reader)
        expected_fields = set(fields)
        for row in rows:
            if set(row) != expected_fields or any(not isinstance(cell, str) for cell in row.values()):
                raise ValueError("Existing review row has missing or extra cells; no file was overwritten")
        return rows


def _validate_existing(output, manifest, mapping, blank_rows):
    try:
        existing = json.loads((output / "manifest.json").read_text(encoding="utf-8"))
        if existing != manifest:
            raise ValueError("Review input, population, model, prompt, policy or rubric lock changed")
        if _read_csv(output / "mapping.csv", MAPPING_FIELDS) != mapping:
            raise ValueError("Review mapping changed")
        reviewed = _read_csv(output / "blind.csv", BLIND_FIELDS)
        by_id = {row["review_id"]: row for row in reviewed}
        if len(by_id) != REVIEW_SIZE or len(reviewed) != REVIEW_SIZE or set(by_id) != {r["review_id"] for r in blank_rows}:
            raise ValueError("Review rows changed")
        for original in blank_rows:
            row = by_id[original["review_id"]]
            if row["text"] != original["text"]:
                raise ValueError("Review input text changed")
            if row["gold_primary"] and row["gold_primary"] not in CATEGORIES:
                raise ValueError("Review gold_primary must use the fixed category codes")
            if row["review_status"] not in STATUSES:
                raise ValueError("Review status must be clear, ambiguous or unjudgeable")
            if row["review_status"] == "clear" and not row["gold_primary"]:
                raise ValueError("Clear review requires a primary label")
        return reviewed
    except (OSError, json.JSONDecodeError, csv.Error, KeyError) as exc:
        raise ValueError("Existing review is incomplete or damaged; no file was overwritten") from None


def prepare_review(rows, *, root, model=label_llm.MODEL, quote_policy=label_llm.QUOTE_SELECTION_POLICY):
    """Prepare fixed blind rows or verify existing rows without overwriting answers."""
    root = Path(root)
    if quote_policy not in ("verbatim-only", label_llm.QUOTE_SELECTION_POLICY):
        raise ValueError("Unknown quote policy")
    selected, development = selected_ids(rows)
    sources = {str(row["odino"]): row for row in rows}
    blind, mapping = [], []
    for number, odino in enumerate(selected, 1):
        # Exactly the labeler's actual send preprocessing, not a 520-char public snippet.
        row = sources[odino]
        source = redact_text(row["text"], 1500, denied=row.get("denied", []))
        review_id = f"R{number:03d}"
        blind.append({"review_id": review_id, "text": source, **{f: "" for f in BLIND_FIELDS[2:]}})
        mapping.append({"review_id": review_id, "odino": odino, "input_hash": digest(source)})
    prompt_hash = digest(label_llm.system_prompt(root) + json.dumps(label_llm.LABEL_SCHEMA, sort_keys=True))
    rubric_path = root / "docs/Development/HUMAN_REVIEW.md"
    policy_lock = {"name": quote_policy,
                   "labeler_code_hash": digest(Path(label_llm.__file__).read_text(encoding="utf-8")),
                   "fallback_system_hash": digest(label_llm.QUOTE_SELECTION_SYSTEM) if quote_policy != "verbatim-only" else None}
    manifest = {"version": VERSION, "purpose": "independent evaluation preparation; human gold not yet measured",
                "population": len(rows), "review_size": REVIEW_SIZE, "excluded_development_size": len(development),
                "sampling_rule": {"development_seed": DEVELOPMENT_SEED, "excluded": "first 50 by SHA256(seed42:ODINO)",
                                  "review_seed": REVIEW_SEED, "selection": "first 30 eligible by SHA256(human-review-v1:ODINO)",
                                  "prediction_conditioning": False},
                "population_ids_hash": digest(canonical(sorted(sources))),
                "excluded_ids_hash": digest(canonical(sorted(development))),
                "model": model, "label_prompt_schema_hash": prompt_hash, "quote_policy": policy_lock,
                "rubric_hash": digest(rubric_path.read_text(encoding="utf-8")),
                "input_preprocessing": "same redact_text(text,1500,denied) as label_rows",
                "mapping_hash": digest(canonical(mapping)), "accuracy": None}
    private = root / "data/private"
    output = private / "human_review_independent30"
    if output.exists():
        reviewed = _validate_existing(output, manifest, mapping, blind)
        created = False
    else:
        private.mkdir(parents=True, exist_ok=True, mode=0o700)
        with tempfile.TemporaryDirectory(prefix="human-review-", dir=private) as temporary:
            stage = Path(temporary)
            os.chmod(stage, 0o700)
            _write_private(stage / "blind.csv", _csv_text(BLIND_FIELDS, blind))
            _write_private(stage / "mapping.csv", _csv_text(MAPPING_FIELDS, mapping))
            _write_private(stage / "manifest.json", canonical(manifest) + "\n")
            # The entire artifact appears together; never replace an existing review.
            stage.rename(output)
        reviewed = blind
        created = True
    return {"output": str(output), "blind_csv": str(output / "blind.csv"), "created": created,
            "population": len(rows), "independent_rows": REVIEW_SIZE, "excluded_development_rows": len(development),
            "filled_gold_rows": sum(bool(r["gold_primary"]) for r in reviewed), "accuracy": None,
            "api_calls": 0, "caveat": "Preparation only; prediction-blind human review remains to be completed."}


def run(config, *, model=label_llm.MODEL, quote_policy=label_llm.QUOTE_SELECTION_POLICY):
    import duckdb
    with duckdb.connect(str(config.database), read_only=True) as con:
        # ODI IDs are used only in the separate private mapping, never printed.
        rows = con.execute("SELECT odino,text FROM demo ORDER BY odino").fetchdf().to_dict("records")
        ids, _ = selected_ids(rows)
        denied = sensitive_values(con, ids)
        for row in rows:
            row["denied"] = denied.get(str(row["odino"]), [])
    return prepare_review(rows, root=config.root, model=model, quote_policy=quote_policy)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare 30 prediction-blind reviews without API or .env access")
    parser.add_argument("--root", type=Path, default=Config().root)
    parser.add_argument("--db", type=Path)
    parser.add_argument("--model", default=label_llm.MODEL)
    parser.add_argument("--quote-policy", choices=["verbatim-only", label_llm.QUOTE_SELECTION_POLICY], default=label_llm.QUOTE_SELECTION_POLICY)
    args = parser.parse_args(argv)
    config = Config(root=args.root.resolve(), db_path=args.db)
    print(json.dumps(run(config, model=args.model, quote_policy=args.quote_policy), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
