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
# Derive task_ids from actual data, preserving order
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
        "avg_total_calls": round(avg([r["total"] for r in rs]), 1),
        "avg_explore_calls": round(avg([r["exploration"] for r in rs]), 1),
        "avg_read": round(avg([r["read"] for r in rs]), 1),
        "avg_glob": round(avg([r["glob"] for r in rs]), 1),
        "avg_grep": round(avg([r["grep"] for r in rs]), 1),
        "avg_write": round(avg([r["write"] for r in rs]), 1),
        "avg_edit": round(avg([r["edit"] for r in rs]), 1),
        "avg_tokens": round(avg([r["total_tokens"] for r in rs])),
        "avg_cost_usd": round(avg([r["cost_usd"] for r in rs]), 4),
        "test_pass_rate_pct": round(avg([1 if r["tests_passed"] else 0 for r in rs]) * 100, 1),
        "completion_rate_pct": round(avg([1 if r["completed"] else 0 for r in rs]) * 100, 1),
    }

def pct_change(old, new):
    if old == 0:
        return 0.0
    return round((old - new) / old * 100, 1)

comparisons = []
for tid in task_ids:
    trad = groups.get((tid, "traditional"), [])
    native = groups.get((tid, "agent-native"), [])
    if not trad or not native:
        continue
    tm = metrics(trad)
    nm = metrics(native)
    comparisons.append({
        "task_id": tid,
        "task_name": task_names.get(tid, tid),
        "traditional": tm,
        "agent_native": nm,
        "tool_call_reduction_pct": pct_change(tm["avg_total_calls"], nm["avg_total_calls"]),
        "exploration_reduction_pct": pct_change(tm["avg_explore_calls"], nm["avg_explore_calls"]),
        "token_reduction_pct": pct_change(tm["avg_tokens"], nm["avg_tokens"]),
        "success_diff_pct": round(nm["test_pass_rate_pct"] - tm["test_pass_rate_pct"], 1),
    })

all_trad = [r for r in runs if r["repo_type"] == "traditional"]
all_native = [r for r in runs if r["repo_type"] == "agent-native"]
tm_all = metrics(all_trad)
nm_all = metrics(all_native)

tool_red = pct_change(tm_all.get("avg_total_calls", 0), nm_all.get("avg_total_calls", 0))
explore_red = pct_change(tm_all.get("avg_explore_calls", 0), nm_all.get("avg_explore_calls", 0))
token_red = pct_change(tm_all.get("avg_tokens", 0), nm_all.get("avg_tokens", 0))
success_diff = round(nm_all.get("test_pass_rate_pct", 0) - tm_all.get("test_pass_rate_pct", 0), 1)

summary = {
    "generated_at": datetime.datetime.now().isoformat(),
    "total_runs": len(runs),
    "experiment_config": {
        "model": "claude-haiku-4-5-20251001",
        "tools_disallowed": ["Bash"],
        "tools_measured": ["Read", "Glob", "Grep", "Write", "Edit"],
        "runs_per_task": 2,
        "tasks": list(task_names.values()),
    },
    "hypotheses": {
        "H1": {
            "description": "Total tool calls reduced by >= 30%",
            "threshold_pct": 30,
            "actual_pct": tool_red,
            "result": "SUPPORTED" if tool_red >= 30 else "NOT SUPPORTED",
        },
        "H2": {
            "description": "Exploration calls (Read+Glob+Grep) reduced by >= 50%",
            "threshold_pct": 50,
            "actual_pct": explore_red,
            "result": "SUPPORTED" if explore_red >= 50 else "NOT SUPPORTED",
        },
        "H3": {
            "description": "Test pass rate improvement >= 20 percentage points",
            "threshold_pct": 20,
            "actual_pct": success_diff,
            "result": "SUPPORTED" if success_diff >= 20 else "NOT SUPPORTED",
        },
    },
    "overall": {
        "traditional": tm_all,
        "agent_native": nm_all,
        "tool_call_reduction_pct": tool_red,
        "exploration_reduction_pct": explore_red,
        "token_reduction_pct": token_red,
        "success_rate_improvement_pct": success_diff,
    },
    "task_comparisons": comparisons,
}

(RESULTS_DIR / "summary.json").write_text(json.dumps(summary, indent=2))

# Print table
W = 65
print("=" * W)
print("EXPERIMENT RESULTS")
print("=" * W)
print(f"Total runs: {len(runs)}  ({len(all_trad)} traditional / {len(all_native)} agent-native)\n")

def row(label, tv, nv, delta=None):
    delta_str = f"{delta:+.1f}%" if delta is not None else ""
    print(f"  {label:<28} {str(tv):>10} {str(nv):>14} {delta_str:>10}")

print(f"  {'Metric':<28} {'Traditional':>10} {'Agent-Native':>14} {'Change':>10}")
print("  " + "-" * 63)
row("Total tool calls", tm_all.get("avg_total_calls","?"), nm_all.get("avg_total_calls","?"), tool_red if tool_red else None)
row("Exploration calls", tm_all.get("avg_explore_calls","?"), nm_all.get("avg_explore_calls","?"), explore_red if explore_red else None)
row("  Read", tm_all.get("avg_read","?"), nm_all.get("avg_read","?"))
row("  Glob", tm_all.get("avg_glob","?"), nm_all.get("avg_glob","?"))
row("  Grep", tm_all.get("avg_grep","?"), nm_all.get("avg_grep","?"))
row("Modification calls", tm_all.get("avg_write",0) + tm_all.get("avg_edit",0),
    nm_all.get("avg_write",0) + nm_all.get("avg_edit",0))
row("Tokens consumed", tm_all.get("avg_tokens","?"), nm_all.get("avg_tokens","?"), token_red if token_red else None)
row("Test pass rate", f"{tm_all.get('test_pass_rate_pct','?')}%", f"{nm_all.get('test_pass_rate_pct','?')}%",
    success_diff if success_diff else None)

print("\nPER-TASK BREAKDOWN:")
for c in comparisons:
    t = c["traditional"]
    n = c["agent_native"]
    symbol = "▲" if c["tool_call_reduction_pct"] > 0 else "▼"
    print(f"\n  {c['task_name']}")
    print(f"    Tools:    Trad={t.get('avg_total_calls','?')}  Native={n.get('avg_total_calls','?')}  ({c['tool_call_reduction_pct']}% reduction)")
    print(f"    Explore:  Trad={t.get('avg_explore_calls','?')}  Native={n.get('avg_explore_calls','?')}  ({c['exploration_reduction_pct']}% reduction)")
    print(f"    Tests:    Trad={t.get('test_pass_rate_pct','?')}%  Native={n.get('test_pass_rate_pct','?')}%  (Δ{c['success_diff_pct']:+.1f}pp)")

print("\nHYPOTHESIS RESULTS:")
for k, v in summary["hypotheses"].items():
    mark = "✓" if v["result"] == "SUPPORTED" else "✗"
    print(f"  {mark} {k}: {v['result']} (actual={v['actual_pct']}%, threshold≥{v['threshold_pct']}%)")

print(f"\nSummary JSON: {RESULTS_DIR}/summary.json")
