"""Evidence scenarios and append-only public forecast snapshots."""
import hashlib
import json
import math
from datetime import date, datetime, timezone

def probability(scores, prior=0.2, dependence=0.65):
    assert 0 < prior < 1 and len(scores) == 5
    assert all(-2 <= s <= 2 for s in scores)
    z = math.log(prior / (1-prior)) + dependence * math.log(2) * sum(scores)
    return 1 / (1 + math.exp(-z))

def estimate(scores, prior=0.2):
    center = probability(scores, prior)
    vals = [probability([max(-2, min(2, s+d)) for s in scores], p, dep)
            for p in (0.1, 0.35) for dep in (0.4, 0.8) for d in (-0.5, 0.5)]
    return {"p": center, "low": min(*vals, center), "high": max(*vals, center)}

def validate_hierarchy(hierarchy, direction_ids):
    assert hierarchy["schema"] == 1 and hierarchy["kind"] == "research_hypothesis"
    date.fromisoformat(hierarchy["reviewedAt"])
    themes, products = hierarchy["themes"], hierarchy["products"]
    assert len({t["id"] for t in themes}) == len(themes)
    assert len({p["id"] for p in products}) == len(products)
    primary = [d for t in themes for d in t["primaryDirections"]]
    assert len(primary) == len(set(primary)) and set(primary) == set(direction_ids), "One primary theme per technology"
    product_ids = {p["id"] for p in products}
    for t in themes:
        assert t["kind"] in ("生活与工作", "基础设施")
        assert t["question"] and t["change"] and t["evidence"] and t["next"]
        assert set(t["primaryDirections"]) <= set(t["directions"]) <= set(direction_ids)
        assert set(t["products"]) <= product_ids
        used = {d for p in products if p["id"] in t["products"] for d in p["directions"]}
        assert set(t["directions"]) == used
    assert {p for t in themes for p in t["products"]} == product_ids

