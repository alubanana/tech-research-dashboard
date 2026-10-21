"""Validate research records and build the standalone dashboard."""
import gzip
import json
from datetime import date
from pathlib import Path
import re
from system_core import prepare

ROOT = Path(__file__).resolve().parent
data = json.loads((ROOT / "frontier.json").read_text(encoding="utf-8"))
presentation = json.loads((ROOT / "presentation.json").read_text(encoding="utf-8"))
company_data = json.loads((ROOT / "companies.json").read_text(encoding="utf-8"))
assert data["schema"] == 1
assert date.fromisoformat(data["checkedAt"]) <= date.fromisoformat(data["asOf"])
ids = [d["id"] for d in data["directions"]]
assert len(ids) == len(set(ids))
assert set(presentation["directions"]) == set(ids), "Every direction needs a reviewed presentation entry"
for direction in data["directions"]:
    for key in ("mechanism", "proven", "unproven", "bottleneck", "trigger", "counter"):
        assert direction[key], (direction["id"], key)
    assert direction["companies"] and direction["signals"] and direction["papers"]
    assert presentation["directions"][direction["id"]]["checkpoint"] in range(4)
    for record in direction["signals"] + direction["papers"]:
        assert record["url"].startswith("https://")
        assert date.fromisoformat(record["date"]) <= date.fromisoformat(data["asOf"])
for reading in presentation["readings"]:
    assert reading["direction"] in ids
    direction = next(d for d in data["directions"] if d["id"] == reading["direction"])
    assert any(s["date"] == reading["date"] for s in direction["signals"])

assert company_data["schema"] == 1
company_ids = [c["id"] for c in company_data["companies"]]
assert len(company_ids) == len(set(company_ids))
assert set(presentation["companies"]) == set(company_ids), "Every company needs a reviewed dashboard summary"
for company_id, summary in presentation["companies"].items():
    assert all(summary.get(key) for key in ("founders", "round", "investors")), company_id
for company in company_data["companies"]:
    assert set(company["directions"]) <= set(ids)
    assert company["founders"] and company["capital"]["event"] and company["watch"]
    assert company["founderSource"].startswith("https://")
    for key in ("productUrl",):
        assert company[key].startswith("https://")
    assert company["capital"]["url"].startswith("https://")
    if company["capital"]["date"]:
        assert date.fromisoformat(company["capital"]["date"]) <= date.fromisoformat(company_data["checkedAt"])
    valuation = company["valuation"]
    assert valuation["amount"] and valuation["basis"] and valuation["status"] and valuation["detail"]
    assert valuation["url"].startswith("https://")
    if valuation["date"]:
        assert re.fullmatch(r"\d{4}-\d{2}(?:-\d{2})?", valuation["date"])
        dated = valuation["date"] + ("-01" if len(valuation["date"]) == 7 else "")
        assert date.fromisoformat(dated) <= date.fromisoformat(company_data["checkedAt"])
    for record in company.get("investors", []) + company.get("financing", []):
        assert record["url"].startswith("https://") and record["status"]
        if record.get("date"):
            assert date.fromisoformat(record["date"]) <= date.fromisoformat(company_data["checkedAt"])
    for record in company.get("financing", []):
        assert record["title"] and record["amount"] and record["detail"]
    for case in company.get("cases", []):
        assert all(case.get(k) for k in ("title", "use", "mechanism", "evidence", "limit", "url", "checkedAt"))
        assert case["url"].startswith("https://")
        assert date.fromisoformat(case["checkedAt"]) <= date.fromisoformat(company_data["checkedAt"])
        for source in case.get("sources", []):
            assert source["url"].startswith("https://")
for direction in data["directions"]:
    for company in direction["companies"]:
        if "companyId" in company:
            assert company["companyId"] in company_ids
            matched = next(c for c in company_data["companies"] if c["id"] == company["companyId"])
            assert direction["id"] in matched["directions"]


system_data = json.loads((ROOT / "system.json").read_text(encoding="utf-8"))
hierarchy = json.loads((ROOT / "hierarchy.json").read_text(encoding="utf-8"))
for theme in hierarchy["themes"]:
    for evidence in theme["evidence"]:
        assert evidence["date"] <= system_data["asOf"]
        if "sourceId" in evidence:
            assert any(s["id"] == evidence["sourceId"] for s in system_data["sources"])
        else:
            direction = next(d for d in data["directions"] if d["id"] == evidence["direction"])
            assert any(s["date"] == evidence["date"] for s in direction["signals"])
data["hierarchy"] = hierarchy
data["system"] = prepare(system_data, ROOT, ids, hierarchy)
data["presentation"] = presentation
data["companyData"] = company_data
template = (ROOT / "page.html").read_text(encoding="utf-8")
assert template.count("__DATA__") == 1
assert template.count("__SYSTEM_CSS__") == 1 and template.count("__SYSTEM_JS__") == 1
template = template.replace("__SYSTEM_CSS__", (ROOT / "system.css").read_text(encoding="utf-8") + "\n" + (ROOT / "hierarchy.css").read_text(encoding="utf-8"))
system_js = "\n".join((ROOT / name).read_text(encoding="utf-8") for name in ("system-model.js", "system-ui.js", "hierarchy-ui.js"))
template = template.replace("__SYSTEM_JS__", system_js)
payload = json.dumps(data, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
html = template.replace("__DATA__", payload)
output = ROOT / "docs"
output.mkdir(exist_ok=True)
(output / "index.html").write_text(html, encoding="utf-8")
(output / "frontier.json").write_text(json.dumps(data, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
print(json.dumps({
    "directions": len(ids),
    "signals": sum(len(d["signals"]) for d in data["directions"]),
    "research_entries": sum(len(d["papers"]) for d in data["directions"]),
    "companies": len(company_ids),
    "html_bytes": len(html.encode("utf-8")),
    "gzip_bytes": len(gzip.compress(html.encode("utf-8"))),
    "output": str(output / "index.html")
}, ensure_ascii=False))
