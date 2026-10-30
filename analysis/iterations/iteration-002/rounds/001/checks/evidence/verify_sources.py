"""Bounded source verification; run from OTP_bank root. Writes only beside this file."""
import datetime
import hashlib
import json
from pathlib import Path
import re
import subprocess
import xml.etree.ElementTree as ET
import zipfile

ROOT = Path(__file__).resolve().parents[7]
ROUND = ROOT / "analysis/iterations/iteration-002/rounds/001"
OUT = Path(__file__).parent
NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
FROZEN = ROUND / "inputs"

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

expected = {
    "C01": ("knowledge/raw/задание_кейса_с_диска/Кейс_ОТП_1 тур_CL Cup Moscow 2026.pdf", "3beee7c3a81b315dcd6a026b05d827ec9f405bf8243053d843334405b20b6a60"),
    "C03": ("knowledge/raw/задание_кейса_с_диска/Приложение. ОТПМания_отзывы.xlsx", "787a4adf74f3ff9ab52396515e49e5bf7ffa88569fcd0fa654ba8934841420fe"),
    "C04": ("knowledge/raw/additions_2026-10-29/organizer/discussion_2026-10-26_29.txt", "541c0ef7d080ddd260c259fc5d627ed0c5ac2b7dcecd53f9fca7af8b2bd3f617"),
    "E03": ("knowledge/raw/web_research_2026-10-26/extracted/S47.txt", "97adc7f21004b8524015fd7300e261e3e25c37a3a63b7127967ab6f5d2bb48c5"),
    "E04": ("knowledge/raw/web_research_2026-10-26/extracted/S48.txt", "928c5853b40bd00b0c1cbe5f0141371c490fc88a17bf4ed0529cc717c096d1b9"),
    "E05": ("knowledge/raw/web_research_2026-10-26/extracted/S49.txt", "9032eee0f23db3f8fd0924e67a8e652f0a64a2d35cb626821a4e7f06cf97abd8"),
    "M01_basis": ("analysis/preparation/iteration-002-finance-basis/basis.md", "4b158ad58af0061951f40853c50d642b2933cf55e5ca07fc619c00396e8c83e3"),
    "M01_inputs": ("analysis/preparation/iteration-002-finance-basis/scenario-inputs.json", "b589997e9c2c210117e3974658c52c40350c3a38f2322fb06a37fd36e6f36e40"),
    "M01_assumptions": ("analysis/preparation/iteration-002-finance-basis/assumptions.csv", "6561e5586b5c5e882a8a93485fb90912bf4425ee1ea89ce28b11715592cc120b"),
}
sources = {key: {"path": path, "sha256": sha(ROOT / path), "matches_frozen_reference": sha(ROOT / path) == h} for key, (path, h) in expected.items()}
assert all(x["matches_frozen_reference"] for x in sources.values())
manifest = json.loads((FROZEN / "manifest.json").read_text())
frozen_checks = {name: sha(FROZEN / name) == h for name, h in manifest["files"].items()}
assert len(frozen_checks) == 5 and all(frozen_checks.values())
context = (FROZEN / "context.md").read_text()
m01 = json.loads(re.search(r"```json\n(.*?)\n```", context, re.S).group(1))
assert m01 == json.loads((ROOT / expected["M01_inputs"][0]).read_text())

pdf_pages = {}
for page in (3, 9, 10, 11, 12, 14, 15, 16, 17, 18, 19):
    pdf_pages[str(page)] = subprocess.check_output(["pdftotext", "-f", str(page), "-l", str(page), "-layout", str(ROOT / expected["C01"][0]), "-"], text=True)
assert "30–34 млн" in pdf_pages["19"] and "оба целевых значения не" in pdf_pages["19"]
assert "19 427 591" in pdf_pages["15"] and "19 112 409" in pdf_pages["15"]
assert "38 540 000" in pdf_pages["14"] and "315" in pdf_pages["14"]

