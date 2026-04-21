#!/usr/bin/env python3
"""Programmatic grader for finance-variance iteration runs.

Usage: python3 grade_iteration.py <workspace_dir> <iteration_n>
Writes grading.json into each run directory.
"""
import csv, json, os, re, sys
from pathlib import Path

WS   = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".")
ITER = int(sys.argv[2]) if len(sys.argv) > 2 else 1

ITER_DIR = WS / f"iteration-{ITER}"

# ── helpers ──────────────────────────────────────────────────────────────────

def _read_csv(path):
    rows = []
    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            rows.append({k.strip(): v.strip() for k, v in row.items()})
    return rows

def _pass(assertion_id, text, evidence, critical=False):
    return {"assertion_id": assertion_id, "text": text, "passed": True,
            "evidence": evidence, "critical": critical}

def _fail(assertion_id, text, evidence, critical=False):
    return {"assertion_id": assertion_id, "text": text, "passed": False,
            "evidence": evidence, "critical": critical}

# ── per-eval graders ─────────────────────────────────────────────────────────

def grade_eval1(outputs_dir: Path) -> list:
    results = []
    vcsv = outputs_dir / "variance.csv"
    smd  = outputs_dir / "summary.md"

    # variance-csv-exists
    if vcsv.exists():
        results.append(_pass("variance-csv-exists", "variance.csv exists", f"Found at {vcsv}", critical=True))
    else:
        results.append(_fail("variance-csv-exists", "variance.csv exists", "File not found", critical=True))
        return results  # can't check further

    # summary-md-exists
    if smd.exists():
        results.append(_pass("summary-md-exists", "summary.md exists", f"Found at {smd}", critical=True))
    else:
        results.append(_fail("summary-md-exists", "summary.md exists", "File not found", critical=True))

    rows = _read_csv(vcsv)
    cols = list(rows[0].keys()) if rows else []

    # variance-csv-has-5-cols
    expected_cols = {"category", "budget", "actual", "variance", "variance_pct"}
    if expected_cols.issubset({c.lower() for c in cols}):
        results.append(_pass("variance-csv-has-5-cols",
            "variance.csv has exactly category, budget, actual, variance, variance_pct",
            f"Columns: {cols}", critical=True))
    else:
        results.append(_fail("variance-csv-has-5-cols",
            "variance.csv has exactly category, budget, actual, variance, variance_pct",
            f"Columns found: {cols}", critical=True))

    # variance-pct-format  (e.g. "25.0%" or "-4.0%")
    pct_col = next((c for c in cols if c.lower() == "variance_pct"), None)
    bad_pct = []
    if pct_col:
        for r in rows:
            v = r[pct_col]
            if not re.match(r'^-?\d+\.\d%$', v) and v != "N/A":
                bad_pct.append(v)
    if not bad_pct:
        results.append(_pass("variance-pct-format",
            "variance_pct uses format like '25.0%'", "All values match pattern", critical=True))
    else:
        results.append(_fail("variance-pct-format",
            "variance_pct uses format like '25.0%'",
            f"Bad values: {bad_pct[:5]}", critical=True))

    # marketing-over-budget
    mkt = next((r for r in rows if r.get("category","").lower() == "marketing"), None)
    if mkt:
        var_col  = next((c for c in cols if c.lower() == "variance"), None)
        pct_col2 = next((c for c in cols if c.lower() == "variance_pct"), None)
        v  = mkt.get(var_col, "")
        p  = mkt.get(pct_col2, "")
        try:
            v_num = float(str(v).replace(",", ""))
            if abs(v_num - 2500) < 0.1 and p == "25.0%":
                results.append(_pass("marketing-over-budget",
                    "Marketing variance=2500 and variance_pct=25.0%",
                    f"variance={v}, variance_pct={p}"))
            else:
                results.append(_fail("marketing-over-budget",
                    "Marketing variance=2500 and variance_pct=25.0%",
                    f"Got variance={v}, variance_pct={p}"))
        except ValueError:
            results.append(_fail("marketing-over-budget", "Marketing variance=2500", f"Could not parse: {v}"))
    else:
        results.append(_fail("marketing-over-budget", "Marketing row exists", "Row not found"))

    # engineering-under-budget
    eng = next((r for r in rows if r.get("category","").lower() == "engineering"), None)
    if eng:
        var_col  = next((c for c in cols if c.lower() == "variance"), None)
        pct_col2 = next((c for c in cols if c.lower() == "variance_pct"), None)
        v = eng.get(var_col, "")
        p = eng.get(pct_col2, "")
        try:
            v_num = float(str(v).replace(",", ""))
            if abs(v_num - (-2000)) < 0.1 and p == "-4.0%":
                results.append(_pass("engineering-under-budget",
                    "Engineering variance=-2000 and variance_pct=-4.0%",
                    f"variance={v}, variance_pct={p}"))
            else:
                results.append(_fail("engineering-under-budget",
                    "Engineering variance=-2000 and variance_pct=-4.0%",
                    f"Got variance={v}, variance_pct={p}"))
        except ValueError:
            results.append(_fail("engineering-under-budget", "Engineering -2000", f"Could not parse: {v}"))
    else:
        results.append(_fail("engineering-under-budget", "Engineering row exists", "Row not found"))

    # summary-has-top3
    if smd.exists():
        text = smd.read_text()
        if "Marketing" in text and ("Top 3" in text or "Over-Budget" in text):
            results.append(_pass("summary-has-top3",
                "summary.md lists over-budget categories", "Marketing found in Top 3 section"))
        else:
            results.append(_fail("summary-has-top3",
                "summary.md lists over-budget categories", "Missing expected content"))

    # summary-has-totals
    if smd.exists():
        text = smd.read_text()
        if "Total Budget" in text and "Total Actual" in text and "Total Variance" in text:
            results.append(_pass("summary-has-totals", "summary.md has Totals section", "All total rows found"))
        else:
            results.append(_fail("summary-has-totals", "summary.md has Totals section", f"Missing rows. Content: {text[:300]}"))

    return results


