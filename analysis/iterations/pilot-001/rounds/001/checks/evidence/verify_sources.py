"""Scoped source/locator checks; does not repeat the 1,913-row diagnosis."""
from pathlib import Path
import csv
import hashlib
import json
import xml.etree.ElementTree as ET
import zipfile

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]
ROUND = HERE.parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def csv_rows(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


manifest = json.loads((ROUND / "inputs/manifest.json").read_text())
frozen = {name: sha(ROUND / "inputs" / name) == expected
          for name, expected in manifest["files"].items()}
case_dir = ROOT / "knowledge/raw/задание_кейса_с_диска"
source_paths = {
    "C01": case_dir / "Кейс_ОТП_1 тур_CL Cup Moscow 2026.pdf",
    "C03": case_dir / "Приложение. ОТПМания_отзывы.xlsx",
    **{key: ROOT / f"knowledge/raw/web_research_2026-10-26/extracted/S{number}.txt"
       for key, number in (("E03", 47), ("E04", 48), ("E05", 49))},
}
expected_hashes = {
    "C01": "3beee7c3a81b315dcd6a026b05d827ec9f405bf8243053d843334405b20b6a60",
    "C03": "787a4adf74f3ff9ab52396515e49e5bf7ffa88569fcd0fa654ba8934841420fe",
    "E03": "97adc7f21004b8524015fd7300e261e3e25c37a3a63b7127967ab6f5d2bb48c5",
    "E04": "928c5853b40bd00b0c1cbe5f0141371c490fc88a17bf4ed0529cc717c096d1b9",
    "E05": "9032eee0f23db3f8fd0924e67a8e652f0a64a2d35cb626821a4e7f06cf97abd8",
}
sources = {key: {"path_base": "project_root", "path": str(path.relative_to(ROOT)),
                 "sha256": sha(path), "matches_frozen_evidence": sha(path) == expected_hashes[key]}
           for key, path in source_paths.items()}
sources["C01"].update({
    "publication": "Cup Moscow 2026; exact publication date not established; rules dated 2026-04-14 on physical p.12",
    "depth_this_check": "Existing page images visually read: physical pp.8,10,11,15,19. Existing extracted text read: pp.9,12,14,17,18. No new full-PDF read.",
    "locators": "pp.10-12: currencies/awards; pp.14-15: fund; pp.17-18: assortment and August; p.19: budget and targets; p.8: banner only",
    "derived_views": "analysis/preparation/evidence/case-page-{08,10,11,15,19}.png; case-excerpts.txt pp.9,12,14,17,18",
    "limit": "Educational case, incomplete program register; figures are case facts, not audited transaction data. Screenshot is not the full/current certificate policy.",
})
sources["C03"].update({
    "period": "2026-01-01 to 2026-10-14 per frozen diagnosis/audit; collection/publication date unknown",
    "depth_this_check": "Workbook/sheet metadata, header A1:T4 and eight selected comment cells read from original XLSX XML. Other 1,913-row computations reused from named diagnosis outputs, not rerun.",
    "locators": "старая-2026!A1:T4,T41,T261,T578,T1297,T1335,T1433,T1499,T1531",
    "limit": "Response row is not a unique employee/order. Post-purchase sample; no denominator for eligible workforce or invitations.",
})
external = {
    "E03": ("2025", "10.1287/mnsc.2023.00318", "Three experiments; propensity to seek help under broad/narrow peer recognition; N and detailed recruitment/protocol absent from read abstract.", "Supports measuring subgroup coverage. Does not establish bank retention, actual help volume or effect of nomination register."),
    "E04": ("2010", "10.1037/a0017935", "Four experiments, including field experiment with university fundraisers; social worth mediation stated; sample sizes and full protocol not in read abstract.", "Supports plausible social-worth mechanism. Does not test these prompts, coins, frequency or OTP effect."),
    "E05": ("2001", "10.1037/0021-9010.86.3.386", "Two construct-validation studies: university and automobile-parts employees; four-factor CFA and predictive validity; N not in read abstract.", "Four dimensions are a measurement framework, not an OTP injustice finding, Russian validated scale or causal intervention effect."),
}
for key, (year, doi, design, limit) in external.items():
    sources[key].update({"publication_year": year, "url": "https://doi.org/" + doi,
        "depth_this_check": "Saved reconstructed OpenAlex ABSTRACT, lines 1-7; selected provenance metadata. Full study not read or newly retrieved.",
        "locator": "lines 6-7, ABSTRACT", "design_and_sample": design, "transferability_limit": limit,
        "dependency": "Frozen evidence and concept restatements depend on this one paper/abstract; mirrors are not independent studies; no effect coefficient transferred."})
sources["E05"]["metadata_discrepancy"] = "Local metadata line 4 uses DOI with double slash 10.1037//0021-9010.86.3.386; frozen packet documents this. Single-slash canonical spelling not re-resolved online in this check; same title/year/author."

ns = {"s": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
targets = {"T41", "T261", "T578", "T1297", "T1335", "T1433", "T1499", "T1531"}
cells = {}
headers = {}
with zipfile.ZipFile(source_paths["C03"]) as archive:
    wb = ET.fromstring(archive.read("xl/workbook.xml"))
    sheets = [s.attrib["name"] for s in wb.find("s:sheets", ns)]
    assert sheets == ["старая-2026"]
    strings = ["".join(t.text or "" for t in si.iter("{" + ns["s"] + "}t"))
               for si in ET.fromstring(archive.read("xl/sharedStrings.xml"))]
    sheet = ET.fromstring(archive.read("xl/worksheets/sheet1.xml"))
    for cell in sheet.findall(".//s:c", ns):
        address = cell.attrib["r"]
        row = int("".join(filter(str.isdigit, address)))
        if address not in targets and row > 4:
            continue
        value = cell.find("s:v", ns)
        text = value.text if value is not None else ""
        if cell.attrib.get("t") == "s":
            text = strings[int(text)]
        if address in targets:
            cells[address] = text
        elif text.strip():
            headers[address] = text
assert cells["T261"] == "Чтобы всегда были в наличии были сертификаты Ozon"
assert cells["T1297"] == "в магазине почти нечего покупать. А то, что осталось (единичные товары) по невероятной цене"
assert cells["T1433"].startswith("Хотелось бы видеть информацию о перемещениях посылки.")
assert cells["T1335"].startswith("Хотелось бы сделать механику начисления рукоинов более прозрачной и понятной:")
themes = [{"csv_line": i, **{k: v for k, v in row.items() if k != "locators"}}
          for i, row in enumerate(csv_rows(ROOT / "analysis/preparation/diagnosis/theme_counts.csv"), 2)
          if row["theme"] in {"availability", "price_value"}]
assert [(t["response_count"], t["denominator_nonempty"]) for t in themes] == [("126", "1061"), ("113", "1061")]
ratings = csv_rows(ROOT / "analysis/preparation/diagnosis/rating_summary.csv")
assert [r["valid_n"] for r in ratings[:3]] == ["1908", "1903", "1902"]
for scope in ("all_rows", "one_row_per_exact_A_T_pattern"):
    group = {r["question"]: float(r["mean"]) for r in ratings if r["scope"] == scope and r["mean"]}
    assert min(group, key=group.get) == "delivery"
arithmetic = {"fund_total_R": 19427591 + 19112409,
              "fund_realized_pct": 100 * 19427591 / 38540000,
              "fund_remaining_pct": 100 * 19112409 / 38540000,
              "managers_with_remainder": 39 + 79 + 63 + 39,
              "august_gifts": 3154 + 735 + 6,
              "august_certificate_count_pct": 100 * 3154 / 3895,
              "thanks_two_basis_upper_bound_C_per_person_month": 50 * 5 + 100 * 5}
assert arithmetic["fund_total_R"] == 38540000
assert arithmetic["managers_with_remainder"] == 220
assert arithmetic["august_gifts"] == 3895
assert all(frozen.values()) and all(s["matches_frozen_evidence"] for s in sources.values())
output = {"scope": "Targeted verification only; hashes are integrity checks, not proof of truth.",
          "checked_on": "2026-10-27", "input_manifest_fingerprint": manifest["fingerprint"],
          "frozen_hash_checks": frozen, "sources": sources,
          "xlsx_selected_cells": cells, "xlsx_nonempty_header_cells": headers,
          "reused_diagnosis": {"rating_summary_path": "analysis/preparation/diagnosis/rating_summary.csv",
                               "ratings": ratings, "theme_counts_path": "analysis/preparation/diagnosis/theme_counts.csv",
                               "selected_themes": themes},
          "arithmetic_checks": arithmetic,
          "not_performed": ["Full feedback diagnosis rerun", "New literature search/full-study review", "Financial scenario gates", "Concept ranking"]}
(HERE / "source-checks.json").write_text(json.dumps(output, ensure_ascii=False, indent=2) + "\n")
print("PASS: 5 frozen files, 5 source hashes, 8 source comment cells, targeted summaries and case arithmetic.")
