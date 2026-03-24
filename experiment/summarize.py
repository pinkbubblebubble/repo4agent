#!/usr/bin/env python3
"""Generate experiment summary from raw_results.jsonl"""
import json
import datetime
from pathlib import Path
from collections import defaultdict

RESULTS_DIR = Path(__file__).parent / "results"
raw_file = RESULTS_DIR / "raw_results.jsonl"

runs = []
with open(raw_file) as f:
    for line in f:
        line = line.strip()
        if line:
            runs.append(json.loads(line))

def avg(vals):
    return sum(vals) / len(vals) if vals else 0.0

groups = defaultdict(list)
for r in runs:
    groups[(r["task_id"], r["repo_type"])].append(r)

task_names = {
    "task-a": "Add Feature: PATCH /users/:id/email",
    "task-b": "Fix Bug: Sessions not invalidated on delete",
    "task-c": "Add Middleware: Input validation on POST /users",
    "task-d": "Add Feature: GET /users list all users",
    "task-e": "Add Feature: PATCH /users/:id/password",
    "task-f": "Fix Bug: Sessions never expire",
    "task-g": "Add Feature: GET /users with email search",
    "task-h": "Add Feature: POST /auth/refresh session token",
    "task-i": "Add Middleware: Request logging",
    "task-j": "Add Feature: DELETE /users/:id soft delete",
}

seen = set()
task_ids = []
for r in runs:
    tid = r["task_id"]
    if tid not in seen:
        seen.add(tid)
        task_ids.append(tid)

def metrics(rs):
    if not rs:
        return {}
    return {
        "n": len(rs),
        "avg_total_calls":   round(avg([r["total"] for r in rs]), 1),
        "avg_explore_calls": round(avg([r["exploration"] for r in rs]), 1),
        "avg_read":          round(avg([r["read"] for r in rs]), 1),
        "avg_glob":          round(avg([r["glob"] for r in rs]), 1),
        "avg_grep":          round(avg([r["grep"] for r in rs]), 1),
        "avg_write":         round(avg([r["write"] for r in rs]), 1),
        "avg_edit":          round(avg([r["edit"] for r in rs]), 1),
        "avg_tokens":        round(avg([r["total_tokens"] for r in rs])),
        "avg_cost_usd":      round(avg([r["cost_usd"] for r in rs]), 4),
        "test_pass_rate_pct":   round(avg([1 if r["tests_passed"] else 0 for r in rs]) * 100, 1),
        "completion_rate_pct":  round(avg([1 if r["completed"] else 0 for r in rs]) * 100, 1),
    }

def pp(old, new):
    return round(new - old, 1) if (old is not None and new is not None) else None

all_trad = [r for r in runs if r["repo_type"] == "traditional"]
all_v1   = [r for r in runs if r["repo_type"] == "agent-native"]
all_v2   = [r for r in runs if r["repo_type"] == "agent-native-v2"]
all_v3   = [r for r in runs if r["repo_type"] == "agent-native-v3"]

tm = metrics(all_trad)
v1 = metrics(all_v1)
v2 = metrics(all_v2)
v3 = metrics(all_v3)

comparisons = []
for tid in task_ids:
    trad = groups.get((tid, "traditional"), [])
    n1   = groups.get((tid, "agent-native"), [])
    n2   = groups.get((tid, "agent-native-v2"), [])
    n3   = groups.get((tid, "agent-native-v3"), [])
    tm_t = metrics(trad)
    v1_t = metrics(n1)
    v2_t = metrics(n2)
    v3_t = metrics(n3)
    base = tm_t.get("test_pass_rate_pct")
    comparisons.append({
        "task_id":   tid,
        "task_name": task_names.get(tid, tid),
        "traditional":      tm_t,
        "agent_native_v1":  v1_t,
        "agent_native_v2":  v2_t,
        "agent_native_v3":  v3_t,
        "v1_pp": pp(base, v1_t.get("test_pass_rate_pct")) if v1_t else None,
        "v2_pp": pp(base, v2_t.get("test_pass_rate_pct")) if v2_t else None,
        "v3_pp": pp(base, v3_t.get("test_pass_rate_pct")) if v3_t else None,
    })