def grade_eval2(outputs_dir: Path) -> list:
    results = []
    vcsv = outputs_dir / "variance.csv"
    smd  = outputs_dir / "summary.md"

    if vcsv.exists():
        results.append(_pass("variance-csv-exists", "variance.csv exists", f"Found at {vcsv}", critical=True))
    else:
        results.append(_fail("variance-csv-exists", "variance.csv exists", "Not found", critical=True))
        return results

    if smd.exists():
        results.append(_pass("summary-md-exists", "summary.md exists", f"Found at {smd}", critical=True))
    else:
        results.append(_fail("summary-md-exists", "summary.md exists", "Not found", critical=True))

    rows = _read_csv(vcsv)
    cols = list(rows[0].keys()) if rows else []

    # quoted-category-preserved
    travel = next((r for r in rows if "travel" in r.get("category","").lower()), None)
    if travel and travel.get("category","") == "Travel, domestic":
        results.append(_pass("quoted-category-preserved",
            "category 'Travel, domestic' preserved with comma inside",
            f"Found row: {travel}", critical=True))
    elif travel:
        results.append(_fail("quoted-category-preserved",
            "category 'Travel, domestic' preserved with comma inside",
            f"Found but value is: {travel.get('category')}", critical=True))
    else:
        results.append(_fail("quoted-category-preserved",
            "category 'Travel, domestic' preserved",
            "No row with 'travel' found", critical=True))

    # travel-variance-correct
    if travel:
        var_col  = next((c for c in cols if c.lower() == "variance"), None)
        pct_col  = next((c for c in cols if c.lower() == "variance_pct"), None)
        v  = travel.get(var_col, "")
        p  = travel.get(pct_col, "")
        try:
            v_num = float(str(v).replace(",", ""))
            if abs(v_num - 1200) < 0.1 and p == "24.0%":
                results.append(_pass("travel-variance-correct",
                    "Travel, domestic variance=1200, pct=24.0%", f"variance={v}, pct={p}"))
            else:
                results.append(_fail("travel-variance-correct",
                    "Travel, domestic variance=1200, pct=24.0%", f"Got variance={v}, pct={p}"))
        except ValueError:
            results.append(_fail("travel-variance-correct", "parse error", str(v)))

    # row-count-correct
    if len(rows) == 5:
        results.append(_pass("row-count-correct", "variance.csv has 5 data rows",
            f"Row count: {len(rows)}", critical=True))
    else:
        results.append(_fail("row-count-correct", "variance.csv has 5 data rows",
            f"Row count: {len(rows)}", critical=True))

    # top3-over-budget-in-summary
    if smd.exists():
        text = smd.read_text()
        if "Travel" in text and "Marketing" in text:
            results.append(_pass("top3-over-budget-in-summary",
                "summary.md includes Travel and Marketing as over-budget",
                "Both found in summary"))
        else:
            results.append(_fail("top3-over-budget-in-summary",
                "summary.md includes Travel and Marketing as over-budget",
                f"Content: {text[:400]}"))

    return results


