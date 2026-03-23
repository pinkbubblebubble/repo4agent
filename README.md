<div align="center">

# repo4agent

**Today's repos serve humans 👨‍💻. Tomorrow's users will be agents 🤖.**

<p align="center">
  <a href="https://pinkbubblebubble.github.io/repo4agent/"><img src="https://img.shields.io/badge/Live_Demo-View-ff6b35?style=for-the-badge" alt="Live Demo"></a>
  <a href="reports/report_en.md"><img src="https://img.shields.io/badge/Experiment_Report-Read-4a90d9?style=for-the-badge" alt="Report"></a>
  <a href="reports/analysis_en.md"><img src="https://img.shields.io/badge/Deep_Analysis-6_Mechanisms-8b5cf6?style=for-the-badge" alt="Analysis"></a>
  <a href="skill/init-agent-repo/SKILL.md"><img src="https://img.shields.io/badge/Claude_Skill-install-22c55e?style=for-the-badge" alt="Skill"></a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/experiment_runs-40-orange" alt="Runs">
  <img src="https://img.shields.io/badge/tasks-10-blue" alt="Tasks">
  <img src="https://img.shields.io/badge/pass_rate-55%%20→%2080%%20(%2B25pp)-brightgreen" alt="Pass Rate">
  <img src="https://img.shields.io/badge/model-claude--haiku--4--5-lightgrey" alt="Model">
  <img src="https://img.shields.io/badge/license-MIT-yellow" alt="License">
</p>

</div>

---

## 📖 Overview

Code repositories were designed for human navigation: layered folders, prose READMEs, monolithic controllers that mix all operations. AI agents that work in these repos read the wrong files, miss cross-module side effects, and commit to edits before understanding the full constraint space.

**repo4agent** is an empirical investigation into what happens when you redesign a repository for the agent that will work in it — not the human who wrote it.

We ran **40 controlled experiment runs** (2 runs × 10 tasks × 2 repo types) with claude-haiku-4-5-20251001 and measured the outcome:

| | Traditional | Agent-Native | Δ |
|:--|:-----------:|:------------:|:-:|
| Avg tool calls | 9.0 | 14.0 | +55.6% |
| Avg tokens | 189,518 | 300,779 | +58.7% |
| **Test pass rate** | **55%** | **80%** | **+25pp** |

On complex tasks with hidden constraints (auth refresh, soft delete): **0% → 100%**.

---

## 🔍 Why It Works

The counter-intuitive result is that agent-native repos use *more* tool calls — not fewer. The explanation has three layers:

**① Premature commit is the primary failure mode.** Traditional agents read 4–7 files, decide "that's enough," and start editing — usually the wrong files. Agent-native repos open with a mandatory pre-read instruction, forcing agents to read 13–19 files and build complete context before touching anything.

**② Side effects are the #1 unknown unknown.** `MANIFEST.yaml` declares what each operation writes, reads, and affects beyond its return value. Without this, an agent fixing a delete handler won't know it also needs to invalidate sessions. The agent-native agent knows — because the manifest says so explicitly.

**③ Structure is a silent instruction.** Domain-organized source (`src/user/`, `src/auth/`) with semantic file names cues the agent to create new isolated files rather than pile into an existing controller — 4× more new file creation in agent-native runs, fewer unintended side effects.

The token cost per **correct implementation**: 339K (traditional) vs 371K (agent-native). Only 9.3% more expensive, while producing 45% more correct answers.

---

## 🗂️ What Is an Agent-Native Repository?

An agent-native repo adds a **metadata layer** tuned for how AI agents actually read and act. The source code doesn't change. The structure does.

```
.agent/
  MANIFEST.yaml      ← Every capability: handler path, side_effects, known_issues, test coverage
  INVARIANTS.md      ← Non-obvious constraints + pre-annotated bugs with exact fix locations
  IMPACT_MAP.yaml    ← "Changing X requires also changing Y" — converts unknown unknowns to known
AGENT.md             ← Machine-optimized entry: "Read INVARIANTS.md before touching anything"
src/
  user/
    user.create.handler.ts    ← One file per operation (not one controller for everything)
    user.contract.ts
    user.test.ts
  auth/
    auth.login.handler.ts
    ...
```

Feature impact ranking from the experiment data:

| Feature | Impact |
|---------|--------|
| `INVARIANTS.md` with pre-annotated bugs (WHERE + FIX) | **Highest** |
| `MANIFEST.yaml` with `side_effects` + `known_issues` | **High** |
| `IMPACT_MAP.yaml` cross-module impact chains | **High** |
| Domain-organized source structure | **Medium** |
| Semantic file naming (`user.delete.handler.ts`) | **Medium** |
| `TASK_TEMPLATES/` per task type | **Low** |

---

## 📊 Results by Task

