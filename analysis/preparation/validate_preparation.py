"""Read-only preparation checks; writes validation.json, never opens an iteration.

Run from any directory with the bundled Python (openpyxl available).
This checks source versions, arithmetic, quotes and artifact consistency; it does
not establish representativeness, causality or the accuracy of every theme code.
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import unquote

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[2]
PREP = ROOT / "analysis/preparation"
PACK = PREP / "pilot-inputs"
DIAG = PREP / "diagnosis"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict]:
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def main() -> None:
    expected = {"context.md", "evidence.md", "diagnosis.md", "baseline.md", "rubric.json"}
    require({p.name for p in PACK.iterdir() if p.is_file()} == expected,
            "Input pack must contain exactly the five contracted files")
    for path in PACK.iterdir():
        require(path.stat().st_size > 100, f"Empty/placeholder input: {path.name}")
        require("PENDING" not in path.read_text(), f"Unresolved placeholder: {path.name}")
    rubric_source = ROOT / ".agents/skills/case-iteration/assets/rubric.json"
    require((PACK / "rubric.json").read_bytes() == rubric_source.read_bytes(), "Rubric changed")
    rubric = json.loads((PACK / "rubric.json").read_text())
    require(set(rubric["gates"]) == {"case_scope", "budget", "currency_balances", "three_user_groups", "evidence_integrity"}, "Gates differ")

    registry = read_csv(ROOT / "knowledge/wiki/meta/sources.csv")
    actual = {p.relative_to(ROOT / "knowledge/raw").as_posix()
              for p in (ROOT / "knowledge/raw").rglob("*") if p.is_file()}
    require(actual == {r["relative_path"] for r in registry}, "Raw inventory changed")
    for row in registry:
        require(sha(ROOT / "knowledge/raw" / row["relative_path"]) == row["content_sha256"],
                "Raw source changed: " + row["relative_path"])

    source = next((ROOT / "knowledge/raw/задание_кейса_с_диска").glob("*.xlsx"))
    book = load_workbook(source, read_only=True, data_only=True)
    sheet = book["старая-2026"]
    raw = list(sheet.iter_rows(min_row=5, max_row=1917, values_only=True))
    responses = read_csv(DIAG / "responses.csv")
    summary = read_csv(DIAG / "rating_summary.csv")
    audit = json.loads((DIAG / "audit.json").read_text())
    require(len(raw) == len(responses) == audit["rows"] == 1913, "Response row count mismatch")
    require([int(r["source_row"]) for r in responses] == list(range(5, 1918)), "Source row mapping differs")
    raw_by_row = dict(enumerate(raw, 5))
    score_results = {}
    for name, start, stop, values in [
        ("convenience", 2, 7, [5, 4, 3, 2, 1]),
        ("delivery", 7, 12, [5, 4, 3, 2, 1]),
        ("purchase", 12, 17, [5, 4, 3, 2, 1]),
        ("recommend", 17, 19, ["Да", "Нет"]),
    ]:
        observed = []
        missing = 0
        for row in raw:
            selected = [i for i, v in enumerate(row[start:stop]) if str(v or "").strip() == "V"]
            require(len(selected) <= 1, f"Multiple marks in {name}")
            if selected:
                observed.append(values[selected[0]])
            else:
                missing += 1
        recorded = next(r for r in summary if r["scope"] == "all_rows" and r["question"] == name)
        require(len(observed) == int(recorded["valid_n"]), "Denominator mismatch: " + name)
        require(missing == int(recorded["missing_n"]), "Missing count mismatch: " + name)
        mean = sum(observed) / len(observed) if name != "recommend" else None
        if mean is not None:
            require(abs(mean - float(recorded["mean"])) < 1e-6, "Mean mismatch: " + name)
        else:
            require(observed.count("Да") == int(recorded["top_score_or_yes_n"]), "Yes count mismatch")
        score_results[name] = {"valid": len(observed), "missing": missing,
                               "mean": mean, "distribution": dict(Counter(observed))}

    # Compare to the documented conversion: whitespace plus integral numeric
    # cells rendered without .0. Original strings are not converted to numbers.
    # This does not claim a quotation preserves all original whitespace.
    def compact(value):
        if isinstance(value, float) and value.is_integer():
            value = int(value)
        return re.sub(r"\s+", " ", str("" if value is None else value)).strip()
    for row in responses:
        source_row = raw_by_row[int(row["source_row"])]
        require(compact(source_row[19]) == compact(row["comment"]),
                "Comment no longer maps to source cell T" + row["source_row"])
    exact_counts = Counter(raw)
    require(len(exact_counts) == audit["exact_row_unique_patterns"], "Exact row pattern count mismatch")
    require(sum(n - 1 for n in exact_counts.values()) == audit["exact_duplicate_excess_rows"],
            "Exact row excess count mismatch")
    packet_quotes_checked = 0
    for match in re.finditer(r"^\| T(\d+) \| «(.*?)»", (PACK / "diagnosis.md").read_text(), re.M):
        row_number, quotation = int(match.group(1)), match.group(2)
        original = str(raw_by_row[row_number][19]).strip()
        require(original.startswith(quotation) if row_number == 1433 else original == quotation,
                "Packet quotation does not match T" + str(row_number))
        packet_quotes_checked += 1
    require(packet_quotes_checked == 8, "Expected eight packet quotations")
    book.close()

    analyst_validation = json.loads((DIAG / "validation.json").read_text())
    require(all(analyst_validation["checks"].values()), "Analyst reported a failed check")

    themes = read_csv(DIAG / "theme_counts.csv")
    counts = Counter()
    for row in responses:
        counts.update(set(filter(None, row["codes"].split(";"))))
    for theme in themes:
        require(counts[theme["theme"]] == int(theme["response_count"]), "Theme count mismatch")
        require(int(theme["denominator_nonempty"]) == audit["comment_nonempty"], "Comment denominator mismatch")
        require(int(theme["denominator_meaningful"]) == audit["meaningful_comments"], "Meaningful denominator mismatch")
    by_row = {int(r["source_row"]): r for r in responses}
    require("delivery" not in by_row[1297]["codes"].split(";"), "T1297 false delivery remains")
    require("availability" in by_row[1486]["codes"].split(";"), "T1486 replenishment missing")
    require(by_row[1255]["manual_review"] == "yes", "T1255 not reviewed")

    checked_links = 0
    for path in PREP.rglob("*.md"):
        for match in re.finditer(r"\]\((<[^>]+>|[^)]+)\)", path.read_text()):
            target = match.group(1).strip("<>")
            if "://" in target or target.startswith(("#", "mailto:")):
                continue
            target = unquote(target.split("#")[0])
            if target:
                require((path.parent / target).exists(), f"Broken link: {path}: {target}")
                checked_links += 1

    run = ROOT / "analysis/iterations/pilot-001"
    state = json.loads((run / "state.json").read_text())
    require(state["completed_rounds"] == 0 and state["active_round"] is None,
            "Preparation must not start an iteration")
    require(state["status"] == "stopped", "Pilot should remain stopped until explicit continuation")
    require(not list(run.glob("rounds/*/round.json")), "Unexpected round created")
    standard = ROOT / ".agents/skills/case-iteration/assets/run-config.json"
    require(sha(standard) == "9ab6ae6cf566e60e1cd497a285b99c321f0b437771011411973df86b99ece3d6",
            "Standard run limits changed")
    local_config = json.loads((run / "run-config.json").read_text())
    require(local_config["max_iterations"] == 1 and local_config["parallel_branches"] == 2,
            "Pilot limits changed")

    files = [p for p in PREP.rglob("*") if p.is_file()
             and p.name != "validation.json" and "__pycache__" not in p.parts]
    result = {
        "checked_at_utc": datetime.now(timezone.utc).isoformat(),
        "result": "ready_for_pilot_with_explicit_limits",
        "scope": "Preparation only; no iteration, concepts, finance scenarios or sealed snapshot.",
        "input_pack": "analysis/preparation/pilot-inputs",
        "five_files_present": True,
        "rubric_exact_copy": True,
        "raw_files_hash_checked": len(registry),
        "raw_sources_unchanged": True,
        "independent_raw_rating_check": score_results,
        "all_response_texts_match_source_cells_after_documented_normalization": True,
        "text_normalization_checked": "Whitespace and integral numeric cells without .0, as documented; original text strings are not converted to numbers.",
        "exact_duplicate_counts_rechecked_against_raw": True,
        "packet_quotes_checked_against_raw": packet_quotes_checked,
        "analyst_checks_passed": len(analyst_validation["checks"]),
        "theme_counts_match_row_codes": True,
        "three_coordinator_coding_findings_resolved": True,
        "local_markdown_links_checked": checked_links,
        "no_iteration_started": True,
        "standard_and_pilot_limits_preserved": True,
        "limitations": [
            "Observation is a response row, not an identified unique employee or purchase.",
            "Exact identical rows are not proven duplicate people.",
            "Theme coding is hybrid and partly manually audited, not a validated classifier or independent gold standard.",
            "Customer feedback is selected and cannot establish population prevalence or causality.",
            "Missing bank balances, event definitions, purchase prices and official metric baselines limit future financial gates.",
        ],
        "input_hashes": {p.name: sha(p) for p in sorted(PACK.iterdir()) if p.is_file()},
        "preparation_file_hashes": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(files)},
        "unchanged_pilot_files": {p.relative_to(ROOT).as_posix(): sha(p) for p in sorted(run.iterdir()) if p.is_file()},
    }
    (PREP / "validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["result", "five_files_present", "rubric_exact_copy", "raw_files_hash_checked", "three_coordinator_coding_findings_resolved", "local_markdown_links_checked", "no_iteration_started"]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