def grade_eval3(outputs_dir: Path) -> list:
    results = []
    vcsv = outputs_dir / "variance.csv"
    smd  = outputs_dir / "summary.md"

    if vcsv.exists():
        results.append(_pass("variance-csv-exists", "variance.csv exists", f"Found at {vcsv}", critical=True))
    else:
        results.append(_fail("variance-csv-exists", "variance.csv exists", "Not found", critical=True))
        return results

    if smd.exists():
        results.append(_pass("summary-md-exists", "summary.md exists", f"Found at {smd}", critical=True))
    else:
        results.append(_fail("summary-md-exists", "summary.md exists", "Not found", critical=True))

    rows = _read_csv(vcsv)
    cols = list(rows[0].keys()) if rows else []

    # thousands-separators-stripped
    bud_col = next((c for c in cols if c.lower() == "budget"), None)
    bad_vals = []
    if bud_col:
        for r in rows:
            v = r[bud_col]
            if "," in v:
                bad_vals.append(v)
    if not bad_vals:
        results.append(_pass("thousands-separators-stripped",
            "numeric columns have no thousands separators",
            "No commas in budget values", critical=True))
    else:
        results.append(_fail("thousands-separators-stripped",
            "numeric columns have no thousands separators",
            f"Values with commas: {bad_vals}", critical=True))

    # row-count-correct  (5 rows, trailing blanks ignored)
    if len(rows) == 5:
        results.append(_pass("row-count-correct", "variance.csv has 5 data rows (blanks ignored)",
            f"Row count: {len(rows)}", critical=True))
    else:
        results.append(_fail("row-count-correct", "variance.csv has 5 data rows (blanks ignored)",
            f"Row count: {len(rows)}", critical=True))

    # marketing-variance-correct
    mkt = next((r for r in rows if r.get("category","").lower() == "marketing"), None)
    if mkt:
        var_col  = next((c for c in cols if c.lower() == "variance"), None)
        pct_col  = next((c for c in cols if c.lower() == "variance_pct"), None)
        v  = mkt.get(var_col, "")
        p  = mkt.get(pct_col, "")
        try:
            v_num = float(str(v).replace(",", ""))
            if abs(v_num - 2500) < 0.1 and p == "20.0%":
                results.append(_pass("marketing-variance-correct",
                    "Marketing variance=2500, pct=20.0%", f"variance={v}, pct={p}"))
            else:
                results.append(_fail("marketing-variance-correct",
                    "Marketing variance=2500, pct=20.0%", f"Got variance={v}, pct={p}"))
        except ValueError:
            results.append(_fail("marketing-variance-correct", "parse error", str(v)))

    # office-supplies-quoted-comma
    office = next((r for r in rows if "office" in r.get("category","").lower()), None)
    if office and "," in office.get("category",""):
        results.append(_pass("office-supplies-quoted-comma",
            "category 'Office, supplies' preserved with comma",
            f"Found: {office.get('category')}", critical=True))
    elif office:
        results.append(_fail("office-supplies-quoted-comma",
            "category 'Office, supplies' preserved",
            f"Found but value: {office.get('category')}", critical=True))
    else:
        results.append(_fail("office-supplies-quoted-comma",
            "category 'Office, supplies' row exists",
            "No office row found", critical=True))

    # top3-over-budget-correct
    if smd.exists():
        text = smd.read_text()
        if "Marketing" in text and "Sales" in text and "Office" in text:
            results.append(_pass("top3-over-budget-correct",
                "summary top-3 includes Marketing, Sales, Office",
                "All three found in summary"))
        else:
            results.append(_fail("top3-over-budget-correct",
                "summary top-3 includes Marketing, Sales, Office",
                f"Content: {text[:400]}"))

    return results


GRADERS = {"eval-1": grade_eval1, "eval-2": grade_eval2, "eval-3": grade_eval3}

# ── main ─────────────────────────────────────────────────────────────────────

for eval_id, grader in GRADERS.items():
    for side in ["with_skill", "without_skill"]:
        run_dir = ITER_DIR / eval_id / side / "run-1"
        outputs_dir = run_dir / "outputs"
        if not outputs_dir.exists():
            print(f"  SKIP {eval_id}/{side} — outputs dir missing")
            continue

        expectations = grader(outputs_dir)
        passed = sum(1 for e in expectations if e["passed"])
        total  = len(expectations)
        grading = {
            "expectations": expectations,
            "summary": {
                "passed": passed,
                "failed": total - passed,
                "total":  total,
                "pass_rate": round(passed / total, 3) if total else 0.0,
            },
            "eval_feedback": {"suggestions": [], "overall": "Programmatic grading."},
        }
        out_path = run_dir / "grading.json"
        out_path.write_text(json.dumps(grading, indent=2) + "\n", encoding="utf-8")
        status = "✓" if passed == total else f"✗ {total-passed} fail"
        print(f"  {eval_id}/{side}: {passed}/{total} [{status}]  → {out_path}")