<table>
<tr>
<th>Task</th>
<th align="center">Traditional</th>
<th align="center">Agent-Native</th>
<th align="center">Δ</th>
</tr>
<tr><td>A: Add PATCH /email endpoint</td><td align="center">50%</td><td align="center">100%</td><td align="center">+50pp</td></tr>
<tr><td>B: Fix sessions not invalidated on delete</td><td align="center">50%</td><td align="center">100%</td><td align="center">+50pp</td></tr>
<tr><td>C: Input validation middleware</td><td align="center">0%</td><td align="center">0%</td><td align="center">—</td></tr>
<tr><td>D: GET /users list endpoint</td><td align="center">100%</td><td align="center">100%</td><td align="center">—</td></tr>
<tr><td>E: PATCH /password endpoint</td><td align="center">100%</td><td align="center">50%</td><td align="center"><b>−50pp</b></td></tr>
<tr><td>F: Session expiry fix</td><td align="center">100%</td><td align="center">100%</td><td align="center">—</td></tr>
<tr><td>G: GET /users?email search</td><td align="center">100%</td><td align="center">50%</td><td align="center"><b>−50pp</b></td></tr>
<tr><td><b>H: POST /auth/refresh</b></td><td align="center"><b>0%</b></td><td align="center"><b>100%</b></td><td align="center"><b>+100pp</b></td></tr>
<tr><td>I: Global request logging</td><td align="center">50%</td><td align="center">100%</td><td align="center">+50pp</td></tr>
<tr><td><b>J: Soft delete + session invalidation</b></td><td align="center"><b>0%</b></td><td align="center"><b>100%</b></td><td align="center"><b>+100pp</b></td></tr>
</table>

Tasks E and G are intentional counter-examples — agent-native *underperformed* on simple, well-scoped tasks. Over-reading metadata causes over-engineering. **Agent-native advantage scales with task hidden complexity.** This informed the key design rule: keep `INVARIANTS.md` sparse, document only non-obvious constraints.

---

## ⚡ Quick Start: `/init-agent-repo` Skill

The research produced a Claude Code skill that generates the agent-native metadata layer for any existing codebase automatically.

**Install**

```bash
mkdir -p ~/.claude/skills/init-agent-repo
cp skill/init-agent-repo/SKILL.md ~/.claude/skills/init-agent-repo/SKILL.md
```

Restart Claude Code, then run `/init-agent-repo` in any project.

**What it generates**

The skill explores your codebase — entry points, handlers, models, tests — and produces:

- `AGENT.md` with capability table, known issues, and mandatory pre-read instruction
- `.agent/MANIFEST.yaml` with side effects declared per operation
- `.agent/INVARIANTS.md` with active violations and non-obvious constraints
- `.agent/IMPACT_MAP.yaml` with cross-module impact chains

---

## 🔬 Reproducing the Experiment

<details>
<summary><b>Prerequisites & Setup</b></summary>

- [Claude Code](https://claude.ai/code) installed and authenticated
- Python 3.8+, Node.js 18+

```bash
cd traditional-repo && npm install && cd ..
cd agent-native-repo && npm install && cd ..
```

</details>

<details open>
<summary><b>Run</b></summary>

```bash
cd experiment

# Run all 10 tasks × 2 repos × 2 runs = 40 total
python3 run_experiment.py

# Aggregate results
python3 summarize.py
```

The experiment uses `--disallowedTools Bash` to force the agent to use discrete Read/Glob/Grep/Write/Edit — making tool call counts reproducible and meaningful.

Results append to `experiment/results/raw_results.jsonl`. Each line contains:

```
repo_type, task_id, run_number, read, glob, grep, write, edit,
input_tokens, output_tokens, total_tokens, cost_usd,
tests_passed, failed_test_count, duration_ms
```

</details>

---

## 📁 Repository Structure

```
repo4agent/
├── traditional-repo/        # Standard Express.js + TypeScript
│   └── src/controllers/     # Mixed operations per controller
│
├── agent-native-repo/       # Same API, restructured for agents
│   ├── .agent/              # MANIFEST.yaml, INVARIANTS.md, IMPACT_MAP.yaml
│   ├── AGENT.md
│   └── src/user/, src/auth/ # Domain-organized, one file per operation
│
├── experiment/
│   ├── run_experiment.py    # Experiment runner (claude CLI subprocess)
│   ├── parse_stream.py      # stream-json parser, counts tool calls
│   ├── summarize.py         # Aggregates → summary.json
│   └── results/             # 40 raw runs + aggregated data
│
├── reports/
│   ├── report_en.md / report_cn.md      # Full experiment report
│   └── analysis_en.md / analysis_cn.md  # Deep analysis: 6 mechanisms
│
├── skill/
│   └── init-agent-repo/SKILL.md        # Claude Code skill
│
└── docs/index.html          # Interactive demo (GitHub Pages)
```

---

## 📚 Further Reading

- [Full Experiment Report (EN)](reports/report_en.md) — methodology, per-task breakdown, hypothesis evaluations
- [Deep Analysis (EN)](reports/analysis_en.md) — 6 mechanisms: premature commit, missing edit, write ratio, token timing, information density, counter-examples
- [实验报告（中文）](reports/report_cn.md) · [深度分析（中文）](reports/analysis_cn.md)

---

## 📄 Citation

```
repo4agent: Agent-Native Repository Design
40-run empirical comparison, claude-haiku-4-5-20251001, 2026
https://github.com/pinkbubblebubble/repo4agent
```

---

<div align="center">

**repo4agent** — *Design your codebase for the agent that will work in it.*

<sub>40 experiment runs · 10 tasks · claude-haiku-4-5-20251001</sub>

</div>
