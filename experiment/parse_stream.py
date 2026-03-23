#!/usr/bin/env python3
"""Parse claude CLI stream-json output and emit structured metrics."""
import sys
import json
from collections import Counter

counts = Counter()
completed = False

for line in sys.stdin:
    line = line.strip()
    if not line:
        continue
    try:
        ev = json.loads(line)
        etype = ev.get("type")
        if etype == "assistant":
            for block in ev.get("message", {}).get("content", []):
                if block.get("type") == "tool_use":
                    counts[block["name"]] += 1
                if block.get("type") == "text" and "TASK_COMPLETE" in block.get("text", ""):
                    completed = True
        elif etype == "result":
            if "TASK_COMPLETE" in str(ev.get("result", "")):
                completed = True
            usage = ev.get("usage", {})
            counts["_input"] = (
                usage.get("input_tokens", 0)
                + usage.get("cache_read_input_tokens", 0)
                + usage.get("cache_creation_input_tokens", 0)
            )
            counts["_output"] = usage.get("output_tokens", 0)
            cost_raw = ev.get("total_cost_usd", 0)
            counts["_cost_usd"] = float(str(cost_raw)) if cost_raw else 0.0
    except Exception:
        pass

result = {
    "read": counts.get("Read", 0),
    "glob": counts.get("Glob", 0),
    "grep": counts.get("Grep", 0),
    "write": counts.get("Write", 0),
    "edit": counts.get("Edit", 0),
    "input_tokens": counts.get("_input", 0),
    "output_tokens": counts.get("_output", 0),
    "cost_usd": counts.get("_cost_usd", 0.0),
    "completed": completed,
}
result["total"] = result["read"] + result["glob"] + result["grep"] + result["write"] + result["edit"]
result["exploration"] = result["read"] + result["glob"] + result["grep"]
result["modification"] = result["write"] + result["edit"]
result["total_tokens"] = result["input_tokens"] + result["output_tokens"]

print(json.dumps(result))