with zipfile.ZipFile(ROOT / expected["C03"][0]) as z:
    strings = ["".join(x.itertext()) for x in ET.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", NS)]
    cells = {}
    for c in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).findall(".//m:c", NS):
        value = c.find("m:v", NS)
        if value is not None:
            cells[c.attrib["r"]] = strings[int(value.text)] if c.attrib.get("t") == "s" else value.text
    workbook = ET.fromstring(z.read("xl/workbook.xml"))
    assert workbook.find("m:sheets/m:sheet", NS).attrib["name"] == "старая-2026"
ratings = []
for cols in ("CDEFG", "HIJKL", "MNOPQ"):
    counts = [sum(cells.get(c + str(r), "").strip().upper() == "V" for r in range(5, 1918)) for c in cols]
    ratings.append({"columns": cols, "counts_5_to_1": counts, "n": sum(counts), "mean": sum(n * s for n, s in zip(counts, (5, 4, 3, 2, 1))) / sum(counts)})
quotes = {"T" + str(r): cells.get("T" + str(r)) for r in (41, 261, 578, 1297, 1335, 1433, 1499, 1531)}
assert quotes["T1335"] == "Хотелось бы сделать механику начисления рукоинов более прозрачной и понятной: сейчас количество начислений у сотрудников может заметно различаться, и не всегда понятно, от каких критериев это зависит."
rows = sum("A" + str(r) in cells for r in range(5, 1918))
names = len({cells.get("A" + str(r)) for r in range(5, 1918)})
dates = [float(cells["B" + str(r)]) for r in range(5, 1918)]
date_origin = datetime.datetime(1899, 12, 30)
date_range = [(date_origin + datetime.timedelta(days=d)).isoformat() for d in (min(dates), max(dates))]
assert rows == 1913 and names == 1 and [x["n"] for x in ratings] == [1908, 1903, 1902]

result = {
    "schema_version": 1,
    "checked_on": "2026-10-30",
    "source_path_base": "project_root",
    "scope": "Selected source facts, quotations, versions and assumption provenance; candidate financial arithmetic and full research protocols excluded.",
    "frozen_manifest_matches": frozen_checks,
    "frozen_M01_matches_scenario_inputs": True,
    "sources": sources,
    "candidate_versions": {key: {"path": path, "sha256": sha(ROUND / path)} for key, path in {"BASELINE": "inputs/baseline.md", "CON-005@v1": "branches/A/concept.md", "CON-006@v1": "branches/B/concept.md"}.items()},
    "pdf_pages_extracted_this_check": list(pdf_pages),
    "pdf_visuals_read_this_check": ["analysis/preparation/evidence/case-page-08.png", "analysis/preparation/evidence/case-page-10.png", "analysis/preparation/evidence/case-page-19.png"],
    "xlsx": {
        "sheet": "старая-2026", "headers": {c + str(r): cells.get(c + str(r)) for r in (3, 4) for c in "ABCDEFGHIJKLMNOPQRST"},
        "scope": "Headers and selected quotations read; A/B and score marks scanned for verification; other comments not recoded or reread exhaustively.",
        "rows": rows, "distinct_anonymous_names": names, "date_range": date_range,
        "ratings": ratings, "nonempty_comments": sum(bool(cells.get("T" + str(r), "").strip()) for r in range(5, 1918)),
        "recommend_yes_no": [sum(cells.get(c + str(r), "").strip().upper() == "V" for r in range(5, 1918)) for c in "RS"],
        "selected_quotations": quotes,
    },
    "case_source_arithmetic": {"fund_sum_R": 19427591 + 19112409, "realized_share": 19427591 / 38540000, "unused_share": 19112409 / 38540000, "certificate_count_share": 3154 / 3895},
    "external_search_performed": False,
    "full_external_studies_read_this_check": False,
}
(OUT / "source-checks.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"sources_checked": len(sources), "frozen_files_checked": len(frozen_checks), "rows": rows, "quotes_checked": len(quotes), "output": str((OUT / 'source-checks.json').relative_to(ROOT))}, ensure_ascii=False))