summary = {
    "generated_at": datetime.datetime.now().isoformat(),
    "total_runs": len(runs),
    "overall": {
        "traditional":     tm,
        "agent_native_v1": v1,
        "agent_native_v2": v2,
        "agent_native_v3": v3,
    },
    "task_comparisons": comparisons,
}
(RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

# ── Print ──────────────────────────────────────────────────────────────────────
W = 90
print("=" * W)
print("EXPERIMENT RESULTS — Traditional / V1 / V2 / V3")
print("=" * W)
print(f"Total runs: {len(runs)}  "
      f"({len(all_trad)} trad / {len(all_v1)} v1 / {len(all_v2)} v2 / {len(all_v3)} v3)\n")

def row(label, tv, v1v, v2v, v3v):
    print(f"  {label:<26} {str(tv):>10} {str(v1v):>10} {str(v2v):>10} {str(v3v):>10}")

print(f"  {'Metric':<26} {'Trad':>10} {'V1':>10} {'V2':>10} {'V3':>10}")
print("  " + "-" * 68)
row("Avg explore calls",  tm.get("avg_explore_calls","?"), v1.get("avg_explore_calls","?"), v2.get("avg_explore_calls","?"), v3.get("avg_explore_calls","?"))
row("  Read",             tm.get("avg_read","?"), v1.get("avg_read","?"), v2.get("avg_read","?"), v3.get("avg_read","?"))
row("Avg tokens",         tm.get("avg_tokens","?"), v1.get("avg_tokens","?"), v2.get("avg_tokens","?"), v3.get("avg_tokens","?"))
row("Test pass rate",
    f"{tm.get('test_pass_rate_pct','?')}%",
    f"{v1.get('test_pass_rate_pct','?')}%",
    f"{v2.get('test_pass_rate_pct','?')}%",
    f"{v3.get('test_pass_rate_pct','?')}%")

trad_rate = tm.get("test_pass_rate_pct", 0)
print(f"\n  vs Traditional:   V1={pp(trad_rate, v1.get('test_pass_rate_pct',0)):+.1f}pp  "
      f"V2={pp(trad_rate, v2.get('test_pass_rate_pct',0)):+.1f}pp  "
      f"V3={pp(trad_rate, v3.get('test_pass_rate_pct',0)):+.1f}pp")
if v1.get('test_pass_rate_pct') is not None:
    print(f"  V3 vs V1:         {pp(v1.get('test_pass_rate_pct',0), v3.get('test_pass_rate_pct',0)):+.1f}pp")

print("\nPER-TASK BREAKDOWN:")
for c in comparisons:
    t  = c["traditional"]
    n1 = c["agent_native_v1"]
    n2 = c["agent_native_v2"]
    n3 = c["agent_native_v3"]
    def r(m): return f"{m.get('test_pass_rate_pct','?')}%" if m else "n/a"
    def d(v): return f"{v:+.0f}pp" if v is not None else "n/a"
    print(f"\n  {c['task_name']}")
    print(f"    Pass rate: Trad={r(t):<7} V1={r(n1):<7} V2={r(n2):<7} V3={r(n3):<7}"
          f"  (Δ v1={d(c['v1_pp'])} v2={d(c['v2_pp'])} v3={d(c['v3_pp'])})")
    exp_vals = [str(m.get('avg_explore_calls','?')) for m in [t, n1, n2, n3]]
    print(f"    Explore:   Trad={exp_vals[0]:<7} V1={exp_vals[1]:<7} V2={exp_vals[2]:<7} V3={exp_vals[3]:<7}")

print(f"\nSummary JSON: {RESULTS_DIR}/summary.json")
