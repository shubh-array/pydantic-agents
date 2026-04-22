#!/usr/bin/env python3
"""Write grading.json for all iteration-1 runs."""
import csv, json, re
from pathlib import Path

WS = Path("/Users/sshukla/Desktop/src/pydantic-agents/.cursor/skills/csv-dedup-workspace/iteration-1")

def count_data_rows(csv_path):
    """Return number of data rows (excluding header)."""
    with open(csv_path, newline="", encoding="utf-8") as f:
        rows = list(csv.reader(f))
    return max(0, len(rows) - 1)

def get_header(csv_path):
    with open(csv_path, newline="", encoding="utf-8") as f:
        return next(csv.reader(f))

def report_removed_count(report_path):
    text = report_path.read_text(encoding="utf-8")
    patterns = [
        r"[Dd]uplicates?\s+removed\s*\|\s*(\d+)",
        r"[Dd]uplicate\s+rows?\s+removed\s*\|\s*(\d+)",
        r"\*\*[Rr]ows?\s+removed[:\*]+\*?\*?\s*(\d+)",
        r"[Rr]ows?\s+removed[:\s]+(\d+)",
        r"removed[:\s]+(\d+)\s*duplicate",
        r"(\d+)\s+duplicate[s]?\s+removed",
    ]
    for pat in patterns:
        m = re.search(pat, text)
        if m:
            return int(m.group(1))
    return None

def has_removed_table(report_path):
    text = report_path.read_text(encoding="utf-8")
    # A table has at least one | separator line with dashes
    return bool(re.search(r"\|\s*[-:]+\s*\|", text)) and "Row" in text

def grade_eval(eval_id, side, expectations):
    run_dir = WS / str(eval_id) / side / "run-1"
    outputs = run_dir / "outputs"
    timing_path = run_dir / "timing.json"
    
    dedup_csv = outputs / "dedup.csv"
    report_md = outputs / "dedup-report.md"
    
    graded = []
    for exp in expectations:
        aid = exp["assertion_id"]
        text = exp["text"]
        critical = exp.get("critical", False)
        passed = False
        evidence = ""
        
        if aid == "dedup-csv-exists":
            passed = dedup_csv.exists()
            evidence = f"dedup.csv {'found' if passed else 'NOT found'} at {dedup_csv}"
        
        elif aid == "dedup-report-exists":
            passed = report_md.exists()
            evidence = f"dedup-report.md {'found' if passed else 'NOT found'} at {report_md}"
        
        elif aid == "correct-row-count":
            if dedup_csv.exists():
                n = count_data_rows(dedup_csv)
                passed = (n == 4)
                hdr = get_header(dedup_csv) if dedup_csv.exists() else []
                evidence = f"dedup.csv has {n} data rows (expected 4). Header: {hdr}"
            else:
                evidence = "dedup.csv not found"
        
        elif aid == "whitespace-trimmed-dedup":
            if dedup_csv.exists():
                n = count_data_rows(dedup_csv)
                passed = (n == 3)
                evidence = f"dedup.csv has {n} data rows (expected 3 after whitespace-aware dedup)"
            else:
                evidence = "dedup.csv not found"
        
        elif aid == "case-insensitive-dedup":
            if dedup_csv.exists():
                n = count_data_rows(dedup_csv)
                passed = (n == 2)
                evidence = f"dedup.csv has {n} data rows (expected 2 after case-insensitive dedup)"
            else:
                evidence = "dedup.csv not found"
        
        elif aid == "report-shows-2-removed":
            if report_md.exists():
                n = report_removed_count(report_md)
                passed = (n == 2)
                evidence = f"Report shows {n} duplicates removed (expected 2)"
            else:
                evidence = "report not found"
        
        elif aid == "report-shows-3-removed":
            if report_md.exists():
                n = report_removed_count(report_md)
                passed = (n == 3)
                evidence = f"Report shows {n} duplicates removed (expected 3)"
            else:
                evidence = "report not found"
        
        elif aid == "removed-table-present":
            if report_md.exists():
                passed = has_removed_table(report_md)
                evidence = f"Table {'found' if passed else 'NOT found'} in report"
            else:
                evidence = "report not found"
        
        elif aid == "column-order-preserved":
            if dedup_csv.exists():
                hdr = get_header(dedup_csv)
                passed = (hdr == ["Name", "Age", "City"])
                evidence = f"Headers: {hdr}"
            else:
                evidence = "dedup.csv not found"
        
        elif aid == "headers-preserved-as-is":
            if dedup_csv.exists():
                hdr = get_header(dedup_csv)
                passed = (hdr == ["Name", "EMAIL", "City"])
                evidence = f"Headers: {hdr} (expected ['Name', 'EMAIL', 'City'])"
            else:
                evidence = "dedup.csv not found"
        
        else:
            evidence = f"Unknown assertion_id: {aid}"
        
        graded.append({
            "assertion_id": aid,
            "text": text,
            "passed": passed,
            "evidence": evidence,
            "critical": critical,
        })
    
    passed_count = sum(1 for g in graded if g["passed"])
    failed_count = len(graded) - passed_count
    
    result = {
        "expectations": graded,
        "summary": {
            "passed": passed_count,
            "failed": failed_count,
            "total": len(graded),
            "pass_rate": round(passed_count / len(graded), 2) if graded else 0.0,
        },
        "eval_feedback": {
            "suggestions": [],
            "overall": "Evals look solid.",
        },
    }
    
    if timing_path.exists():
        t = json.loads(timing_path.read_text())
        result["timing"] = {"executor_duration_seconds": t.get("duration_s", 0)}
    
    out_path = run_dir / "grading.json"
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(f"Graded eval {eval_id}/{side}: {passed_count}/{len(graded)} passed")
    return result


# Load evals to get expectations per eval
evals_path = Path("/Users/sshukla/Desktop/src/pydantic-agents/.cursor/skills/csv-dedup/evals/evals.json")
evals = json.loads(evals_path.read_text())

for ev in evals:
    eid = ev["id"]
    exps = ev.get("expectations", [])
    for side in ["with_skill", "without_skill"]:
        grade_eval(eid, side, exps)

print("All grading complete.")
