"""Verify contract, reproduction and frozen input integrity; writes here only."""
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROUND = HERE.parent.parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if __name__ == "__main__":
    outputs = ["model-inputs.json", "annual-results.csv", "monthly-results.csv", "author-comparisons.csv", "validation.json"]
    subprocess.run([sys.executable, str(HERE / "model.py")], check=True, capture_output=True)
    before = {name: digest(HERE / name) for name in outputs}
    subprocess.run([sys.executable, str(HERE / "model.py")], check=True, capture_output=True)
    assert before == {name: digest(HERE / name) for name in outputs}
    report = json.loads((ROUND / "checks/finance.json").read_text())
    assert {r["candidate_key"] for r in report["results"]} == {"BASELINE", "CON-005@v1", "CON-006@v1"}
    assert len(report["results"]) == 3
    with (HERE / "annual-results.csv").open() as f:
        annual = {(r["candidate_key"], r["scenario"], r["year"]): r for r in csv.DictReader(f)}
    required = {"candidate_key", "scenario_scope", "gates", "evidence_refs", "assumption_refs", "findings", "calculation_paths"}
    for result in report["results"]:
        assert required <= result.keys()
        assert set(result["gates"]) == {"budget", "currency_balances"}
        assert all(s in {"pass", "fail", "uncertain"} for s in result["gates"].values())
        assert len(result["scenario_checks"]) == 9
        assert len({r["scenario"] for r in result["scenario_checks"]}) == 8
        for scenario in result["scenario_checks"]:
            a = annual[(result["candidate_key"], scenario["scenario"], scenario["year"])]
            assert scenario["capacity"] == ("pass" if a["capacity_pass"] == "True" else "fail")
            for budget in [30000000, 34000000]:
                assert scenario["narrow_procurement_budget"][str(budget)] == ("pass" if a[f"narrow_budget_{budget}_pass"] == "True" else "fail")
            for metric in ["procurement_required_rub", "reward_cash_required_rub", "external_cash_required_rub", "peak_basket_units_required", "peak_R_units_required", "peak_HR_hours", "C_queue_close", "R_queue_close", "J_overdue", "peak_J_overdue"]:
                assert abs(float(scenario[metric]) - float(a[metric])) < 1e-5
            if result["candidate_key"] != "BASELINE":
                assert scenario["named_external_envelope"] == ("pass" if a["scoped_external_envelope_pass"] == "True" else "fail")
        for path in result["calculation_paths"]:
            assert (ROUND / path).is_file()
    for name in ["annual-results.csv", "monthly-results.csv", "author-comparisons.csv", "assumptions.csv"]:
        with (HERE / name).open() as f:
            rows = list(csv.DictReader(f))
        assert rows and all(None not in r and all(v is not None for v in r.values()) for r in rows)
    validation = json.loads((HERE / "validation.json").read_text())
    assert validation["status"] == "pass" and not validation["author_discrepancies"]
    for path, expected in validation["input_hashes"].items():
        assert digest(ROUND / path) == expected
    result = dict(status="pass", reproduction_files=before, contract_results=3, all8scenarios_plus_COREyear2_per_variant=True,
                  frozen_inputs_and_concept_hashes_unchanged=True, author_claims_checked=validation["author_claims_checked"],
                  max_reconciliation_error=validation["max_reconciliation_error"],
                  finance_json_sha256=digest(ROUND / "checks/finance.json"),
                  report_sha256=digest(HERE / "finance-report.md"), assumptions_sha256=digest(HERE / "assumptions.csv"))
    (HERE / "artifact-validation.json").write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps({k: result[k] for k in ["status", "contract_results", "author_claims_checked", "max_reconciliation_error"]}))