def prepare(system, root, direction_ids, hierarchy=None):
    assert system["schema"] == 1 and system["model"]["id"] == "odds-v1"
    assert system["model"]["prior"] == .2 and system["model"]["dependence"] == .65
    assert abs(system["model"]["logLikelihoodPerPoint"] - math.log(2)) < 1e-12
    assert len(system["bets"]) == len(direction_ids)
    assert {b["direction"] for b in system["bets"]} == set(direction_ids)
    for b in system["bets"]:
        assert b["event"] and b["counter"] and b["trigger"] and len(b["evidence"]) == 5
        assert date.fromisoformat(b["createdAt"]) <= date.fromisoformat(system["asOf"])
        assert date.fromisoformat(b["deadline"]) > date.fromisoformat(b["createdAt"])
        estimate([e["score"] for e in b["evidence"]], b["prior"])
        if b["consumerEvent"]:
            assert len(b["consumerEvidence"]) == 5
            assert [e["score"] for e in b["consumerEvidence"]] == b["consumerScores"]
            estimate(b["consumerScores"], b["prior"])
        for e in b["evidence"] + (b.get("consumerEvidence") or []):
            assert e["note"] and e["kind"] == "人工证据判断"
            for s in e["sources"]:
                assert s["url"].startswith("https://")
                known_at = s.get("date") or s.get("availableAt")
                assert known_at and known_at <= system["asOf"], s
    for c in system["history"]:
        assert c["historicalProbability"] is None and c["outcome"] in (0, 1)
        for e in c["evidence"]:
            assert e["date"] <= c["forecastCutoff"], (c["id"], e)
            assert e["source"]["date"] <= c["forecastCutoff"]
        estimate(c["scores"], c["prior"])
    for s in system["sources"]:
        assert s["url"].startswith("https://") and s["scope"]
        assert s["availableAt"] <= system["asOf"]
    graph = system["graph"]
    node_ids = [n["id"] for n in graph["nodes"]]
    assert len(node_ids) == len(set(node_ids))
    edge_ids = [e["id"] for e in graph["edges"]]
    assert len(edge_ids) == len(set(edge_ids))
    for e in graph["edges"]:
        assert e["from"] in node_ids and e["to"] in node_ids
        assert e["kind"] in ("fact", "hypothesis")
        assert e["recordedAt"] <= system["asOf"] and e["validFrom"] <= system["asOf"]
        if e["kind"] == "fact":
            assert e["source"] and e["source"]["url"].startswith("https://")
    contract = {"model": system["model"], "bets": system["bets"],
                "milestones": system["milestones"], "graph": graph}
    if hierarchy is not None:
        validate_hierarchy(hierarchy, direction_ids)
        contract["hierarchy"] = hierarchy
    signature = hashlib.sha256(json.dumps(contract, ensure_ascii=False, sort_keys=True).encode()).hexdigest()
    archive = root / "snapshots"
    archive.mkdir(exist_ok=True)
    record_date = max(system["asOf"], hierarchy["reviewedAt"]) if hierarchy else system["asOf"]
    snapshot_id = record_date + "-" + signature[:12]
    path = archive / (snapshot_id + ".json")
    if not path.exists():
        forecasts = []
        for b in system["bets"]:
            for lens in ("industry", "consumer"):
                scores = [e["score"] for e in b["evidence"]] if lens == "industry" else b["consumerScores"]
                if scores is None:
                    continue
                forecasts.append({"id": b["id"]+":"+lens, "bet": b["id"], "lens": lens,
                    "event": b["event"] if lens == "industry" else b["consumerEvent"],
                    "deadline": b["deadline"], "prior": b["prior"], "scores": scores,
                    "evidence": b["evidence"] if lens == "industry" else b["consumerEvidence"],
                    "sources": b["sources"], "counter": b["counter"], "trigger": b["trigger"],
                    "resolutionPolicy": b["resolutionPolicy"],
                    **estimate(scores, b["prior"])})
        for b in system["milestones"]:
            forecasts.append({"id": b["id"], "bet": b["id"], "lens": "milestone", "event": b["event"],
                              "deadline": b["deadline"], "prior": b["prior"], "scores": b["scores"],
                              "evidence": b["evidence"], "resolutionPolicy": b["resolution"],
                              **estimate(b["scores"], b["prior"])})
        snapshot = {"id": snapshot_id, "recordedAt": record_date,
            "recordedTimestamp": datetime.now(timezone.utc).isoformat(),
            "signature": signature, "modelId": system["model"]["id"],
            "kind": "prospective", "forecasts": forecasts, "model": system["model"], "graph": graph}
        if hierarchy is not None:
            snapshot["hierarchy"] = hierarchy
        # Exclusive creation prevents an old record from being silently rewritten.
        with path.open("x", encoding="utf-8") as f:
            json.dump(snapshot, f, ensure_ascii=False, indent=2)
            f.write("\n")
    snapshots = [json.loads(p.read_text(encoding="utf-8")) for p in archive.glob("*.json")]
    system["snapshots"] = sorted(snapshots, key=lambda s: s["recordedTimestamp"])
    losses, baselines = [], []
    for result in system["settlement"]["results"]:
        snap = next(s for s in snapshots if s["id"] == result["snapshotId"])
        f = next(f for f in snap["forecasts"] if f["id"] == result["forecastId"])
        assert result["sourceUrl"].startswith("https://") and result["outcome"] in (0,1)
        assert result["resolvedAt"] <= system["asOf"]
        if result["outcome"] == 0:
            assert result["resolvedAt"] >= f["deadline"], "Premature negative settlement"
        losses.append((f["p"] - result["outcome"])**2)
        baselines.append((f["prior"] - result["outcome"])**2)
    system["validation"] = {"prospectiveResolved": len(losses),
        "brier": sum(losses)/len(losses) if losses else None,
        "baselineBrier": sum(baselines)/len(baselines) if baselines else None,
        "calibrated": False, "historicalCases": len(system["history"])}
    return system
